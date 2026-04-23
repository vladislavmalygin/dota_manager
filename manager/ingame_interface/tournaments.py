import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

from logic.tournaments.runner import (
    generate_tournament_events,
    save_tournament_results,
    get_lineup,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _add_message(db_name, text, author="Система"):
    conn = sqlite3.connect(db_name)
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
        (text, author),
    )
    conn.commit()
    conn.close()


def _lbl(text, height=36, color=(1, 1, 1, 1), bold=False, halign='left'):
    if bold:
        text = f"[b]{text}[/b]"
    lbl = Label(
        text=text, markup=bold,
        size_hint_y=None, height=height,
        color=color, halign=halign, valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


# ─── TournamentPopup – step-by-step match runner ──────────────────────────────

class TournamentPopup(Popup):
    """
    Opened automatically when the game date matches a tournament start date.
    Shows the tournament match-by-match; the player must click through each step.
    Player-team matches show full lineups before the result.
    """

    _BTN_LABELS = {
        'draw':              'Начать групповой этап',
        'match_lineup':      'Сыграть матч  ▶',
        'match_result':      'Следующий матч',
        'groups_complete':   'К плей-офф',
        'stage_header':      'Начать матчи',
        'tournament_results':'Завершить',
    }

    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        self._results_saved = False

        # Load the first unplayed tournament
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name FROM tournaments WHERE place1 IS NULL ORDER BY start_date LIMIT 1"
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            self.title = "Нет турниров"
            self.content = Label(text="Все турниры сезона сыграны.")
            return

        self.tournament_id, tournament_name = row
        self.title = tournament_name

        # Generate all events upfront (all matches pre-simulated)
        self.events, self.placements, self.group_eliminated = \
            generate_tournament_events(db_name, self.tournament_id)
        self.event_idx = 0

        # ── UI ────────────────────────────────────────────────
        # Top bar: tournament name
        self._title_lbl = Label(
            text=f"[b]{tournament_name}[/b]", markup=True,
            size_hint_y=None, height=44,
            color=(0.4, 0.9, 1.0, 1), halign='center', valign='middle',
        )
        self._title_lbl.bind(size=self._title_lbl.setter('text_size'))

        # Scrollable log
        self._log_lbl = Label(
            text='', size_hint_y=None,
            color=(1, 1, 1, 1), halign='left', valign='top',
        )
        self._log_lbl.bind(texture_size=self._log_lbl.setter('size'))

        self._scroll = ScrollView(size_hint=(1, 1))
        self._scroll.add_widget(self._log_lbl)

        # Buttons
        self._next_btn = Button(
            text='Показать жеребьёвку',
            size_hint=(0.75, None), height=52,
            background_color=(0.2, 0.6, 0.9, 1),
        )
        self._next_btn.bind(on_press=self._on_next)

        close_btn = Button(
            text='Закрыть', size_hint=(0.25, None), height=52,
            background_color=(0.7, 0.2, 0.2, 1),
        )
        close_btn.bind(on_press=self.dismiss)

        btn_row = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=56, spacing=4,
        )
        btn_row.add_widget(self._next_btn)
        btn_row.add_widget(close_btn)

        layout = BoxLayout(orientation='vertical', spacing=4, padding=4)
        layout.add_widget(self._title_lbl)
        layout.add_widget(self._scroll)
        layout.add_widget(btn_row)

        self.content = layout

    # ── stepping ──────────────────────────────────────────────

    def _on_next(self, _):
        if self.event_idx >= len(self.events):
            return

        event = self.events[self.event_idx]
        self.event_idx += 1

        # Render and append
        rendered = self._render(event)
        if rendered:
            sep = '\n' if self._log_lbl.text else ''
            self._log_lbl.text += sep + rendered

        # Save results when we hit the results event
        if event['type'] == 'tournament_results' and not self._results_saved:
            self._persist_results(event)
            self._results_saved = True

        # Update button label based on the *next* event
        if self.event_idx >= len(self.events):
            self._next_btn.disabled = True
            self._next_btn.text = 'Завершено'
        else:
            next_type = self.events[self.event_idx]['type']
            self._next_btn.text = self._BTN_LABELS.get(next_type, 'Далее')

        # Scroll to bottom after layout
        Clock.schedule_once(lambda dt: setattr(self._scroll, 'scroll_y', 0), 0.05)

    # ── rendering ─────────────────────────────────────────────

    def _render(self, ev):
        t = ev['type']
        lines = []

        if t == 'draw':
            lines += [
                '\n' + '═' * 52,
                'ЖЕРЕБЬЁВКА',
                '─' * 52,
            ]
            player_teams = set(ev.get('player_teams', []))
            for i, group in enumerate(ev['groups']):
                members = []
                for team in group:
                    mark = ' ★' if team in player_teams else ''
                    members.append(team + mark)
                lines.append(f"  Группа {i + 1}: {', '.join(members)}")

        elif t == 'match_lineup':
            t1, t2 = ev['team1'], ev['team2']
            stage = ev.get('stage', '')
            lines += [
                '',
                '┌' + '─' * 52 + '┐',
                f"│  МАТЧ [{stage}]: {t1}  vs  {t2}",
                f"│  Составы:",
                '├' + '─' * 52 + '┤',
            ]
            l1, l2 = ev['t1_lineup'], ev['t2_lineup']
            # Header
            lines.append(f"│  {'Роль':<13}  {t1[:20]:<23} {t2[:20]}")
            lines.append('│  ' + '─' * 52)
            for i in range(max(len(l1), len(l2))):
                p1 = l1[i] if i < len(l1) else {}
                p2 = l2[i] if i < len(l2) else {}
                role = (p1 or p2).get('role', '')
                n1 = f"{p1['nick']} ({p1['micro']}/{p1['macro']})" if p1 else '—'
                n2 = f"{p2['nick']} ({p2['micro']}/{p2['macro']})" if p2 else '—'
                lines.append(f"│  {role:<13}  {n1:<25}{n2}")
            lines.append('└' + '─' * 52 + '┘')

        elif t == 'match_result':
            t1, t2, winner = ev['team1'], ev['team2'], ev['winner']
            loser = ev['loser']
            stage = ev.get('stage', '')

            if ev.get('is_player_match'):
                lines += [
                    f"  ✦ Победитель: {winner}",
                    f"  ✦ Проиграл:   {loser}",
                ]
            else:
                lines.append(f"  {stage}: {t1} vs {t2}  →  {winner}")

            # Show group standings inline
            if 'standings' in ev:
                gi = ev.get('group_idx', -1)
                sorted_s = sorted(ev['standings'].items(), key=lambda x: x[1], reverse=True)
                standing_str = '  |  '.join(f"{tm}: {pts}" for tm, pts in sorted_s)
                lines.append(f"  Таблица гр.{gi + 1}: {standing_str}")

        elif t == 'groups_complete':
            lines += [
                '\n' + '═' * 52,
                'ГРУППОВОЙ ЭТАП — ИТОГИ',
                '─' * 52,
            ]
            for i, sorted_g in enumerate(ev['group_standings']):
                lines.append(f"  Группа {i + 1}:")
                for rank, (team, pts) in enumerate(sorted_g):
                    arrow = '→ плей-офф' if rank < 2 else '  выбывает'
                    lines.append(f"    {'★' if rank < 2 else ' '} {rank + 1}. {team:<22} {pts} очков  {arrow}")

        elif t == 'stage_header':
            stage = ev['stage']
            pairs = ev['pairs']
            lines += [
                '\n' + '═' * 52,
                stage,
                '─' * 52,
            ]
            for t1, t2 in pairs:
                lines.append(f"  {t1}  vs  {t2}")

        elif t == 'tournament_results':
            champion = ev['champion']
            placements = ev['placements']
            group_eliminated = ev['group_eliminated']

            lines += [
                '\n' + '═' * 52,
                f'ЧЕМПИОН:  {champion}',
                '═' * 52,
            ]
            medals = {1: '🥇', 2: '🥈', 3: '🥉', 4: ' 4.'}
            for team, place in sorted(placements.items(), key=lambda x: x[1]):
                m = medals.get(place, f'{place:2}.')
                lines.append(f"  {m}  {team}")
            lines.append('─' * 52)
            lines.append('  Вылет в групповом этапе:')
            for i, (team, pts) in enumerate(
                sorted(group_eliminated, key=lambda x: x[1], reverse=True)
            ):
                lines.append(f"  {9 + i:2}.  {team}")

        return '\n'.join(lines)

    # ── DB persistence ────────────────────────────────────────

    def _persist_results(self, event):
        save_tournament_results(
            event['tournament_id'],
            event['placements'],
            event['group_eliminated'],
            self.db_name,
        )
        # Find player's team place and send inbox message
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT name FROM teams WHERE player = 'yes'")
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        my_team = row[0]
        place = event['placements'].get(my_team)
        if not place:
            for i, (t, _) in enumerate(
                sorted(event['group_eliminated'], key=lambda x: x[1], reverse=True)
            ):
                if t == my_team:
                    place = 9 + i
                    break
        if place:
            _add_message(
                self.db_name,
                f"{self.title} завершён. {my_team} заняла {place}-е место.",
                "Спортивный директор",
            )


# ─── TournamentsViewPopup – schedule + season rating viewer ───────────────────

class TournamentsViewPopup(Popup):
    """
    Opened from the 'Турниры' sidebar button.
    Shows season rating and the full tournament schedule/results.
    """

    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = "Турниры"
        self.size_hint = (0.9, 0.9)

        grid = GridLayout(cols=1, size_hint_y=None, spacing=3, padding=(8, 4))
        grid.bind(minimum_height=grid.setter('height'))

        self._fill(db_name, grid)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=50,
            background_color=(0.7, 0.2, 0.2, 1),
        )
        close_btn.bind(on_press=self.dismiss)

        layout = BoxLayout(orientation='vertical', spacing=4, padding=4)
        layout.add_widget(scroll)
        layout.add_widget(close_btn)
        self.content = layout

    # ── helpers ───────────────────────────────────────────────

    @staticmethod
    def _h(text, height=46):
        lbl = Label(
            text=f'[b]{text}[/b]', markup=True,
            size_hint_y=None, height=height,
            color=(0.4, 0.9, 1.0, 1), halign='center', valign='middle',
        )
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    @staticmethod
    def _r(text, height=34, color=(1, 1, 1, 1)):
        lbl = Label(
            text=text, size_hint_y=None, height=height,
            color=color, halign='left', valign='middle',
        )
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    # ── data population ───────────────────────────────────────

    def _fill(self, db_name, grid):
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()

        # ── Season rating ──────────────────────────────────────
        grid.add_widget(self._h("═══  РЕЙТИНГ СЕЗОНА  ═══"))

        cur.execute(
            "SELECT name, COALESCE(rating, 0) FROM teams ORDER BY COALESCE(rating,0) DESC, name"
        )
        teams = cur.fetchall()

        cur.execute("SELECT name FROM teams WHERE player = 'yes'")
        player_row = cur.fetchone()
        player_team = (player_row[0] if player_row else '').strip()

        for rank, (name, rating) in enumerate(teams):
            name = name.strip()
            is_player = name == player_team
            if rank == 0:
                color = (1.0, 0.85, 0.2, 1)    # gold
            elif rank == 1:
                color = (0.85, 0.85, 0.85, 1)  # silver
            elif rank == 2:
                color = (0.8, 0.55, 0.35, 1)   # bronze
            elif is_player:
                color = (0.5, 1.0, 0.5, 1)     # green for player team
            else:
                color = (1, 1, 1, 1)

            marker = '  ★' if is_player else ''
            grid.add_widget(self._r(
                f"  {rank + 1:2}.  {name:<24} {int(rating):>5} pts{marker}",
                color=color,
            ))

        # ── Tournament schedule ────────────────────────────────
        grid.add_widget(self._h("═══  РАСПИСАНИЕ ТУРНИРОВ  ═══"))

        cur.execute(
            """
            SELECT t.id, t.name, t.start_date, t.end_date,
                   t.prizepool, t.ratingpool, t.place1,
                   tm.name
            FROM tournaments t
            LEFT JOIN teams tm ON t.place1 = tm.id
            ORDER BY t.start_date
            """
        )
        tournaments = cur.fetchall()

        for tid, name, start, end, prize, rpool, place1, winner in tournaments:
            if place1 and winner:
                status_txt = f"✓  Победитель: {winner.strip()}"
                c = (0.6, 0.95, 0.6, 1)
            else:
                status_txt = "→  Предстоит"
                c = (0.95, 0.95, 0.5, 1)

            grid.add_widget(self._r(
                f"  {start}  ─  {name}",
                height=38, color=c,
            ))
            grid.add_widget(self._r(
                f"       Призовой: ${prize:,}   |   {rpool or 0} pts рейтинга   |   {status_txt}",
                height=28, color=c,
            ))

            # Show top-8 for completed tournaments
            if place1:
                cur.execute(
                    """
                    SELECT tm.name
                    FROM (VALUES
                      (t.place1,1),(t.place2,2),(t.place3,3),(t.place4,4),
                      (t.place5,5),(t.place6,6),(t.place7,7),(t.place8,8)
                    ) AS pl(tid,pos)
                    JOIN teams tm ON tm.id = pl.tid
                    JOIN tournaments t ON t.id = ?
                    ORDER BY pl.pos
                    """,
                    (tid,)
                )
                # Fallback: simpler query
                row = cur.execute(
                    "SELECT place1,place2,place3,place4,place5,place6,place7,place8 FROM tournaments WHERE id=?",
                    (tid,)
                ).fetchone()
                if row:
                    place_names = []
                    for pid in row:
                        if pid:
                            n = cur.execute("SELECT name FROM teams WHERE id=?", (pid,)).fetchone()
                            if n:
                                place_names.append(n[0].strip())
                    if place_names:
                        grid.add_widget(self._r(
                            '       Топ-8: ' + ', '.join(
                                f"{i + 1}.{n}" for i, n in enumerate(place_names)
                            ),
                            height=26, color=(0.75, 0.95, 0.75, 1),
                        ))

        conn.close()
