import sqlite3
import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Line


class SelectTeamPopup(Popup):
    def __init__(self, **kwargs):
        super(SelectTeamPopup, self).__init__(**kwargs)
        self.title = "Выбор команды"
        self.size_hint = (1, 1)

        layout = BoxLayout(orientation='horizontal', padding=10, spacing=10)

        # Сетка для выбора логотипов
        self.logo_selection_layout = GridLayout(cols=4, size_hint_y=None, spacing=10)
        self.logo_selection_layout.bind(minimum_height=self.logo_selection_layout.setter('height'))

        self.selected_logo = None
        self.selected_team = None

        # Текстовое поле для информации о команде
        self.team_info_label = Label(size_hint_y=None, height=100, halign='center', valign='middle')
        self.team_info_label.bind(size=self.team_info_label.setter('text_size'))

        # Загрузка команд из базы данных
        self.load_teams()

        # Создаем отдельный BoxLayout для размещения информации о команде
        info_layout = BoxLayout(orientation='vertical', size_hint_x=None, width=200, padding=(10, 0), spacing=10)
        info_layout.add_widget(self.team_info_label)

        # Добавляем сетку логотипов и текстовое поле в основной макет
        layout.add_widget(self.logo_selection_layout)
        layout.add_widget(info_layout)

        # Кнопка для подтверждения выбора команды
        select_button = Button(text='Выбрать', size_hint_y=None, height=50)
        select_button.bind(on_press=self.select_team)
        layout.add_widget(select_button)

        self.add_widget(layout)

    def load_teams(self):
        # Соединение с базой данных
        from new_game import NewGamePopup
        new_db_name = NewGamePopup.get_db_name(self)

        # Сохранение в базу данных
        conn = sqlite3.connect(new_db_name)
        cursor = conn.cursor()

        # Получение всех команд
        cursor.execute("SELECT name, logo, budget, country FROM teams")
        teams = cursor.fetchall()

        # Закрытие соединения
        conn.close()

        # Создание кнопок с логотипами
        for team in teams:
            name, logo, budget, country = team
            logo_path = os.path.join('images', f"{logo}.png")  # Формируем путь к логотипу

            # Создаём кнопку для логотипа
            team_button = Button(size_hint=(None, None), size=(100, 100))
            team_button.bind(on_press=lambda btn, n=name, b=budget, c=country: self.on_select_logo(btn, n, b, c))

            # Загружаем изображение
            logo_image = Image(source=logo_path, allow_stretch=True, size=(100, 100), size_hint=(None, None))
            team_button.add_widget(logo_image)

            self.logo_selection_layout.add_widget(team_button)

    def on_select_logo(self, button, name, budget, country):
        # Снятие выделения с предыдущего логотипа
        if self.selected_logo:
            self.selected_logo.canvas.before.clear()

        self.selected_logo = button

        # Рисуем желтую рамку вокруг выбранного логотипа
        with button.canvas.before:
            Color(1, 1, 0, 1)  # Жёлтый цвет
            self.rect = Rectangle(pos=button.pos, size=button.size)
            self.line = Line(rectangle=(button.x, button.y, button.width, button.height), width=2)

        # Обновление информации о команде
        self.selected_team = name
        self.team_info_label.text = f"Команда: {name}\nБюджет: {budget}\nСтрана: {country}"
    def select_team(self, instance):
        if self.selected_team:
            print(f"Выбрана команда: {self.selected_team}")
            self.dismiss()  # Закрыть всплывающее окно
