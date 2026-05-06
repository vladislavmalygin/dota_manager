import sqlite3
import shutil
import os
import random

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle
from team_choice import TeamChoicePopup


def _randomize_skill_caps(db_name):
    """Randomize skill_cap only for players that have the default/unset cap."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    # Only randomize players whose skill_cap matches the migration default (200)
    # or is NULL — preserves values manually set in DB editor
    cur.execute(
        "SELECT id, micro_skills, macro_skills, soft_skills, skill_cap FROM players "
        "WHERE skill_cap IS NULL OR skill_cap = 200"
    )
    players = cur.fetchall()
    for pid, mi, ma, so, _ in players:
        mi = mi or 0; ma = ma or 0; so = so or 0
        current_total = mi + ma + so
        base = random.choices(
            [random.randint(150, 200),
             random.randint(180, 250),
             random.randint(220, 280),
             random.randint(260, 300)],
            weights=[30, 35, 25, 10],
            k=1
        )[0]
        cap = max(current_total + 10, base)
        cur.execute("UPDATE players SET skill_cap=? WHERE id=?", (cap, pid))
    conn.commit()
    conn.close()


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

        # Копируем шаблон ПЕРВЫМ — пользовательские правки из DB-редактора сохранятся
        shutil.copy('start_database.db', new_db_name)

        # Миграции запускаем на КОПИИ, не на шаблоне
        from db_migrate2 import migrate as _m2
        from db_migrate3 import migrate as _m3
        from db_migrate4 import migrate as _m4
        from db_migrate5 import migrate as _m5
        from db_migrate6 import migrate as _m6
        from db_migrate7 import migrate as _m7
        from db_migrate8 import migrate as _m8
        from db_migrate9  import migrate as _m9
        from db_migrate15 import migrate as _m15
        from db_migrate18 import migrate as _m18
        from db_migrate18_fix import migrate as _m18fix
        from db_migrate19 import migrate as _m19
        from db_migrate20 import migrate as _m20
        from db_fix_orphans import fix as _fix
        _m2(new_db_name)
        _m3(new_db_name)
        _m4(new_db_name)
        _m5(new_db_name)
        _m6(new_db_name)
        _m7(new_db_name)
        _m8(new_db_name)
        _m9(new_db_name)
        _m15(new_db_name)
        _m18(new_db_name)
        _m18fix(new_db_name)
        _m19(new_db_name)
        _m20(new_db_name)
        _fix(new_db_name)

        # Рандомизация skill_cap для новых игроков (пропускаем у кого уже задано)
        _randomize_skill_caps(new_db_name)

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
        global new_db_name
        return new_db_name

    def get_nickname(self):
        global nickname
        return nickname