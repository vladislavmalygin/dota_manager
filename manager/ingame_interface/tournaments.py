import sqlite3
import random
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView


class TournamentPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.teams = []
        self.groups = []
        self.tournament_name = ""
        self.current_round = 0  # 0 - групповой этап, 1 - плей-офф
        self.results = []  # Для хранения результатов матчей
        self.playoff_results = []

        self.title = "Турнир"
        self.size_hint = (0.8, 0.8)
        self.orientation = 'vertical'

        self.start_button = Button(text='Начать турнир', size_hint=(1, 0.1))
        self.start_button.bind(on_press=self.start_tournament)

        self.output_area = ScrollView(size_hint=(1, 0.9))
        self.output_label = Label(size_hint_y=None)
        self.output_label.bind(size=self.output_label.setter('text_size'))
        self.output_label.text_size = (self.output_area.width, None)
        self.output_label.text = ""

        self.output_area.add_widget(self.output_label)

        layout = BoxLayout(orientation='vertical')
        layout.add_widget(self.start_button)
        layout.add_widget(self.output_area)

        self.content = layout

    def load_teams(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM teams LIMIT 16")
        self.teams = [row[0] for row in cursor.fetchall()]
        conn.close()

    def create_groups(self):
        random.shuffle(self.teams)
        self.groups = [self.teams[i:i + 4] for i in range(0, len(self.teams), 4)]

    def load_tournament_name(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM tournaments LIMIT 1")
        self.tournament_name = cursor.fetchone()[0]
        conn.close()

    def play_group_stage(self):
        group_results_text = ""
        for group in self.groups:
            group_results = {team: 0 for team in group}  # Счет для каждой команды
            group_results_text += f"Группа: {group}\n"

            # Проведение матчей в группе
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    winner = self.play_match(group[i], group[j])
                    if winner == group[i]:
                        group_results[group[i]] += 3
                    else:
                        group_results[group[j]] += 3

            # Сохраняем результаты группы
            group_results_text += f"Результаты: {group_results}\n"
            self.results.append(group_results)

        return group_results_text

    def play_match(self, team_a, team_b):
        # Симуляция матча (монетка)
        return random.choice([team_a, team_b])

    def get_top_teams(self):
        top_teams = []
        for group in self.results:
            sorted_teams = sorted(group.items(), key=lambda x: x[1], reverse=True)
            top_teams.extend([team[0] for team in sorted_teams[:2]])  # Берем 2 лучшие команды
        return top_teams

    def play_knockout_stage(self, teams):
        playoff_results_text = "Плей-офф:\n"
        while len(teams) > 1:
            next_round_teams = []
            for i in range(0, len(teams), 2):
                winner = self.play_match(teams[i], teams[i + 1])
                next_round_teams.append(winner)
                playoff_results_text += f"{teams[i]} vs {teams[i + 1]} - Победитель: {winner}\n"
            teams = next_round_teams
            self.current_round += 1

        return playoff_results_text, teams[0]  # Возвращаем текст и победителя

    def start_tournament(self, instance):
        self.load_teams()
        self.create_groups()
        self.load_tournament_name()

        tournament_info = f"Турнир: {self.tournament_name}\n"

        # Групповой этап
        tournament_info += self.play_group_stage()

        # Плей-офф
        top_teams = self.get_top_teams()
        playoff_results_text, champion = self.play_knockout_stage(top_teams)

        tournament_info += playoff_results_text
        tournament_info += f"Турнир {self.tournament_name} выиграла команда: {champion}"

        # Обновляем текстовое поле с результатами
        self.output_label.text = tournament_info