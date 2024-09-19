import sqlite3
import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from core import DotaPopup


class SelectTeamPopup(Popup):
    def __init__(self, **kwargs):
        super(SelectTeamPopup, self).__init__(**kwargs)
        self.title = "Выбор команды"
        self.size_hint = (1, 1)

        main_layout = BoxLayout(orientation='horizontal', padding=10)

        # Сетка для выбора логотипов
        self.logo_selection_layout = GridLayout(cols=4, size_hint_y=None)
        self.logo_selection_layout.bind(minimum_height=self.logo_selection_layout.setter('height'))

        self.selected_team = None

        # Обернем логотипы в ScrollView, если их много
        scroll_view = ScrollView(size_hint=(0.5, 1))
        scroll_view.add_widget(self.logo_selection_layout)

        # Панель для информации о команде с серым фоном
        info_layout = BoxLayout(orientation='vertical', size_hint=(0.4, 1), padding=10)
        info_layout.canvas.before.clear()
        with info_layout.canvas.before:
            Color(0.8, 0.8, 0.8, 0)  # Серый цвет
            self.rect = Rectangle(size=info_layout.size, pos=info_layout.pos)

        # Обновляем фон при изменении размера
        info_layout.bind(size=self._update_rect, pos=self._update_rect)

        self.team_info_label = Label(size_hint_y=None, height=200)
        info_layout.add_widget(self.team_info_label)

        # Создаем отдельный BoxLayout для кнопки
        button_layout = BoxLayout(size_hint_y=None, height=44)
        select_button = Button(text='Выбрать команду', size_hint_y=None, height=30)
        select_button.bind(on_press=self.select_team)
        button_layout.add_widget(select_button)

        info_layout.add_widget(button_layout)

        main_layout.add_widget(scroll_view)
        main_layout.add_widget(info_layout)

        # Загрузка команд из базы данных
        self.load_teams()

        self.content = main_layout

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def load_teams(self):
        # Получение списка команд из базы данных
        from new_game import NewGamePopup
        new_db_name = NewGamePopup.get_db_name(self)

        conn = sqlite3.connect(new_db_name)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, logo, country, carry, mid, offlane, partial_support, full_support, budget FROM teams")
        teams = cursor.fetchall()

        for team in teams:
            team_id, name, logo, country, carry, mid, offlane, partial_support, full_support, budget = team

            # Формирование пути к изображению
            logo_path = os.path.join('images', logo)

            logo_button = Button(background_normal=logo_path, size_hint=(None, None), size=(100, 100))
            logo_button.bind(on_press=lambda instance, t=team: self.select_team_callback(t))
            self.logo_selection_layout.add_widget(logo_button)

        conn.close()

    def select_team_callback(self, team):
        # Обработка выбора команды
        self.selected_team = team
        self.update_team_info()

    def update_team_info(self):
        if self.selected_team:
            team_id, name, logo, country, carry, mid, offlane, partial_support, full_support, budget = self.selected_team

            info_text = f"Команда: {name}\nСтрана: {country}\nБюджет: {budget}\nСостав:\n" \
                        f"Carry: {carry}\nMid: {mid}\nOfflane: {offlane}\n" \
                        f"Partial Support: {partial_support}\nFull Support: {full_support}"
            self.team_info_label.text = info_text

    def select_team(self, instance):
        from new_game import NewGamePopup
        manager_nickname = NewGamePopup.get_nickname(self)
        new_db_name = NewGamePopup.get_db_name(self)
        if self.selected_team:
            team_id, name, logo, country, carry, mid, offlane, partial_support, full_support, budget = self.selected_team

            # Подключение к базе данных
            conn = sqlite3.connect(new_db_name)
            cursor = conn.cursor()

            # Обновление колонки manager для выбранной команды
            cursor.execute("UPDATE teams SET manager = ? WHERE id = ?", (manager_nickname, team_id))

            # Обновление колонки player для всех команд
            cursor.execute("UPDATE teams SET player = 'no'")
            cursor.execute("UPDATE teams SET player = 'yes' WHERE id = ?", (team_id,))

            # Сохранение изменений и закрытие соединения
            conn.commit()
            conn.close()

            print(f"Выбрана команда: {name}, Страна: {country}, Бюджет: {budget}")
            self.dismiss()
            db_name = new_db_name
            DotaPopup(db_name).open_popup(db_name)
        else:
            print("Пожалуйста, выберите команду.")


