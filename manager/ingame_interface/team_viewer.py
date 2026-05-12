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
            "carry, mid, offlane, partial_support, full_support, "
            "COALESCE(cohesion, 0), COALESCE(tactic, 'balanced') "
            "FROM teams WHERE id=?", (team_id,)
        )
        team = cur.fetchone()
        if not team:
            self.title = 'Команда не найдена'
            self.content = Label(text='Не найдено.')
            conn.close()
            return

        name, logo_file, country, budget, manager, rating, *rest = team
        slot_ids = rest[:5]
        cohesion = rest[5]
        tactic   = rest[6]

        _TACTIC_RU = {
            'balanced':   'Сбаланс.',
            'aggressive': 'Агрессия',
            'farming':    'Фарм',
            'teamplay':   'Команда',
        }
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

        coh_color = (
            (0.2, 0.95, 0.35, 1) if cohesion >= 75 else
            (0.5, 0.95, 0.3,  1) if cohesion >= 50 else
            (1.0, 0.85, 0.25, 1) if cohesion >= 25 else
            (0.9, 0.3,  0.2,  1)
        )
        for label, val, vc in [
            ('Страна',      country or '—',                    _WHITE),
            ('Менеджер',    manager or '—',                    _WHITE),
            ('Рейтинг',     f'{int(rating or 0)} pts',         _WHITE),
            ('Бюджет',      f'${budget or 0:,}',               _WHITE),
            ('Сыгранность', f'{cohesion}/100',                 coh_color),
            ('Тактика',     _TACTIC_RU.get(tactic, tactic),   _ACCENT),
        ]:
            row = _BgBox(bg=_BG_MED, orientation='horizontal',
                         size_hint_y=None, height=34, padding=(8, 0))
            row.add_widget(_lbl(f'{label}:', color=_DIM, height=34))
            row.add_widget(_lbl(val, color=vc, height=34, halign='right'))
            left.add_widget(row)

        # H2H record vs this team
        try:
            h2h = cur.execute(
                "SELECT wins, losses FROM h2h_records WHERE opponent_team_id=?",
                (team_id,)
            ).fetchone()
            if h2h and (h2h[0] or h2h[1]):
                wins, losses = h2h
                h2h_color = _GREEN if wins > losses else (_DIM if wins == losses else (1.0, 0.4, 0.3, 1))
                h2h_row = _BgBox(bg=(0.10, 0.18, 0.10, 1) if wins > losses else _BG_MED,
                                 orientation='horizontal', size_hint_y=None, height=34, padding=(8, 0))
                h2h_row.add_widget(_lbl('H2H:', color=_DIM, height=34))
                h2h_row.add_widget(_lbl(f'{wins}W – {losses}L', color=h2h_color,
                                        height=34, halign='right'))
                left.add_widget(h2h_row)
        except Exception:
            pass

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
        for txt, sw in [('Роль', 0.17), ('Игрок', 0.30),
                        ('Возр', 0.08), ('Micro', 0.11), ('Macro', 0.11), ('Soft', 0.11), ('Зарп.', 0.12)]:
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
                    "soft_skills, wage, face, COALESCE(age, 22) FROM players WHERE id=?",
                    (int(sid),)
                )
                p = cur.fetchone()
                if p:
                    fname, lname, nick, micro, macro, soft, wage, face, age = p
                    micro = micro or 0; macro = macro or 0; soft = soft or 0
                    wage = wage or 0
                    total_wage += wage

                    face_p = f"images/{face}" if face and os.path.exists(f"images/{face}") else None

                    def _cell(t, sw, c=_WHITE):
                        l = Label(text=t, size_hint_x=sw, color=c,
                                  halign='center', valign='middle')
                        l.bind(size=l.setter('text_size'))
                        return l

                    row.add_widget(_cell(ROLE_LABELS.get(role_col, role_col), 0.17, _DIM))
                    if face_p:
                        row.add_widget(Image(source=face_p, size_hint=(None, 1), width=34))
                    row.add_widget(_cell(f'{nick}\n{fname} {lname}', 0.30))
                    row.add_widget(_cell(str(age),  0.08, _DIM))
                    row.add_widget(_cell(str(micro), 0.11, SKILL_COLOR(micro)))
                    row.add_widget(_cell(str(macro), 0.11, SKILL_COLOR(macro)))
                    row.add_widget(_cell(str(soft),  0.11, SKILL_COLOR(soft)))
                    row.add_widget(_cell(f'${wage:,}', 0.12, (0.9, 0.85, 0.5, 1)))
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
            "SELECT id, name, logo, country, COALESCE(rating,0), "
            "COALESCE(cohesion,0), COALESCE(tactic,'balanced') "
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

        _TACTIC_SHORT = {
            'balanced': 'Сб.', 'aggressive': 'Агр.',
            'farming': 'Фарм', 'teamplay': 'Кмд.',
        }

        # Column header
        hdr = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                     size_hint_y=None, height=32, padding=(8, 0))
        for txt, sw in [('', 0.06), ('Команда', 0.34), ('Страна', 0.14),
                        ('Рейтинг', 0.13), ('Сыгр.', 0.10), ('Тактика', 0.10), ('', 0.13)]:
            lbl = Label(text=f'[b]{txt}[/b]', markup=True, size_hint_x=sw,
                        color=_ACCENT, halign='center', valign='middle', font_size='13sp')
            lbl.bind(size=lbl.setter('text_size'))
            hdr.add_widget(lbl)
        grid.add_widget(hdr)

        for rank, (tid, name, logo, country, rating, cohesion, tactic) in enumerate(teams):
            name = name.strip()
            is_p = name == player_name
            # Color tiers: 1st gold, 2nd silver, 3rd bronze, top-8 light blue, player green
            if rank == 0:
                bg, color = (0.22, 0.18, 0.04, 1), _GOLD
            elif rank == 1:
                bg, color = (0.16, 0.16, 0.16, 1), _SILVER
            elif rank == 2:
                bg, color = (0.18, 0.10, 0.04, 1), _BRONZE
            elif rank < 8:
                bg, color = (0.10, 0.14, 0.22, 1), (0.75, 0.85, 1.00, 1)
            elif is_p:
                bg, color = (0.05, 0.20, 0.08, 1), _PLAYER
            else:
                bg, color = (_BG_MED if rank % 2 == 0 else _BG_DARK), _WHITE

            if is_p and rank >= 8:
                bg, color = (0.05, 0.20, 0.08, 1), _PLAYER

            row = _BgBox(bg=bg, orientation='horizontal',
                         size_hint_y=None, height=52, padding=(6, 4), spacing=6)

            # Rank number
            rank_lbl = Label(
                text=f'[b]{rank+1}[/b]', markup=True, size_hint_x=0.06,
                color=color, halign='center', valign='middle', font_size='14sp',
            )
            rank_lbl.bind(size=rank_lbl.setter('text_size'))
            row.add_widget(rank_lbl)

            # Logo
            logo_w = _logo(logo, size=38) if logo else Label(
                text='', size_hint=(None, None), size=(38, 38))
            logo_w.size_hint_x = None
            logo_w.width = 42

            # Name
            mark = '  [МОYA]' if is_p else ''
            name_lbl = Label(
                text=f'[b]{name}{mark}[/b]', markup=True,
                size_hint_x=0.34, color=color, font_size='14sp',
                halign='left', valign='middle',
            )
            name_lbl.bind(size=name_lbl.setter('text_size'))
            row.add_widget(name_lbl)

            country_lbl = Label(
                text=country or '—', size_hint_x=0.14,
                color=_DIM, halign='center', valign='middle', font_size='13sp',
            )
            row.add_widget(country_lbl)

            rating_lbl = Label(
                text=f'[b]{int(rating)}[/b] pts', markup=True, size_hint_x=0.13,
                color=color, halign='center', valign='middle', font_size='14sp',
            )
            rating_lbl.bind(size=rating_lbl.setter('text_size'))
            row.add_widget(rating_lbl)

            coh_c = (
                (0.2, 0.95, 0.35, 1) if cohesion >= 75 else
                (1.0, 0.85, 0.25, 1) if cohesion >= 40 else
                (0.9, 0.3,  0.2,  1)
            )
            row.add_widget(Label(
                text=str(cohesion), size_hint_x=0.10,
                color=coh_c, halign='center', valign='middle', font_size='13sp',
            ))
            row.add_widget(Label(
                text=_TACTIC_SHORT.get(tactic, tactic), size_hint_x=0.10,
                color=_ACCENT, halign='center', valign='middle', font_size='13sp',
            ))

            view_btn = Button(
                text='Подробнее', size_hint_x=0.13,
                background_color=(0.18, 0.40, 0.70, 1),
                background_normal='', font_size='13sp',
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
