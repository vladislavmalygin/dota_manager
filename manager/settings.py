from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.core.window import Window
import pygame

_AUTO_SPEED_OPTIONS = [
    ('Медленно (2с)',  2.0),
    ('Нормально (1.5с)', 1.5),
    ('Быстро (0.8с)', 0.8),
    ('Очень быстро (0.3с)', 0.3),
]
AUTO_ADVANCE_SPEED = 1.5  # seconds between days, global mutable


class SettingsPopup(Popup):
    def __init__(self, **kwargs):
        super(SettingsPopup, self).__init__(**kwargs)
        self.title = "Настройки"
        self.size_hint = (0.55, 0.60)

        layout = BoxLayout(orientation='vertical', padding=14, spacing=10)

        # Volume
        layout.add_widget(Label(text='Громкость', size_hint_y=None, height=28,
                                color=(0.8, 0.8, 0.8, 1)))
        self.volume_slider = Slider(min=0, max=1, value=1, size_hint_y=None, height=36)
        self.volume_slider.bind(value=self.on_volume_change)
        layout.add_widget(self.volume_slider)

        # Auto-advance speed
        layout.add_widget(Label(text='Скорость листания', size_hint_y=None, height=28,
                                color=(0.8, 0.8, 0.8, 1)))
        speed_row = BoxLayout(size_hint_y=None, height=40, spacing=4)
        for label, secs in _AUTO_SPEED_OPTIONS:
            btn = Button(text=label, background_normal='',
                         background_color=(0.18, 0.45, 0.65, 1) if secs == AUTO_ADVANCE_SPEED
                                          else (0.18, 0.20, 0.28, 1))
            btn._speed_val = secs  # store speed value as attribute for reliable matching
            btn.bind(on_press=lambda _, s=secs: self._set_speed(s, speed_row))
            speed_row.add_widget(btn)
        layout.add_widget(speed_row)

        # Fullscreen
        self.fullscreen_button = Button(
            text='Переключить полноэкранный режим',
            size_hint_y=None, height=44,
            background_normal='', background_color=(0.22, 0.28, 0.40, 1))
        self.fullscreen_button.bind(on_press=self.toggle_fullscreen)
        layout.add_widget(self.fullscreen_button)

        close_button = Button(text='Закрыть', size_hint_y=None, height=44,
                              background_normal='', background_color=(0.55, 0.18, 0.18, 1))
        close_button.bind(on_press=self.dismiss)
        layout.add_widget(close_button)

        self.content = layout

    def _set_speed(self, secs, speed_row):
        global AUTO_ADVANCE_SPEED
        AUTO_ADVANCE_SPEED = secs
        for btn in speed_row.children:
            btn.background_color = (0.18, 0.45, 0.65, 1) if getattr(btn, '_speed_val', None) == secs \
                                    else (0.18, 0.20, 0.28, 1)

    def on_volume_change(self, instance, value):
        try:
            pygame.mixer.music.set_volume(value)
        except Exception:
            pass

    def toggle_fullscreen(self, instance):
        if Window.fullscreen == 'auto':
            Window.fullscreen = False
            self.fullscreen_button.text = 'Включить полноэкранный режим'
        else:
            Window.fullscreen = 'auto'
            self.fullscreen_button.text = 'Выключить полноэкранный режим'
