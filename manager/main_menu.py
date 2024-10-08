import pygame
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle

from new_game import NewGamePopup
from settings import SettingsPopup
from load_game import LoadSavePopup
from continue_game import ContinueLastSavePopup

class MainMenu(FloatLayout):
    def __init__(self, **kwargs):  # Исправлено init на __init__
        super(MainMenu, self).__init__(**kwargs)

        # Задать фон основного экрана
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(source='images/background2.png', pos=self.pos, size=self.size)

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
            Button(text='Настройки', background_color=button_color, size_hint_y=None, height=50, on_press=self.open_settings),
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
        NewGamePopup().open()

    def continue_game(self, instance):
        ContinueLastSavePopup().open()

    def load_game(self, instance):
        LoadSavePopup().open()

    def open_settings(self, instance):
        SettingsPopup().open()  # Открываем окно настроек

    def exit_game(self, instance):
        if hasattr(self, 'conn'):
            self.conn.close()  # Закрываем соединение с базой данных при выходе
        App.get_running_app().stop()


class Dota_Manager(App):
    def build(self):
        return MainMenu()

    def on_start(self):
        pygame.mixer.init()
        pygame.mixer.music.load('music/music.mp3')  # Замените на путь к вашему музыкальному файлу
        pygame.mixer.music.play(-1)  # -1 означает бесконечное воспроизведение

if __name__ == '__main__':
    Dota_Manager().run()
