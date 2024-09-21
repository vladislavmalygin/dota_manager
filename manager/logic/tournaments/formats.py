from manager.logic.dota.Game import determine_winner
from manager.logic.tournaments.draw import worldcup_system_draw
from manager.logic.tournaments.invites import invites


import random

class WorldCupSystemTournament:
    def __init__(self, database, tournament_id):
        self.database = database
        self.tournament_id = tournament_id
        self.teams = self.invites()
        self.groups = self.worldcup_system_draw()
        self.tables = {f"Группа {i + 1}": {team: 0 for team in group} for i, group in enumerate(self.groups)}  # Таблицы очков для каждой группы

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

        print(f"\nРезультаты тура {round_number}:")
        for i, matches in enumerate(matches_per_group):
            group_name = f"Группа {i + 1}"
            print(f"\nМатчи в {group_name}:")
            if len(matches) >= 2:  # Проверяем, достаточно ли матчей для тура
                for _ in range(2):  # Проигрываем два матча в группе
                    if not matches:  # Если нет матчей, выходим
                        break
                    match = matches.pop(0)
                    team1, team2 = match
                    winner = determine_winner(team1, team2)
                    winners.append(f"Победитель пары {team1} : {team2} - {winner}")

                    # Обновляем таблицу очков для соответствующей группы
                    if winner == team1:
                        self.tables[group_name][team1] += 3
                    else:
                        self.tables[group_name][team2] += 3

                    # Печатаем результат матча
                    print(f"{team1} : {team2} - Победитель: {winner}")

        # Печатаем таблицы после текущего тура
        print("\nТаблицы после текущего тура:")
        tables = self.get_table()
        for group, table in tables.items():
            print(f"\n{group}:")
            for team, points in table:
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



# Пример использования:
tournament = WorldCupSystemTournament('test_database.db', 'tournament_id')
tournament.print_tournament_info()
