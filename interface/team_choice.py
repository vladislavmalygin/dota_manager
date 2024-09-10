import sqlite3
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout


# Создаем базу данных и таблицу, если они не существуют
def init_db():
    conn = sqlite3.connect('new_game_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY,
            name TEXT,
            logo TEXT,
            country TEXT,
            owner TEXT,
            manager TEXT,
            carry TEXT,
            mid TEXT,
            offlane TEXT,
            partial_support TEXT,
            full_support TEXT,
            budget INTEGER
        )
    ''')
    conn.commit()
    conn.close()


class TeamChoicePopup(Popup):
    def __init__(self, **kwargs):
        super(TeamChoicePopup, self).__init__(**kwargs)
        self.title = "Выбор команды"
        self.size_hint = (0.6, 0.4)

        layout = BoxLayout(orientation='vertical', padding=10)

        create_team_button = Button(text='Создать команду', on_press=self.create_team)
        choose_existing_button = Button(text='Выбрать существующую', on_press=self.choose_existing)

        layout.add_widget(create_team_button)
        layout.add_widget(choose_existing_button)

        self.content = layout

    def create_team(self, instance):
        CreateTeamPopup().open()

    def choose_existing(self, instance):
        print("Выбор существующей команды...")
        # Логика выбора существующей команды


class CreateTeamPopup(Popup):
    def __init__(self, **kwargs):
        super(CreateTeamPopup, self).__init__(**kwargs)
        self.title = "Создание команды"
        self.size_hint = (0.8, 0.6)

        layout = BoxLayout(orientation='vertical', padding=10)

        # Поле для ввода названия команды
        self.team_name_input = TextInput(hint_text='Название команды')
        layout.add_widget(self.team_name_input)

        # Поле для ввода страны
        self.country_input = TextInput(hint_text='Страна')
        layout.add_widget(self.country_input)

        # Создаем сетку для выбора логотипа
        self.logo_display = Image(size_hint=(1, 0.5))
        layout.add_widget(self.logo_display)

        logo_selection_layout = GridLayout(cols=3, size_hint_y=None)
        logo_selection_layout.bind(minimum_height=logo_selection_layout.setter('height'))

        # Предустановленные логотипы
        self.logos = [
            'images/logo1.png',
            'images/logo2.png',
            'images/logo3.png',
            'images/logo4.png',
        ]

        for logo in self.logos:
            logo_button = Button(background_normal=logo, size_hint=(None, None), size=(100, 100))
            logo_button.bind(on_press=self.set_logo)
            logo_selection_layout.add_widget(logo_button)

        layout.add_widget(logo_selection_layout)

        # Кнопка для подтверждения создания команды
        create_button = Button(text='Создать', on_press=self.create_team)
        layout.add_widget(create_button)

        self.content = layout

    def set_logo(self, instance):
        logo_path = instance.background_normal
        self.logo_display.source = logo_path
        self.logo_display.reload()

    def create_team(self, instance):
        team_name = self.team_name_input.text.strip()
        country = self.country_input.text.strip()
        logo_path = self.logo_display.source if self.logo_display.source else "Нет логотипа"

        # Здесь можно указать имя менеджера, который создаёт команду
        manager_name = "Менеджер"  # Замените на имя вашего менеджера

        if not team_name or not country:
            print("Пожалуйста, заполните все поля.")
            return

        # Сохранение в базу данных
        conn = sqlite3.connect('new_game_database.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO teams (name, logo, country, owner, manager, carry, mid, offlane, partial_support, full_support, budget)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (team_name, logo_path, country, manager_name, manager_name, '', '', '', '', '', 100000))

        conn.commit()
        conn.close()

        print(f"Создана команда: {team_name}, Страна: {country}, Логотип: {logo_path}, Бюджет: 100000")


# Инициализация базы данных при запуске приложения
init_db()






