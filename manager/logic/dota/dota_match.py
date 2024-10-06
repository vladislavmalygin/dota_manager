import random

from draft_random import draft
from get_match_data import get_match_data


class DotaMatch:
    def __init__(self, team_a, team_b, db_name):
        self.team_a = team_a
        self.team_b = team_b
        self.db_name = db_name
        self.match_data = get_match_data(team_a, team_b, db_name)
        self.draft_results = draft(team_a, team_b)

        # Инициализация баффов для команды A
        self.team_a_carry_draft_buff = 1.0
        if f'Carry команды {team_a} получил контрпик' in self.draft_results[self.team_a]:
            self.team_a_carry_draft_buff = 0.8

        self.team_a_mid_draft_buff = 1.0
        if f'Mid команды {team_a} получил контрпик' in self.draft_results[self.team_a]:
            self.team_a_mid_draft_buff = 0.8

        self.team_a_offlane_draft_buff = 1.0
        if f'Offlane команды {team_a} получил контрпик' in self.draft_results[self.team_a]:
            self.team_a_offlane_draft_buff = 0.8

        self.team_a_partial_support_draft_buff = 1.0
        if f'Partial_support команды {team_a} получил контрпик' in self.draft_results[self.team_a]:
            self.team_a_partial_support_draft_buff = 0.8
        if f'Partial_support команды {team_a} получил сигнатурного героя' in self.draft_results[self.team_a]:
            self.team_a_partial_support_draft_buff = 1.2

        self.team_a_full_support_draft_buff = 1.0
        if f'Full_support команды {team_a} получил контрпик' in self.draft_results[self.team_a]:
            self.team_a_full_support_draft_buff = 0.8
        if f'Full_support команды {team_a} получил сигнатурного героя' in self.draft_results[self.team_a]:
            self.team_a_full_support_draft_buff = 1.2

        # Инициализация баффов для команды B
        self.team_b_carry_draft_buff = 1.0
        if f'Carry команды {team_b} получил контрпик' in self.draft_results[self.team_b]:
            self.team_b_carry_draft_buff = 0.8

        self.team_b_mid_draft_buff = 1.0
        if f'Mid команды {team_b} получил контрпик' in self.draft_results[self.team_b]:
            self.team_b_mid_draft_buff = 0.8

        self.team_b_offlane_draft_buff = 1.0
        if f'Offlane команды {team_b} получил контрпик' in self.draft_results[self.team_b]:
            self.team_b_offlane_draft_buff = 0.8

        self.team_b_partial_support_draft_buff = 1.0
        if f'Partial_support команды {team_b} получил контрпик' in self.draft_results[self.team_b]:
            self.team_b_partial_support_draft_buff = 0.8
        if f'Partial_support команды {team_b} получил сигнатурного героя' in self.draft_results[self.team_b]:
            self.team_b_partial_support_draft_buff = 1.2

        self.team_b_full_support_draft_buff = 1.0
        if f'Full_support команды {team_b} получил контрпик' in self.draft_results[self.team_b]:
            self.team_b_full_support_draft_buff = 0.8
        if f'Full_support команды {team_b} получил сигнатурного героя' in self.draft_results[self.team_b]:
            self.team_b_full_support_draft_buff = 1.2

    def early_game(self):
        self.team_draft_buff_a = 1.0
        self.team_draft_buff_b = 1.0

        if f'Драфт команды {self.team_a} хорош на стадии лайнинг' in self.draft_results[self.team_a]:
            self.team_draft_buff_a = 1.2
        if f'Драфт команды {self.team_b} хорош на стадии лайнинг' in self.draft_results[self.team_b]:
            self.team_draft_buff_b = 1.2

        team_a_tokens = 0
        team_b_tokens = 0

        # Линия бот
        for _ in range(3):  # 3 тика по 3 виртуальные минуты
            random_value_a = random.randint(0, 100) * self.team_draft_buff_a + \
                             (self.match_data[f"{self.team_a}_carry"]["micro_skills"] +
                              self.match_data[f"{self.team_a}_full_support"]["micro_skills"])
            random_value_b = random.randint(0, 100) * self.team_draft_buff_b + \
                             (self.match_data[f"{self.team_b}_offlane"]["micro_skills"] +
                              self.match_data[f"{self.team_b}_partial_support"]["micro_skills"])

            if random_value_a > random_value_b:
                team_a_tokens += 2  # Добавляем 2 токена за победу
            else:
                team_b_tokens += 2  # Добавляем 2 токена за победу

        # Линия топ
        for _ in range(3):  # 3 тика по 3 виртуальные минуты
            random_value_a = random.randint(0, 100) * self.team_draft_buff_a + \
                             (self.match_data[f"{self.team_a}_carry"]["micro_skills"] +
                              self.match_data[f"{self.team_a}_full_support"]["micro_skills"])
            random_value_b = random.randint(0, 100) * self.team_draft_buff_b + \
                             (self.match_data[f"{self.team_b}_offlane"]["micro_skills"] +
                              self.match_data[f"{self.team_b}_partial_support"]["micro_skills"])

            if random_value_a > random_value_b:
                team_a_tokens += 2
            else:
                team_b_tokens += 2

        # Линия мид
        for _ in range(2):  # 2 тика по 2 виртуальные минуты
            random_value_a = random.randint(0, 100) * self.team_draft_buff_a + \
                             self.match_data[f"{self.team_a}_mid"]["micro_skills"]
            random_value_b = random.randint(0, 100) * self.team_draft_buff_b + \
                             self.match_data[f"{self.team_b}_mid"]["micro_skills"]

            if random_value_a > random_value_b:
                team_a_tokens += 1
            else:
                team_b_tokens += 1

        return team_a_tokens, team_b_tokens


match = DotaMatch('Team Spirit', 'Team Falcons', "test_database.db")
tokens_a, tokens_b = match.early_game()
print(f"Tokens for Team A: {tokens_a}")
print(f"Tokens for Team B: {tokens_b}")



















