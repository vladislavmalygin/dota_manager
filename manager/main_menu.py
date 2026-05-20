import pygame
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

from new_game import NewGamePopup
from settings import SettingsPopup
from load_game import LoadSavePopup
from continue_game import ContinueLastSavePopup
from db_editor import open_db_editor
import ui_theme as T


class HoverButton(Button):
    """Button that brightens on mouse hover."""

    def __init__(self, hover_color=None, **kwargs):
        self._base_color  = list(kwargs.get('background_color', T.BTN_PRIMARY))
        self._hover_color = list(hover_color or T.NAV_ACTIVE)
        super().__init__(**kwargs)

    def on_parent(self, widget, parent):
        from kivy.core.window import Window
        if parent:
            Window.bind(mouse_pos=self._on_mouse_pos)
        else:
            Window.unbind(mouse_pos=self._on_mouse_pos)

    def _on_mouse_pos(self, _win, pos):
        if not self.get_root_window():
            return
        inside = self.collide_point(*self.to_widget(*pos))
        self.background_color = self._hover_color if inside else self._base_color


class MainMenu(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(source='images/background2.png', pos=self.pos, size=self.size)
        self.bind(size=self._update_rect, pos=self._update_rect)

        self.box_layout = BoxLayout(
            orientation='vertical',
            size_hint=(0.32, 0.70),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            spacing=6,
        )
        self.add_widget(self.box_layout)

        title = Label(
            text='Главное меню', font_size=T.FS_HERO,
            size_hint_y=0.18, color=T.TEXT_MAIN,
        )
        self.box_layout.add_widget(title)
        with title.canvas.before:
            Color(*T.NAV_ACTIVE)
            self.rect_title = Rectangle(pos=title.pos, size=title.size)
        title.bind(size=self._update_title_rect, pos=self._update_title_rect)

        main_items = [
            ('► Новая игра',           self.new_game,       T.BTN_PRIMARY),
            ('↩ Продолжить игру',      self.continue_game,  T.BTN_PRIMARY),
            ('≡ Загрузить игру',       self.load_game,      T.BTN_PRIMARY),
            ('✎ Редактор базы данных', self.open_db_editor, T.BTN_NEUTRAL),
            ('⚙ Настройки',            self.open_settings,  T.BTN_NEUTRAL),
        ]
        for text, handler, color in main_items:
            btn = HoverButton(
                text=text,
                background_color=color,
                hover_color=T.NAV_ACTIVE,
                background_normal='',
                font_size=T.FS_BODY,
                size_hint_y=1,
                on_press=handler,
            )
            self.box_layout.add_widget(btn)

        # Separator before exit
        sep = Widget(size_hint_y=None, height=8)
        self.box_layout.add_widget(sep)

        exit_btn = HoverButton(
            text='✕ Выйти из игры',
            background_color=T.BTN_DANGER,
            hover_color=(0.80, 0.22, 0.22, 1),
            background_normal='',
            font_size=T.FS_BODY,
            size_hint_y=0.8,
            on_press=self.exit_game,
        )
        self.box_layout.add_widget(exit_btn)

        ver = Label(
            text='v0.1', font_size=T.FS_TINY,
            color=T.TEXT_DIM,
            size_hint=(None, None), size=(50, 20),
            pos_hint={'right': 0.99, 'y': 0.01},
        )
        self.add_widget(ver)

    def _update_rect(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _update_title_rect(self, instance, value):
        self.rect_title.pos = instance.pos
        self.rect_title.size = instance.size

    def new_game(self, instance):       NewGamePopup().open()
    def continue_game(self, instance):  ContinueLastSavePopup().open()
    def load_game(self, instance):      LoadSavePopup().open()
    def open_db_editor(self, instance): open_db_editor()
    def open_settings(self, instance):  SettingsPopup().open()

    def exit_game(self, instance):
        if hasattr(self, 'conn'):
            self.conn.close()
        App.get_running_app().stop()


class Dota_Manager(App):
    def build(self):
        return MainMenu()

    def on_start(self):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load('music/music.mp3')
            pygame.mixer.music.play(-1)
        except Exception:
            pass


if __name__ == '__main__':
    Dota_Manager().run()
