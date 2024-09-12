from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle

import sqlite3

from new_game import NewGamePopup

class MainMenu(FloatLayout):
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)

        # Задать фон основного экрана
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(source='images/background.png', pos=self.pos, size=self.size)

        self.bind(size=self._update_rect, pos=self._update_rect)

        # Создаем BoxLayout для кнопок
        self.box_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(400, 400),
                                    pos_hint={'center_x': 0.5, 'center_y': 0.5})

        self.add_widget(self.box_layout)

        title = Label(text='Главное меню', font_size=32, size_hint_y=None, height=50, color=(1, 1, 1, 1))
        self.box_layout.add_widget(title)

        # Задать фон только для заголовка
        with title.canvas.before:
            Color(0.2, 0.6, 0.8, 0.7)  # Прозрачный фон
            self.rect_title = Rectangle(pos=title.pos, size=title.size)

        title.bind(size=self._update_title_rect, pos=self._update_title_rect)

        button_color = (0.2, 0.6, 0.8, 0.7)

        # Создание кнопок с заданной высотой
        buttons = [
            Button(text='Новая игра', background_color=button_color, size_hint_y=None, height=50, on_press=self.new_game),
            Button(text='Продолжить игру', background_color=button_color, size_hint_y=None, height=50, on_press=self.continue_game),
            Button(text='Загрузить игру', background_color=button_color, size_hint_y=None, height=50, on_press=self.load_game),
            Button(text='Настройки', background_color=button_color, size_hint_y=None, height=50, on_press=self.settings),
            Button(text='Выйти из игры', background_color=button_color, size_hint_y=None, height=50, on_press=self.exit_game)
        ]

        for button in buttons:
            self.box_layout.add_widget(button)

    def _update_rect(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _update_title_rect(self, instance, value):
        self.rect_title.pos = instance.pos
        self.rect_title.size = instance.size

    def new_game(self, instance):
        db_name = 'new_game_database.db'

        # Создаем новую базу данных для новой игры
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Создаем необходимые таблицы
        cursor.execute('''CREATE TABLE IF NOT EXISTS characters (
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            surname TEXT,
                            nickname TEXT,
                            portrait TEXT)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS game_state (
                            id INTEGER PRIMARY KEY,
                            character_id INTEGER,
                            state TEXT)''')

        conn.commit()
        conn.close()

        NewGamePopup().open()

    def continue_game(self, instance):
        print("Продолжаем игру!")

    def load_game(self, instance):
        print("Загружаем игру!")

    def settings(self, instance):
        print("Открываем настройки!")

    def exit_game(self, instance):
        if hasattr(self, 'conn'):
            self.conn.close()  # Закрываем соединение с базой данных при выходе
        App.get_running_app().stop()


class Dota_Manager(App):
    def build(self):
        return MainMenu()

if __name__ == '__main__':
    Dota_Manager().run()
