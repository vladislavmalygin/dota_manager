import sqlite3
import os

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image

from logic.ai import _BASE_XP_PER_GAME


ROLE_ORDER  = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
ROLE_LABELS = {
    'carry':           'Carry (1)',
    'mid':             'Mid (2)',
    'offlane':         'Offlane (3)',
    'partial_support': 'Support (4)',
    'full_support':    'Support (5)',
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
    if value >= 85:
        return (0.3, 1.0, 0.4, 1)
    if value >= 65:
        return (1.0, 0.9, 0.3, 1)
    return (1.0, 0.45, 0.3, 1)


def _cohesion_color(v):
    if v >= 75:
        return (0.2, 0.95, 0.35, 1)
    if v >= 50:
        return (0.5, 0.95, 0.3, 1)
    if v >= 25:
        return (1.0, 0.85, 0.25, 1)
    return (0.95, 0.35, 0.25, 1)


def _lbl(text, height=36, color=(1, 1, 1, 1), bold=False, halign='left'):
    if bold:
        text = f'[b]{text}[/b]'
    lbl = Label(
        text=text, markup=bold,
        size_hint_y=None, height=height,
        color=color, halign=halign, valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _header(text, height=46):
    lbl = Label(
        text=f'[b]{text}[/b]', markup=True,
        size_hint_y=None, height=height,
        color=(0.4, 0.9, 1.0, 1), halign='center', valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


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
            prefix = '✓  ' if is_active else '      '
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
            text='✓  Нет приоритета' if none_active else '      Нет приоритета',
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
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute(
            "SELECT id, name, budget, carry, mid, offlane, partial_support, full_support, "
            "COALESCE(cohesion, 0) FROM teams WHERE player='yes'"
        )
        team = cur.fetchone()
        if not team:
            grid.add_widget(_lbl('Команда не найдена.'))
            conn.close()
            return

        team_id, team_name, budget, *slot_and_cohesion = team
        cohesion = slot_and_cohesion[-1]
        slot_ids = slot_and_cohesion[:-1]
        budget = budget or 0

        grid.add_widget(_header(f'Состав: {team_name}'))

        info_row = BoxLayout(size_hint_y=None, height=28, spacing=12)
        info_row.add_widget(_lbl(f'  Бюджет: ${budget:,}', color=(0.9, 0.9, 0.4, 1),
                                 height=28))
        info_row.add_widget(_lbl(
            f'  Сыгранность: {cohesion}/100',
            color=_cohesion_color(cohesion), height=28,
        ))
        grid.add_widget(info_row)

        # Column headers
        hrow = BoxLayout(size_hint_y=None, height=28)
        for txt, sw in [('Роль', 0.12), ('', 0.06), ('Игрок', 0.22),
                        ('Micro', 0.09), ('Macro', 0.09), ('Soft', 0.09),
                        ('Мораль', 0.09), ('Зарплата', 0.13), ('Трен.', 0.11)]:
            lbl = Label(
                text=f'[b]{txt}[/b]' if txt else '',
                markup=True, size_hint_x=sw,
                color=(0.6, 0.9, 1.0, 1), halign='center', valign='middle',
            )
            lbl.bind(size=lbl.setter('text_size'))
            hrow.add_widget(lbl)
        grid.add_widget(hrow)

        total_wage = 0

        for col, sid in zip(ROLE_ORDER, slot_ids):
            role_label = ROLE_LABELS[col]
            row = BoxLayout(size_hint_y=None, height=58, spacing=2)

            if sid:
                cur.execute(
                    "SELECT name, surname, nickname, micro_skills, macro_skills, "
                    "soft_skills, wage, face, skill_cap, COALESCE(morale, 5), train_priority "
                    "FROM players WHERE id=?",
                    (int(sid),)
                )
                p = cur.fetchone()
                if p:
                    fname, lname, nick, micro, macro, soft, wage, face, skill_cap, morale, priority = p
                    micro = micro or 0; macro = macro or 0; soft = soft or 0
                    wage  = wage  or 0; skill_cap = skill_cap or 300
                    total_wage += wage

                    face_path = (
                        f"images/{face}" if face and os.path.exists(f"images/{face}")
                        else "images/players/generic.png"
                    )

                    def _cell(text, sw, color=(1, 1, 1, 1)):
                        lbl = Label(text=text, size_hint_x=sw,
                                    color=color, halign='center', valign='middle')
                        lbl.bind(size=lbl.setter('text_size'))
                        return lbl

                    def _morale_color(m):
                        if m >= 8: return (0.3, 1.0, 0.4, 1)
                        if m >= 5: return (1.0, 0.9, 0.3, 1)
                        return (1.0, 0.4, 0.3, 1)

                    row.add_widget(_cell(role_label, 0.12, (0.75, 0.85, 1.0, 1)))
                    row.add_widget(Image(source=face_path, size_hint=(None, 1), width=46))
                    row.add_widget(_cell(f"{nick}\n{fname} {lname}", 0.22))
                    row.add_widget(_cell(str(micro), 0.09, _skill_color(micro)))
                    row.add_widget(_cell(str(macro), 0.09, _skill_color(macro)))
                    row.add_widget(_cell(str(soft),  0.09, _skill_color(soft)))
                    row.add_widget(_cell(f'{morale}/10', 0.09, _morale_color(morale)))
                    row.add_widget(_cell(f'${wage:,}', 0.13, (0.9, 0.85, 0.5, 1)))

                    pid = int(sid)
                    p_label = _PRIORITY_LABEL.get(priority, '—')
                    p_color = _PRIORITY_COLOR.get(priority, _PRIORITY_COLOR[None])
                    train_btn = Button(
                        text=p_label, size_hint_x=0.11,
                        background_color=p_color,
                        background_normal='',
                        font_size='13sp',
                    )
                    train_btn.bind(on_press=lambda _, pid=pid: self._open_priority(pid))
                    row.add_widget(train_btn)
                else:
                    row.add_widget(_lbl(f'  [{role_label}]  — нет данных —',
                                        color=(0.5, 0.5, 0.5, 1)))
            else:
                row.add_widget(_lbl(f'  [{role_label}]  — слот свободен —',
                                    color=(0.5, 0.5, 0.5, 1)))

            grid.add_widget(row)

        conn.close()

        grid.add_widget(_lbl(''))
        grid.add_widget(_lbl(
            f'  Итого зарплат: ${total_wage:,}/мес',
            height=40, color=(0.8, 0.8, 0.5, 1), bold=True,
        ))
        grid.add_widget(_lbl(
            '  Трен. = приоритетный навык (M=Micro, Ma=Macro, S=Soft, —=нет)  '
            '|  Навык растёт автоматически от игр в турнирах',
            height=26, color=(0.55, 0.55, 0.55, 1),
        ))

    def _open_priority(self, player_id):
        SetPriorityPopup(
            db_name=self.db_name,
            player_id=player_id,
            on_changed=self._rebuild,
        ).open()


def show_squad_popup(db_name):
    SquadPopup(db_name=db_name).open()
