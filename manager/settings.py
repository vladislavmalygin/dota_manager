from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.popup import Popup
from kivy.core.window import Window
import pygame

class SettingsPopup(Popup):
    def __init__(self, **kwargs):
        super(SettingsPopup, self).__init__(**kwargs)
        self.title = "Настройки"
        self.size_hint = (0.5, 0.5)

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Ползунок для громкости
        self.volume_slider = Slider(min=0, max=1, value=1)  # По умолчанию 100%
        self.volume_slider.bind(value=self.on_volume_change)
        layout.add_widget(Label(text='Громкость'))
        layout.add_widget(self.volume_slider)

        # Кнопка для переключения режима
        self.fullscreen_button = Button(text='Переключить полноэкранный режим')
        self.fullscreen_button.bind(on_press=self.toggle_fullscreen)
        layout.add_widget(self.fullscreen_button)

        # Кнопка закрытия
        close_button = Button(text='Закрыть', size_hint_y=None, height=50)
        close_button.bind(on_press=self.dismiss)
        layout.add_widget(close_button)

        self.add_widget(layout)

    def on_volume_change(self, instance, value):
        # Измените громкость музыки
        pygame.mixer.music.set_volume(value)

    def toggle_fullscreen(self, instance):
        # Переключение между полноэкранным и оконным режимом
        if Window.fullscreen == 'auto':
            Window.fullscreen = False
            self.fullscreen_button.text = 'Включить полноэкранный режим'
        else:
            Window.fullscreen = 'auto'
            self.fullscreen_button.text = 'Выключить полноэкранный режим'
