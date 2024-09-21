import sqlite3
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
import os

class SquadPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = ""
        self.size_hint = (0.8, 0.8)
        self.background_color = (1, 1, 1, 0)

        layout = BoxLayout(orientation='vertical', padding=0, spacing=0)

        # Создаем ScrollView
        scroll_view = ScrollView(size_hint=(1, 1))
        info_layout = GridLayout(cols=1, size_hint_y=None)
        info_layout.bind(minimum_height=info_layout.setter('height'))

        # Получаем данные из базы данных
        self.load_data(db_name, info_layout)

        scroll_view.add_widget(info_layout)
        layout.add_widget(scroll_view)

        close_button = Button(
            text="Close",
            size_hint_y=None,
            height=50,
            background_color=(1, 0, 0, 0.5),
            size_hint_x=1  # Занимает всю ширину
        )
        close_button.bind(on_press=self.dismiss)
        layout.add_widget(close_button)

        self.add_widget(layout)

        self.pos_hint = {'right': 1}
        self.y = 0

    def load_data(self, db_name, layout):
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Получаем команды с игроками
        cursor.execute(
            "SELECT id, carry, mid, offlane, partial_support, full_support FROM teams WHERE player = 'yes'")
        teams = cursor.fetchall()

        for team in teams:
            player_ids = team[1:]  # carry_id, mid_id, offlane_id, partial_support_id, full_support_id

            for player_id in player_ids:
                if player_id is not None:
                    cursor.execute("SELECT name, surname, nickname, face FROM players WHERE id = ?", (player_id,))
                    player = cursor.fetchone()
                    if player:
                        name, surname, nickname, face = player

                        # Проверка на наличие изображения
                        if not face or not os.path.exists(f"images/{face}"):
                            face_image_path = "images/players/generic.png"
                        else:
                            face_image_path = f"images/{face}"

                        # Создаем виджет для отображения информации об игроке
                        player_info = BoxLayout(size_hint_y=None, height=100, size_hint_x=1)

                        # Добавляем изображение игрока с масштабированием
                        player_image = Image(source=face_image_path, size_hint=(1, 1), width=50)
                        player_info.add_widget(player_image)

                        # Добавляем текст с именем и фамилией
                        player_label = Label(text=f"{name} {surname}", size_hint_x=None, width=200)
                        player_info.add_widget(player_label)

                        # Добавляем никнейм как кликабельный элемент с прозрачным фоном
                        nickname_button = Button(text=nickname, size_hint_x=None, width=200,
                                                 background_color=(0, 0, 0, 0.2))
                        nickname_button.bind(on_press=lambda instance, n=nickname: self.on_nickname_click(n))
                        player_info.add_widget(nickname_button)

                        layout.add_widget(player_info)

        conn.close()

    def on_nickname_click(self, nickname):
        print(f"Nickname {nickname} clicked!")

def show_squad_popup(db_name):
    popup = SquadPopup(db_name=db_name)
    popup.open()

