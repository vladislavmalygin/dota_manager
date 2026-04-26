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
from db_editor import open_db_editor

class MainMenu(FloatLayout):
    def __init__(self, **kwargs):  # Исправлено init на __init__
        super(MainMenu, self).__init__(**kwargs)

        # Задать фон основного экрана
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(source='images/background2.png', pos=self.pos, size=self.size)

        self.bind(size=self._update_rect, pos=self._update_rect)

        # Центральная панель с кнопками (адаптивный размер)
        self.box_layout = BoxLayout(
            orientation='vertical',
            size_hint=(0.32, 0.65),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            spacing=6,
        )
        self.add_widget(self.box_layout)

        title = Label(
            text='Главное меню', font_size='28sp',
            size_hint_y=0.22, color=(1, 1, 1, 1),
        )
        self.box_layout.add_widget(title)

        with title.canvas.before:
            Color(0.2, 0.6, 0.8, 0.7)
            self.rect_title = Rectangle(pos=title.pos, size=title.size)
        title.bind(size=self._update_title_rect, pos=self._update_title_rect)

        button_color = (0.2, 0.6, 0.8, 0.8)
        items = [
            ('Новая игра',           self.new_game),
            ('Продолжить игру',      self.continue_game),
            ('Загрузить игру',       self.load_game),
            ('Редактор базы данных', self.open_db_editor),
            ('Настройки',            self.open_settings),
            ('Выйти из игры',        self.exit_game),
        ]
        for text, handler in items:
            btn = Button(
                text=text, background_color=button_color,
                font_size='15sp', size_hint_y=1,
                on_press=handler,
            )
            self.box_layout.add_widget(btn)

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

    def open_db_editor(self, instance):
        open_db_editor()

    def open_settings(self, instance):
        SettingsPopup().open()

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
