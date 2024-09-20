from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle


class MessagePopup(Popup):
    def __init__(self, messages, **kwargs):
        super().__init__(**kwargs)
        self.title = ""  # Убираем заголовок
        self.size_hint = (0.8, 0.8)
        self.background_color = (1, 1, 1, 0)  # Прозрачный фон попапа

        layout = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # Создаем ScrollView
        scroll_view = ScrollView()
        messages_layout = GridLayout(cols=1, size_hint_y=None)
        messages_layout.bind(minimum_height=messages_layout.setter('height'))

        # Добавляем сообщения в GridLayout
        for message in messages:
            message_box = BoxLayout(size_hint_y=None, height=50, padding=[10], spacing=10)

            with message_box.canvas.before:
                Color(0, 0, 0, 0)  # Черный цвет фона сообщения
                rect = Rectangle(size=message_box.size, pos=message_box.pos)

            message_box.bind(size=lambda instance, value: self.update_rect(rect, instance),
                             pos=lambda instance, value: self.update_rect(rect, instance))

            message_label = Label(
                text=f"{message['date']} - {message['author']}: {message['text']}",
                size_hint_y=None,
                height=40,
                color=(1, 1, 1, 1),  # Белый цвет текста
                halign='left',
                valign='middle'
            )
            message_label.bind(size=message_label.setter('text_size'))
            message_box.add_widget(message_label)
            messages_layout.add_widget(message_box)

        scroll_view.add_widget(messages_layout)
        layout.add_widget(scroll_view)

        close_button = Button(
            text="Close",
            size_hint_y=None,
            height=50,
            background_color=(1, 0, 0, 0.5)  # Красный цвет с полупрозрачностью
        )
        close_button.bind(on_press=self.dismiss)
        layout.add_widget(close_button)

        self.add_widget(layout)

        self.pos_hint = {'right': 1}
        self.y = 0

    def update_rect(self, rect, instance):
        rect.pos = instance.pos
        rect.size = instance.size


def show_message(messages):
    popup = MessagePopup(messages)
    popup.open()
