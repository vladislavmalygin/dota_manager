from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup


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