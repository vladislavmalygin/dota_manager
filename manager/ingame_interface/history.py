import json
import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

_GOLD   = (1.00, 0.85, 0.25, 1)
_SILVER = (0.80, 0.80, 0.80, 1)
_BRONZE = (0.78, 0.52, 0.25, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_ACCENT = (0.35, 0.85, 1.00, 1)
_WIN    = (0.25, 0.90, 0.42, 1)
_LOSE   = (0.95, 0.30, 0.22, 1)
_BG     = (0.07, 0.09, 0.13, 1)
_BG_ROW = (0.10, 0.13, 0.18, 1)


def _lbl(text, sw=1.0, color=_WHITE, bold=False, height=36, halign='center'):
    t = f'[b]{text}[/b]' if bold else text
    lbl = Label(text=t, markup=True, size_hint_x=sw, size_hint_y=None, height=height,
                color=color, halign=halign, valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _place_color(place):
    if place == 1:   return _GOLD
    if place == 2:   return _SILVER
    if place <= 4:   return _BRONZE
    if place <= 8:   return _WHITE
    return _DIM


def _place_medal(place):
    if place == 1:  return '[1] 1'
    if place == 2:  return '[2] 2'
    if place == 3:  return '[3] 3'
    return str(place)


def _sec_header(text):
    lbl = Label(
        text=f'[b]{text}[/b]', markup=True,
        size_hint_y=None, height=32,
        color=_ACCENT, halign='left', valign='middle', font_size='13sp',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


class MatchReplayPopup(Popup):
    """Scrollable log for a past match."""

    def __init__(self, team1, team2, winner, score_t1, score_t2,
                 best_of, tournament, stage, log_lines, **kw):
        super().__init__(**kw)
        self.title = ''
        self.size_hint = (0.90, 0.92)
        self.background = ''
        self.background_color = _BG
        self.separator_color = (0.15, 0.30, 0.50, 1)

        root = BoxLayout(orientation='vertical', spacing=4, padding=(6, 6))

        # Header
        w_color = _WIN if winner == team1 else _LOSE
        l_color = _LOSE if winner == team1 else _WIN
        score_txt = (
            f'[b][color=#{_hex(w_color)}]{team1}[/color]  '
            f'{score_t1} — {score_t2}  '
            f'[color=#{_hex(l_color)}]{team2}[/color][/b]'
        )
        hdr_lbl = Label(
            text=score_txt, markup=True,
            size_hint_y=None, height=40,
            color=_WHITE, halign='center', valign='middle', font_size='15sp',
        )
        hdr_lbl.bind(size=hdr_lbl.setter('text_size'))
        root.add_widget(hdr_lbl)

        meta_lbl = Label(
            text=f'{tournament}  ·  {stage}  ·  BO{best_of}',
            size_hint_y=None, height=22,
            color=_DIM, halign='center', valign='middle', font_size='12sp',
        )
        meta_lbl.bind(size=meta_lbl.setter('text_size'))
        root.add_widget(meta_lbl)

        # Log
        scroll = ScrollView(size_hint=(1, 1))
        log_grid = GridLayout(cols=1, size_hint_y=None, spacing=1)
        log_grid.bind(minimum_height=log_grid.setter('height'))

        for line in log_lines:
            lbl = Label(
                text=line, markup=True,
                size_hint_y=None, height=22,
                color=_WHITE, halign='left', valign='middle',
                font_size='12sp',
            )
            lbl.bind(size=lbl.setter('text_size'))
            log_grid.add_widget(lbl)

        scroll.add_widget(log_grid)
        root.add_widget(scroll)

        close = Button(
            text='Закрыть', size_hint_y=None, height=44,
            background_color=(0.55, 0.18, 0.18, 1), background_normal='',
        )
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root


def _hex(rgba):
    r, g, b = int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255)
    return f'{r:02x}{g:02x}{b:02x}'


class HistoryPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.88, 0.92)
        self.background = ''
        self.background_color = _BG
        self.separator_color = (0.15, 0.30, 0.50, 1)

        layout = BoxLayout(orientation='vertical', padding=6, spacing=6)
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))

        self._build(db_name, grid)

        scroll.add_widget(grid)
        layout.add_widget(scroll)
        close = Button(text='Закрыть', size_hint_y=None, height=50,
                       background_color=(0.8, 0.2, 0.2, 1), background_normal='')
        close.bind(on_press=self.dismiss)
        layout.add_widget(close)
        self.content = layout

    def _build(self, db_name, grid):
        conn = sqlite3.connect(db_name)
        c = conn.cursor()

        row = c.execute("SELECT id, name FROM teams WHERE player='yes'").fetchone()
        if not row:
            grid.add_widget(_lbl('Команда не найдена.'))
            conn.close()
            return
        team_id, team_name = row[0], row[1].strip()

        # ── Tournament results ────────────────────────────────────
        grid.add_widget(_sec_header(f'История турниров: {team_name}'))

        hrow = BoxLayout(size_hint_y=None, height=26)
        for txt, sw in [('Турнир', 0.45), ('Дата', 0.18), ('Место', 0.17), ('Приз', 0.20)]:
            hrow.add_widget(_lbl(f'[b]{txt}[/b]', sw=sw, color=_ACCENT, bold=False, height=26))
        grid.add_widget(hrow)

        c.execute("""
            SELECT name, start_date,
                   place1,  place2,  place3,  place4,
                   place5,  place6,  place7,  place8,
                   place9,  place10, place11, place12,
                   place13, place14, place15, place16,
                   prizepool
            FROM tournaments
            WHERE place1 IS NOT NULL
            ORDER BY start_date DESC
        """)
        results = []
        for r in c.fetchall():
            t_name, t_date = r[0], r[1]
            places = r[2:18]
            prize  = r[18] or 0
            for i, p in enumerate(places, 1):
                if p == team_id:
                    results.append((t_name, t_date, i, prize))
                    break

        # Re-fetch with tournament IDs for bracket links
        c.execute("""
            SELECT t.id, t.name, t.start_date,
                   place1,place2,place3,place4,place5,place6,place7,place8,
                   COALESCE(prizepool,0)
            FROM tournaments t WHERE place1 IS NOT NULL
            ORDER BY t.start_date DESC
        """)
        t_results_with_id = []
        for row in c.fetchall():
            tid_r, tname_r, tdate_r = row[0], row[1], row[2]
            places = row[3:11]
            prize_r = row[11]
            for i, p in enumerate(places, 1):
                if p == team_id:
                    t_results_with_id.append((tid_r, tname_r, tdate_r, i, prize_r))
                    break

        if not results:
            grid.add_widget(_lbl('Ещё нет сыгранных турниров.', color=_DIM))
        else:
            for t_name, t_date, place, prize in results:
                color = _place_color(place)
                # Find tournament id for bracket link
                t_id_for_bracket = next(
                    (tid_r for tid_r, tname_r, _, pl_r, _ in t_results_with_id
                     if tname_r == t_name and pl_r == place), None
                )

                r = BoxLayout(size_hint_y=None, height=34)
                r.add_widget(_lbl(t_name, sw=0.40, color=color, height=34, halign='left'))
                r.add_widget(_lbl(t_date[:7] if t_date else '—', sw=0.15, color=color, height=34))
                r.add_widget(_lbl(_place_medal(place), sw=0.15, color=color, height=34))
                prize_txt = f'${prize:,}' if prize else '—'
                r.add_widget(_lbl(prize_txt, sw=0.17, color=color, height=34))
                if t_id_for_bracket:
                    bkt_btn = Button(
                        text='Сетка', size_hint_x=None, width=55, height=30,
                        background_color=(0.18, 0.30, 0.55, 1), background_normal='',
                        font_size='12sp',
                    )
                    bkt_btn.bind(on_press=lambda _, _tid=t_id_for_bracket:
                                 show_bracket_popup(db_name, _tid))
                    r.add_widget(bkt_btn)
                grid.add_widget(r)

            wins        = sum(1 for _, _, p, _ in results if p == 1)
            top4        = sum(1 for _, _, p, _ in results if p <= 4)
            total_prize = sum(pr for _, _, _, pr in results)
            grid.add_widget(_lbl(
                f'Турниров: {len(results)}  |  Побед: {wins}  |  Топ-4: {top4}  |  '
                f'Призовых: ${total_prize:,}',
                color=_ACCENT, height=30,
            ))

        # ── Match replays ─────────────────────────────────────────
        matches = []
        try:
            matches = c.execute("""
                SELECT id, played_date, tournament, stage,
                       team1, team2, winner, score_t1, score_t2, best_of, log_json
                FROM match_history
                ORDER BY id DESC
                LIMIT 50
            """).fetchall()
        except Exception:
            pass

        conn.close()

        if not matches:
            return

        # spacer
        grid.add_widget(_lbl('', height=12))
        grid.add_widget(_sec_header('История матчей'))

        hrow2 = BoxLayout(size_hint_y=None, height=26)
        for txt, sw in [('Дата', 0.14), ('Турнир', 0.28), ('Этап', 0.18),
                        ('Матч', 0.28), ('Счёт', 0.12)]:
            hrow2.add_widget(_lbl(f'[b]{txt}[/b]', sw=sw, color=_ACCENT, bold=False, height=26))
        grid.add_widget(hrow2)

        for (mid, date, tourn, stage, t1, t2, winner, s1, s2, bo, log_json) in matches:
            won = (winner == team_name)
            result_color = _WIN if won else _LOSE

            r = BoxLayout(size_hint_y=None, height=34, spacing=2)
            r.add_widget(_lbl(date[:10] if date else '—', sw=0.14, color=_DIM, height=34))
            r.add_widget(_lbl(tourn or '—', sw=0.28, color=_WHITE, height=34, halign='left'))
            r.add_widget(_lbl(stage or '—', sw=0.18, color=_DIM, height=34))
            match_txt = f'[b]{t1}[/b] vs {t2}'
            r.add_widget(_lbl(match_txt, sw=0.28, color=result_color, height=34, halign='left'))
            r.add_widget(_lbl(f'{s1}:{s2}', sw=0.12, color=result_color, height=34))

            replay_btn = Button(
                text='>', size_hint=(None, None), width=36, height=30,
                background_color=(0.12, 0.30, 0.55, 1), background_normal='',
                font_size='14sp',
            )
            _log = log_json
            _t1, _t2, _w, _s1, _s2, _bo = t1, t2, winner, s1, s2, bo
            _tourn, _stage = tourn, stage

            def _open(_, log=_log, team1=_t1, team2=_t2, w=_w, sc1=_s1,
                      sc2=_s2, best=_bo, tr=_tourn, st=_stage):
                try:
                    lines = json.loads(log) if log else []
                except Exception:
                    lines = []
                MatchReplayPopup(
                    team1=team1, team2=team2, winner=w,
                    score_t1=sc1, score_t2=sc2, best_of=best,
                    tournament=tr, stage=st, log_lines=lines,
                ).open()

            replay_btn.bind(on_press=_open)
            r.add_widget(replay_btn)
            grid.add_widget(r)


def show_history_popup(db_name):
    HistoryPopup(db_name=db_name).open()


class TransferHistoryPopup(Popup):
    """Season transfer feed — all transfers from inbox messages."""

    def __init__(self, db_name, **kw):
        super().__init__(**kw)
        self.title = 'История трансферов'
        self.size_hint = (0.80, 0.88)
        self.background_color = _BG
        self._build(db_name)

    def _build(self, db_name):
        conn = sqlite3.connect(db_name)
        c = conn.cursor()

        # Get game date for year filter
        gd = c.execute("SELECT date FROM save WHERE id=1").fetchone()
        year = gd[0][:4] if gd else '2024'
        my_team_row = c.execute("SELECT name FROM teams WHERE player='yes'").fetchone()
        my_team = my_team_row[0].strip() if my_team_row else ''

        # All transfer messages this year
        rows = c.execute("""
            SELECT text, date FROM messages
            WHERE author LIKE '%Трансфер%'
              AND (date >= ? OR date = 'now')
            ORDER BY id DESC LIMIT 100
        """, (f'{year}-01-01',)).fetchall()
        conn.close()

        root = BoxLayout(orientation='vertical', padding=8, spacing=6)

        sv = ScrollView(size_hint=(1, 1))
        gl = GridLayout(cols=1, size_hint_y=None, spacing=3)
        gl.bind(minimum_height=gl.setter('height'))

        if not rows:
            gl.add_widget(_lbl('Трансферов ещё не было в этом сезоне.', color=_DIM))
        else:
            for text, date in rows:
                involves_my_team = my_team.lower() in text.lower() if my_team else False
                color = _WIN if involves_my_team else _WHITE
                row_box = BoxLayout(size_hint_y=None, height=36, spacing=4)
                date_lbl = _lbl(date[:10] if date and date != 'now' else '—',
                                sw=0.14, color=_DIM, height=36)
                row_box.add_widget(date_lbl)
                txt_lbl = _lbl(text[:80], sw=0.86, color=color, height=36, halign='left')
                row_box.add_widget(txt_lbl)
                gl.add_widget(row_box)

        sv.add_widget(gl)
        root.add_widget(sv)

        close = Button(text='Закрыть', size_hint_y=None, height=44,
                       background_color=(0.55, 0.18, 0.18, 1), background_normal='')
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root


def show_transfer_history_popup(db_name):
    TransferHistoryPopup(db_name=db_name).open()


class BracketPopup(Popup):
    """Visual tournament bracket from the last completed tournament."""

    def __init__(self, db_name, tourn_id=None, **kw):
        super().__init__(**kw)
        self.title = ''
        self.size_hint = (0.92, 0.90)
        self.background_color = _BG
        self._build(db_name, tourn_id)

    def _build(self, db_name, tourn_id):
        conn = sqlite3.connect(db_name)
        c = conn.cursor()

        if not tourn_id:
            row = c.execute(
                "SELECT id, name FROM tournaments WHERE place1 IS NOT NULL "
                "ORDER BY start_date DESC LIMIT 1"
            ).fetchone()
            if not row:
                self.content = Label(text='Нет завершённых турниров')
                conn.close(); return
            tourn_id, tourn_name = row
        else:
            tourn_name = (c.execute("SELECT name FROM tournaments WHERE id=?",
                                    (tourn_id,)).fetchone() or ('?',))[0]

        # Load all place columns
        places_row = c.execute(
            "SELECT " + ",".join(f"place{i}" for i in range(1, 17)) +
            " FROM tournaments WHERE id=?", (tourn_id,)
        ).fetchone()

        team_map = {r[0]: r[1].strip() for r in c.execute("SELECT id, name FROM teams").fetchall()}
        my_tid = (c.execute("SELECT id FROM teams WHERE player='yes'").fetchone() or (None,))[0]
        conn.close()

        placements = {}
        if places_row:
            for i, tid in enumerate(places_row, 1):
                if tid and tid in team_map:
                    placements[i] = team_map[tid]
                    placements[team_map[tid]] = i

        def _card(place, width=160):
            team = placements.get(place, f'—')
            is_my = (my_tid and placements.get(team) == place and
                     placements.get(place) == team)
            color = _GOLD if place == 1 else _WIN if place <= 4 else _WHITE
            if is_my:
                color = (0.50, 0.90, 1.00, 1)
            box = BoxLayout(size_hint=(None, None), width=width, height=34,
                            padding=(4, 0))
            lbl = Label(text=f'{place}. {team[:16]}', color=color,
                        halign='left', valign='middle', font_size='12sp')
            lbl.bind(size=lbl.setter('text_size'))
            box.add_widget(lbl)
            return box

        root = BoxLayout(orientation='vertical', padding=8, spacing=6)
        hdr = Label(text=f'[b]{tourn_name}[/b]', markup=True,
                    color=_ACCENT, size_hint_y=None, height=38,
                    halign='center', valign='middle', font_size='14sp')
        hdr.bind(size=hdr.setter('text_size'))
        root.add_widget(hdr)

        # Bracket laid out as columns: GF / Finals / SF / QF / R1 / Groups
        sv = ScrollView(size_hint=(1, 1))
        bracket = BoxLayout(orientation='horizontal', spacing=10,
                            size_hint=(None, None), padding=8)
        bracket.bind(minimum_width=bracket.setter('width'),
                     minimum_height=bracket.setter('height'))

        # Stages and place ranges
        stages = [
            ('Группа\n(13-16)',   range(13, 17)),
            ('Группа\n(9-12)',    range(9, 13)),
            ('LB Р1\n(7-8)',      range(7, 9)),
            ('LB Р2\n(5-6)',      range(5, 7)),
            ('Полуфиналы\n(3-4)', range(3, 5)),
            ('Финал\n(2)',        [2]),
            ('Чемпион\n(1)',      [1]),
        ]

        for stage_name, places in stages:
            col = BoxLayout(orientation='vertical', size_hint=(None, None),
                            width=170, spacing=4)
            col.bind(minimum_height=col.setter('height'))

            hdr_lbl = Label(
                text=stage_name, color=_ACCENT,
                size_hint_y=None, height=32, font_size='12sp',
                halign='center', valign='middle',
            )
            hdr_lbl.bind(size=hdr_lbl.setter('text_size'))
            col.add_widget(hdr_lbl)

            for place in places:
                col.add_widget(_card(place))

            bracket.add_widget(col)

        sv.add_widget(bracket)
        root.add_widget(sv)

        close = Button(text='Закрыть', size_hint_y=None, height=44,
                       background_color=(0.55, 0.18, 0.18, 1), background_normal='')
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root


def show_bracket_popup(db_name, tourn_id=None):
    BracketPopup(db_name=db_name, tourn_id=tourn_id).open()
