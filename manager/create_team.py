import sqlite3
import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label

from core import DotaPopup

REGIONS = ['EEU', 'WEU', 'NA', 'SA', 'China', 'SEA']


class CreateTeamPopup(Popup):
    def __init__(self, **kwargs):
        super(CreateTeamPopup, self).__init__(**kwargs)
        self.title = "Создание команды"
        self.size_hint = (1, 1)

        layout = BoxLayout(orientation='vertical', padding=10, spacing=6)

        self.team_name_input = TextInput(hint_text='Название команды', size_hint_y=None, height=44)
        layout.add_widget(self.team_name_input)

        region_row = BoxLayout(size_hint_y=None, height=44, spacing=6)
        region_row.add_widget(Label(text='Регион:', size_hint_x=None, width=80))
        self.region_spinner = Spinner(
            text='EEU',
            values=REGIONS,
            background_color=(0.18, 0.35, 0.55, 1),
            background_normal='',
        )
        region_row.add_widget(self.region_spinner)
        layout.add_widget(region_row)

        self.logo_display = Image(size_hint=(3, 3), pos_hint={'center_x': 0.75, 'center_y': 0.5})
        layout.add_widget(self.logo_display)

        logo_selection_layout = GridLayout(cols=3, size_hint_y=None)
        logo_selection_layout.bind(minimum_height=logo_selection_layout.setter('height'))

        self.logos = [
            'images/logo7.png', 'images/logo5.png', 'images/logo6.png',
            'images/logo8.png', 'images/logo1.png', 'images/logo2.png',
            'images/logo3.png', 'images/logo4.png',
        ]
        for logo in self.logos:
            btn = Button(background_normal=logo, size_hint=(None, None), size=(100, 100))
            btn.bind(on_press=self.set_logo)
            logo_selection_layout.add_widget(btn)

        layout.add_widget(logo_selection_layout)

        create_button = Button(text='Создать', size_hint_y=None, height=48,
                               on_press=self.create_team)
        layout.add_widget(create_button)

        self.content = layout

    def set_logo(self, instance):
        self.logo_display.source = instance.background_normal
        self.logo_display.reload()

    def create_team(self, instance):
        team_name = self.team_name_input.text.strip()
        region    = self.region_spinner.text
        logo_path = self.logo_display.source if self.logo_display.source else None

        from new_game import NewGamePopup
        manager_nickname = NewGamePopup.get_nickname(self)

        if not team_name:
            print("Пожалуйста, введите название команды.")
            return

        new_db_name = NewGamePopup.get_db_name(self)
        conn = sqlite3.connect(new_db_name)
        cursor = conn.cursor()
        logo_filename = os.path.basename(logo_path) if logo_path else None

        cursor.execute('''
            INSERT INTO teams
              (name, logo, country, region, owner, manager,
               carry, mid, offlane, partial_support, full_support,
               budget, player)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 2000000, 'yes')
        ''', (team_name, logo_filename, region, region,
              'rational', manager_nickname,
              '', '', '', '', ''))

        conn.commit()
        conn.close()

        self.dismiss()
        DotaPopup(new_db_name).open_popup(new_db_name)
