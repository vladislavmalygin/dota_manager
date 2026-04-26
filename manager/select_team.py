import sqlite3
import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, RoundedRectangle

from core import DotaPopup

_ACCENT  = (0.35, 0.85, 1.00, 1)
_GREEN   = (0.20, 0.88, 0.35, 1)
_YELLOW  = (1.00, 0.90, 0.25, 1)
_WHITE   = (0.92, 0.92, 0.92, 1)
_DIM     = (0.55, 0.55, 0.55, 1)
_RED     = (0.90, 0.28, 0.20, 1)

_BG_DARK  = (0.08, 0.08, 0.10, 1)
_BG_MED   = (0.13, 0.13, 0.16, 1)
_BG_PANEL = (0.10, 0.16, 0.22, 1)
_BG_HEAD  = (0.08, 0.18, 0.28, 1)
_BG_SEL   = (0.08, 0.25, 0.12, 1)   # selected team highlight

ROLES = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
ROLE_LABELS = {
    'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Offlane',
    'partial_support': 'Sup 4', 'full_support': 'Sup 5',
}
SKILL_COLOR = lambda v: (
    (0.3, 1.0, 0.4, 1) if v >= 85 else
    (1.0, 0.9, 0.3, 1) if v >= 65 else
    (1.0, 0.45, 0.3, 1)
)


class _BgBox(BoxLayout):
    def __init__(self, bg=_BG_MED, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._col = Color(*bg)
            self._rect = Rectangle()
        self.bind(pos=self._upd, size=self._upd)

    def set_bg(self, rgba):
        self._col.rgba = rgba

    def _upd(self, *_):
        self._rect.pos  = self.pos
        self._rect.size = self.size


def _lbl(text, height=30, color=_WHITE, bold=False, halign='left'):
    t = f'[b]{text}[/b]' if bold else text
    lbl = Label(text=t, markup=True,
                size_hint_y=None, height=height,
                color=color, halign=halign, valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _auto_grid():
    g = GridLayout(cols=1, size_hint_y=None, spacing=2)
    g.bind(minimum_height=g.setter('height'))
    return g


def _logo_path(logo):
    if logo:
        p = f"images/{logo}"
        if os.path.exists(p):
            return p
    return None


class SelectTeamPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Выбор команды'
        self.size_hint = (1, 1)

        from new_game import NewGamePopup
        self._db_name = NewGamePopup.get_db_name(self)
        self._selected_team = None
        self._logo_buttons = {}   # team_id → button widget

        root = BoxLayout(orientation='horizontal', spacing=6, padding=6)

        # ── left: logo grid ───────────────────────────────────
        self._logo_grid = GridLayout(cols=4, size_hint_y=None, spacing=6)
        self._logo_grid.bind(minimum_height=self._logo_grid.setter('height'))

        left_sv = ScrollView(size_hint=(0.45, 1))
        left_bg = _BgBox(bg=_BG_DARK, orientation='vertical', size_hint=(1, 1))
        left_bg.add_widget(left_sv)
        left_sv.add_widget(self._logo_grid)
        root.add_widget(left_bg)

        # ── right: info panel ─────────────────────────────────
        self._info_grid = _auto_grid()
        self._info_grid.padding = (6, 4)
        self._info_grid.spacing = 3

        right_sv = ScrollView(size_hint=(0.55, 1))
        right_bg = _BgBox(bg=_BG_PANEL, orientation='vertical', size_hint=(1, 1))
        right_bg.add_widget(right_sv)
        right_sv.add_widget(self._info_grid)
        root.add_widget(right_bg)

        # ── bottom bar ────────────────────────────────────────
        self._select_btn = Button(
            text='Выбрать команду',
            size_hint_y=None, height=52,
            background_color=(0.10, 0.60, 0.18, 1),
            background_normal='',
            disabled=True,
        )
        self._select_btn.bind(on_press=self._confirm_select)

        layout = BoxLayout(orientation='vertical', spacing=4, padding=4)
        layout.add_widget(root)
        layout.add_widget(self._select_btn)
        self.content = layout

        self._load_teams()
        self._show_placeholder()

    # ── load teams ────────────────────────────────────────────

    def _load_teams(self):
        conn = sqlite3.connect(self._db_name)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, logo, country, carry, mid, offlane, "
            "partial_support, full_support, budget FROM teams"
        )
        teams = cur.fetchall()
        conn.close()

        for team in teams:
            tid = team[0]
            logo_file = team[2]
            path = _logo_path(logo_file)

            btn = Button(
                size_hint=(None, None), size=(96, 96),
                background_normal=path or '',
                background_color=(1, 1, 1, 1) if path else (0.2, 0.2, 0.25, 1),
                border=(0, 0, 0, 0),
            )
            if not path:
                btn.text = team[1][:8]
                btn.color = _WHITE
                btn.font_size = '10sp'

            btn.bind(on_press=lambda inst, t=team: self._on_team_selected(t))
            self._logo_grid.add_widget(btn)
            self._logo_buttons[tid] = btn

    # ── placeholder ───────────────────────────────────────────

    def _show_placeholder(self):
        self._info_grid.clear_widgets()
        self._info_grid.add_widget(_lbl(
            '  Выберите команду слева',
            height=50, color=_DIM, halign='center',
        ))

    # ── team selected ─────────────────────────────────────────

    def _on_team_selected(self, team):
        tid, name, logo_file, country, carry, mid, offlane, sup4, sup5, budget = team
        self._selected_team = team

        # Highlight selected button
        for t_id, btn in self._logo_buttons.items():
            btn.background_color = (1, 1, 1, 1) if _logo_path(
                team[2] if t_id == tid else None
            ) else (0.2, 0.2, 0.25, 1)
        for t_id, btn in self._logo_buttons.items():
            btn.canvas.before.clear()
            with btn.canvas.before:
                if t_id == tid:
                    Color(0.2, 0.9, 0.4, 0.3)
                    RoundedRectangle(pos=btn.pos, size=btn.size, radius=[6])
            btn.bind(pos=lambda b, v: self._refresh_highlight(b, b == self._logo_buttons.get(tid)))
        self._select_btn.disabled = False
        self._render_team_info(team)

    def _refresh_highlight(self, btn, active):
        btn.canvas.before.clear()
        if active:
            with btn.canvas.before:
                Color(0.2, 0.9, 0.4, 0.3)
                RoundedRectangle(pos=btn.pos, size=btn.size, radius=[6])

    # ── render team info ──────────────────────────────────────

    def _render_team_info(self, team):
        tid, name, logo_file, country, carry, mid, offlane, sup4, sup5, budget = team
        self._info_grid.clear_widgets()

        conn = sqlite3.connect(self._db_name)
        cur = conn.cursor()

        # ── logo + name header ────────────────────────────────
        header = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                        size_hint_y=None, height=110, padding=8, spacing=10)
        path = _logo_path(logo_file)
        if path:
            header.add_widget(Image(source=path, size_hint=(None, None),
                                    size=(90, 90), allow_stretch=True, keep_ratio=True))
        name_box = BoxLayout(orientation='vertical')
        name_lbl = Label(text=f'[b]{name}[/b]', markup=True,
                         color=_ACCENT, halign='left', valign='middle', font_size='17sp')
        name_lbl.bind(size=name_lbl.setter('text_size'))
        country_lbl = Label(text=country or '—', color=_DIM,
                            halign='left', valign='top', font_size='13sp')
        country_lbl.bind(size=country_lbl.setter('text_size'))
        name_box.add_widget(name_lbl)
        name_box.add_widget(country_lbl)
        header.add_widget(name_box)
        self._info_grid.add_widget(header)

        # budget
        brow = _BgBox(bg=_BG_MED, orientation='horizontal',
                      size_hint_y=None, height=34, padding=(10, 0))
        brow.add_widget(_lbl('Бюджет:', color=_DIM, height=34))
        brow.add_widget(_lbl(f'${budget or 0:,}', color=_YELLOW,
                             height=34, halign='right', bold=True))
        self._info_grid.add_widget(brow)

        # roster header
        rhdr = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                      size_hint_y=None, height=28)
        rhdr.add_widget(_lbl('  Состав', color=_ACCENT, bold=True, height=28))
        self._info_grid.add_widget(rhdr)

        # column header
        chdr = _BgBox(bg=(0.08, 0.10, 0.14, 1), orientation='horizontal',
                      size_hint_y=None, height=24, padding=(4, 0))
        for txt, sw in [('Роль', 0.18), ('Игрок', 0.38),
                        ('Mic', 0.12), ('Mac', 0.12), ('Sft', 0.12), ('Зарп', 0.08)]:
            l = Label(text=f'[b]{txt}[/b]', markup=True, size_hint_x=sw,
                      color=_ACCENT, halign='center', valign='middle', font_size='11sp')
            l.bind(size=l.setter('text_size'))
            chdr.add_widget(l)
        self._info_grid.add_widget(chdr)

        slot_ids = [carry, mid, offlane, sup4, sup5]
        total_wage = 0
        for i, (role_col, sid) in enumerate(zip(ROLES, slot_ids)):
            bg = _BG_MED if i % 2 == 0 else _BG_DARK
            row = _BgBox(bg=bg, orientation='horizontal',
                         size_hint_y=None, height=40, padding=(4, 2))
            if sid:
                cur.execute(
                    "SELECT name, surname, nickname, micro_skills, macro_skills, "
                    "soft_skills, wage, face FROM players WHERE id=?", (int(sid),)
                )
                p = cur.fetchone()
                if p:
                    fname, lname, nick, micro, macro, soft, wage, face = p
                    micro = micro or 0; macro = macro or 0; soft = soft or 0
                    wage = wage or 0
                    total_wage += wage

                    face_p = f"images/{face}" if face and os.path.exists(f"images/{face}") else None

                    def _cell(t, sw, c=_WHITE):
                        l = Label(text=t, size_hint_x=sw, color=c,
                                  halign='center', valign='middle', font_size='12sp')
                        l.bind(size=l.setter('text_size'))
                        return l

                    row.add_widget(_cell(ROLE_LABELS.get(role_col, role_col), 0.18, _DIM))
                    if face_p:
                        row.add_widget(Image(source=face_p,
                                            size_hint=(None, 1), width=34))
                    name_str = f'{nick}\n{fname} {lname[:6]}.'
                    row.add_widget(_cell(name_str, 0.38))
                    row.add_widget(_cell(str(micro), 0.12, SKILL_COLOR(micro)))
                    row.add_widget(_cell(str(macro), 0.12, SKILL_COLOR(macro)))
                    row.add_widget(_cell(str(soft),  0.12, SKILL_COLOR(soft)))
                    row.add_widget(_cell(f'${wage//1000}k', 0.08, (0.9, 0.85, 0.5, 1)))
            else:
                row.add_widget(_lbl(
                    f'  {ROLE_LABELS.get(role_col, role_col)}: — свободно —',
                    color=_DIM, height=40,
                ))
            self._info_grid.add_widget(row)

        if total_wage:
            wrow = _BgBox(bg=_BG_PANEL, orientation='horizontal',
                          size_hint_y=None, height=32, padding=(8, 0))
            wrow.add_widget(_lbl(f'  Фонд зарплат: ${total_wage:,}/мес',
                                 color=(0.9, 0.85, 0.5, 1), height=32))
            self._info_grid.add_widget(wrow)

        conn.close()

    # ── confirm selection ─────────────────────────────────────

    def _confirm_select(self, _):
        if not self._selected_team:
            return
        from new_game import NewGamePopup
        manager_nickname = NewGamePopup.get_nickname(self)
        tid, name = self._selected_team[0], self._selected_team[1]

        conn = sqlite3.connect(self._db_name)
        conn.execute("UPDATE teams SET manager=? WHERE id=?", (manager_nickname, tid))
        conn.execute("UPDATE teams SET player='no'")
        conn.execute("UPDATE teams SET player='yes' WHERE id=?", (tid,))
        conn.commit()
        conn.close()

        self.dismiss()
        DotaPopup(self._db_name).open_popup(self._db_name)
