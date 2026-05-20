"""
Feature 9: Custom Invitational Tournament setup popup.
Player configures prizepool, format, and teams, then launches the event.
"""
import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton


class InvitationalSetupPopup(Popup):
    def __init__(self, db_name, on_launch, **kwargs):
        super().__init__(**kwargs)
        self.db_name   = db_name
        self.on_launch = on_launch
        self.title     = ''
        self.size_hint = (0.70, 0.80)
        self.background_color = (1, 1, 1, 0)

        self._prizepool  = 50_000
        self._fmt        = 8
        self._selected   = set()  # AI team names selected

        self._build()

    def _build(self):
        conn = sqlite3.connect(self.db_name)
        budget_row = conn.execute(
            "SELECT COALESCE(budget,0) FROM teams WHERE player='yes'"
        ).fetchone()
        my_team_row = conn.execute(
            "SELECT name FROM teams WHERE player='yes'"
        ).fetchone()
        ai_teams = conn.execute(
            "SELECT id, name FROM teams WHERE player!='yes' ORDER BY COALESCE(rating,0) DESC"
        ).fetchall()
        conn.close()

        budget    = budget_row[0] if budget_row else 0
        my_team   = my_team_row[0].strip() if my_team_row else 'Ваша команда'
        self._my_team = my_team

        root = BoxLayout(orientation='vertical', padding=10, spacing=8)

        # Title
        hdr = Label(
            text='[b]Организовать инвитэйшнл[/b]',
            markup=True, color=(1.0, 0.85, 0.20, 1),
            size_hint_y=None, height=44, halign='center', valign='middle',
        )
        hdr.bind(size=hdr.setter('text_size'))
        root.add_widget(hdr)

        budget_lbl = Label(
            text=f'Ваш бюджет: ${budget:,}',
            color=(0.65, 0.95, 0.55, 1),
            size_hint_y=None, height=28, halign='center', valign='middle',
        )
        budget_lbl.bind(size=budget_lbl.setter('text_size'))
        root.add_widget(budget_lbl)

        # ── Prizepool ─────────────────────────────────────────────────────────
        pz_lbl = Label(
            text='Призовой фонд:', color=(0.80, 0.80, 1.00, 1),
            size_hint_y=None, height=28, halign='left', valign='middle',
        )
        pz_lbl.bind(size=pz_lbl.setter('text_size'))
        root.add_widget(pz_lbl)

        pz_row = BoxLayout(size_hint_y=None, height=44, spacing=6)
        self._pz_btns = {}
        for amt in [50_000, 100_000, 200_000]:
            can = budget >= amt
            tb  = ToggleButton(
                text=f'${amt//1000}k',
                group='prizepool',
                state='down' if amt == 50_000 else 'normal',
                background_normal='',
                background_color=(0.20, 0.45, 0.65, 1) if can else (0.3, 0.3, 0.3, 1),
                disabled=not can,
            )
            tb.bind(on_press=lambda inst, a=amt: self._set_prizepool(a))
            pz_row.add_widget(tb)
            self._pz_btns[amt] = tb
        root.add_widget(pz_row)

        # ── Format ────────────────────────────────────────────────────────────
        fmt_lbl = Label(
            text='Формат:', color=(0.80, 0.80, 1.00, 1),
            size_hint_y=None, height=28, halign='left', valign='middle',
        )
        fmt_lbl.bind(size=fmt_lbl.setter('text_size'))
        root.add_widget(fmt_lbl)

        fmt_row = BoxLayout(size_hint_y=None, height=44, spacing=6)
        for n in [8, 16]:
            tb = ToggleButton(
                text=f'{n} команд',
                group='format',
                state='down' if n == 8 else 'normal',
                background_normal='',
                background_color=(0.25, 0.40, 0.60, 1),
            )
            tb.bind(on_press=lambda inst, f=n: self._set_fmt(f))
            fmt_row.add_widget(tb)
        root.add_widget(fmt_row)

        self._slots_lbl = Label(
            text=f'Выберите до {self._fmt - 1} команд (ваша добавлена автоматически):',
            color=(0.75, 0.75, 0.75, 1),
            size_hint_y=None, height=26, halign='left', valign='middle',
        )
        self._slots_lbl.bind(size=self._slots_lbl.setter('text_size'))
        root.add_widget(self._slots_lbl)

        # ── Team list ─────────────────────────────────────────────────────────
        sv = ScrollView(size_hint=(1, 1))
        self._teams_grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        self._teams_grid.bind(minimum_height=self._teams_grid.setter('height'))

        self._ai_teams = ai_teams
        self._team_btns = {}
        for tid, tname in ai_teams:
            name = tname.strip()
            tb = ToggleButton(
                text=name, size_hint_y=None, height=38,
                background_normal='',
                background_color=(0.18, 0.32, 0.50, 1),
            )
            tb.bind(on_press=lambda inst, n=name: self._toggle_team(n))
            self._teams_grid.add_widget(tb)
            self._team_btns[name] = tb

        sv.add_widget(self._teams_grid)
        root.add_widget(sv)

        # ── Launch ────────────────────────────────────────────────────────────
        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)

        launch_btn = Button(
            text='Провести инвитэйшнл',
            background_color=(0.18, 0.55, 0.22, 1), background_normal='',
        )
        launch_btn.bind(on_press=self._on_launch)
        btn_row.add_widget(launch_btn)

        cancel_btn = Button(
            text='Отмена',
            background_color=(0.50, 0.15, 0.15, 1), background_normal='',
        )
        cancel_btn.bind(on_press=self.dismiss)
        btn_row.add_widget(cancel_btn)

        root.add_widget(btn_row)

        self.content = root

    def _set_prizepool(self, amt):
        self._prizepool = amt

    def _set_fmt(self, n):
        self._fmt = n
        self._slots_lbl.text = (
            f'Выберите до {n - 1} команд (ваша добавлена автоматически):'
        )
        # Deselect excess teams if limit reduced
        limit = n - 1
        while len(self._selected) > limit:
            extra = next(iter(self._selected))
            self._selected.discard(extra)
            if extra in self._team_btns:
                self._team_btns[extra].state = 'normal'

    def _toggle_team(self, name):
        limit = self._fmt - 1
        if name in self._selected:
            self._selected.discard(name)
        else:
            if len(self._selected) >= limit:
                # Deselect oldest
                oldest = next(iter(self._selected))
                self._selected.discard(oldest)
                if oldest in self._team_btns:
                    self._team_btns[oldest].state = 'normal'
            self._selected.add(name)

    def _on_launch(self, _inst):
        teams = [self._my_team] + list(self._selected)
        if len(teams) < 4:
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            Popup(
                content=Label(text='Выберите минимум 3 команды-соперника'),
                size_hint=(0.50, 0.22),
            ).open()
            return
        self.dismiss()
        self.on_launch(self._prizepool, self._fmt, teams)
