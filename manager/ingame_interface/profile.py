import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout
import os


class ProfilePopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = ""
        self.size_hint = (0.7, 0.7)
        self.background_color = (1, 1, 1, 0)

        layout = BoxLayout(orientation='vertical', padding=10, spacing=8)

        self._populate(db_name, layout)

        close_btn = Button(text='Закрыть', size_hint_y=None, height=50,
                           background_color=(0.8, 0.2, 0.2, 0.8))
        close_btn.bind(on_press=self.dismiss)
        layout.add_widget(close_btn)
        self.add_widget(layout)

    def _label(self, text, font_size=16, color=(1, 1, 1, 1), height=40):
        lbl = Label(text=text, font_size=font_size, color=color,
                    size_hint_y=None, height=height,
                    halign='center', valign='middle')
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _populate(self, db_name, layout):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name, surname, nickname, portrait, COALESCE(reputation,0) "
            "FROM characters LIMIT 1"
        )
        char = cursor.fetchone()

        cursor.execute("SELECT name, country, rating FROM teams WHERE player = 'yes'")
        team = cursor.fetchone()

        cursor.execute("SELECT date FROM save WHERE id = 1")
        save = cursor.fetchone()
        conn.close()

        _REP_LEVEL = [
            (0,   'Новичок'),
            (10,  'Известный'),
            (25,  'Опытный'),
            (50,  'Ветеран'),
            (100, 'Легенда'),
            (200, 'Икона'),
        ]

        layout.add_widget(self._label("МОЙ ПРОФИЛЬ", font_size=22,
                                       color=(0.4, 0.9, 1.0, 1), height=50))

        if char:
            name, surname, nickname, portrait, reputation = char
            if portrait and os.path.exists(portrait):
                img = Image(source=portrait, size_hint_y=None, height=150)
                layout.add_widget(img)

            layout.add_widget(self._label(f"{name} '{nickname}' {surname}", font_size=20, height=44))

            rep_label = next((l for th, l in reversed(_REP_LEVEL) if reputation >= th), 'Новичок')
            layout.add_widget(self._label(
                f"Репутация: {reputation} пт  [{rep_label}]",
                height=36, color=(1.0, 0.85, 0.25, 1),
            ))
        else:
            layout.add_widget(self._label("Менеджер", font_size=20, height=44))

        if team:
            team_name, country, rating = team
            rating = rating or 0
            layout.add_widget(self._label(f"Команда: {team_name}", height=36))
            layout.add_widget(self._label(f"Страна команды: {country or '—'}", height=36))
            layout.add_widget(self._label(f"Рейтинг: {int(rating)}", height=36))

        if save:
            layout.add_widget(self._label(f"Дата: {save[0]}", height=36,
                                           color=(0.8, 0.8, 0.5, 1)))


def show_profile_popup(db_name):
    popup = ProfilePopup(db_name=db_name)
    popup.open()
