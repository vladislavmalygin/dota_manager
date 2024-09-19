import os
import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.image import Image

from core import DotaApp
from core import MainWindow

class LoadSavePopup(Popup):
    def __init__(self, **kwargs):
        super(LoadSavePopup, self).__init__(**kwargs)
        self.title = "Выберите сейв"
        self.size_hint = (0.8, 0.8)

        layout = BoxLayout(orientation='vertical')
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(grid)

        self.selected_save = None

        # Поиск всех баз данных в папке saves
        save_files = [f for f in os.listdir('saves') if f.endswith('.db')]

        for save_file in save_files:
            conn = sqlite3.connect(os.path.join('saves', save_file))
            cursor = conn.cursor()

            # Извлечение данных из базы
            cursor.execute("SELECT logo, name, manager FROM teams WHERE player = 'yes'")
            teams = cursor.fetchall()  # Извлечение всех записей
            conn.close()

            for team_data in teams:
                logo, name, manager = team_data

                # Путь к файлу изображения
                logo_path = os.path.join('images', logo)
                if not os.path.isfile(logo_path):
                    continue  # Пропустить, если файл отсутствует

                box = BoxLayout(orientation='horizontal', size_hint_y=None, height=120)

                img = Image(source=logo_path, size_hint_x=None, width=120)
                box.add_widget(img)

                btn = ToggleButton(
                    text=f"Команда: {name}\nМенеджер: {manager}",
                    group='saves',
                    size_hint=(1, None),
                    height=100
                )

                btn.bind(on_press=self.select_save)
                box.add_widget(btn)

                grid.add_widget(box)

        layout.add_widget(scroll_view)

        continue_btn = Button(text="Продолжить", size_hint=(1, 0.1))
        continue_btn.bind(on_press=self.continue_with_save)
        layout.add_widget(continue_btn)

        self.add_widget(layout)

    def select_save(self, instance):
        self.selected_save = instance.text

    def continue_with_save(self, instance):
        if self.selected_save:
            print(f"Вы выбрали: {self.selected_save}")
            self.dismiss()
            DotaApp.open_popup(self, instance)
        else:
            print("Сохранение не выбрано.")

    def load(self):
        # Логика загрузки сохранения
        selected_save = {self.selected_save}
        main_window = MainWindow(selected_save=selected_save)
        main_window.database_name  # Используем базу данных

    def open_popup(self, instance):
        popup = LoadSavePopup()
        popup.open()