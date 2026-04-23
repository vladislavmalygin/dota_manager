import random

from logic.dota.match_data import get_match_data

dispersion = 200


def _early_game(team1, team2, skills, tokens):
    synergy = 1
    for tick in range(12):
        if tick % 2 == 0:
            if (random.randint(0, dispersion) + skills['team1']['team1_mid']['micro_skills'] >
                    random.randint(0, dispersion) + skills['team2']['team2_mid']['micro_skills']):
                tokens[team1] += 1
            else:
                tokens[team2] += 1

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_offlane']['micro_skills'] * synergy +
                    skills['team1']['team1_partial_support']['micro_skills'] >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_carry']['micro_skills'] * synergy +
                    skills['team2']['team2_full_support']['micro_skills'] * synergy):
                tokens[team1] += 2
            else:
                tokens[team2] += 2

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_carry']['micro_skills'] * synergy +
                    skills['team1']['team1_full_support']['micro_skills'] * synergy >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_offlane']['micro_skills'] * synergy +
                    skills['team2']['team2_partial_support']['micro_skills'] * synergy):
                tokens[team1] += 2
            else:
                tokens[team2] += 2


def _mid_game(team1, team2, skills, tokens):
    tick_params = [
        (['team1_mid', 'team1_partial_support', 'team1_full_support'],
         ['team2_mid', 'team2_partial_support', 'team2_full_support']),
        (['team1_mid', 'team1_partial_support', 'team1_offlane'],
         ['team2_mid', 'team2_partial_support', 'team2_offlane']),
        (['team1_mid', 'team1_carry', 'team1_offlane'],
         ['team2_mid', 'team2_carry', 'team2_offlane']),
    ]
    for t1_roles, t2_roles in tick_params:
        s1 = sum(skills['team1'][r][k] for r in t1_roles for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in t2_roles for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 4
        else:
            tokens[team2] += 4
        if abs(tokens[team1] - tokens[team2]) >= 24:
            return


def _late_game(team1, team2, skills, tokens):
    all_roles_t1 = ['team1_mid', 'team1_carry', 'team1_offlane', 'team1_partial_support', 'team1_full_support']
    all_roles_t2 = ['team2_mid', 'team2_carry', 'team2_offlane', 'team2_partial_support', 'team2_full_support']

    while abs(tokens[team1] - tokens[team2]) < 24:
        s1 = sum(skills['team1'][r][k] for r in all_roles_t1 for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in all_roles_t2 for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 8
        else:
            tokens[team2] += 8


def dota_simulation_for_bots(team1, team2, skills):
    tokens = {team1: 0, team2: 0}
    _early_game(team1, team2, skills, tokens)
    _mid_game(team1, team2, skills, tokens)
    _late_game(team1, team2, skills, tokens)
    return team1 if tokens[team1] > tokens[team2] else team2


def dota_simulation(team1, team2, skills):
    """Версия с выводом для матчей игрока (без задержек)."""
    tokens = {team1: 0, team2: 0}
    synergy = 1

    print(f"\n=== МАТЧ: {team1} vs {team2} ===")

    for tick in range(12):
        if tick % 2 == 0:
            if (random.randint(0, dispersion) + skills['team1']['team1_mid']['micro_skills'] >
                    random.randint(0, dispersion) + skills['team2']['team2_mid']['micro_skills']):
                tokens[team1] += 1
                print(f"  Мид: {team1} получает преимущество [{tokens[team1]}:{tokens[team2]}]")
            else:
                tokens[team2] += 1
                print(f"  Мид: {team2} получает преимущество [{tokens[team1]}:{tokens[team2]}]")

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_offlane']['micro_skills'] * synergy +
                    skills['team1']['team1_partial_support']['micro_skills'] >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_carry']['micro_skills'] * synergy +
                    skills['team2']['team2_full_support']['micro_skills'] * synergy):
                tokens[team1] += 2
                print(f"  Топ: {team1} выигрывает лайн [{tokens[team1]}:{tokens[team2]}]")
            else:
                tokens[team2] += 2
                print(f"  Топ: {team2} выигрывает лайн [{tokens[team1]}:{tokens[team2]}]")

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_carry']['micro_skills'] * synergy +
                    skills['team1']['team1_full_support']['micro_skills'] * synergy >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_offlane']['micro_skills'] * synergy +
                    skills['team2']['team2_partial_support']['micro_skills'] * synergy):
                tokens[team1] += 2
                print(f"  Бот: {team1} выигрывает лайн [{tokens[team1]}:{tokens[team2]}]")
            else:
                tokens[team2] += 2
                print(f"  Бот: {team2} выигрывает лайн [{tokens[team1]}:{tokens[team2]}]")

    print(f"После лайнстейджа: {team1}={tokens[team1]}, {team2}={tokens[team2]}")

    tick_params = [
        (['team1_mid', 'team1_partial_support', 'team1_full_support'],
         ['team2_mid', 'team2_partial_support', 'team2_full_support']),
        (['team1_mid', 'team1_partial_support', 'team1_offlane'],
         ['team2_mid', 'team2_partial_support', 'team2_offlane']),
        (['team1_mid', 'team1_carry', 'team1_offlane'],
         ['team2_mid', 'team2_carry', 'team2_offlane']),
    ]
    for t1_roles, t2_roles in tick_params:
        s1 = sum(skills['team1'][r][k] for r in t1_roles for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in t2_roles for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 4
            print(f"  Тимфайт: {team1} выигрывает [{tokens[team1]}:{tokens[team2]}]")
        else:
            tokens[team2] += 4
            print(f"  Тимфайт: {team2} выигрывает [{tokens[team1]}:{tokens[team2]}]")
        if abs(tokens[team1] - tokens[team2]) >= 24:
            winner = team1 if tokens[team1] > tokens[team2] else team2
            print(f"  Ранняя победа: {winner}!")
            return winner

    all_roles_t1 = ['team1_mid', 'team1_carry', 'team1_offlane', 'team1_partial_support', 'team1_full_support']
    all_roles_t2 = ['team2_mid', 'team2_carry', 'team2_offlane', 'team2_partial_support', 'team2_full_support']
    events = ["забрала Рошана", "сломала бараки", "убила кора", "совершила смок-ганг"]
    minute = 30

    while abs(tokens[team1] - tokens[team2]) < 24:
        s1 = sum(skills['team1'][r][k] for r in all_roles_t1 for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in all_roles_t2 for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 8
            print(f"  {minute}мин: {team1} {random.choice(events)} [{tokens[team1]}:{tokens[team2]}]")
        else:
            tokens[team2] += 8
            print(f"  {minute}мин: {team2} {random.choice(events)} [{tokens[team1]}:{tokens[team2]}]")
        minute += 5

    winner = team1 if tokens[team1] > tokens[team2] else team2
    print(f"=== Победитель: {winner} ===\n")
    return winner
