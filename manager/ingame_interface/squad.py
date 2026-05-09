import sqlite3
import os

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior


class _FaceBtn(ButtonBehavior, Image):
    pass

from logic.ai import _BASE_XP_PER_GAME
import ui_theme as T


ROLE_ORDER  = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
ROLE_LABELS = {
    'carry':           'Carry (1)',
    'mid':             'Mid (2)',
    'offlane':         'Offlane (3)',
    'partial_support': 'Support (4)',
    'full_support':    'Support (5)',
}
ROLE_SHORT = {
    'carry':           'Carry',
    'mid':             'Mid',
    'offlane':         'Offlane',
    'partial_support': 'Sup 4',
    'full_support':    'Sup 5',
}

_PRIORITY_LABEL = {
    'micro_skills': 'M',
    'macro_skills': 'Ma',
    'soft_skills':  'S',
    None:           '—',
}
_PRIORITY_COLOR = {
    'micro_skills': (0.10, 0.55, 0.90, 1),
    'macro_skills': (0.15, 0.70, 0.25, 1),
    'soft_skills':  (0.80, 0.55, 0.10, 1),
    None:           (0.30, 0.30, 0.30, 1),
}


def _skill_color(value):
    return T.skill_color(value)


def _cohesion_color(v):
    return T.cohesion_color(v)


def _lbl(text, height=36, color=(1, 1, 1, 1), bold=False, halign='left'):
    if bold:
        text = f'[b]{text}[/b]'
    lbl = Label(
        text=text, markup=bold,
        size_hint_y=None, height=height,
        color=color, halign=halign, valign='middle',
        font_size='14sp',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _header(text, height=46):
    lbl = Label(
        text=f'[b]{text}[/b]', markup=True,
        size_hint_y=None, height=height,
        color=(0.4, 0.9, 1.0, 1), halign='center', valign='middle',
        font_size='16sp',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _skill_bar(value, cap=100, sw=0.09):
    """Colored progress bar with number label for a skill stat."""
    from kivy.uix.widget import Widget
    from kivy.graphics import Color as GColor, Rectangle as GRect
    container = BoxLayout(size_hint_x=sw, orientation='vertical',
                          padding=(2, 4), spacing=1)
    bar_box = BoxLayout(size_hint_y=None, height=10)
    pct = max(0.0, min(1.0, value / 100.0))
    if value >= 85:
        bar_color = (0.25, 0.95, 0.40, 1)
    elif value >= 65:
        bar_color = (0.95, 0.85, 0.20, 1)
    else:
        bar_color = (0.95, 0.35, 0.25, 1)

    fill = Widget(size_hint=(pct, 1))
    with fill.canvas.before:
        GColor(*bar_color)
        _r = GRect()
    fill.bind(pos=lambda w, _: setattr(_r, 'pos', w.pos),
              size=lambda w, _: setattr(_r, 'size', w.size))

    empty = Widget(size_hint=(1 - pct, 1))
    with empty.canvas.before:
        GColor(0.20, 0.20, 0.22, 1)
        _r2 = GRect()
    empty.bind(pos=lambda w, _: setattr(_r2, 'pos', w.pos),
               size=lambda w, _: setattr(_r2, 'size', w.size))

    bar_box.add_widget(fill)
    bar_box.add_widget(empty)

    num = Label(text=str(value), color=bar_color, font_size='13sp',
                size_hint_y=None, height=18, halign='center', valign='middle')
    num.bind(size=num.setter('text_size'))

    container.add_widget(bar_box)
    container.add_widget(num)
    return container


def _morale_dots(morale):
    """Show morale as filled/empty dots."""
    filled = round(morale)
    dots = ''.join(['●' if i < filled else '○' for i in range(10)])
    if morale >= 7:
        color = (0.25, 0.95, 0.40, 1)
    elif morale >= 4:
        color = (0.95, 0.85, 0.20, 1)
    else:
        color = (0.95, 0.35, 0.25, 1)
    lbl = Label(text=dots, color=color, font_size='11sp',
                size_hint_y=None, height=22,
                halign='center', valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _row_bg(row, color):
    """Paint a 3px left border on a row to signal player status."""
    from kivy.graphics import Color as GColor, Rectangle as GRect
    with row.canvas.before:
        GColor(*color)
        _stripe = GRect(size=(3, row.height))
    row.bind(
        pos =lambda w, _: setattr(_stripe, 'pos',  w.pos),
        size=lambda w, _: setattr(_stripe, 'size', (3, w.height)),
    )


def _chips_box(chips):
    """BoxLayout containing chip labels, or empty widget if no chips."""
    box = BoxLayout(size_hint=(None, None), width=66, height=18, spacing=3)
    for chip in chips:
        box.add_widget(T.make_chip(*chip))
    return box


# ─── Priority popup ───────────────────────────────────────────────────────────

class SetPriorityPopup(Popup):
    def __init__(self, db_name, player_id, on_changed, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.player_id = player_id
        self.on_changed = on_changed
        self.size_hint = (0.55, 0.60)
        self.auto_dismiss = False
        self._build()

    def _build(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute(
            "SELECT nickname, micro_skills, macro_skills, soft_skills, "
            "COALESCE(skill_cap, 300), COALESCE(competence, 5), "
            "COALESCE(train_xp, 0.0), train_priority "
            "FROM players WHERE id=?",
            (self.player_id,),
        )
        p = cur.fetchone()
        conn.close()

        if not p:
            self.content = Label(text='Игрок не найден.')
            return

        nick, micro, macro, soft, skill_cap, competence, xp, priority = p
        micro = micro or 0; macro = macro or 0; soft = soft or 0
        total = micro + macro + soft

        self.title = f'Тренировка: {nick}'

        xp_per_game = (competence / 5.0) * _BASE_XP_PER_GAME
        games_per_pt = int(1.0 / xp_per_game + 0.5) if xp_per_game > 0 else 99

        grid = GridLayout(cols=1, spacing=8, padding=10)

        grid.add_widget(_lbl(
            f'  Micro: {micro}   Macro: {macro}   Soft: {soft}',
            bold=True,
        ))
        grid.add_widget(_lbl(
            f'  Потенциал: {total}/{skill_cap}   XP накоплен: {xp:.2f}',
            color=(0.7, 0.85, 1.0, 1),
        ))
        grid.add_widget(_lbl(
            f'  Компетентность: {competence}/10   '
            f'Рост: {xp_per_game:.2f} XP/игру (~1 очко каждые {games_per_pt} игр)',
            color=(0.9, 0.9, 0.5, 1), height=30,
        ))
        grid.add_widget(_lbl('  Выбери приоритетный навык:', bold=True, height=30))

        for skill_col, label, val in [
            ('micro_skills', 'Micro', micro),
            ('macro_skills', 'Macro', macro),
            ('soft_skills',  'Soft',  soft),
        ]:
            is_active = (priority == skill_col)
            prefix = 'OK ' if is_active else '      '
            btn = Button(
                text=f'{prefix}{label}: {val}',
                size_hint_y=None, height=46,
                background_color=_PRIORITY_COLOR[skill_col] if is_active
                                 else (0.20, 0.28, 0.35, 1),
                background_normal='',
            )
            btn.bind(on_press=lambda _, sc=skill_col: self._set(sc))
            grid.add_widget(btn)

        none_active = not priority
        none_btn = Button(
            text='OK Нет приоритета' if none_active else '      Нет приоритета',
            size_hint_y=None, height=46,
            background_color=(0.40, 0.18, 0.18, 1) if none_active else (0.22, 0.22, 0.22, 1),
            background_normal='',
        )
        none_btn.bind(on_press=lambda _: self._set(None))
        grid.add_widget(none_btn)

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=44,
            background_color=(0.65, 0.18, 0.18, 1), background_normal='',
        )
        close_btn.bind(on_press=self.dismiss)
        grid.add_widget(close_btn)

        self.content = grid

    def _set(self, skill_col):
        conn = sqlite3.connect(self.db_name)
        conn.execute("UPDATE players SET train_priority=? WHERE id=?", (skill_col, self.player_id))
        conn.commit()
        conn.close()
        self.dismiss()
        if self.on_changed:
            self.on_changed()


# ─── Main squad popup ─────────────────────────────────────────────────────────

class SquadPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.title = ''
        self.size_hint = (0.92, 0.92)
        self.background_color = (1, 1, 1, 0)
        self._build()

    def _build(self):
        grid = GridLayout(cols=1, size_hint_y=None, spacing=4, padding=(8, 4))
        grid.bind(minimum_height=grid.setter('height'))
        self._populate(grid)

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

    def _rebuild(self):
        self._build()

    def _populate(self, grid):
        from datetime import date as _date
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        try:
            _gd = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
            game_today = _date.fromisoformat(_gd[0]) if _gd else _date.today()
        except Exception:
            game_today = _date.today()

        cur.execute(
            "SELECT id, name, budget, carry, mid, offlane, partial_support, full_support, "
            "COALESCE(cohesion, 0), COALESCE(conflict_targets, '') FROM teams WHERE player='yes'"
        )
        team = cur.fetchone()
        if not team:
            grid.add_widget(_lbl('Команда не найдена.'))
            conn.close()
            return

        team_id, team_name, budget, *rest = team
        conflict_targets_str = rest[-1] or ''
        cohesion = rest[-2]
        slot_ids = rest[:-2]
        budget = budget or 0
        conflict_target_ids = set(
            int(x) for x in conflict_targets_str.split(',') if x.strip().isdigit()
        )

        # ── Header ───────────────────────────────────────────────
        hdr_box = BoxLayout(size_hint_y=None, height=44, spacing=16, padding=(8, 4))
        hdr_lbl = Label(
            text=f'[b]{team_name}[/b]', markup=True,
            color=T.ACCENT, font_size='18sp', halign='left', valign='middle',
        )
        hdr_lbl.bind(size=hdr_lbl.setter('text_size'))
        hdr_box.add_widget(hdr_lbl)

        def _stat_lbl(txt, color):
            l = Label(text=txt, markup=True, color=color, font_size='14sp',
                      size_hint_x=None, width=160, halign='left', valign='middle')
            l.bind(size=l.setter('text_size'))
            return l

        hdr_box.add_widget(_stat_lbl(f'Бюджет: [b]${budget:,}[/b]', (0.9, 0.9, 0.4, 1)))
        hdr_box.add_widget(_stat_lbl(
            f'Сыгранность: [b]{cohesion}/100[/b]', _cohesion_color(cohesion)))
        grid.add_widget(hdr_box)

        # Alerts
        if conflict_target_ids:
            conflict_names = []
            for cid in conflict_target_ids:
                r = cur.execute("SELECT nickname FROM players WHERE id=?", (cid,)).fetchone()
                if r:
                    conflict_names.append(r[0])
            grid.add_widget(_lbl(
                f'[!] РАСКОЛ: команда требует уволить {", ".join(conflict_names)}. '
                f'Сыгранность заморожена.',
                color=(1.0, 0.30, 0.20, 1), height=30,
            ))

        leaving_players = cur.execute(
            "SELECT nickname FROM players WHERE team_id=? AND COALESCE(wants_to_leave,0)=1",
            (team_id,)
        ).fetchall()
        for (lnick,) in leaving_players:
            grid.add_widget(_lbl(
                f'{lnick} хочет покинуть команду. Мораль заморожена на 1.',
                color=(1.0, 0.75, 0.15, 1), height=26,
            ))

        # Column header bar
        COL_H = 26
        hrow = BoxLayout(size_hint_y=None, height=COL_H, padding=(92, 0, 0, 0))

        def _ch(txt, sw):
            l = Label(text=f'[b]{txt}[/b]', markup=True, size_hint_x=sw,
                      color=T.ACCENT, halign='center', valign='middle', font_size='11sp')
            l.bind(size=l.setter('text_size'))
            return l

        hrow.add_widget(_ch('Игрок / роль', 0.26))
        hrow.add_widget(_ch('Micro', 0.10))
        hrow.add_widget(_ch('Macro', 0.10))
        hrow.add_widget(_ch('Soft', 0.10))
        hrow.add_widget(_ch('Мораль', 0.13))
        hrow.add_widget(_ch('Зарплата', 0.13))
        hrow.add_widget(_ch('Трен.', 0.10))
        hrow.add_widget(_ch('↓', 0.07))
        hrow.add_widget(_ch('', 0.07))
        grid.add_widget(hrow)

        # ── Player rows ──────────────────────────────────────────
        ROW_H   = 92
        PHOTO_W = 88   # container width
        PHOTO_SZ = 82  # actual image size (near-square)

        total_wage = 0

        for col, sid in zip(ROLE_ORDER, slot_ids):
            role_short = ROLE_SHORT[col]
            row = BoxLayout(size_hint_y=None, height=ROW_H, spacing=3, padding=(0, 2))

            if sid:
                cur.execute(
                    "SELECT name, surname, nickname, country, micro_skills, macro_skills, "
                    "soft_skills, wage, face, skill_cap, COALESCE(morale, 5), train_priority, "
                    "COALESCE(age, 22), injured_until, COALESCE(wants_to_leave, 0), "
                    "contract_end, COALESCE(form, 5), secondary_role "
                    "FROM players WHERE id=?",
                    (int(sid),)
                )
                p = cur.fetchone()
                if p:
                    (fname, lname, nick, country,
                     micro, macro, soft, wage, face, skill_cap, morale,
                     priority, age, injured_until, wants_to_leave,
                     contract_end, form, secondary_role) = p
                    micro = micro or 0; macro = macro or 0; soft = soft or 0
                    wage  = wage  or 0; skill_cap = skill_cap or 300
                    total_wage += wage

                    face_path = (
                        f"images/{face}" if face and os.path.exists(f"images/{face}")
                        else "images/players/generic.png"
                    )

                    pid = int(sid)
                    is_conflict = pid in conflict_target_ids
                    is_leaving  = bool(wants_to_leave)
                    is_injured  = False
                    if injured_until:
                        try:
                            is_injured = _date.fromisoformat(injured_until) >= game_today
                        except Exception:
                            pass

                    # Row left border
                    if is_conflict:
                        _row_bg(row, T.NEGATIVE)
                    elif is_leaving:
                        _row_bg(row, T.WARNING)
                    elif is_injured:
                        _row_bg(row, (0.20, 0.55, 0.90, 1))

                    nick_color = (
                        T.NEGATIVE if is_conflict else
                        T.WARNING  if is_leaving  else
                        (0.95, 0.95, 1.00, 1)
                    )

                    # Contract expiry
                    cend_txt   = None
                    cend_color = T.TEXT_DIM
                    days_left_contract = None
                    if contract_end:
                        try:
                            days_left_contract = (
                                _date.fromisoformat(contract_end) - game_today
                            ).days
                            cend_color = (
                                T.NEGATIVE if days_left_contract < 60  else
                                T.WARNING  if days_left_contract < 180 else
                                (0.55, 0.75, 0.55, 1)
                            )
                            mo = contract_end[5:7]
                            yr = contract_end[2:4]
                            cend_txt = f'{mo}.{yr}'
                        except Exception:
                            pass

                    # ── Photo (near-square) ───────────────────────
                    photo_outer = BoxLayout(
                        size_hint=(None, 1), width=PHOTO_W,
                        padding=(3, 5, 3, 5),
                    )
                    face_btn = _FaceBtn(
                        source=face_path,
                        size_hint=(None, None), width=PHOTO_SZ, height=PHOTO_SZ,
                        keep_ratio=True, allow_stretch=True,
                        mipmap=True,
                    )
                    face_btn.bind(on_press=lambda _, p=pid: self._open_detail(p))
                    photo_outer.add_widget(face_btn)

                    # ── Name / info column ────────────────────────
                    name_col = BoxLayout(
                        orientation='vertical', size_hint_x=0.26,
                        spacing=2, padding=(4, 4, 4, 4),
                    )

                    nick_display = nick or f'{fname} {lname}'
                    nick_lbl = Label(
                        text=f'[b]{nick_display}[/b]', markup=True,
                        color=nick_color, halign='left', valign='middle',
                        font_size='16sp', size_hint_y=None, height=28,
                    )
                    nick_lbl.bind(size=nick_lbl.setter('text_size'))

                    fullname_lbl = Label(
                        text=f'{fname} {lname}  [{age}л]',
                        color=T.TEXT_DIM, halign='left', valign='middle',
                        font_size='10sp', size_hint_y=None, height=15,
                    )
                    fullname_lbl.bind(size=fullname_lbl.setter('text_size'))

                    chips_row = BoxLayout(size_hint_y=None, height=20, spacing=3)
                    chips_row.add_widget(T.make_chip(role_short, T.ACCENT, T.BG_CARD))
                    if secondary_role and secondary_role in ROLE_SHORT:
                        chips_row.add_widget(T.make_chip(
                            ROLE_SHORT[secondary_role], T.BTN_NEUTRAL, T.TEXT_DIM))
                    if is_conflict:
                        chips_row.add_widget(T.make_chip('КОНФЛ', T.NEGATIVE))
                    elif is_leaving:
                        chips_row.add_widget(T.make_chip('УХОДИТ', T.WARNING))
                    elif is_injured:
                        chips_row.add_widget(T.make_chip(
                            f'до {injured_until[5:]}', (0.15, 0.40, 0.70, 1),
                            (0.60, 0.85, 1.00, 1)))
                    if cend_txt:
                        chips_row.add_widget(T.make_chip(cend_txt, T.BG_ROW_A, cend_color))

                    name_col.add_widget(nick_lbl)
                    name_col.add_widget(fullname_lbl)
                    name_col.add_widget(chips_row)

                    # helper for centered label in a skill-style column
                    def _cv(txt, color=(1, 1, 1, 1), fs='13sp', sw=0.10):
                        l = Label(text=txt, color=color, font_size=fs,
                                  size_hint_x=sw, halign='center', valign='middle')
                        l.bind(size=l.setter('text_size'))
                        return l

                    # ── Skill bars ────────────────────────────────
                    row.add_widget(photo_outer)
                    row.add_widget(name_col)
                    row.add_widget(_skill_bar(micro, sw=0.10))
                    row.add_widget(_skill_bar(macro, sw=0.10))
                    row.add_widget(_skill_bar(soft,  sw=0.10))

                    # ── Morale column ─────────────────────────────
                    morale_col = BoxLayout(
                        orientation='vertical', size_hint_x=0.13,
                        spacing=1, padding=(2, 6),
                    )
                    morale_col.add_widget(_morale_dots(morale))
                    form_c = T.morale_color(form)
                    f_lbl = Label(
                        text=f'F{form}', color=form_c, font_size='11sp',
                        size_hint_y=None, height=16,
                        halign='center', valign='middle',
                    )
                    f_lbl.bind(size=f_lbl.setter('text_size'))
                    morale_col.add_widget(f_lbl)
                    row.add_widget(morale_col)

                    # ── Wage column ───────────────────────────────
                    wage_col = BoxLayout(
                        orientation='vertical', size_hint_x=0.13,
                        spacing=2, padding=(2, 8),
                    )
                    w_lbl = Label(
                        text=f'[b]${wage:,}[/b]', markup=True,
                        color=T.WARNING, font_size='13sp',
                        size_hint_y=None, height=22,
                        halign='center', valign='middle',
                    )
                    w_lbl.bind(size=w_lbl.setter('text_size'))
                    wage_col.add_widget(w_lbl)
                    if days_left_contract is not None:
                        d_lbl = Label(
                            text=f'{days_left_contract}д',
                            color=cend_color, font_size='10sp',
                            size_hint_y=None, height=16,
                            halign='center', valign='middle',
                        )
                        d_lbl.bind(size=d_lbl.setter('text_size'))
                        wage_col.add_widget(d_lbl)
                    row.add_widget(wage_col)

                    # ── Training button ───────────────────────────
                    p_label = _PRIORITY_LABEL.get(priority, '—')
                    p_color = _PRIORITY_COLOR.get(priority, _PRIORITY_COLOR[None])
                    if is_injured:
                        inj_lbl = Label(
                            text='отпуск', color=(0.40, 0.70, 1.00, 1),
                            font_size='10sp', size_hint_x=0.10,
                            halign='center', valign='middle',
                        )
                        inj_lbl.bind(size=inj_lbl.setter('text_size'))
                        row.add_widget(inj_lbl)
                    else:
                        train_btn = Button(
                            text=p_label, size_hint_x=0.10,
                            background_color=p_color,
                            background_normal='', font_size='13sp',
                        )
                        train_btn.bind(on_press=lambda _, p=pid: self._open_priority(p))
                        row.add_widget(train_btn)

                    # ── Bench button ──────────────────────────────
                    bench_btn = Button(
                        text='↓', size_hint_x=0.07,
                        background_color=(0.28, 0.22, 0.10, 1),
                        background_normal='', font_size='16sp',
                    )
                    bench_btn.bind(on_press=lambda _, p=pid, c=col: self._bench_player(p, c))
                    row.add_widget(bench_btn)

                    # ── Detail button ─────────────────────────────
                    det_btn = Button(
                        text='>', size_hint_x=0.07,
                        background_color=(0.15, 0.25, 0.45, 1),
                        background_normal='', font_size='16sp',
                    )
                    det_btn.bind(on_press=lambda _, p=pid: self._open_detail(p))
                    row.add_widget(det_btn)

                else:
                    row.add_widget(_lbl(f'  [{role_short}]  — нет данных —',
                                        color=(0.5, 0.5, 0.5, 1)))
            else:
                # Empty slot
                empty_box = BoxLayout(size_hint_y=None, height=ROW_H,
                                      padding=(PHOTO_W + 8, 0))
                empty_lbl = Label(
                    text=f'[b]{role_short}[/b]  — слот свободен —', markup=True,
                    color=(0.40, 0.40, 0.42, 1), halign='left', valign='middle',
                    font_size='13sp',
                )
                empty_lbl.bind(size=empty_lbl.setter('text_size'))
                row.add_widget(empty_lbl)

            grid.add_widget(row)

        # ── Bench ────────────────────────────────────────────────
        active_ids = set(s for s in slot_ids if s)
        ph = ','.join('?' * len(active_ids)) if active_ids else '0'
        cur.execute(
            f"SELECT id, nickname, role, micro_skills, macro_skills, soft_skills, "
            f"wage, injured_until FROM players "
            f"WHERE team_id=? AND id NOT IN ({ph}) ORDER BY role",
            [team_id] + list(active_ids),
        )
        bench_players = cur.fetchall()
        conn.close()

        if bench_players:
            grid.add_widget(_lbl(''))
            grid.add_widget(_header('Скамейка', height=32))
            for bpid, bnick, brole, bmic, bmac, bsft, bwage, bvac in bench_players:
                bmic = bmic or 0; bmac = bmac or 0; bsft = bsft or 0
                bwage = bwage or 0
                is_away = False
                if bvac:
                    try:
                        is_away = _date.fromisoformat(bvac) >= game_today
                    except Exception:
                        pass
                vac_txt = f'  до {bvac[5:]}' if is_away else ''
                brow = BoxLayout(size_hint_y=None, height=44, spacing=4)
                role_lbl = ROLE_SHORT.get(brole, brole or '?')
                brow.add_widget(_lbl(
                    f'  [{role_lbl}]  {bnick}   '
                    f'Mi {bmic}  Ma {bmac}  S {bsft}   ${bwage:,}/мес{vac_txt}',
                    height=44, color=(0.85, 0.85, 0.55, 1),
                ))
                role_col = brole if brole in ROLE_ORDER else None
                if role_col:
                    swap_btn = Button(
                        text='В состав', size_hint=(None, None), width=110, height=36,
                        background_color=(0.15, 0.55, 0.20, 1),
                        background_normal='', font_size='12sp',
                    )
                    swap_btn.bind(on_press=lambda _, p=bpid, rc=role_col:
                                  self._swap_to_active(p, rc))
                    brow.add_widget(swap_btn)
                grid.add_widget(brow)

        grid.add_widget(_lbl(''))
        grid.add_widget(_lbl(
            f'  Итого зарплат: ${total_wage:,}/мес',
            height=38, color=(0.8, 0.8, 0.5, 1), bold=True,
        ))
        grid.add_widget(_lbl(
            '  Трен.: M=Micro, Ma=Macro, S=Soft, —=нет приоритета  |  '
            'Навыки растут от игр в турнирах',
            height=24, color=(0.45, 0.45, 0.45, 1),
        ))

    def _swap_to_active(self, bench_pid, role_col):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute(f"SELECT {role_col} FROM teams WHERE player='yes'")
        row = cur.fetchone()
        cur.execute(f"UPDATE teams SET {role_col}=? WHERE player='yes'", (bench_pid,))
        conn.commit()
        conn.close()
        self._rebuild()

    def _bench_player(self, player_id, role_col):
        conn = sqlite3.connect(self.db_name)
        conn.execute(f"UPDATE teams SET {role_col}=NULL WHERE player='yes'")
        conn.commit()
        conn.close()
        self._rebuild()

    def _open_priority(self, player_id):
        SetPriorityPopup(
            db_name=self.db_name,
            player_id=player_id,
            on_changed=self._rebuild,
        ).open()

    def _open_detail(self, player_id):
        PlayerDetailPopup(
            db_name=self.db_name,
            player_id=player_id,
            on_priority_changed=self._rebuild,
        ).open()

    def _open_history(self, player_id, nick):
        PlayerHistoryPopup(db_name=self.db_name,
                           player_id=player_id, nick=nick).open()


class PlayerHistoryPopup(Popup):
    def __init__(self, db_name, player_id, nick, **kw):
        super().__init__(**kw)
        self.title     = f'История: {nick}'
        self.size_hint = (0.65, 0.80)
        self._build(db_name, player_id)

    def _build(self, db_name, pid):
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute(
            "SELECT season, tournament_name, place, team_name "
            "FROM player_history WHERE player_id=? "
            "ORDER BY season DESC, place ASC",
            (pid,)
        )
        rows = c.fetchall()

        # Skill snapshots for growth chart
        snapshots = []
        try:
            snapshots = c.execute(
                "SELECT season, micro, macro, soft FROM player_skill_snapshot "
                "WHERE player_id=? ORDER BY season ASC",
                (pid,)
            ).fetchall()
        except Exception:
            pass
        conn.close()

        grid = GridLayout(cols=1, size_hint_y=None, spacing=3, padding=8)
        grid.bind(minimum_height=grid.setter('height'))

        if not rows:
            grid.add_widget(_lbl('  Нет данных о карьере', color=(0.6, 0.6, 0.6, 1)))
        else:
            last_season = None
            for season, t_name, place, team in rows:
                if season != last_season:
                    hdr = Label(
                        text=f'[b]Сезон {season}[/b]', markup=True,
                        color=(0.35, 0.85, 1.0, 1),
                        size_hint_y=None, height=28,
                        halign='left', valign='middle',
                    )
                    hdr.bind(size=hdr.setter('text_size'))
                    grid.add_widget(hdr)
                    last_season = season
                medals = {1: '[1]', 2: '[2]', 3: '[3]'}
                m = medals.get(place, f'{place}.')
                c_color = (
                    (1.0, 0.85, 0.25, 1) if place == 1 else
                    (0.85, 0.85, 0.85, 1) if place == 2 else
                    (0.80, 0.55, 0.30, 1) if place <= 4 else
                    (0.75, 0.75, 0.75, 1)
                )
                row = Label(
                    text=f'  {m}  {t_name}  [{team}]',
                    color=c_color, size_hint_y=None, height=26,
                    halign='left', valign='middle',
                )
                row.bind(size=row.setter('text_size'))
                grid.add_widget(row)

        # Skill growth chart
        if snapshots:
            grid.add_widget(_lbl(''))
            hdr = Label(text='[b]Рост скиллов по сезонам[/b]', markup=True,
                        color=(0.35, 0.85, 1.0, 1), size_hint_y=None, height=26,
                        halign='left', valign='middle')
            hdr.bind(size=hdr.setter('text_size'))
            grid.add_widget(hdr)
            for season, micro, macro, soft in snapshots:
                total = micro + macro + soft
                bar_m  = '█' * (micro // 10)
                bar_ma = '█' * (macro // 10)
                bar_s  = '█' * (soft  // 10)
                row = Label(
                    text=(f'  [b]{season}[/b]  '
                          f'[color=55aaff]M {micro:3d} {bar_m}[/color]  '
                          f'[color=ffcc44]Ma{macro:3d} {bar_ma}[/color]  '
                          f'[color=66ee88]S {soft:3d} {bar_s}[/color]  '
                          f'Σ{total}'),
                    markup=True, color=(0.85, 0.85, 0.85, 1),
                    size_hint_y=None, height=24,
                    halign='left', valign='middle', font_size='11sp',
                )
                row.bind(size=row.setter('text_size'))
                grid.add_widget(row)

        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(grid)
        root = BoxLayout(orientation='vertical', spacing=4, padding=4)
        root.add_widget(sv)
        root.add_widget(Button(
            text='Закрыть', size_hint_y=None, height=44,
            background_color=(0.55, 0.18, 0.18, 1), background_normal='',
            on_press=self.dismiss,
        ))
        self.content = root


class PlayerDetailPopup(Popup):
    """Full player card: photo, skills, status, contract, career."""

    def __init__(self, db_name, player_id, on_priority_changed=None, **kw):
        super().__init__(**kw)
        self.size_hint = (0.78, 0.92)
        self.auto_dismiss = True
        self.background = ''
        self.background_color = (0.07, 0.09, 0.13, 1)
        self.separator_color = (0.15, 0.30, 0.50, 1)
        self.title_color = (0.20, 0.82, 1.00, 1)
        self._build(db_name, player_id, on_priority_changed)

    def _build(self, db_name, pid, on_priority_changed):
        from datetime import date as _date
        from kivy.graphics import Color as GC, Rectangle as GR, RoundedRectangle as RR

        conn = sqlite3.connect(db_name)
        c = conn.cursor()

        game_today = _date.today()
        try:
            gd = c.execute("SELECT date FROM save WHERE id=1").fetchone()
            if gd:
                game_today = _date.fromisoformat(gd[0])
        except Exception:
            pass

        p = c.execute(
            "SELECT name, surname, nickname, country, role, secondary_role, "
            "COALESCE(age,22), micro_skills, macro_skills, soft_skills, "
            "COALESCE(morale,5), COALESCE(form,5), COALESCE(stability,5), "
            "wage, contract_end, train_priority, COALESCE(skill_cap,300), "
            "COALESCE(competence,5), face, "
            "COALESCE(micro_cap,100), COALESCE(macro_cap,100), COALESCE(soft_cap,100), "
            "COALESCE(train_xp,0.0), COALESCE(wants_to_leave,0), "
            "injured_until "
            "FROM players WHERE id=?", (pid,)
        ).fetchone()

        history = c.execute(
            "SELECT season, tournament_name, place, team_name "
            "FROM player_history WHERE player_id=? ORDER BY season DESC LIMIT 8",
            (pid,)
        ).fetchall()

        snapshots = []
        try:
            snapshots = c.execute(
                "SELECT season, micro, macro, soft FROM player_skill_snapshot "
                "WHERE player_id=? ORDER BY season DESC LIMIT 5", (pid,)
            ).fetchall()
        except Exception:
            pass
        conn.close()

        if not p:
            self.title = 'Игрок'
            self.content = Label(text='Нет данных.')
            return

        (fname, lname, nick, country, role, sec_role, age,
         micro, macro, soft, morale, form, stability,
         wage, contract_end, priority, skill_cap, competence,
         face, micro_cap, macro_cap, soft_cap, train_xp, wants_to_leave,
         injured_until) = p

        micro = micro or 0; macro = macro or 0; soft = soft or 0
        micro_cap = micro_cap or 100; macro_cap = macro_cap or 100; soft_cap = soft_cap or 100

        self.title = ''

        face_path = (
            f"images/{face}" if face and os.path.exists(f"images/{face}")
            else "images/players/generic.png"
        )

        is_injured = False
        if injured_until:
            try:
                is_injured = _date.fromisoformat(injured_until) >= game_today
            except Exception:
                pass

        contract_days = None
        contract_color = T.TEXT_MAIN
        if contract_end:
            try:
                contract_days = (_date.fromisoformat(contract_end) - game_today).days
                contract_color = (
                    T.NEGATIVE if contract_days < 60 else
                    T.WARNING  if contract_days < 180 else
                    (0.55, 0.85, 0.55, 1)
                )
            except Exception:
                pass

        # ── helpers ──────────────────────────────────────────────
        def _sec(txt):
            l = Label(text=f'[b]{txt}[/b]', markup=True,
                      color=T.ACCENT, font_size='11sp',
                      size_hint_y=None, height=22,
                      halign='left', valign='middle')
            l.bind(size=l.setter('text_size'))
            return l

        def _kv(key, val, vc=T.TEXT_MAIN, key_w=0.42):
            r = BoxLayout(size_hint_y=None, height=24)
            lk = Label(text=key, color=T.TEXT_LABEL, font_size='12sp',
                       halign='left', valign='middle', size_hint_x=key_w)
            lv = Label(text=str(val), color=vc, font_size='12sp',
                       halign='left', valign='middle', size_hint_x=1-key_w)
            lk.bind(size=lk.setter('text_size'))
            lv.bind(size=lv.setter('text_size'))
            r.add_widget(lk); r.add_widget(lv)
            return r

        def _skill_row_full(label, val, cap):
            r = BoxLayout(size_hint_y=None, height=30, spacing=6)
            ll = Label(text=label, color=T.TEXT_LABEL, font_size='12sp',
                       size_hint_x=0.14, halign='left', valign='middle')
            ll.bind(size=ll.setter('text_size'))
            r.add_widget(ll)
            r.add_widget(_skill_bar(val, sw=0.55))
            val_lbl = Label(
                text=f'[b]{val}[/b]', markup=True,
                color=_skill_color(val), font_size='13sp',
                size_hint_x=0.10, halign='center', valign='middle',
            )
            val_lbl.bind(size=val_lbl.setter('text_size'))
            r.add_widget(val_lbl)
            cap_lbl = Label(
                text=f'/{cap}', color=T.TEXT_DIM, font_size='11sp',
                size_hint_x=0.21, halign='left', valign='middle',
            )
            cap_lbl.bind(size=cap_lbl.setter('text_size'))
            r.add_widget(cap_lbl)
            return r

        def _dots_bar(val, max_val=10, color_fn=None):
            filled = round(val)
            color = color_fn(val) if color_fn else T.TEXT_MAIN
            dots = ''.join(['●' if i < filled else '○' for i in range(max_val)])
            l = Label(text=dots, color=color, font_size='12sp',
                      size_hint_y=None, height=20, halign='left', valign='middle')
            l.bind(size=l.setter('text_size'))
            return l

        # ── ROOT: horizontal split ────────────────────────────────
        root = BoxLayout(orientation='vertical', spacing=4, padding=6)

        body = BoxLayout(orientation='horizontal', spacing=8)

        # ═══ LEFT PANEL ══════════════════════════════════════════
        left = BoxLayout(
            orientation='vertical', size_hint_x=0.38,
            spacing=6, padding=(4, 4),
        )

        # Photo + name block
        photo_box = BoxLayout(orientation='vertical', size_hint_y=None,
                              height=200, spacing=4)

        face_img = Image(
            source=face_path,
            size_hint=(1, None), height=160,
            allow_stretch=True, keep_ratio=True,
        )
        photo_box.add_widget(face_img)

        nick_lbl = Label(
            text=f'[b]{nick}[/b]', markup=True,
            color=(0.95, 0.95, 1.0, 1), font_size='18sp',
            size_hint_y=None, height=28,
            halign='center', valign='middle',
        )
        nick_lbl.bind(size=nick_lbl.setter('text_size'))
        photo_box.add_widget(nick_lbl)

        fullname_lbl = Label(
            text=f'{fname} {lname}',
            color=T.TEXT_DIM, font_size='11sp',
            size_hint_y=None, height=18,
            halign='center', valign='middle',
        )
        fullname_lbl.bind(size=fullname_lbl.setter('text_size'))
        photo_box.add_widget(fullname_lbl)

        left.add_widget(photo_box)

        left.add_widget(_sec('ПРОФИЛЬ'))
        role_txt = ROLE_LABELS.get(role, role or '—')
        sec_txt  = ROLE_LABELS.get(sec_role, '—') if sec_role else '—'
        left.add_widget(_kv('Роль', role_txt))
        if sec_role:
            left.add_widget(_kv('Доп. роль', sec_txt, T.TEXT_DIM))
        left.add_widget(_kv('Возраст', f'{age} лет'))
        left.add_widget(_kv('Страна', country or '—'))
        left.add_widget(_kv('Компетентность', f'{competence}/10'))

        if is_injured and injured_until:
            left.add_widget(_kv('Статус', f'Недоступен до {injured_until[5:]}',
                                (0.40, 0.70, 1.00, 1)))
        elif wants_to_leave:
            left.add_widget(_kv('Статус', 'Хочет уйти', T.WARNING))

        left.add_widget(Label())  # spacer

        # ═══ RIGHT PANEL ═════════════════════════════════════════
        right_scroll_content = GridLayout(cols=1, size_hint_y=None, spacing=5,
                                          padding=(4, 4))
        right_scroll_content.bind(minimum_height=right_scroll_content.setter('height'))

        # Skills
        right_scroll_content.add_widget(_sec('НАВЫКИ'))
        right_scroll_content.add_widget(_skill_row_full('Micro', micro, micro_cap))
        right_scroll_content.add_widget(_skill_row_full('Macro', macro, macro_cap))
        right_scroll_content.add_widget(_skill_row_full('Soft',  soft,  soft_cap))

        total_skill = micro + macro + soft
        total_cap   = micro_cap + macro_cap + soft_cap
        total_row = BoxLayout(size_hint_y=None, height=22)
        tot_lbl = Label(
            text=f'  Сумма: [b]{total_skill}[/b] / {total_cap}  '
                 f'(XP: {train_xp:.1f})',
            markup=True, color=T.TEXT_DIM, font_size='11sp',
            halign='left', valign='middle',
        )
        tot_lbl.bind(size=tot_lbl.setter('text_size'))
        total_row.add_widget(tot_lbl)
        right_scroll_content.add_widget(total_row)

        # Status
        right_scroll_content.add_widget(_sec('СОСТОЯНИЕ'))
        form_c   = T.morale_color(form)
        morale_c = T.morale_color(morale)

        form_row = BoxLayout(size_hint_y=None, height=24, spacing=8)
        form_key = Label(text='Форма', color=T.TEXT_LABEL, font_size='12sp',
                         size_hint_x=0.30, halign='left', valign='middle')
        form_key.bind(size=form_key.setter('text_size'))
        form_row.add_widget(form_key)
        form_row.add_widget(_dots_bar(form, color_fn=T.morale_color))
        form_val = Label(text=f'[b]{form}[/b]/10', markup=True, color=form_c,
                         font_size='12sp', size_hint_x=0.20,
                         halign='right', valign='middle')
        form_val.bind(size=form_val.setter('text_size'))
        form_row.add_widget(form_val)
        right_scroll_content.add_widget(form_row)

        mor_row = BoxLayout(size_hint_y=None, height=24, spacing=8)
        mor_key = Label(text='Мораль', color=T.TEXT_LABEL, font_size='12sp',
                        size_hint_x=0.30, halign='left', valign='middle')
        mor_key.bind(size=mor_key.setter('text_size'))
        mor_row.add_widget(mor_key)
        mor_row.add_widget(_dots_bar(morale, color_fn=T.morale_color))
        mor_val = Label(text=f'[b]{morale}[/b]/10', markup=True, color=morale_c,
                        font_size='12sp', size_hint_x=0.20,
                        halign='right', valign='middle')
        mor_val.bind(size=mor_val.setter('text_size'))
        mor_row.add_widget(mor_val)
        right_scroll_content.add_widget(mor_row)

        right_scroll_content.add_widget(_kv('Стабильность', f'{stability}/10'))

        # Contract
        right_scroll_content.add_widget(_sec('КОНТРАКТ'))
        right_scroll_content.add_widget(
            _kv('Зарплата', f'${wage:,}/мес' if wage else '—', T.WARNING))

        if contract_days is not None:
            right_scroll_content.add_widget(
                _kv('Истекает',
                    f'{contract_end}  ({contract_days} дн.)',
                    contract_color))
        elif contract_end:
            right_scroll_content.add_widget(_kv('Истекает', contract_end))

        prior_txt = {
            'micro_skills': 'Micro', 'macro_skills': 'Macro',
            'soft_skills': 'Soft', None: 'нет',
        }.get(priority, priority or 'нет')
        right_scroll_content.add_widget(_kv('Тренировка', prior_txt))

        # Career
        if snapshots or history:
            right_scroll_content.add_widget(_sec('КАРЬЕРА'))

        if snapshots:
            snap_hdr = Label(
                text='  Сезон   Micro  Macro   Soft   Σ',
                color=T.TEXT_DIM, font_size='10sp',
                size_hint_y=None, height=18, halign='left', valign='middle',
            )
            snap_hdr.bind(size=snap_hdr.setter('text_size'))
            right_scroll_content.add_widget(snap_hdr)
            for season, sm, sx, ss in snapshots:
                tot = sm + sx + ss
                sl = Label(
                    text=f'  [b]{season}[/b]     {sm:3d}     {sx:3d}     {ss:3d}   {tot}',
                    markup=True, color=T.TEXT_LABEL, font_size='11sp',
                    size_hint_y=None, height=20, halign='left', valign='middle',
                )
                sl.bind(size=sl.setter('text_size'))
                right_scroll_content.add_widget(sl)

        if history:
            medals = {1: '[1]', 2: '[2]', 3: '[3]'}
            for season, t_name, place, team in history:
                pc    = T.place_color(place)
                medal = medals.get(place, f'{place}.')
                hl = Label(
                    text=f'  {medal}  [b]{season}[/b]  {t_name[:24]}  [{team[:12]}]',
                    markup=True, color=pc, font_size='11sp',
                    size_hint_y=None, height=22, halign='left', valign='middle',
                )
                hl.bind(size=hl.setter('text_size'))
                right_scroll_content.add_widget(hl)

        right_sv = ScrollView(size_hint=(0.62, 1))
        right_sv.add_widget(right_scroll_content)

        body.add_widget(left)
        body.add_widget(right_sv)
        root.add_widget(body)

        # ── Buttons ──────────────────────────────────────────────
        btn_row = BoxLayout(size_hint_y=None, height=46, spacing=6)

        if on_priority_changed:
            train_btn = Button(
                text='Тренировка',
                background_color=T.BTN_PRIMARY, background_normal='',
                font_size='13sp',
            )
            train_btn.bind(on_press=lambda _: (
                self.dismiss(),
                SetPriorityPopup(db_name=db_name, player_id=pid,
                                 on_changed=on_priority_changed).open()
            ))
            btn_row.add_widget(train_btn)

        hist_btn = Button(
            text='История',
            background_color=(0.18, 0.28, 0.48, 1), background_normal='',
            font_size='13sp',
        )
        hist_btn.bind(on_press=lambda _: (
            self.dismiss(),
            PlayerHistoryPopup(db_name=db_name, player_id=pid, nick=nick).open()
        ))
        btn_row.add_widget(hist_btn)

        close_btn = Button(
            text='Закрыть',
            background_color=T.BTN_DANGER, background_normal='',
            font_size='13sp',
        )
        close_btn.bind(on_press=self.dismiss)
        btn_row.add_widget(close_btn)

        root.add_widget(btn_row)
        self.content = root


def show_squad_popup(db_name):
    SquadPopup(db_name=db_name).open()
