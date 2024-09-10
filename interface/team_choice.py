import sqlite3

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle


class TeamChoicePopup(Popup):
    def __init__(self, **kwargs):
        super(TeamChoicePopup, self).__init__(**kwargs)
        self.title = "Выбор команды"
        self.size_hint = (0.6, 0.4)

        layout = BoxLayout(orientation='vertical', padding=10)

        create_team_button = Button(text='Создать команду', on_press=self.create_team)
        choose_existing_button = Button(text='Выбрать существующую', on_press=self.choose_existing)

        layout.add_widget(create_team_button)
        layout.add_widget(choose_existing_button)

        self.content = layout

    def create_team(self, instance):
        print("Создание команды...")
        # Логика создания команды

    def choose_existing(self, instance):
        print("Выбор существующей команды...")
        # Логика выбора существующей команды