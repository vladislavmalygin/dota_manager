import sqlite3
import os

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image


ROLE_ORDER = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
ROLE_LABELS = {
    'carry':           'Carry (1)',
    'mid':             'Mid (2)',
    'offlane':         'Offlane (3)',
    'partial_support': 'Support (4)',
    'full_support':    'Support (5)',
}

TRAIN_COST = 15_000   # $ per training session
TRAIN_GAIN = 3        # skill points gained per session
SKILL_MAX  = 100      # hard cap per individual skill


def _skill_color(value):
    if value >= 85:
        return (0.3, 1.0, 0.4, 1)
    if value >= 65:
        return (1.0, 0.9, 0.3, 1)
    return (1.0, 0.45, 0.3, 1)


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


# ─── Training sub-popup ───────────────────────────────────────────────────────

class TrainPlayerPopup(Popup):
    def __init__(self, db_name, player_id, on_trained, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.player_id = player_id
        self.on_trained = on_trained
        self.size_hint = (0.55, 0.55)
        self.auto_dismiss = False
        self._build()

    def _build(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute(
            "SELECT nickname, micro_skills, macro_skills, soft_skills, skill_cap "
            "FROM players WHERE id=?", (self.player_id,)
        )
        p = cur.fetchone()
        cur.execute("SELECT budget FROM teams WHERE player='yes'")
        budget_row = cur.fetchone()
        conn.close()

        if not p:
            self.content = Label(text='Игрок не найден.')
            return

        nick, micro, macro, soft, skill_cap = p
        micro = micro or 0
        macro = macro or 0
        soft  = soft  or 0
        skill_cap = skill_cap or 300
        budget = budget_row[0] if budget_row else 0

        self.title = f'Тренировка: {nick}'
        total = micro + macro + soft
        cap_left = skill_cap - total

        grid = GridLayout(cols=1, spacing=6, padding=8)

        grid.add_widget(_lbl(
            f'  Micro: {micro}   Macro: {macro}   Soft: {soft}',
            bold=True, color=(1, 1, 1, 1),
        ))
        grid.add_widget(_lbl(
            f'  Потенциал: {total}/{skill_cap}  (осталось {cap_left})',
            color=(0.7, 0.85, 1.0, 1),
        ))
        grid.add_widget(_lbl(
            f'  Бюджет команды: ${budget:,}   '
            f'Стоимость тренировки: ${TRAIN_COST:,} (+{TRAIN_GAIN})',
            color=(0.9, 0.9, 0.5, 1), height=32,
        ))

        can_afford = budget >= TRAIN_COST
        can_cap    = cap_left >= TRAIN_GAIN

        for skill_name, current, col in [
            ('micro_skills', micro, 'Micro'),
            ('macro_skills', macro, 'Macro'),
            ('soft_skills',  soft,  'Soft'),
        ]:
            can_train = can_afford and can_cap and current + TRAIN_GAIN <= SKILL_MAX
            btn = Button(
                text=f'Тренировать {col}: {current} → {current + TRAIN_GAIN}',
                size_hint_y=None, height=44,
                background_color=(0.1, 0.6, 0.2, 1) if can_train else (0.3, 0.3, 0.3, 1),
                disabled=not can_train,
            )
            btn.bind(
                on_press=lambda _, sn=skill_name: self._train(sn)
            )
            grid.add_widget(btn)

        if not can_afford:
            grid.add_widget(_lbl('  Недостаточно бюджета.', color=(1, 0.3, 0.3, 1)))
        if not can_cap:
            grid.add_widget(_lbl('  Потенциал исчерпан.', color=(1, 0.3, 0.3, 1)))

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=44,
            background_color=(0.7, 0.2, 0.2, 1),
        )
        close_btn.bind(on_press=self.dismiss)
        grid.add_widget(close_btn)

        self.content = grid

    def _train(self, skill_col):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute(f"SELECT {skill_col}, skill_cap FROM players WHERE id=?", (self.player_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        current, skill_cap = row[0] or 0, row[1] or 300

        cur.execute(
            "SELECT micro_skills + macro_skills + soft_skills FROM players WHERE id=?",
            (self.player_id,)
        )
        total = cur.fetchone()[0] or 0

        cur.execute("SELECT id, budget FROM teams WHERE player='yes'")
        team_row = cur.fetchone()
        if not team_row:
            conn.close()
            return
        team_id, budget = team_row
        budget = budget or 0

        if (budget < TRAIN_COST
                or total + TRAIN_GAIN > skill_cap
                or current + TRAIN_GAIN > SKILL_MAX):
            conn.close()
            return

        new_val = min(current + TRAIN_GAIN, SKILL_MAX)
        cur.execute(f"UPDATE players SET {skill_col}=? WHERE id=?", (new_val, self.player_id))
        cur.execute("UPDATE teams SET budget=budget-? WHERE id=?", (TRAIN_COST, team_id))

        cur.execute("SELECT nickname FROM players WHERE id=?", (self.player_id,))
        nick = cur.fetchone()[0]
        skill_label = {'micro_skills': 'Micro', 'macro_skills': 'Macro', 'soft_skills': 'Soft'}[skill_col]
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
            (f"{nick}: {skill_label} {current} → {new_val} (тренировка, −${TRAIN_COST:,})", "Тренер"),
        )
        conn.commit()
        conn.close()

        self.dismiss()
        if self.on_trained:
            self.on_trained()


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
            "SELECT id, name, budget, carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE player='yes'"
        )
        team = cur.fetchone()
        if not team:
            grid.add_widget(_lbl('Команда не найдена.'))
            conn.close()
            return

        team_id, team_name, budget, *slot_ids = team
        budget = budget or 0

        grid.add_widget(_header(f'Состав: {team_name}'))
        grid.add_widget(_lbl(f'  Бюджет: ${budget:,}', color=(0.9, 0.9, 0.4, 1)))

        # Column headers
        hrow = BoxLayout(size_hint_y=None, height=28)
        for txt, sw in [('Роль', 0.13), ('', 0.07), ('Игрок', 0.26),
                        ('Micro', 0.10), ('Macro', 0.10), ('Soft', 0.10),
                        ('Зарплата', 0.14), ('', 0.10)]:
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
                    "soft_skills, wage, face, skill_cap FROM players WHERE id=?",
                    (int(sid),)
                )
                p = cur.fetchone()
                if p:
                    fname, lname, nick, micro, macro, soft, wage, face, skill_cap = p
                    micro = micro or 0; macro = macro or 0; soft = soft or 0
                    wage  = wage  or 0; skill_cap = skill_cap or 300
                    total_wage += wage

                    face_path = (
                        f"images/{face}" if face and os.path.exists(f"images/{face}")
                        else "images/players/generic.png"
                    )
                    total_pts  = micro + macro + soft
                    cap_pct    = int(total_pts / skill_cap * 100) if skill_cap else 0

                    def _cell(text, sw, color=(1, 1, 1, 1)):
                        lbl = Label(
                            text=text, size_hint_x=sw,
                            color=color, halign='center', valign='middle',
                        )
                        lbl.bind(size=lbl.setter('text_size'))
                        return lbl

                    row.add_widget(_cell(role_label, 0.13, color=(0.75, 0.85, 1.0, 1)))
                    row.add_widget(Image(source=face_path, size_hint=(None, 1), width=46))
                    row.add_widget(_cell(f"{nick}\n{fname} {lname}", 0.26))
                    row.add_widget(_cell(str(micro), 0.10, color=_skill_color(micro)))
                    row.add_widget(_cell(str(macro), 0.10, color=_skill_color(macro)))
                    row.add_widget(_cell(str(soft),  0.10, color=_skill_color(soft)))
                    row.add_widget(_cell(f'${wage:,}', 0.14, color=(0.9, 0.85, 0.5, 1)))

                    train_btn = Button(
                        text=f'Трен.\n{cap_pct}%', size_hint_x=0.10,
                        background_color=(0.1, 0.5, 0.85, 1),
                        font_size='11sp',
                    )
                    pid = int(sid)
                    train_btn.bind(
                        on_press=lambda _, pid=pid: self._open_training(pid)
                    )
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

        # Legend
        grid.add_widget(_lbl(
            f'  Трен. = тренировка  |  +{TRAIN_GAIN} к выбранному скиллу за ${TRAIN_COST:,}'
            f'  |  % = использование потенциала',
            height=26, color=(0.55, 0.55, 0.55, 1),
        ))

    def _open_training(self, player_id):
        TrainPlayerPopup(
            db_name=self.db_name,
            player_id=player_id,
            on_trained=self._rebuild,
        ).open()


def show_squad_popup(db_name):
    SquadPopup(db_name=db_name).open()
