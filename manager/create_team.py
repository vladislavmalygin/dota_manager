import sqlite3
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout

class CreateTeamPopup(Popup):
    def __init__(self, **kwargs):
        super(CreateTeamPopup, self).__init__(**kwargs)
        self.title = "Создание команды"
        self.size_hint = (1, 1)

        layout = BoxLayout(orientation='vertical', padding=10)

        # Поле для ввода названия команды
        self.team_name_input = TextInput(hint_text='Название команды')
        layout.add_widget(self.team_name_input)

        # Поле для ввода страны
        self.country_input = TextInput(hint_text='Страна')
        layout.add_widget(self.country_input)

        # Создаем сетку для выбора логотипа
        self.logo_display = Image(size_hint=(3, 3), pos_hint={'center_x': 0.75, 'center_y': 0.5})
        layout.add_widget(self.logo_display)

        logo_selection_layout = GridLayout(cols=3, size_hint_y=None)
        logo_selection_layout.bind(minimum_height=logo_selection_layout.setter('height'))

        # Предустановленные логотипы
        self.logos = [
            'images/logo7.png',
            'images/logo5.png',
            'images/logo6.png',
            'images/logo8.png',
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
        from new_game import NewGamePopup
        manager_nickname = NewGamePopup.get_nickname(self)

        if not team_name or not country:
            print("Пожалуйста, заполните все поля.")
            return

        from new_game import NewGamePopup
        new_db_name = NewGamePopup.get_db_name(self)
        # Сохранение в базу данных
        conn = sqlite3.connect(new_db_name)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO teams (name, logo, country, owner, manager, carry, mid, offlane, partial_support, full_support, budget, player)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (team_name, logo_path, country, 'rational', manager_nickname, '', '', '', '', '', 100000, 'yes'))

        conn.commit()
        conn.close()

        print(f"Создана команда: {team_name}, Страна: {country}, Логотип: {logo_path}, Бюджет: 100000")
