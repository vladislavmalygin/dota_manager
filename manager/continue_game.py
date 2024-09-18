import os
import sqlite3
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from datetime import datetime


class ContinueLastSavePopup(Popup):
    def __init__(self, **kwargs):
        super(ContinueLastSavePopup, self).__init__(**kwargs)
        self.title = "Продолжить последнюю игру"
        self.size_hint = (0.8, 0.8)

        layout = BoxLayout(orientation='vertical')

        # Найти последний измененный файл в папке saves
        save_files = [f for f in os.listdir('saves') if f.endswith('.db')]
        if not save_files:
            layout.add_widget(Button(text="Нет доступных сохранений", size_hint=(1, 0.9)))
            self.add_widget(layout)
            return

        latest_save = max(save_files, key=lambda f: os.path.getmtime(os.path.join('saves', f)))

        # Подключение к базе данных последнего сохранения
        conn = sqlite3.connect(os.path.join('saves', latest_save))
        cursor = conn.cursor()

        cursor.execute("SELECT logo, name, manager FROM teams WHERE player = 'yes'")
        team_data = cursor.fetchone()  # Достаем только одну команду
        conn.close()

        # Проверяем и показываем данные
        if team_data:
            logo, name, manager = team_data

            logo_path = os.path.join('images', logo)
            if os.path.isfile(logo_path):
                img = Image(source=logo_path, size_hint_y=0.6)
                layout.add_widget(img)

            info_label = Button(text=f"Команда: {name}\nМенеджер: {manager}", size_hint=(1, 0.3))
            layout.add_widget(info_label)

        confirm_btn = Button(text="Продолжить", size_hint=(1, 0.1))
        confirm_btn.bind(on_press=self.confirm_continue)
        layout.add_widget(confirm_btn)

        self.add_widget(layout)

    def confirm_continue(self, instance):
        print("Продолжение последней игры.")
        self.dismiss()