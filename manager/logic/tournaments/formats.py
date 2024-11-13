from manager.logic.dota.match_data import get_match_data, get_teams_with_player_yes
from manager.logic.tournaments.draw import worldcup_system_draw
from manager.logic.tournaments.invites import invites
from manager.logic.dota.game import dota_simulation_for_bots, dota_simulation

import random
database = 'test_database.db'

import random

class WorldCupSystemTournamentGroupStage:
    def __init__(self, database, tournament_id):
        self.database = database
        self.tournament_id = tournament_id
        self.teams = self.invites()
        self.groups = self.worldcup_system_draw()
        self.tables = {f"Группа {i + 1}": {team: 0 for team in group} for i, group in enumerate(self.groups)}  # Таблицы очков для каждой группы
        self.current_round = 0

    def invites(self):
        """Получить список команд из базы данных."""
        return invites(self.database)

    def worldcup_system_draw(self):
        """Получить жеребьёвку команд по группам."""
        return worldcup_system_draw(self.database)  # Предполагается, что возвращает список групп

    def generate_matches(self):
        """Генерирует матчи для всех групп."""
        matches_per_group = []

        for group in self.groups:
            matches = []
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    matches.append((group[i], group[j]))  # Создаем пары без повторений
            random.shuffle(matches)  # Перемешиваем матчи
            matches_per_group.append(matches)

        return matches_per_group

    def play_round(self, round_number):
        """Определяет победителей тура и обновляет таблицы."""
        winners = []
        matches_per_group = self.generate_matches()

        print(f"nРезультаты тура {round_number}:")
        for i, (matches, group) in enumerate(zip(matches_per_group, self.groups)):
            group_name = f"Группа {i + 1}"
            print(f"nМатчи в {group_name}:")
            played_teams = set()  # Множество для отслеживания сыгравших команд

            for match in matches:
                team1, team2 = match
                if team1 not in played_teams and team2 not in played_teams:  # Проверяем, играли ли команды в этом туре
                    skills = get_match_data(team1, team2, self.database)

                    # Проверяем, является ли одна из команд командой под управлением игрока
                    player_teams = get_teams_with_player_yes(self.database)
                    if team1 in player_teams or team2 in player_teams:
                        winner = dota_simulation(team1, team2, skills)  # Используем симуляцию для игроков
                    else:
                        winner = dota_simulation_for_bots(team1, team2, skills)  # Используем симуляцию для ботов

                    winners.append(f"Победитель пары {team1} : {team2} - {winner}")

                    if winner == team1:
                        self.tables[group_name][team1] += 3
                    else:
                        self.tables[group_name][team2] += 3

                    played_teams.add(team1)
                    played_teams.add(team2)

                    print(f"{team1} : {team2} - Победитель: {winner}")

                if len(played_teams) >= len(group):  # Если все команды сыграли, выходим
                    break

        self.current_round += 1

        # Печатаем таблицы после текущего тура
        print("nТаблицы после текущего тура:")
        tables = self.get_table()
        for group, table in tables.items():
            print(f"n{group}:")
            for team, points in table.items():
                print(f"{team}: {points} очков")

        return winners


    def get_table(self):
        """Возвращает таблицы очков для всех групп."""
        return {group: sorted(table.items(), key=lambda x: x[1], reverse=True) for group, table in self.tables.items()}

    def print_tournament_info(self):
        """Печатает всю информацию о турнире в заданном порядке."""

        # Печатаем список команд
        print("Список команд:")
        print(", ".join(self.teams))

        # Печатаем группы
        print("\nГруппы:")
        for i, group in enumerate(self.groups, start=1):
            print(f"Группа {i}: {', '.join(group)}")

        # Печатаем результаты и таблицы после каждого тура
        for round_number in range(1, 4):
            self.play_round(round_number)
    def are_all_rounds_played(self):
        """Проверяет, сыграны ли все три тура."""
        round = self.current_round == 3

    def get_top_teams(self):
        """Возвращает список команд, занявших первые два места в каждой группе."""
        top_teams = {}
        for group_name, table in self.tables.items():
            # Сортируем команды по очкам (по убыванию) и по имени (по возрастанию)
            sorted_teams = sorted(table.items(), key=lambda x: (-x[1], x[0]))

            # Берем первые две команды
            top_teams[group_name] = [team for team, points in sorted_teams[:2]]

        return top_teams

    def get_all_top_teams(self):
        """Возвращает общий список команд, занявших первые два места во всех группах."""
        top_teams_dict = self.get_top_teams()
        all_top_teams = []

        for teams in top_teams_dict.values():
            all_top_teams.extend(teams)  # Добавляем команды в общий список

        return all_top_teams

    def main(self):
        while not self.are_all_rounds_played():
            self.get_top_teams()
            self.get_all_top_teams()

    def print_top_teams(self):
        top_teams = tournament.get_top_teams()
        print(""
              "Команды, занявшие первые два места в группах:")
        for group, teams in top_teams.items():
            print(f"{group}: {', '.join(teams)}")


class WorldCupSystemTournamentPlayoff:
    def __init__(self, teams):
        if len(teams) != 8:
            raise ValueError("Должно быть ровно 8 команд для плей-офф.")
        self.teams = teams

    def generate_quarter_finals(self):
        """Составляет пары четвертьфинала и печатает их."""
        print("Пары четвертьфинала:")
        random.shuffle(self.teams)  # Перемешиваем команды
        self.quarter_finals_pairs = [(self.teams[i], self.teams[i + 1]) for i in range(0, 8, 2)]
        for match in self.quarter_finals_pairs:
            print(f"{match[0]} vs {match[1]}")

    def play_quarter_finals(self):
        """Симулирует результаты матчей четвертьфинала."""
        print("\nРезультаты четвертьфинала:")
        self.quarter_finals_winners = []
        for match in self.quarter_finals_pairs:
            skills = get_match_data(match[0], match[1], database)
            winner = dota_simulation_for_bots(match[0], match[1], skills)
            self.quarter_finals_winners.append(winner)
            print(f"Победитель: {winner}")

    def generate_semi_finals(self):
        """Составляет пары полуфинала и печатает их."""
        if len(self.quarter_finals_winners) < 4:
            raise ValueError("Недостаточно команд для формирования полуфинала.")

        print("\nПары полуфинала:")
        random.shuffle(self.quarter_finals_winners)
        self.semi_finals_pairs = [(self.quarter_finals_winners[i], self.quarter_finals_winners[i + 1]) for i in range(0, 4, 2)]
        for match in self.semi_finals_pairs:
            print(f"{match[0]} vs {match[1]}")

    def play_semi_finals(self):
        """Симулирует результаты матчей полуфинала."""
        print("\nРезультаты полуфинала:")
        self.semi_finals_winners = []
        for match in self.semi_finals_pairs:
            skills = get_match_data(match[0], match[1], database)
            winner = dota_simulation_for_bots(match[0], match[1], skills)
            self.semi_finals_winners.append(winner)
            print(f"Победитель: {winner}")

    def final_match(self):
        """Печатает пару финала и результат."""
        if len(self.semi_finals_winners) < 2:
            raise ValueError("Недостаточно команд для проведения финала.")

        print("\nФинал:")
        final_match = (self.semi_finals_winners[0], self.semi_finals_winners[1])
        print(f"{final_match[0]} vs {final_match[1]}")
        skills = get_match_data(final_match[0], final_match[1], database)
        winner = dota_simulation_for_bots(final_match[0], final_match[1], skills)
        print(f"Победитель финала: {winner}")
        print(f"Поздравляем {winner} с победой в турнире!")




tournament = WorldCupSystemTournamentGroupStage('test_database.db', 'tournament_id')
tournament.print_tournament_info()
teams = tournament.get_all_top_teams()
playoff = WorldCupSystemTournamentPlayoff(teams)
playoff.generate_quarter_finals()
playoff.play_quarter_finals()
playoff.generate_semi_finals()
playoff.play_semi_finals()
playoff.final_match()