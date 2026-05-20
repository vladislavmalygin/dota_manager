import sqlite3
import os

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

_ACCENT = (0.35, 0.85, 1.00, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_RED    = (0.90, 0.28, 0.20, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_BG     = (0.10, 0.10, 0.12, 1)
_BG_MED = (0.14, 0.14, 0.18, 1)
_BG_HDR = (0.10, 0.22, 0.32, 1)

_REP_LEVELS = [
    (200, 'Икона'),
    (100, 'Легенда'),
    (50,  'Ветеран'),
    (25,  'Опытный'),
    (10,  'Известный'),
    (0,   'Новичок'),
]


class _BgBox(BoxLayout):
    def __init__(self, bg=_BG_MED, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*bg)
            self._r = Rectangle()
        self.bind(pos=self._u, size=self._u)

    def _u(self, *_):
        self._r.pos = self.pos
        self._r.size = self.size


def _lbl(text, color=_WHITE, height=30, halign='left', bold=False, font_size='13sp'):
    t = f'[b]{text}[/b]' if bold else text
    l = Label(text=t, markup=True, color=color,
              size_hint_y=None, height=height,
              halign=halign, valign='middle', font_size=font_size)
    l.bind(size=l.setter('text_size'))
    return l


def _hdr(text, color=_ACCENT):
    box = _BgBox(bg=_BG_HDR, orientation='horizontal',
                 size_hint_y=None, height=34, padding=(8, 0))
    box.add_widget(_lbl(text, color=color, height=34, bold=True))
    return box


def _row(left, right, color_r=_WHITE, bg=_BG_MED):
    box = _BgBox(bg=bg, orientation='horizontal',
                 size_hint_y=None, height=30, padding=(10, 0))
    box.add_widget(_lbl(left, color=_WHITE, height=30))
    box.add_widget(_lbl(right, color=color_r, height=30, halign='right'))
    return box


class ProfilePopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title      = ''
        self.size_hint  = (0.78, 0.92)
        self.auto_dismiss = True
        self._build(db_name)

    def _build(self, db_name):
        conn = sqlite3.connect(db_name)
        c    = conn.cursor()

        char = c.execute(
            "SELECT name, surname, nickname, portrait, COALESCE(reputation,0) "
            "FROM characters LIMIT 1"
        ).fetchone()

        team_row = c.execute(
            "SELECT id, name, COALESCE(country,''), COALESCE(rating,0), COALESCE(cohesion,0) "
            "FROM teams WHERE player='yes'"
        ).fetchone()

        save_row = c.execute("SELECT date FROM save WHERE id=1").fetchone()
        game_date = save_row[0] if save_row else '—'

        # ── tournament career ─────────────────────────────────
        my_tid = team_row[0] if team_row else None
        total_played = 0
        total_wins   = 0
        best_place   = 99
        total_prizes = 0
        t_history    = []   # [(name, date, place, prize)]

        if my_tid:
            for row in c.execute("""
                SELECT name, start_date,
                       place1,place2,place3,place4,place5,place6,place7,place8,
                       COALESCE(money1,0),COALESCE(money2,0),COALESCE(money3,0),
                       COALESCE(money4,0),COALESCE(money5,0),COALESCE(money6,0),
                       COALESCE(money7,0),COALESCE(money8,0)
                FROM tournaments WHERE place1 IS NOT NULL
                ORDER BY start_date DESC
            """).fetchall():
                tname, tdate = row[0], row[1]
                places = row[2:10]
                prizes = row[10:18]
                for i, pid in enumerate(places):
                    if pid == my_tid:
                        place = i + 1
                        prize = prizes[i] or 0
                        total_played += 1
                        total_prizes += prize
                        if place < best_place:
                            best_place = place
                        if place == 1:
                            total_wins += 1
                        t_history.append((tname, tdate, place, prize))
                        break

        # ── ranking ──────────────────────────────────────────
        all_ratings = c.execute(
            "SELECT COALESCE(rating,0), player FROM teams ORDER BY COALESCE(rating,0) DESC"
        ).fetchall()
        my_rank = next((i + 1 for i, (r, pl) in enumerate(all_ratings) if pl == 'yes'), '?')

        # ── goals ────────────────────────────────────────────
        goals_done  = (c.execute("SELECT COUNT(*) FROM season_goals WHERE completed=1").fetchone() or (0,))[0]
        goals_total = (c.execute("SELECT COUNT(*) FROM season_goals").fetchone() or (0,))[0]

        # ── rival & H2H ──────────────────────────────────────
        rival_data = None
        h2h_records = []
        if my_tid:
            rv = c.execute(
                "SELECT rival_team_id, COALESCE(rival_wins,0), COALESCE(rival_losses,0) "
                "FROM teams WHERE player='yes'"
            ).fetchone()
            rival_tid, rival_wins, rival_losses = (rv or (None, 0, 0))
            if rival_tid:
                rv_name = (c.execute("SELECT name FROM teams WHERE id=?", (rival_tid,)).fetchone() or ('?',))[0]
                rival_data = (rv_name, rival_wins, rival_losses)

            h2h_rows = c.execute("""
                SELECT t.name, h.wins, h.losses
                FROM h2h_records h JOIN teams t ON t.id=h.opponent_team_id
                WHERE (h.wins+h.losses) > 0
                ORDER BY (h.wins+h.losses) DESC LIMIT 8
            """).fetchall()
            h2h_records = [(n, w, l) for n, w, l in h2h_rows]

        # All AI team names for rival picker
        all_team_names = c.execute(
            "SELECT id, name FROM teams WHERE player!='yes' ORDER BY COALESCE(rating,0) DESC"
        ).fetchall()

        conn.close()

        # ── UI ───────────────────────────────────────────────
        root = _BgBox(bg=_BG, orientation='vertical', spacing=0)

        sv   = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=3, padding=(0, 4))
        grid.bind(minimum_height=grid.setter('height'))

        # Header
        grid.add_widget(_lbl('МОЙ ПРОФИЛЬ', color=_ACCENT, height=44,
                             bold=True, halign='center', font_size='17sp'))

        # Avatar
        if char:
            name, surname, nickname, portrait, reputation = char
            if portrait and os.path.exists(portrait):
                img = Image(source=portrait, size_hint_y=None, height=120)
                grid.add_widget(img)
            grid.add_widget(_lbl(f"{name} '{nickname}' {surname}",
                                 color=_WHITE, height=38, halign='center', font_size='15sp'))
            rep_label = next((l for th, l in _REP_LEVELS if reputation >= th), 'Новичок')
            grid.add_widget(_lbl(
                f'Репутация: {reputation} пт  [{rep_label}]',
                color=_GOLD, height=32, halign='center',
            ))
        else:
            grid.add_widget(_lbl('Менеджер', color=_WHITE, height=38,
                                 halign='center', font_size='15sp'))
            reputation = 0

        # Team overview
        grid.add_widget(_hdr('КОМАНДА'))
        if team_row:
            _, tname, country, rating, cohesion = team_row
            grid.add_widget(_row('Название', tname))
            grid.add_widget(_row('Страна', country or '—'))
            grid.add_widget(_row('Рейтинг', f'{int(rating)} pts  (#{my_rank})', color_r=_ACCENT))
            grid.add_widget(_row('Сыгранность', f'{cohesion}/100'))
        grid.add_widget(_row('Дата', game_date, color_r=_DIM))

        # Career stats
        grid.add_widget(_hdr('КАРЬЕРА МЕНЕДЖЕРА'))
        grid.add_widget(_row('Турниров сыграно', str(total_played)))
        grid.add_widget(_row(
            'Победы (1-е место)',
            str(total_wins),
            color_r=_GOLD if total_wins > 0 else _DIM,
        ))
        if best_place < 99:
            medals = {1: '[1] 1-е', 2: '[2] 2-е', 3: '[3] 3-е'}
            bp_str = medals.get(best_place, f'{best_place}-е')
            grid.add_widget(_row('Лучший результат', bp_str,
                                 color_r=_GOLD if best_place == 1 else _WHITE))
        else:
            grid.add_widget(_row('Лучший результат', '—', color_r=_DIM))
        grid.add_widget(_row(
            'Призовые всего',
            f'${total_prizes:,}' if total_prizes else '—',
            color_r=_GREEN if total_prizes > 0 else _DIM,
        ))
        grid.add_widget(_row(
            'Целей выполнено',
            f'{goals_done} / {goals_total}' if goals_total else '—',
            color_r=_GREEN if goals_done > 0 else _DIM,
        ))

        # ── Trophy room ───────────────────────────────────────────
        golds   = [(n, d) for n, d, p, _ in t_history if p == 1]
        silvers = [(n, d) for n, d, p, _ in t_history if p == 2]
        bronzes = [(n, d) for n, d, p, _ in t_history if p == 3]
        if golds or silvers or bronzes:
            grid.add_widget(_hdr('КУБКИ И ТРОФЕИ'))
            trophy_row = BoxLayout(size_hint_y=None, height=52, spacing=6, padding=(8, 4))
            for trophy_list, symbol, color in [
                (golds,   '🏆', _GOLD),
                (silvers, '🥈', _SILVER),
                (bronzes, '🥉', _BRONZE),
            ]:
                if trophy_list:
                    lbl = Label(
                        text=f'{symbol}×{len(trophy_list)}',
                        color=color, font_size='22sp',
                        size_hint=(None, 1), width=70,
                        halign='center', valign='middle',
                    )
                    trophy_row.add_widget(lbl)
            grid.add_widget(trophy_row)
            if golds:
                for tname, tdate in golds[:3]:
                    grid.add_widget(_row(f'🏆 {tname[:30]}', tdate[:7] if tdate else '—',
                                         color_r=_GOLD))

        # Recent tournament results
        if t_history:
            grid.add_widget(_hdr('ПОСЛЕДНИЕ ТУРНИРЫ'))
            _MEDALS = {1: '[1]', 2: '[2]', 3: '[3]'}
            for tname, tdate, place, prize in t_history[:8]:
                medal = _MEDALS.get(place, f'{place}.')
                prize_str = f'  +${prize:,}' if prize else ''
                pc = _GOLD if place == 1 else (_WHITE if place <= 4 else _DIM)
                grid.add_widget(_row(
                    f'{medal}  {tname[:30]}',
                    f'{tdate[:7]}{prize_str}',
                    color_r=pc,
                ))

        # ── Rival section ─────────────────────────────────────
        grid.add_widget(_hdr('ГЛАВНЫЙ СОПЕРНИК'))
        if rival_data:
            rv_name, rv_w, rv_l = rival_data
            rv_clr = _GREEN if rv_w >= rv_l else (_RED if rv_l > rv_w else _WHITE)
            grid.add_widget(_row('Соперник', rv_name, color_r=_GOLD))
            grid.add_widget(_row('Счёт', f'W {rv_w}  —  L {rv_l}', color_r=rv_clr))
        else:
            grid.add_widget(_lbl('  Соперник не выбран. Нажмите кнопку ниже.',
                                 color=_DIM, height=28))

        # Rival picker button
        pick_box = BoxLayout(size_hint_y=None, height=40)
        pick_btn = Button(
            text='Выбрать/сменить соперника',
            background_color=(0.18, 0.38, 0.60, 1), background_normal='',
            font_size='13sp',
        )

        def _pick_rival(_):
            from kivy.uix.popup import Popup
            from kivy.uix.scrollview import ScrollView
            p = Popup(title='Выбрать соперника', size_hint=(0.55, 0.75))
            sv2 = ScrollView()
            gl = GridLayout(cols=1, size_hint_y=None, spacing=2)
            gl.bind(minimum_height=gl.setter('height'))
            for tid, tname in all_team_names:
                b = Button(
                    text=tname.strip(), size_hint_y=None, height=40,
                    background_color=(0.20, 0.28, 0.40, 1), background_normal='',
                )
                def _set(_, _tid=tid):
                    con2 = sqlite3.connect(db_name)
                    con2.execute("UPDATE teams SET rival_team_id=? WHERE player='yes'", (_tid,))
                    con2.commit(); con2.close()
                    p.dismiss()
                    self._build(db_name)
                b.bind(on_press=_set)
                gl.add_widget(b)
            sv2.add_widget(gl)
            p.content = sv2
            p.open()

        pick_btn.bind(on_press=_pick_rival)
        pick_box.add_widget(pick_btn)
        grid.add_widget(pick_box)

        # ── H2H records ───────────────────────────────────────
        if h2h_records:
            grid.add_widget(_hdr('СТАТИСТИКА H2H'))
            for opp_name, w, l in h2h_records:
                clr = _GREEN if w > l else (_RED if l > w else _WHITE)
                grid.add_widget(_row(opp_name.strip()[:28], f'{w}W — {l}L', color_r=clr))

        sv.add_widget(grid)
        root.add_widget(sv)

        close = Button(
            text='Закрыть', size_hint_y=None, height=46,
            background_color=(0.55, 0.18, 0.18, 1), background_normal='',
        )
        close.bind(on_press=self.dismiss)
        root.add_widget(close)

        self.content = root


def show_profile_popup(db_name):
    ProfilePopup(db_name=db_name).open()
