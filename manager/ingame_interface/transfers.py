import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView


ROLE_LABELS = {
    'carry':           'Carry (1)',
    'mid':             'Mid (2)',
    'offlane':         'Offlane (3)',
    'partial_support': 'Support (4)',
    'full_support':    'Support (5)',
}
ROLE_COLS = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']


def _add_message(db_name, text, author="Трансфер"):
    conn = sqlite3.connect(db_name)
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
        (text, author),
    )
    conn.commit()
    conn.close()


def _lbl(text, height=36, color=(1, 1, 1, 1), bold=False):
    if bold:
        text = f"[b]{text}[/b]"
    lbl = Label(
        text=text, markup=bold,
        size_hint_y=None, height=height,
        color=color, halign='left', valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _header(text, height=42):
    lbl = Label(
        text=f'[b]{text}[/b]', markup=True,
        size_hint_y=None, height=height,
        color=(0.4, 0.9, 1.0, 1), halign='center', valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


class TransferPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.title = "Трансферный рынок"
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False

        self._build()

    # ── build / rebuild ───────────────────────────────────────

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=4, padding=4)

        # Two-column body
        body = BoxLayout(orientation='horizontal', spacing=6)
        body.add_widget(self._make_squad_panel())
        body.add_widget(self._make_free_agents_panel())
        root.add_widget(body)

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=50,
            background_color=(0.7, 0.2, 0.2, 1),
        )
        close_btn.bind(on_press=self.dismiss)
        root.add_widget(close_btn)

        self.content = root

    def _rebuild(self):
        self._build()

    # ── left panel: current squad ─────────────────────────────

    def _make_squad_panel(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute(
            "SELECT id, name, budget, carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE player='yes'"
        )
        team = cur.fetchone()

        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))

        if not team:
            grid.add_widget(_lbl("Команда не найдена."))
            conn.close()
            sv = ScrollView(size_hint=(0.38, 1))
            sv.add_widget(grid)
            return sv

        team_id, team_name, budget, *slot_ids = team
        budget = budget or 0

        grid.add_widget(_header(f"  {team_name}"))
        grid.add_widget(_lbl(f"  Бюджет: ${budget:,}", color=(0.9, 0.9, 0.4, 1)))

        # Total wage
        cur.execute(
            "SELECT COALESCE(SUM(wage),0) FROM players WHERE team_id=?", (team_id,)
        )
        total_wage = cur.fetchone()[0] or 0
        grid.add_widget(_lbl(f"  Зарплатный фонд: ${total_wage:,}/мес", height=30,
                             color=(0.8, 0.8, 0.8, 1)))

        grid.add_widget(_header("  Текущий состав", height=36))

        for col, sid in zip(ROLE_COLS, slot_ids):
            role_label = ROLE_LABELS[col]
            if sid:
                cur.execute(
                    "SELECT id, nickname, micro_skills, macro_skills, wage "
                    "FROM players WHERE id=?", (int(sid),)
                )
                p = cur.fetchone()
                if p:
                    pid, nick, micro, macro, wage = p
                    avg = (micro + macro) // 2
                    row = BoxLayout(size_hint_y=None, height=40, spacing=3)
                    info = _lbl(
                        f"  [{role_label}]  {nick}   скилл {avg}   ${wage:,}",
                        height=40, color=(0.9, 1.0, 0.85, 1),
                    )
                    rel_btn = Button(
                        text='Отпустить', size_hint=(None, None),
                        width=90, height=36,
                        background_color=(0.8, 0.3, 0.1, 1),
                    )
                    rel_btn.bind(on_press=lambda _, pid=pid, col=col: self._release(pid, col))
                    row.add_widget(info)
                    row.add_widget(rel_btn)
                    grid.add_widget(row)
            else:
                grid.add_widget(_lbl(f"  [{role_label}]  — свободно —",
                                     color=(0.6, 0.6, 0.6, 1)))

        conn.close()

        sv = ScrollView(size_hint=(0.38, 1))
        sv.add_widget(grid)
        return sv

    # ── right panel: free agents ──────────────────────────────

    def _make_free_agents_panel(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        # Get player team info (free slots, budget)
        cur.execute(
            "SELECT id, budget, carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE player='yes'"
        )
        team = cur.fetchone()
        if team:
            team_id, budget, *slot_ids = team
            budget = budget or 0
            filled = {ROLE_COLS[i]: slot_ids[i] for i in range(5)}
        else:
            team_id, budget, filled = None, 0, {}

        # Free agents: team_id=0 and have a role
        cur.execute(
            "SELECT id, name, surname, nickname, role, micro_skills, macro_skills, expected_wage "
            "FROM players WHERE team_id=0 AND role IS NOT NULL AND nickname != '' "
            "ORDER BY role, micro_skills DESC"
        )
        free_agents = cur.fetchall()
        conn.close()

        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))
        grid.add_widget(_header("  Свободные агенты"))

        if not free_agents:
            grid.add_widget(_lbl("  Нет свободных игроков.", color=(0.7, 0.7, 0.7, 1)))
        else:
            current_role = None
            for pid, fname, lname, nick, role, micro, macro, exp_wage in free_agents:
                exp_wage = exp_wage or 0
                avg = (micro + macro) // 2

                if role != current_role:
                    current_role = role
                    grid.add_widget(_lbl(
                        f"  ── {ROLE_LABELS.get(role, role)} ──",
                        height=30, color=(0.5, 0.85, 1.0, 1), bold=True,
                    ))

                row = BoxLayout(size_hint_y=None, height=42, spacing=3)

                can_sign = (
                    team_id is not None
                    and not filled.get(role)
                    and budget >= exp_wage
                )
                color = (1, 1, 1, 1) if can_sign else (0.55, 0.55, 0.55, 1)

                info = _lbl(
                    f"  {nick} ({fname} {lname.strip()})   "
                    f"скилл {avg}   ожид. ${exp_wage:,}/мес",
                    height=42, color=color,
                )
                sign_btn = Button(
                    text='Подписать',
                    size_hint=(None, None), width=100, height=38,
                    background_color=(0.1, 0.65, 0.2, 1) if can_sign else (0.3, 0.3, 0.3, 1),
                    disabled=not can_sign,
                )
                sign_btn.bind(
                    on_press=lambda _, pid=pid, role=role, wage=exp_wage:
                        self._sign(pid, role, wage)
                )

                row.add_widget(info)
                row.add_widget(sign_btn)
                grid.add_widget(row)

        sv = ScrollView(size_hint=(0.62, 1))
        sv.add_widget(grid)
        return sv

    # ── actions ───────────────────────────────────────────────

    def _release(self, player_id, role_col):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute("SELECT name, nickname FROM players WHERE id=?", (player_id,))
        p = cur.fetchone()
        nick = p[1] if p else str(player_id)

        cur.execute("SELECT id, name FROM teams WHERE player='yes'")
        team = cur.fetchone()
        if not team:
            conn.close()
            return
        team_id, team_name = team

        # Remove from team slot and set team_id=0, wage=0
        cur.execute(f"UPDATE teams SET {role_col}=NULL WHERE id=?", (team_id,))
        cur.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (player_id,))
        conn.commit()
        conn.close()

        _add_message(self.db_name, f"{nick} отпущен из {team_name}.")
        self._rebuild()

    def _sign(self, player_id, role, wage):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute("SELECT id, name, budget FROM teams WHERE player='yes'")
        team = cur.fetchone()
        if not team:
            conn.close()
            return
        team_id, team_name, budget = team
        budget = budget or 0

        # Double-check slot is free and budget ok
        cur.execute(f"SELECT {role} FROM teams WHERE id=?", (team_id,))
        slot = cur.fetchone()[0]
        if slot or budget < wage:
            conn.close()
            return

        cur.execute("SELECT nickname FROM players WHERE id=?", (player_id,))
        p = cur.fetchone()
        nick = p[0] if p else str(player_id)

        cur.execute(f"UPDATE teams SET {role}=? WHERE id=?", (player_id, team_id))
        cur.execute("UPDATE players SET team_id=?, wage=? WHERE id=?", (team_id, wage, player_id))
        conn.commit()
        conn.close()

        _add_message(self.db_name, f"{nick} подписан в {team_name} за ${wage:,}/мес.")
        self._rebuild()


def show_transfers_popup(db_name):
    TransferPopup(db_name=db_name).open()
