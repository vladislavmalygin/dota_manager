import random

from logic.dota.match_data import get_match_data
from logic.tournaments.draw import worldcup_system_draw
from logic.tournaments.invites import invites
from logic.dota.game import dota_simulation_for_bots


class WorldCupSystemTournamentGroupStage:
    def __init__(self, database, tournament_id):
        self.database = database
        self.tournament_id = tournament_id
        self.teams = invites(self.database)
        self.groups = worldcup_system_draw(self.database)
        self.tables = {
            f"Группа {i + 1}": {team: 0 for team in group}
            for i, group in enumerate(self.groups)
        }
        self.current_round = 0

    def generate_matches(self):
        matches_per_group = []
        for group in self.groups:
            matches = []
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    matches.append((group[i], group[j]))
            random.shuffle(matches)
            matches_per_group.append(matches)
        return matches_per_group

    def play_round(self, round_number):
        winners = []
        matches_per_group = self.generate_matches()

        for i, (matches, group) in enumerate(zip(matches_per_group, self.groups)):
            group_name = f"Группа {i + 1}"
            played_teams = set()

            for match in matches:
                team1, team2 = match
                if team1 not in played_teams and team2 not in played_teams:
                    skills = get_match_data(team1, team2, self.database)
                    winner = dota_simulation_for_bots(team1, team2, skills)
                    winners.append(f"{team1} vs {team2} → {winner}")

                    if winner == team1:
                        self.tables[group_name][team1] += 3
                    else:
                        self.tables[group_name][team2] += 3

                    played_teams.add(team1)
                    played_teams.add(team2)

                if len(played_teams) >= len(group):
                    break

        self.current_round += 1
        return winners

    def get_table(self):
        return {
            group: sorted(table.items(), key=lambda x: x[1], reverse=True)
            for group, table in self.tables.items()
        }

    def are_all_rounds_played(self):
        return self.current_round == 3

    def get_top_teams(self):
        top_teams = {}
        for group_name, table in self.tables.items():
            sorted_teams = sorted(table.items(), key=lambda x: (-x[1], x[0]))
            top_teams[group_name] = [team for team, points in sorted_teams[:2]]
        return top_teams

    def get_all_top_teams(self):
        top_teams_dict = self.get_top_teams()
        all_top_teams = []
        for teams in top_teams_dict.values():
            all_top_teams.extend(teams)
        return all_top_teams

    def print_tournament_info(self):
        print("Список команд:")
        print(", ".join(self.teams))
        print("\nГруппы:")
        for i, group in enumerate(self.groups, start=1):
            print(f"Группа {i}: {', '.join(group)}")
        for round_number in range(1, 4):
            self.play_round(round_number)

    def print_top_teams(self):
        top_teams = self.get_top_teams()
        print("Команды, занявшие первые два места в группах:")
        for group, teams in top_teams.items():
            print(f"{group}: {', '.join(teams)}")


class WorldCupSystemTournamentPlayoff:
    def __init__(self, teams, database):
        if len(teams) != 8:
            raise ValueError("Должно быть ровно 8 команд для плей-офф.")
        self.teams = list(teams)
        self.database = database

    def generate_quarter_finals(self):
        random.shuffle(self.teams)
        self.quarter_finals_pairs = [
            (self.teams[i], self.teams[i + 1]) for i in range(0, 8, 2)
        ]

    def play_quarter_finals(self):
        self.quarter_finals_winners = []
        for t1, t2 in self.quarter_finals_pairs:
            skills = get_match_data(t1, t2, self.database)
            winner = dota_simulation_for_bots(t1, t2, skills)
            self.quarter_finals_winners.append(winner)
            print(f"ЧФ: {t1} vs {t2} → {winner}")
        return self.quarter_finals_winners

    def generate_semi_finals(self):
        random.shuffle(self.quarter_finals_winners)
        self.semi_finals_pairs = [
            (self.quarter_finals_winners[i], self.quarter_finals_winners[i + 1])
            for i in range(0, 4, 2)
        ]

    def play_semi_finals(self):
        self.semi_finals_winners = []
        for t1, t2 in self.semi_finals_pairs:
            skills = get_match_data(t1, t2, self.database)
            winner = dota_simulation_for_bots(t1, t2, skills)
            self.semi_finals_winners.append(winner)
            print(f"ПФ: {t1} vs {t2} → {winner}")
        return self.semi_finals_winners

    def final_match(self):
        t1, t2 = self.semi_finals_winners[0], self.semi_finals_winners[1]
        skills = get_match_data(t1, t2, self.database)
        winner = dota_simulation_for_bots(t1, t2, skills)
        print(f"Финал: {t1} vs {t2} → Чемпион: {winner}!")
        return winner
