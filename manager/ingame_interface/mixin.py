from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle


class GenericPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = ""  # Убираем заголовок
        self.size_hint = (0.8, 0.8)
        self.background_color = (1, 1, 1, 0)  # Прозрачный фон попапа

        layout = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # Создаем ScrollView
        scroll_view = ScrollView()
        info_layout = GridLayout(cols=1, size_hint_y=None)
        info_layout.bind(minimum_height=info_layout.setter('height'))

        scroll_view.add_widget(info_layout)
        layout.add_widget(scroll_view)

        close_button = Button(
            text="Close",
            size_hint_y=None,
            height=50,
            background_color=(1, 0, 0, 0.5)
        )
        close_button.bind(on_press=self.dismiss)
        layout.add_widget(close_button)

        self.add_widget(layout)

        self.pos_hint = {'right': 1}
        self.y = 0

    def update_rect(self, rect, instance):
        rect.pos = instance.pos
        rect.size = instance.size


def show_custom_popup():
    popup = GenericPopup()
    popup.open()
