import sqlite3

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from new_game import NewGamePopup

class MainMenu(FloatLayout):
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)

        # Задать фон
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(source='images/background.png', pos=self.pos, size=self.size)

        self.bind(size=self._update_rect, pos=self._update_rect)

        self.box_layout = BoxLayout(orientation='vertical', size_hint=(None, None), size=(400, 400))
        with self.box_layout.canvas.before:
            Color(255, 255, 255, 0.3)
            self.rect_box = Rectangle(pos=self.box_layout.pos, size=self.box_layout.size)

        self.add_widget(self.box_layout)

        title = Label(text='Главное меню', font_size=32, size_hint_y=None, height=50)
        self.box_layout.add_widget(title)

        self.box_layout.add_widget(Button(text='Новая игра', on_press=self.new_game))
        self.box_layout.add_widget(Button(text='Продолжить игру', on_press=self.continue_game))
        self.box_layout.add_widget(Button(text='Загрузить игру', on_press=self.load_game))
        self.box_layout.add_widget(Button(text='Настройки', on_press=self.settings))
        self.box_layout.add_widget(Button(text='Выйти из игры', on_press=self.exit_game))

    def _update_rect(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def new_game(self, instance):
        # Генерируем уникальное имя базы данных на основе времени
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
