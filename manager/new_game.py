import sqlite3
import shutil
import os

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle
from team_choice import TeamChoicePopup


class NewGamePopup(Popup):
    nickname = 'nickname'
    new_db_name = 'new_db_name'
    def __init__(self, **kwargs):
        super(NewGamePopup, self).__init__(**kwargs)
        self.title = "Создание нового персонажа"
        self.size_hint = (1, 1)

        layout = BoxLayout(orientation='vertical', padding=10)

        # Поля для ввода имени и фамилии
        self.name_input = TextInput(hint_text='Имя', multiline=False)
        self.surname_input = TextInput(hint_text='Фамилия', multiline=False)
        self.nickname_input = TextInput(hint_text='Никнейм', multiline=False)

        layout.add_widget(Label(text='Введите ваше имя:'))
        layout.add_widget(self.name_input)
        layout.add_widget(Label(text='Введите вашу фамилию:'))
        layout.add_widget(self.surname_input)
        layout.add_widget(Label(text='Введите ваш никнейм:'))
        layout.add_widget(self.nickname_input)

        # Выбор портрета
        self.portrait_selector = BoxLayout(size_hint_y=None, height=100, spacing=10)
        self.selected_portrait = None  # Для хранения выбранного портрета

        portraits = ['images/portrait4.png', 'images/portrait5.png', 'images/portrait6.png', 'images/portrait7.png',
                     'images/portrait8.png','images/portrait9.png','images/portrait10.png']
        for portrait in portraits:
            img = Image(source=portrait, size_hint_x=None, width=100)
            img.bind(on_touch_down=lambda instance, touch: self.select_portrait(instance, touch))
            self.portrait_selector.add_widget(img)

        layout.add_widget(Label(text='Выберите портрет:'))
        layout.add_widget(self.portrait_selector)

        # Кнопка создания персонажа
        create_button = Button(text='Создать', on_press=self.create_character)
        layout.add_widget(create_button)

        self.content = layout


    def select_portrait(self, instance, touch):
        if instance.collide_point(touch.x, touch.y):
            # Удаляем выделение с предыдущего портрета
            if self.selected_portrait:
                self.selected_portrait.canvas.before.clear()

            # Устанавливаем новый выбранный портрет
            self.selected_portrait = instance

            # Выделяем новый портрет рамочкой
            with instance.canvas.before:
                Color(255, 246, 0, 1)  # Черная рамка
                self.rect = RoundedRectangle(pos=(instance.x - 5, instance.y - 5),
                                             size=(instance.width + 10, instance.height + 10))

    def create_character(self, instance):
        name = self.name_input.text
        surname = self.surname_input.text
        global nickname
        nickname = self.nickname_input.text


        if not name or not surname or not nickname or not self.selected_portrait:
            print("Пожалуйста, заполните все поля и выберите портрет.")
            return

        print(f"Создан персонаж: {name} {surname}, Никнейм: {nickname}")


        # Создание имени файла для новой базы данных
        global new_db_name
        new_db_name = f"saves/{name}_{surname}.db"

        # Убедитесь, что папка 'saves' существует, если нет - создайте её
        if not os.path.exists('saves'):
            os.makedirs('saves')

        # Копирование базы данных
        shutil.copy('start_database.db', new_db_name)

        # Сохранение персонажа в новую базу данных
        conn = sqlite3.connect(new_db_name)
        cursor = conn.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS characters (
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            surname TEXT,
                            nickname TEXT,
                            portrait TEXT)''')

        cursor.execute("INSERT INTO characters (name, surname, nickname, portrait) VALUES (?, ?, ?, ?)",
                       (name, surname, nickname, self.selected_portrait.source))

        conn.commit()
        conn.close()

        # Закрыть попап после создания персонажа
        self.dismiss()


        # Открыть новое окно с выбором создания команды или выбора существующей
        TeamChoicePopup().open()

    def get_db_name(self):
        return new_db_name

    def get_nickname(self):
        return nickname