import sqlite3
import random

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from logic.dota.match_data import get_match_data
from logic.dota.game import dota_simulation_logged

_XP_WIN  = 0.8
_XP_LOSS = 0.3

_ACCENT = (0.35, 0.85, 1.00, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_RED    = (0.90, 0.28, 0.20, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_BG     = (0.10, 0.10, 0.12, 1)
_BG_MED = (0.15, 0.15, 0.18, 1)
_BG_HDR = (0.10, 0.22, 0.32, 1)


class _BgBox(BoxLayout):
    def __init__(self, bg=_BG_MED, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*bg)
            self._r = Rectangle()
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._r.pos  = self.pos
        self._r.size = self.size


def _lbl(text, color=_WHITE, height=30, halign='left', bold=False, font_size='13sp'):
    t = f'[b]{text}[/b]' if bold else text
    l = Label(text=t, markup=True, color=color,
              size_hint_y=None, height=height,
              halign=halign, valign='middle', font_size=font_size)
    l.bind(size=l.setter('text_size'))
    return l


def _award_xp(db_name, team_name, xp_amount):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        "SELECT carry,mid,offlane,partial_support,full_support "
        "FROM teams WHERE name=?", (team_name,)
    )
    row = c.fetchone()
    if row:
        for pid in row:
            if pid:
                c.execute(
                    "UPDATE players SET train_xp=COALESCE(train_xp,0)+? WHERE id=?",
                    (xp_amount, pid)
                )
    conn.commit()
    conn.close()


def _flush_scrim_xp(db_name, team_name):
    """Apply any accumulated train_xp >= 1.0 immediately after a scrimmage.
    Uses train_priority if set, otherwise weakest skill."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        "SELECT carry,mid,offlane,partial_support,full_support FROM teams WHERE name=?",
        (team_name,)
    )
    row = c.fetchone()
    if not row:
        conn.close(); return
    for pid in row:
        if not pid:
            continue
        c.execute(
            "SELECT train_priority, COALESCE(train_xp,0), "
            "micro_skills, macro_skills, soft_skills, "
            "COALESCE(skill_cap,300), COALESCE(learning_rate,5), "
            "COALESCE(micro_cap,100), COALESCE(macro_cap,100), COALESCE(soft_cap,100) "
            "FROM players WHERE id=?", (pid,)
        )
        p = c.fetchone()
        if not p:
            continue
        priority, xp, micro, macro, soft, cap, lr, mc, xc, sc = p
        if xp < 1.0:
            continue
        micro = micro or 0; macro = macro or 0; soft = soft or 0
        # Pick skill to train
        if not priority:
            candidates = [
                ('micro_skills', micro, mc),
                ('macro_skills', macro, xc),
                ('soft_skills',  soft,  sc),
            ]
            candidates = [(col, v, cv) for col, v, cv in candidates if v < cv]
            if not candidates:
                continue
            priority = min(candidates, key=lambda x: x[1])[0]
        col_cap = {'micro_skills': mc, 'macro_skills': xc, 'soft_skills': sc}.get(priority, 100)
        cur_val = {'micro_skills': micro, 'macro_skills': macro, 'soft_skills': soft}.get(priority, 0)
        total   = micro + macro + soft
        gained  = 0
        lr_f    = lr / 5.0
        while (xp >= 1.0 / max(0.1, lr_f)
               and total + gained < cap
               and cur_val + gained < col_cap):
            xp -= 1.0 / max(0.1, lr_f)
            gained += 1
        if gained:
            c.execute(
                f"UPDATE players SET {priority}={priority}+?, train_xp=? WHERE id=?",
                (gained, max(0.0, xp), pid)
            )
        else:
            c.execute("UPDATE players SET train_xp=? WHERE id=?", (xp, pid))
    conn.commit()
    conn.close()


def _boost_morale(db_name, team_name, delta):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        "SELECT carry,mid,offlane,partial_support,full_support "
        "FROM teams WHERE name=?", (team_name,)
    )
    row = c.fetchone()
    if row:
        for pid in row:
            if pid:
                c.execute(
                    "UPDATE players SET morale=MAX(1,MIN(10,COALESCE(morale,5)+?)) "
                    "WHERE id=?", (delta, pid)
                )
    conn.commit()
    conn.close()


class ScrimmagePopup(Popup):

    def __init__(self, db_name, **kw):
        super().__init__(**kw)
        self.title      = 'Кланвары'
        self.size_hint  = (0.72, 0.85)
        self._db        = db_name
        self._build()

    def _build(self):
        conn = sqlite3.connect(self._db)
        c    = conn.cursor()
        c.execute("SELECT name, COALESCE(budget,0) FROM teams WHERE player='yes'")
        row = c.fetchone()
        if not row:
            conn.close()
            self.content = Label(text='Команда не найдена')
            return
        self._my_team, budget = row

        c.execute(
            "SELECT name, COALESCE(rating,0) FROM teams WHERE player!='yes' "
            "ORDER BY RANDOM() LIMIT 20"
        )
        opponents = c.fetchall()
        conn.close()

        root = BoxLayout(orientation='vertical', spacing=4, padding=6)

        # Check daily limit
        try:
            gd = c.execute("SELECT date FROM save WHERE id=1").fetchone()
            self._game_date_str = gd[0] if gd else None
            last_scrim = c.execute(
                "SELECT last_scrimmage_date FROM teams WHERE player='yes'"
            ).fetchone()
            self._already_played_today = (
                last_scrim and last_scrim[0] == self._game_date_str
            )
        except Exception:
            self._game_date_str = None
            self._already_played_today = False

        if self._already_played_today:
            root.add_widget(_lbl(
                'X  Уже сыграли клан вар сегодня. Завтра можно снова.',
                color=(1.0, 0.4, 0.3, 1), height=34, halign='center',
            ))
        else:
            root.add_widget(_lbl(
                'Кланвары: 1 раз в день. +1 сыгранность всегда. Победа: +0.8 XP, +1 мораль.',
                color=_ACCENT, height=34, halign='center',
            ))
        root.add_widget(_lbl(
            'Поражение: +0.3 XP. Сыгранность не растёт при активном конфликте в команде.',
            color=_DIM, height=30, halign='center', font_size='13sp',
        ))

        sv   = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))

        for opp_name, opp_rating in opponents:
            row_box = _BgBox(bg=_BG_MED, orientation='horizontal',
                             size_hint_y=None, height=44, padding=(8, 0), spacing=6)
            row_box.add_widget(_lbl(
                f'{opp_name}  (рейтинг {int(opp_rating)})',
                height=44,
            ))
            btn = Button(
                text='> Сыграть', size_hint=(None, None), width=110, height=36,
                background_color=(0.18, 0.50, 0.22, 1) if not self._already_played_today
                                 else (0.3, 0.3, 0.3, 1),
                background_normal='', font_size='14sp',
                disabled=self._already_played_today,
            )
            btn.bind(on_press=lambda _, opp=opp_name: self._play(opp))
            row_box.add_widget(btn)
            grid.add_widget(row_box)

        sv.add_widget(grid)
        root.add_widget(sv)
        root.add_widget(Button(
            text='Отмена', size_hint_y=None, height=46,
            background_color=(0.55, 0.18, 0.18, 1), background_normal='',
            on_press=self.dismiss,
        ))
        self.content = root

    def _play(self, opponent):
        from ingame_interface.tournaments import MatchLogPopup

        pass  # free, no budget check needed

        skills = get_match_data(self._my_team, opponent, self._db)
        if not skills:
            return

        winner, lines, snaps, stats = dota_simulation_logged(
            self._my_team, opponent, skills
        )
        won = (winner == self._my_team)

        # XP + morale + cohesion + daily limit
        _award_xp(self._db, self._my_team, _XP_WIN if won else _XP_LOSS)
        _flush_scrim_xp(self._db, self._my_team)
        if won:
            _boost_morale(self._db, self._my_team, 1)
        try:
            conn3 = sqlite3.connect(self._db)
            # +1 cohesion every clan war (not just wins), but skip if conflict active
            conflict = conn3.execute(
                "SELECT conflict_targets FROM teams WHERE name=?", (self._my_team,)
            ).fetchone()
            has_conflict = conflict and conflict[0]
            if not has_conflict:
                conn3.execute(
                    "UPDATE teams SET cohesion=MIN(100,COALESCE(cohesion,0)+3) WHERE name=?",
                    (self._my_team,))
            conn3.commit()
            conn3.close()
        except Exception:
            pass
        # record date
        if self._game_date_str:
            try:
                conn4 = sqlite3.connect(self._db)
                conn4.execute(
                    "UPDATE teams SET last_scrimmage_date=? WHERE player='yes'",
                    (self._game_date_str,))
                conn4.commit()
                conn4.close()
            except Exception:
                pass

        logo_map = {}
        try:
            conn2 = sqlite3.connect(self._db)
            for name, logo in conn2.execute("SELECT name, logo FROM teams").fetchall():
                logo_map[name.strip()] = logo
            conn2.close()
        except Exception:
            pass

        popup = MatchLogPopup(
            team1=self._my_team, team2=opponent,
            winner=winner, log_lines=lines, snapshots=snaps,
            on_close=self._after_match,
            t1_logo=logo_map.get(self._my_team),
            t2_logo=logo_map.get(opponent),
            best_of=1,
            final_score=(1, 0) if won else (0, 1),
            match_stats=stats,
        )
        popup.size_hint = (0.99, 0.99)
        popup.open()

    def _after_match(self):
        self.dismiss()


def show_scrimmage_popup(db_name):
    ScrimmagePopup(db_name=db_name).open()
