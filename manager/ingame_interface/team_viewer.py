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

_ACCENT  = (0.35, 0.85, 1.00, 1)
_GOLD    = (1.00, 0.85, 0.25, 1)
_SILVER  = (0.85, 0.85, 0.85, 1)
_BRONZE  = (0.80, 0.55, 0.30, 1)
_GREEN   = (0.20, 0.88, 0.35, 1)
_WHITE   = (0.92, 0.92, 0.92, 1)
_DIM     = (0.55, 0.55, 0.55, 1)
_PLAYER  = (0.30, 1.00, 0.50, 1)
_YELLOW  = (1.00, 0.90, 0.25, 1)

_BG_DARK  = (0.10, 0.10, 0.12, 1)
_BG_MED   = (0.15, 0.15, 0.18, 1)
_BG_PANEL = (0.12, 0.18, 0.22, 1)
_BG_HEAD  = (0.10, 0.22, 0.32, 1)

ROLE_LABELS = {
    'carry': 'Carry',  'mid': 'Mid',  'offlane': 'Offlane',
    'partial_support': 'Support 4',   'full_support': 'Support 5',
}
ROLES = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']

SKILL_COLOR = lambda v: (
    (0.3, 1.0, 0.4, 1) if v >= 85 else
    (1.0, 0.9, 0.3, 1) if v >= 65 else
    (1.0, 0.45, 0.3, 1)
)


def _lbl(text, height=32, color=_WHITE, bold=False, halign='left'):
    t = f'[b]{text}[/b]' if bold else text
    lbl = Label(text=t, markup=True,
                size_hint_y=None, height=height,
                color=color, halign=halign, valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _logo(logo, size=120):
    if logo:
        p = f"images/{logo}"
        if os.path.exists(p):
            return Image(source=p, size_hint=(None, None), size=(size, size),
                         allow_stretch=True, keep_ratio=True)
    lbl = Label(text='?', size_hint=(None, None), size=(size, size),
                color=_DIM, font_size=f'{size//2}sp')
    return lbl


class _BgBox(BoxLayout):
    def __init__(self, bg=_BG_MED, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*bg)
            self._rect = Rectangle()
        self.bind(pos=self._upd, size=self._upd)
    def _upd(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


def _auto_grid():
    g = GridLayout(cols=1, size_hint_y=None, spacing=2)
    g.bind(minimum_height=g.setter('height'))
    return g


# ── TeamViewerPopup ───────────────────────────────────────────────────────────

class TeamViewerPopup(Popup):
    def __init__(self, db_name, team_id, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.88, 0.88)
        self.auto_dismiss = True
        self._build(db_name, team_id)

    def _build(self, db_name, team_id):
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        cur.execute(
            "SELECT name, logo, country, budget, manager, rating, "
            "carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE id=?", (team_id,)
        )
        team = cur.fetchone()
        if not team:
            self.title = 'Команда не найдена'
            self.content = Label(text='Не найдено.')
            conn.close()
            return

        name, logo_file, country, budget, manager, rating, *slot_ids = team
        self.title = name.strip()

        root = BoxLayout(orientation='horizontal', spacing=8, padding=8)

        # ── left: logo + info ────────────────────────────────
        left = _auto_grid()
        left_sv = ScrollView(size_hint=(0.35, 1))

        logo_box = _BgBox(bg=_BG_PANEL, orientation='vertical',
                          size_hint_y=None, height=160,
                          padding=10, spacing=6)
        logo_img = _logo(logo_file, size=120)
        logo_box.add_widget(logo_img)
        left.add_widget(logo_box)

        for label, val in [
            ('Страна',    country or '—'),
            ('Менеджер',  manager or '—'),
            ('Рейтинг',   f'{int(rating or 0)} pts'),
            ('Бюджет',    f'${budget or 0:,}'),
        ]:
            row = _BgBox(bg=_BG_MED, orientation='horizontal',
                         size_hint_y=None, height=34, padding=(8, 0))
            row.add_widget(_lbl(f'{label}:', color=_DIM, height=34))
            row.add_widget(_lbl(val, color=_WHITE, height=34, halign='right'))
            left.add_widget(row)

        left_sv.add_widget(left)
        root.add_widget(left_sv)

        # ── right: roster ────────────────────────────────────
        right = _auto_grid()
        right_sv = ScrollView(size_hint=(0.65, 1))

        hdr = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                     size_hint_y=None, height=34)
        hdr.add_widget(_lbl('  Состав', color=_ACCENT, bold=True, height=34))
        right.add_widget(hdr)

        # Column header
        col_hdr = _BgBox(bg=(0.08, 0.10, 0.14, 1), orientation='horizontal',
                         size_hint_y=None, height=26, padding=(4, 0))
        for txt, sw in [('Роль', 0.2), ('Игрок', 0.35),
                        ('Micro', 0.12), ('Macro', 0.12), ('Soft', 0.12), ('Зарп.', 0.09)]:
            lbl = Label(text=f'[b]{txt}[/b]', markup=True,
                        size_hint_x=sw, color=_ACCENT,
                        halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            col_hdr.add_widget(lbl)
        right.add_widget(col_hdr)

        total_wage = 0
        for i, (role_col, sid) in enumerate(zip(ROLES, slot_ids)):
            bg = _BG_MED if i % 2 == 0 else _BG_DARK
            row = _BgBox(bg=bg, orientation='horizontal',
                         size_hint_y=None, height=40, padding=(4, 0))
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
                                  halign='center', valign='middle')
                        l.bind(size=l.setter('text_size'))
                        return l

                    row.add_widget(_cell(ROLE_LABELS.get(role_col, role_col), 0.2, _DIM))
                    if face_p:
                        row.add_widget(Image(source=face_p,
                                            size_hint=(None, 1), width=36))
                    row.add_widget(_cell(f'{nick}\n{fname} {lname}', 0.35))
                    row.add_widget(_cell(str(micro), 0.12, SKILL_COLOR(micro)))
                    row.add_widget(_cell(str(macro), 0.12, SKILL_COLOR(macro)))
                    row.add_widget(_cell(str(soft),  0.12, SKILL_COLOR(soft)))
                    row.add_widget(_cell(f'${wage:,}', 0.09, (0.9, 0.85, 0.5, 1)))
                else:
                    row.add_widget(_lbl(f'  {ROLE_LABELS.get(role_col, role_col)}: нет данных',
                                        color=_DIM, height=40))
            else:
                row.add_widget(_lbl(f'  {ROLE_LABELS.get(role_col, role_col)}: — свободно —',
                                    color=_DIM, height=40))
            right.add_widget(row)

        wage_row = _BgBox(bg=_BG_PANEL, orientation='horizontal',
                          size_hint_y=None, height=34, padding=(8, 0))
        wage_row.add_widget(_lbl(f'  Зарплатный фонд: ${total_wage:,}/мес',
                                 color=(0.9, 0.85, 0.5, 1), height=34))
        right.add_widget(wage_row)

        right_sv.add_widget(right)
        root.add_widget(right_sv)

        conn.close()

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=48,
            background_color=(0.65, 0.18, 0.18, 1), background_normal='',
        )
        close_btn.bind(on_press=self.dismiss)

        layout = BoxLayout(orientation='vertical', spacing=4, padding=4)
        layout.add_widget(root)
        layout.add_widget(close_btn)
        self.content = layout


# ── LeaguePopup ───────────────────────────────────────────────────────────────

class LeaguePopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Команды лиги'
        self.size_hint = (0.92, 0.92)
        self._db_name = db_name
        self._build()

    def _build(self):
        conn = sqlite3.connect(self._db_name)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, logo, country, COALESCE(rating,0) "
            "FROM teams ORDER BY COALESCE(rating,0) DESC"
        )
        teams = cur.fetchall()
        cur.execute("SELECT name FROM teams WHERE player='yes'")
        pr = cur.fetchone()
        player_name = (pr[0] if pr else '').strip()
        conn.close()

        grid = _auto_grid()
        grid.padding = (8, 4)
        grid.spacing = 4

        # Column header
        hdr = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                     size_hint_y=None, height=30, padding=(8, 0))
        for txt, sw in [('', 0.06), ('Команда', 0.45),
                        ('Страна', 0.20), ('Рейтинг', 0.15), ('', 0.14)]:
            lbl = Label(text=f'[b]{txt}[/b]', markup=True, size_hint_x=sw,
                        color=_ACCENT, halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            hdr.add_widget(lbl)
        grid.add_widget(hdr)

        for rank, (tid, name, logo, country, rating) in enumerate(teams):
            name = name.strip()
            is_p = name == player_name
            if rank == 0:
                bg, color = (0.20, 0.18, 0.04, 1), _GOLD
            elif rank == 1:
                bg, color = (0.14, 0.14, 0.14, 1), _SILVER
            elif rank == 2:
                bg, color = (0.16, 0.10, 0.04, 1), _BRONZE
            elif is_p:
                bg, color = (0.05, 0.20, 0.08, 1), _PLAYER
            else:
                bg, color = (_BG_MED if rank % 2 == 0 else _BG_DARK), _WHITE

            row = _BgBox(bg=bg, orientation='horizontal',
                         size_hint_y=None, height=52, padding=(6, 4), spacing=6)

            # Logo
            logo_w = _logo(logo, size=40) if logo else Label(
                text='', size_hint=(None, None), size=(40, 40))
            logo_w.size_hint_x = None
            logo_w.width = 44
            row.add_widget(logo_w)

            # Name + star
            mark = ' ★' if is_p else ''
            name_lbl = Label(
                text=f'[b]{name}{mark}[/b]', markup=True,
                size_hint_x=0.42, color=color,
                halign='left', valign='middle',
            )
            name_lbl.bind(size=name_lbl.setter('text_size'))
            row.add_widget(name_lbl)

            country_lbl = Label(
                text=country or '—', size_hint_x=0.20,
                color=_DIM, halign='center', valign='middle',
            )
            row.add_widget(country_lbl)

            rating_lbl = Label(
                text=f'{int(rating)} pts', size_hint_x=0.15,
                color=color, halign='right', valign='middle',
            )
            row.add_widget(rating_lbl)

            view_btn = Button(
                text='Состав', size_hint_x=0.14,
                background_color=(0.18, 0.45, 0.75, 1),
                background_normal='',
            )
            view_btn.bind(on_press=lambda _, t=tid: self._open_team(t))
            row.add_widget(view_btn)

            grid.add_widget(row)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=50,
            background_color=(0.65, 0.18, 0.18, 1), background_normal='',
        )
        close_btn.bind(on_press=self.dismiss)

        layout = BoxLayout(orientation='vertical', spacing=4, padding=4)
        layout.add_widget(scroll)
        layout.add_widget(close_btn)
        self.content = layout

    def _open_team(self, team_id):
        TeamViewerPopup(db_name=self._db_name, team_id=team_id).open()
