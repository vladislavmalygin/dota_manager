import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout


class OrganizationPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = ""
        self.size_hint = (0.85, 0.85)
        self.background_color = (1, 1, 1, 0)

        layout = BoxLayout(orientation='vertical', padding=5, spacing=5)
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=4)
        grid.bind(minimum_height=grid.setter('height'))

        self._populate(db_name, grid)

        scroll.add_widget(grid)
        layout.add_widget(scroll)

        close_btn = Button(text='Закрыть', size_hint_y=None, height=50,
                           background_color=(0.8, 0.2, 0.2, 0.8))
        close_btn.bind(on_press=self.dismiss)
        layout.add_widget(close_btn)
        self.add_widget(layout)

    def _row(self, text, height=40):
        lbl = Label(text=text, size_hint_y=None, height=height,
                    halign='left', valign='middle', color=(1, 1, 1, 1))
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _header(self, text):
        lbl = Label(text=f'[b]{text}[/b]', markup=True,
                    size_hint_y=None, height=50,
                    halign='center', valign='middle',
                    color=(0.4, 0.9, 1.0, 1))
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _populate(self, db_name, grid):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, country, budget, manager, rating FROM teams WHERE player = 'yes'"
        )
        team = cursor.fetchone()
        if not team:
            grid.add_widget(self._row("Команда не найдена."))
            conn.close()
            return

        team_id, name, country, budget, manager, rating = team
        budget = budget or 0
        rating = rating or 0

        grid.add_widget(self._header(f"Организация: {name}"))
        grid.add_widget(self._row(f"  Страна: {country or '—'}"))
        grid.add_widget(self._row(f"  Менеджер: {manager or '—'}"))
        grid.add_widget(self._row(f"  Рейтинг: {int(rating)}"))
        grid.add_widget(self._row(f"  Бюджет: ${budget:,}", height=50))

        roles_order = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
        roles_labels = ['Carry (1)', 'Mid (2)', 'Offlane (3)', 'Support (4)', 'Support (5)']

        cursor.execute(
            "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE id = ?",
            (team_id,)
        )
        role_ids = cursor.fetchone()

        grid.add_widget(self._header("Состав и зарплаты"))

        total_wage = 0
        for idx, role_label in enumerate(roles_labels):
            player_id = role_ids[idx] if role_ids else None
            if player_id:
                cursor.execute(
                    "SELECT name, surname, nickname, wage, micro_skills, macro_skills FROM players WHERE id = ?",
                    (player_id,)
                )
                p = cursor.fetchone()
                if p:
                    pname, psurname, pnick, wage, micro, macro = p
                    wage = wage or 0
                    total_wage += wage
                    skill_avg = int(((micro or 0) + (macro or 0)) / 2)
                    grid.add_widget(self._row(
                        f"  [{role_label}]  {pname} '{pnick}' {psurname}"
                        f"   Скилл: {skill_avg}   Зарплата: ${wage:,}/мес"
                    ))

        grid.add_widget(self._row(f"  Итого зарплат: ${total_wage:,}/мес", height=50))
        months_left = (budget // total_wage) if total_wage > 0 else 0
        grid.add_widget(self._row(
            f"  Бюджет хватит на: ~{months_left} мес.  "
            f"(после выплаты: ${budget - total_wage:,})"
        ))

        conn.close()


def show_organization_popup(db_name):
    popup = OrganizationPopup(db_name=db_name)
    popup.open()
