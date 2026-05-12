import sqlite3
from datetime import date, timedelta

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

_ACCENT = (0.35, 0.85, 1.00, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_RED    = (1.00, 0.35, 0.35, 1)

_ROLE_LABELS = {
    'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Offlane',
    'partial_support': 'Soft Supp', 'full_support': 'Hard Supp',
}
_ROLE_SHORT = {
    'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Off',
    'partial_support': 'Soft', 'full_support': 'Hard',
}
_ROLES_ALL = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
_POTENTIAL_STARS = [(270, '*****'), (230, '****'), (190, '***'), (0, '**')]


def _lbl(text, color=_WHITE, height=28, halign='left', bold=False):
    t = f'[b]{text}[/b]' if bold else text
    l = Label(text=t, markup=True, color=color, size_hint_y=None, height=height,
              halign=halign, valign='middle')
    l.bind(size=l.setter('text_size'))
    return l


def _col(text, sw, color=_WHITE, font_size='13sp'):
    l = Label(text=text, size_hint_x=sw, color=color,
              halign='center', valign='middle', font_size=font_size)
    l.bind(size=l.setter('text_size'))
    return l


def _potential(cap):
    for threshold, stars in _POTENTIAL_STARS:
        if (cap or 0) >= threshold:
            return stars
    return '*'


class AcademyPopup(Popup):
    def __init__(self, db_name, tab='market', role_filter=None, **kw):
        super().__init__(**kw)
        self.title     = 'Академия молодёжи'
        self.size_hint = (0.84, 0.92)
        self.db_name   = db_name
        self._tab      = tab
        self._rf       = role_filter
        self._build()

    # ── shell ─────────────────────────────────────────────────────────────────

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=4, padding=6)

        # Tab bar
        tab_row = BoxLayout(size_hint_y=None, height=38, spacing=4)
        for tid, tlabel in [
            ('market', 'Рынок талантов'),
            ('squad',  'Моя молодёжь'),
            ('camp',   'Сборы'),
        ]:
            active = tid == self._tab
            btn = Button(
                text=tlabel, size_hint_x=0.33,
                background_color=(0.20, 0.55, 0.80, 1) if active else (0.18, 0.20, 0.25, 1),
                background_normal='', bold=active,
            )
            btn.bind(on_press=lambda _, t=tid: self._switch(t))
            tab_row.add_widget(btn)
        root.add_widget(tab_row)

        if self._tab == 'market':
            self._build_market(root)
        elif self._tab == 'squad':
            self._build_squad(root)
        else:
            self._build_camp(root)

        root.add_widget(Button(
            text='Закрыть', size_hint_y=None, height=44,
            background_color=(0.65, 0.18, 0.18, 1), background_normal='',
            on_press=self.dismiss,
        ))
        self.content = root

    def _switch(self, tab):
        self.dismiss()
        AcademyPopup(db_name=self.db_name, tab=tab).open()

    # ── camp tab ──────────────────────────────────────────────────────────────

    _MAX_CAMPS = 2

    def _build_camp(self, root):
        conn = sqlite3.connect(self.db_name)
        team = conn.execute(
            "SELECT id, COALESCE(budget,0), COALESCE(youth_camp_count,0) FROM teams WHERE player='yes'"
        ).fetchone()
        if not team:
            conn.close()
            root.add_widget(_lbl('Нет команды.', _RED))
            return
        team_id, budget, camp_count = team

        youth = conn.execute(
            "SELECT id, nickname, role, micro_skills, macro_skills, soft_skills, "
            "COALESCE(skill_cap,300) FROM players "
            "WHERE team_id=? AND is_youth=1", (team_id,)
        ).fetchall()
        conn.close()

        root.add_widget(_lbl(f'  Бюджет: ${budget:,}', _GOLD, height=30, bold=True))
        root.add_widget(_lbl(
            f'  Молодёжных игроков: {len(youth)}', _WHITE, height=26
        ))

        sv = ScrollView(size_hint=(1, 0.65))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=2)
        grid.bind(minimum_height=grid.setter('height'))
        if youth:
            grid.add_widget(_lbl('  Ник             Роль     Micro  Macro  Soft   Потенциал',
                                  _DIM, height=22))
            for pid, nick, role, mi, mx, so, cap in youth:
                stars = _potential(cap)
                grid.add_widget(_lbl(
                    f'  {(nick or "?")[:14]:<14}  {_ROLE_SHORT.get(role,"?"):<8} '
                    f'{mi:3d}    {mx:3d}    {so:3d}   {stars}',
                    _WHITE, height=22
                ))
        else:
            grid.add_widget(_lbl('  Нет молодёжи в команде.', _DIM))
        sv.add_widget(grid)
        root.add_widget(sv)

        camps_left = self._MAX_CAMPS - camp_count
        root.add_widget(_lbl(
            f'  ── Тренировочные сборы ──  (осталось в сезоне: {camps_left}/{self._MAX_CAMPS})',
            _ACCENT, height=28, bold=True
        ))

        for cost, gain, label, desc in [
            (20_000, 2, 'Лёгкий сбор  ($20,000)',
             f'+2 к каждому скиллу всех {len(youth)} молодёжных игроков'),
            (40_000, 4, 'Серьёзный сбор  ($40,000)',
             f'+4 к каждому скиллу + +1 мораль'),
        ]:
            can = budget >= cost and len(youth) > 0 and camps_left > 0
            root.add_widget(_lbl(f'  {desc}', _DIM if not can else _WHITE, height=22))
            btn = Button(
                text=label, size_hint_y=None, height=44,
                background_color=(0.15, 0.45, 0.20, 1) if can else (0.28, 0.28, 0.28, 1),
                background_normal='', disabled=not can,
            )
            btn.bind(on_press=lambda _, db=self.db_name, tid=team_id,
                     c=cost, g=gain, morale=(1 if cost >= 40_000 else 0):
                     self._do_camp(db, tid, c, g, morale))
            root.add_widget(btn)

    def _do_camp(self, db_name, team_id, cost, gain, morale_gain):
        from kivy.uix.popup import Popup
        conn = sqlite3.connect(db_name)
        budget = conn.execute(
            "SELECT COALESCE(budget,0) FROM teams WHERE id=?", (team_id,)
        ).fetchone()[0]
        if budget < cost:
            conn.close()
            from kivy.uix.label import Label as _L
            Popup(content=_L(text='Недостаточно средств', halign='center'),
                  size_hint=(0.4, 0.22)).open()
            return
        youth_ids = [r[0] for r in conn.execute(
            "SELECT id FROM players WHERE team_id=? AND is_youth=1", (team_id,)
        ).fetchall()]
        if not youth_ids:
            conn.close()
            return
        ph = ','.join('?' * len(youth_ids))
        conn.execute("UPDATE teams SET budget=budget-?, youth_camp_count=COALESCE(youth_camp_count,0)+1 WHERE id=?", (cost, team_id))
        for col in ('micro_skills', 'macro_skills', 'soft_skills'):
            conn.execute(
                f"UPDATE players SET {col}=MIN(100,COALESCE({col},0)+?) WHERE id IN ({ph})",
                [gain] + list(youth_ids)
            )
        if morale_gain:
            conn.execute(
                f"UPDATE players SET morale=MIN(10,COALESCE(morale,5)+1) WHERE id IN ({ph})",
                list(youth_ids)
            )
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
            (f'Молодёжный сбор: {len(youth_ids)} игроков получили +{gain} к навыкам'
             + (' +1 мораль' if morale_gain else '') + f'. Расходы: −${cost:,}',
             'Академия')
        )
        conn.commit(); conn.close()
        self.dismiss()
        AcademyPopup(db_name=db_name, tab='camp').open()

    # ── market tab ────────────────────────────────────────────────────────────

    def _build_market(self, root):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()

        cur.execute("SELECT id, COALESCE(budget,0) FROM teams WHERE player='yes'")
        team_row = cur.fetchone()
        team_id  = team_row[0] if team_row else None
        budget   = team_row[1] if team_row else 0

        cur.execute("""
            SELECT id, nickname, name, surname, role, age,
                   COALESCE(micro_skills,0), COALESCE(macro_skills,0),
                   COALESCE(soft_skills,0),  COALESCE(skill_cap,200),
                   COALESCE(learning_rate,5), COALESCE(expected_wage,3000),
                   COALESCE(country,'?')
            FROM players
            WHERE team_id=0
              AND (COALESCE(is_youth,0)=1 OR (COALESCE(age,25)<=19 AND COALESCE(learning_rate,5)>=6))
            ORDER BY skill_cap DESC, age ASC
        """)
        all_prospects = cur.fetchall()

        gd_str = (cur.execute("SELECT date FROM save WHERE id=1").fetchone() or (str(date.today()),))[0]
        conn.close()

        # Role filter bar
        filter_row = BoxLayout(size_hint_y=None, height=32, spacing=3)
        filter_row.add_widget(Label(text='Роль:', size_hint_x=None, width=44,
                                    color=_DIM, font_size='12sp'))
        for rf in [None] + _ROLES_ALL:
            label  = 'Все' if rf is None else _ROLE_SHORT[rf]
            active = rf == self._rf
            btn = Button(
                text=label, font_size='11sp',
                background_color=(0.20, 0.60, 0.30, 1) if active else (0.15, 0.20, 0.18, 1),
                background_normal='',
            )
            btn.bind(on_press=lambda _, r=rf: self._set_rf(r))
            filter_row.add_widget(btn)
        root.add_widget(filter_row)

        prospects = [p for p in all_prospects if self._rf is None or p[4] == self._rf]

        root.add_widget(_lbl(
            f'Кандидатов: {len(prospects)} / {len(all_prospects)}   Бюджет: ${budget:,}',
            color=_ACCENT, height=26, halign='center', bold=True,
        ))

        sv   = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))

        if not prospects:
            grid.add_widget(_lbl('  Нет молодёжи. Появятся после конца сезона.',
                                 color=_DIM, height=46))
        else:
            hrow = BoxLayout(size_hint_y=None, height=24)
            for txt, sw in [('Ник / страна', 0.20), ('Роль', 0.11), ('Возр', 0.07),
                             ('Mi/Ma/So', 0.16), ('Потенц', 0.12),
                             ('Обуч', 0.10), ('Подписать', 0.24)]:
                hrow.add_widget(_col(f'[b]{txt}[/b]', sw, _ACCENT, '12sp'))
            grid.add_widget(hrow)

            for pid, nick, fname, lname, role, age, mi, ma, so, cap, lr, exp_w, country in prospects:
                wage = max(exp_w, 2000)
                pot  = _potential(cap)
                learn_bar = '▓' * min(lr, 10)

                row = BoxLayout(size_hint_y=None, height=48, spacing=3)
                row.add_widget(_col(f'{nick}\n[color=#888888]{country}[/color]',
                                    0.20, _WHITE, '12sp'))
                row.add_widget(_col(_ROLE_LABELS.get(role, role or '?'), 0.11, (0.75, 0.85, 1.0, 1)))
                row.add_widget(_col(str(age), 0.07, _DIM))
                row.add_widget(_col(f'{mi}/{ma}/{so}', 0.16, _WHITE))
                row.add_widget(_col(pot, 0.12, _GOLD))
                row.add_widget(_col(learn_bar, 0.10, _GREEN, '10sp'))

                sign_box = BoxLayout(size_hint_x=0.24, spacing=3)
                for years in [1, 2]:
                    can = budget >= wage and team_id is not None
                    btn = Button(
                        text=f'{years}г  ${wage//1000}k',
                        background_color=(0.15, 0.50, 0.20, 1) if can else (0.28, 0.28, 0.28, 1),
                        background_normal='', font_size='12sp', disabled=not can,
                    )
                    btn.bind(on_press=lambda _, p=pid, r=role, w=wage, y=years, g=gd_str:
                             self._sign(p, r, w, y, g))
                    sign_box.add_widget(btn)
                row.add_widget(sign_box)
                grid.add_widget(row)

        sv.add_widget(grid)
        root.add_widget(sv)

    # ── squad tab ─────────────────────────────────────────────────────────────

    def _build_squad(self, root):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()

        cur.execute("SELECT id FROM teams WHERE player='yes'")
        team_row = cur.fetchone()
        if not team_row:
            conn.close()
            root.add_widget(_lbl('Нет команды', color=_DIM, height=40))
            return
        tid = team_row[0]

        cur.execute("""
            SELECT p.id, p.nickname, p.name, p.surname, p.role, p.age,
                   COALESCE(p.micro_skills,0), COALESCE(p.macro_skills,0),
                   COALESCE(p.soft_skills,0),  COALESCE(p.skill_cap,200),
                   COALESCE(p.learning_rate,5), COALESCE(p.wage,0),
                   COALESCE(p.contract_end,'?')
            FROM players p
            WHERE p.team_id=?
              AND (COALESCE(p.is_youth,0)=1 OR COALESCE(p.age,25)<=21)
            ORDER BY p.age ASC
        """, (tid,))
        youth = cur.fetchall()

        # Skill deltas from latest snapshot
        snapshots = {}
        for pid, *_ in youth:
            snap = cur.execute(
                "SELECT micro, macro, soft FROM player_skill_snapshot "
                "WHERE player_id=? ORDER BY season DESC LIMIT 1",
                (pid,)
            ).fetchone()
            if snap:
                snapshots[pid] = snap

        conn.close()

        root.add_widget(_lbl(
            f'Молодёжь в составе: {len(youth)} чел.',
            color=_ACCENT, height=26, halign='center', bold=True,
        ))
        if not youth:
            root.add_widget(_lbl(
                'Нет молодёжи (≤21 год или is_youth). Подпишите на вкладке Рынок.',
                color=_DIM, height=50, halign='center',
            ))
            return

        sv   = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))

        hrow = BoxLayout(size_hint_y=None, height=24)
        for txt, sw in [('Ник', 0.18), ('Роль', 0.12), ('Возр', 0.07),
                         ('Mi/Ma/So', 0.16), ('Рост сезон', 0.17),
                         ('Потенц', 0.12), ('Контракт', 0.18)]:
            hrow.add_widget(_col(f'[b]{txt}[/b]', sw, _ACCENT, '12sp'))
        grid.add_widget(hrow)

        for pid, nick, fname, lname, role, age, mi, ma, so, cap, lr, wage, cend in youth:
            pot = _potential(cap)

            if pid in snapshots:
                s_mi, s_ma, s_so = snapshots[pid]
                d = (mi - s_mi) + (ma - s_ma) + (so - s_so)
                def _fmt(x): return f'+{x}' if x >= 0 else str(x)
                growth     = f"{_fmt(mi-s_mi)}/{_fmt(ma-s_ma)}/{_fmt(so-s_so)}"
                grow_color = _GREEN if d > 0 else (_RED if d < 0 else _DIM)
            else:
                growth     = '— нет данных —'
                grow_color = _DIM

            cend_str = str(cend)[:10]

            row = BoxLayout(size_hint_y=None, height=46, spacing=3)
            row.add_widget(_col(f'{nick}\n[color=#888888]{fname} {lname}[/color]',
                                0.18, _WHITE, '12sp'))
            row.add_widget(_col(_ROLE_LABELS.get(role, role or '?'), 0.12, (0.75, 0.85, 1.0, 1)))
            row.add_widget(_col(str(age), 0.07, _DIM))
            row.add_widget(_col(f'{mi}/{ma}/{so}', 0.16, _WHITE))
            row.add_widget(_col(growth, 0.17, grow_color, '12sp'))
            row.add_widget(_col(pot, 0.12, _GOLD))
            row.add_widget(_col(cend_str, 0.18, _DIM))
            grid.add_widget(row)

        sv.add_widget(grid)
        root.add_widget(sv)

    # ── actions ───────────────────────────────────────────────────────────────

    def _set_rf(self, role):
        self.dismiss()
        AcademyPopup(db_name=self.db_name, tab='market', role_filter=role).open()

    def _sign(self, pid, role, wage, years, gd_str):
        err = None
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        try:
            cur.execute("SELECT id FROM teams WHERE player='yes'")
            team = cur.fetchone()
            if not team:
                err = 'Команда игрока не найдена'
            else:
                tid = team[0]
                budget = (cur.execute("SELECT COALESCE(budget,0) FROM teams WHERE id=?", (tid,))
                          .fetchone() or (0,))[0]
                if budget < wage:
                    err = f'Недостаточно средств.\nНужно ${wage:,},  есть ${budget:,}'
                else:
                    slot_col = role if role in _ROLES_ALL else None
                    if slot_col:
                        cur.execute(f"SELECT {slot_col} FROM teams WHERE id=?", (tid,))
                        if not (cur.fetchone() or (None,))[0]:
                            cur.execute(f"UPDATE teams SET {slot_col}=? WHERE id=?", (pid, tid))

                    cend = str(date.fromisoformat(gd_str) + timedelta(days=365 * years))
                    cur.execute(
                        "UPDATE players SET team_id=?, wage=?, contract_end=? WHERE id=?",
                        (tid, wage, cend, pid),
                    )
                    for col in ('poaching_team_id', 'pre_contract_team_id', 'renewal_notified'):
                        try:
                            cur.execute(f"UPDATE players SET {col}=NULL WHERE id=?", (pid,))
                        except Exception:
                            pass

                    cur.execute(
                        "UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (wage, tid),
                    )
                    nick = (cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
                            .fetchone() or ('?',))[0]
                    cur.execute(
                        "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                        (f"Подписан талант: {nick}, {years} г., ${wage:,}/мес.", gd_str, 'Академия'),
                    )
                    conn.commit()
        except Exception as e:
            conn.rollback()
            err = str(e)
        finally:
            conn.close()

        if err:
            Popup(
                title='Ошибка подписания',
                content=Label(text=err, halign='center', valign='middle',
                              color=(1, 0.4, 0.4, 1)),
                size_hint=(0.50, 0.25),
            ).open()
            return

        self.dismiss()
        AcademyPopup(db_name=self.db_name, tab='squad').open()


def show_academy_popup(db_name):
    AcademyPopup(db_name=db_name).open()
