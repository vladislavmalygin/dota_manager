import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

_ACCENT = (0.35, 0.85, 1.00, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_SILVER = (0.80, 0.80, 0.80, 1)
_BRONZE = (0.78, 0.52, 0.25, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)

_REP_LEVELS = [(200,'Икона'),(100,'Легенда'),(50,'Ветеран'),(25,'Опытный'),(10,'Известный'),(0,'Новичок')]


def _lbl(text, height=28, color=_WHITE, bold=False, halign='center'):
    t = f'[b]{text}[/b]' if bold else text
    l = Label(text=t, markup=True, size_hint_y=None, height=height,
              color=color, halign=halign, valign='middle')
    l.bind(size=l.setter('text_size'))
    return l


class StatsPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.92, 0.92)
        self.background_color = (1, 1, 1, 0)
        self._db = db_name
        self._scroll_area = None
        self._build(db_name)

    # ── data helpers ──────────────────────────────────────────────────────────

    def _load_data(self, db_name):
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        char = c.execute(
            "SELECT name, surname, nickname, COALESCE(reputation,0) FROM characters LIMIT 1"
        ).fetchone()
        team_row = c.execute(
            "SELECT id, name, COALESCE(rating,0) FROM teams WHERE player='yes'"
        ).fetchone()
        team_id     = team_row[0] if team_row else None
        team_name   = team_row[1].strip() if team_row else '—'
        team_rating = int(team_row[2]) if team_row else 0

        c.execute("""
            SELECT name, start_date,
                   place1,  place2,  place3,  place4,
                   place5,  place6,  place7,  place8,
                   place9,  place10, place11, place12,
                   place13, place14, place15, place16,
                   COALESCE(prizepool,0)
            FROM tournaments WHERE place1 IS NOT NULL ORDER BY start_date
        """)
        results = []
        for row in c.fetchall():
            t_name, t_date, places, prize = row[0], row[1], row[2:18], row[18]
            for i, p in enumerate(places, 1):
                if p == team_id:
                    results.append((t_name, t_date, i, prize))
                    break

        pstats = []
        if team_id:
            pstats = c.execute("""
                SELECT p.nickname, COALESCE(SUM(cs.games),0),
                       COALESCE(SUM(cs.wins),0), COALESCE(SUM(cs.mvp_count),0),
                       COALESCE(p.comp_exp,0)
                FROM players p
                JOIN teams t ON (p.id=t.carry OR p.id=t.mid OR p.id=t.offlane
                                  OR p.id=t.partial_support OR p.id=t.full_support)
                LEFT JOIN player_career_stats cs ON cs.player_id=p.id
                WHERE t.id=? GROUP BY p.id ORDER BY p.id
            """, (team_id,)).fetchall()

        league = c.execute("""
            SELECT name, COALESCE(rating,0), player,
                   COALESCE(budget,0)
            FROM teams ORDER BY COALESCE(rating,0) DESC
        """).fetchall()
        conn.close()
        return char, team_id, team_name, team_rating, results, pstats, league

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self, db_name):
        char, team_id, team_name, team_rating, results, pstats, league = \
            self._load_data(db_name)

        root = BoxLayout(orientation='vertical', padding=6, spacing=4)

        # Header
        root.add_widget(_lbl('СТАТИСТИКА КАРЬЕРЫ', height=36, color=_ACCENT, bold=True))
        if char:
            name, surname, nick, rep = char
            rep_label = next((l for th, l in _REP_LEVELS if rep >= th), 'Новичок')
            root.add_widget(_lbl(f"{name} '{nick}' {surname}  |  Репутация: {rep} [{rep_label}]",
                                 height=26, color=_GOLD))
        root.add_widget(_lbl(f"Команда: {team_name}  |  Рейтинг: {team_rating} пт",
                             height=24, color=_ACCENT))

        # Summary
        if results:
            wins = sum(1 for _,_,p,_ in results if p == 1)
            top3 = sum(1 for _,_,p,_ in results if p <= 3)
            top8 = sum(1 for _,_,p,_ in results if p <= 8)
            prize_total = sum(pr for _,_,_,pr in results)
            best = min(p for _,_,p,_ in results)
            sg = GridLayout(cols=6, size_hint_y=None, height=50, spacing=4, padding=(6,2))
            for lbl, val, clr in [
                ('Турниров', str(len(results)), _WHITE),
                ('Побед', str(wins), _GOLD),
                ('Топ-3', str(top3), _BRONZE),
                ('Топ-8', str(top8), _WHITE),
                ('Лучший', f'{best}-е', _GREEN),
                ('Призовые', f'${prize_total:,}', _GOLD),
            ]:
                col = BoxLayout(orientation='vertical')
                col.add_widget(_lbl(lbl, height=22, color=_DIM, bold=False))
                col.add_widget(_lbl(val, height=26, color=clr, bold=True))
                sg.add_widget(col)
            root.add_widget(sg)

        # Player stats (compact)
        if pstats:
            ps_row = BoxLayout(size_hint_y=None, height=22, padding=(6,0))
            for txt, sw in [('Игрок', 0.28), ('Матчи', 0.18), ('Победы', 0.18),
                             ('MVP', 0.14), ('Опыт', 0.22)]:
                l = Label(text=f'[b]{txt}[/b]', markup=True, size_hint_x=sw, color=_ACCENT,
                          halign='center', valign='middle', font_size='12sp')
                l.bind(size=l.setter('text_size'))
                ps_row.add_widget(l)
            root.add_widget(ps_row)
            for pnick, pgames, pwins, pmvp, pexp in pstats:
                pr = BoxLayout(size_hint_y=None, height=24, padding=(6,0))
                for txt, sw, clr in [
                    (pnick or '?', 0.28, _WHITE),
                    (str(pgames),  0.18, _DIM),
                    (str(pwins),   0.18, _GOLD if pwins else _DIM),
                    (str(pmvp),    0.14, _SILVER if pmvp else _DIM),
                    (str(pexp),    0.22, _GREEN if pexp > 50 else _DIM),
                ]:
                    l = Label(text=txt, size_hint_x=sw, color=clr,
                              halign='center', valign='middle', font_size='12sp')
                    l.bind(size=l.setter('text_size'))
                    pr.add_widget(l)
                root.add_widget(pr)

        # Tabs
        tab_row = BoxLayout(size_hint_y=None, height=36, spacing=4)
        self._tab_btns = {}
        for name in ('История турниров', 'Рейтинг лиги'):
            b = Button(text=name, size_hint_y=None, height=34, background_normal='',
                       background_color=(0.25,0.50,0.75,1))
            b.bind(on_press=lambda _, n=name: self._switch_tab(n))
            tab_row.add_widget(b)
            self._tab_btns[name] = b
        root.add_widget(tab_row)

        self._scroll_area = BoxLayout(size_hint=(1,1))
        root.add_widget(self._scroll_area)

        close = Button(text='Закрыть', size_hint_y=None, height=42,
                       background_color=(0.7,0.2,0.2,0.9), background_normal='')
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root

        # Build tab content now (cache)
        self._history_grid  = self._make_history(results)
        self._league_grid   = self._make_league(league, team_name)
        self._switch_tab('История турниров')

    def _switch_tab(self, name):
        for n, b in self._tab_btns.items():
            b.background_color = (0.35,0.65,0.90,1) if n == name else (0.18,0.35,0.55,1)
        self._scroll_area.clear_widgets()
        sv = ScrollView(size_hint=(1,1))
        sv.add_widget(self._history_grid if name == 'История турниров'
                      else self._league_grid)
        self._scroll_area.add_widget(sv)

    def _make_history(self, results):
        grid = GridLayout(cols=1, size_hint_y=None, spacing=2)
        grid.bind(minimum_height=grid.setter('height'))
        if not results:
            grid.add_widget(_lbl('Нет данных.', height=30, color=_DIM))
            return grid
        hrow = BoxLayout(size_hint_y=None, height=24, padding=(6,0))
        for txt, sw in [('Турнир', 0.44), ('Дата', 0.19), ('Место', 0.17), ('Приз', 0.20)]:
            l = Label(text=f'[b]{txt}[/b]', markup=True, size_hint_x=sw,
                      color=_ACCENT, halign='center', valign='middle', font_size='13sp')
            l.bind(size=l.setter('text_size'))
            hrow.add_widget(l)
        grid.add_widget(hrow)
        for t_name, t_date, place, prize in reversed(results):
            color = (_GOLD if place==1 else _SILVER if place==2 else
                     _BRONZE if place<=4 else _WHITE if place<=8 else _DIM)
            medal = ('[1]' if place==1 else '[2]' if place==2 else
                     '[3]' if place==3 else str(place))
            row = BoxLayout(size_hint_y=None, height=30, padding=(6,0))
            for txt, sw in [(t_name, 0.44), (t_date[:7] if t_date else '—', 0.19),
                            (medal, 0.17), (f'${prize:,}' if prize else '—', 0.20)]:
                l = Label(text=txt, size_hint_x=sw, color=color,
                          halign='center', valign='middle', font_size='13sp')
                l.bind(size=l.setter('text_size'))
                row.add_widget(l)
            grid.add_widget(row)
        return grid

    def _make_league(self, league, my_team):
        grid = GridLayout(cols=1, size_hint_y=None, spacing=2)
        grid.bind(minimum_height=grid.setter('height'))
        hrow = BoxLayout(size_hint_y=None, height=24, padding=(6,0))
        for txt, sw in [('#', 0.08), ('Команда', 0.50), ('Рейтинг', 0.22), ('Бюджет', 0.20)]:
            l = Label(text=f'[b]{txt}[/b]', markup=True, size_hint_x=sw,
                      color=_ACCENT, halign='center', valign='middle', font_size='13sp')
            l.bind(size=l.setter('text_size'))
            hrow.add_widget(l)
        grid.add_widget(hrow)
        for rank, (name, rating, is_player, budget) in enumerate(league, 1):
            is_my = (is_player == 'yes')
            color = _GOLD if is_my else (_WHITE if rank <= 8 else _DIM)
            row = BoxLayout(size_hint_y=None, height=28, padding=(6,0))
            prefix = '* ' if is_my else ''
            for txt, sw in [
                (str(rank),              0.08),
                (f'{prefix}{name}',      0.50),
                (str(int(rating)),       0.22),
                (f'${budget//1000}k',    0.20),
            ]:
                l = Label(text=txt, size_hint_x=sw, color=color,
                          halign='center', valign='middle', font_size='13sp')
                l.bind(size=l.setter('text_size'))
                row.add_widget(l)
            grid.add_widget(row)
        return grid


def show_stats_popup(db_name):
    StatsPopup(db_name=db_name).open()


class LeaderboardPopup(Popup):
    """Global player skill & experience leaderboard."""

    def __init__(self, db_name, **kw):
        super().__init__(**kw)
        self.title = 'Топ игроки сцены'
        self.size_hint = (0.82, 0.88)
        self._build(db_name)

    def _build(self, db_name):
        import sqlite3 as _sq
        conn = _sq.connect(db_name)
        c = conn.cursor()

        my_pids = set()
        my_row = c.execute("SELECT carry,mid,offlane,partial_support,full_support FROM teams WHERE player='yes'").fetchone()
        if my_row:
            my_pids = {str(p) for p in my_row if p}

        # Top by skill
        top_skill = c.execute("""
            SELECT p.nickname, p.role, p.micro_skills+p.macro_skills as sk,
                   COALESCE(p.age,22), t.name, p.id
            FROM players p JOIN teams t ON t.id=p.team_id
            WHERE p.team_id != 0
            ORDER BY sk DESC LIMIT 15
        """).fetchall()

        # Top by experience (comp_exp)
        top_exp = c.execute("""
            SELECT p.nickname, p.role, COALESCE(p.comp_exp,0) as exp,
                   COALESCE(p.age,22), t.name, p.id
            FROM players p JOIN teams t ON t.id=p.team_id
            WHERE p.team_id != 0
            ORDER BY exp DESC LIMIT 10
        """).fetchall()

        conn.close()

        _BG = (0.07, 0.09, 0.13, 1)
        _ACC = (0.35, 0.85, 1.00, 1)
        _GOLD = (1.00, 0.85, 0.25, 1)
        _W = (0.92, 0.92, 0.92, 1)
        _D = (0.55, 0.55, 0.55, 1)
        _MY = (0.50, 0.90, 1.00, 1)

        def _lbl2(text, color=_W, height=26, sw=1.0, halign='left'):
            l = Label(text=text, markup=True, color=color, size_hint_x=sw,
                      size_hint_y=None, height=height,
                      halign=halign, valign='middle', font_size='12sp')
            l.bind(size=l.setter('text_size'))
            return l

        root = BoxLayout(orientation='vertical', padding=8, spacing=6)

        sv = ScrollView(size_hint=(1, 1))
        gl = GridLayout(cols=1, size_hint_y=None, spacing=4)
        gl.bind(minimum_height=gl.setter('height'))

        # Top by skill
        hdr1 = Label(text='[b]ТОП-15 ПО СКИЛЛУ (micro+macro)[/b]', markup=True,
                     color=_ACC, size_hint_y=None, height=30,
                     halign='center', valign='middle', font_size='13sp')
        hdr1.bind(size=hdr1.setter('text_size'))
        gl.add_widget(hdr1)

        _ROLE_SHORT2 = {'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Off',
                       'partial_support': 'Sup4', 'full_support': 'Sup5'}
        for i, (nick, role, sk, age, team, pid) in enumerate(top_skill, 1):
            is_my = str(pid) in my_pids
            clr = _MY if is_my else (_GOLD if i == 1 else _W)
            row = BoxLayout(size_hint_y=None, height=26)
            row.add_widget(_lbl2(f'{i}.', clr, sw=0.07, halign='right'))
            row.add_widget(_lbl2(f'[b]{nick}[/b]' if is_my else nick, clr, sw=0.25))
            row.add_widget(_lbl2(_ROLE_SHORT2.get(role, role or '?'), _D, sw=0.10))
            row.add_widget(_lbl2(f'{sk}', clr, sw=0.10, halign='center'))
            row.add_widget(_lbl2(f'{age}л', _D, sw=0.08, halign='center'))
            row.add_widget(_lbl2(team.strip()[:20] if team else '—', _D, sw=0.40))
            gl.add_widget(row)

        # Top by experience
        hdr2 = Label(text='[b]ТОП-10 ВЕТЕРАНЫ (опыт матчей)[/b]', markup=True,
                     color=_ACC, size_hint_y=None, height=30,
                     halign='center', valign='middle', font_size='13sp')
        hdr2.bind(size=hdr2.setter('text_size'))
        gl.add_widget(hdr2)

        for i, (nick, role, exp, age, team, pid) in enumerate(top_exp, 1):
            is_my = str(pid) in my_pids
            clr = _MY if is_my else (_GOLD if i == 1 else _W)
            row = BoxLayout(size_hint_y=None, height=26)
            row.add_widget(_lbl2(f'{i}.', clr, sw=0.07, halign='right'))
            row.add_widget(_lbl2(f'[b]{nick}[/b]' if is_my else nick, clr, sw=0.25))
            row.add_widget(_lbl2(f'{exp} матчей', clr, sw=0.20, halign='center'))
            row.add_widget(_lbl2(f'{age}л', _D, sw=0.08, halign='center'))
            row.add_widget(_lbl2(team.strip()[:24] if team else '—', _D, sw=0.40))
            gl.add_widget(row)

        sv.add_widget(gl)
        root.add_widget(sv)

        close = Button(text='Закрыть', size_hint_y=None, height=44,
                       background_color=(0.55, 0.18, 0.18, 1), background_normal='')
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root


def show_leaderboard_popup(db_name):
    LeaderboardPopup(db_name=db_name).open()
