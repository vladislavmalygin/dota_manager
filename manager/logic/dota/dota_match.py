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


        def early_game():
            self.team_draft_buff_a = 1.0
            self.team_draft_buff_b = 1.0
            if f'Драфт команды {team_a} хорош на стадии лайнинг' in self.draft_results[self.team_a]:
                self.team_draft_buff_a = 1.2
            if f'Драфт команды {team_b} хорош на стадии лайнинг' in self.draft_results[self.team_b]:
                self.team_draft_buff_b = 1.2





















