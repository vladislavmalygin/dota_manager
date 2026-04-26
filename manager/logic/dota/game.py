import random

from logic.dota.match_data import get_match_data

dispersion = 1000


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


def dota_simulation_logged(team1, team2, skills):
    """Returns (winner, log_lines, snapshots) for animated display during player matches."""
    tokens = {team1: 0, team2: 0}
    kills  = {team1: 0, team2: 0}
    lines  = []
    snaps  = []
    minute = 0
    synergy = 1

    def _snap(phase):
        return {
            'phase':     phase,
            'minute':    minute,
            'kills_t1':  kills[team1],
            'kills_t2':  kills[team2],
            'tokens_t1': tokens[team1],
            'tokens_t2': tokens[team2],
        }

    def _add(line, phase):
        lines.append(line)
        snaps.append(_snap(phase))

    _add('─' * 46,          'laning')
    _add('  ЛАЙНСТЕЙДЖ',    'laning')
    _add('─' * 46,          'laning')

    for tick in range(12):
        minute = tick
        if tick % 2 == 0:
            if (random.randint(0, dispersion) + skills['team1']['team1_mid']['micro_skills'] >
                    random.randint(0, dispersion) + skills['team2']['team2_mid']['micro_skills']):
                tokens[team1] += 1
                kills[team1] += random.randint(0, 1)
                _add(f"  Мид:  {team1}  захватывает преимущество  [{tokens[team1]}:{tokens[team2]}]", 'laning')
            else:
                tokens[team2] += 1
                kills[team2] += random.randint(0, 1)
                _add(f"  Мид:  {team2}  захватывает преимущество  [{tokens[team1]}:{tokens[team2]}]", 'laning')

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_offlane']['micro_skills'] * synergy +
                    skills['team1']['team1_partial_support']['micro_skills'] >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_carry']['micro_skills'] * synergy +
                    skills['team2']['team2_full_support']['micro_skills'] * synergy):
                tokens[team1] += 2
                kills[team1] += random.randint(1, 2)
                _add(f"  Топ:  {team1}  выигрывает лайн  [{tokens[team1]}:{tokens[team2]}]", 'laning')
            else:
                tokens[team2] += 2
                kills[team2] += random.randint(1, 2)
                _add(f"  Топ:  {team2}  выигрывает лайн  [{tokens[team1]}:{tokens[team2]}]", 'laning')

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_carry']['micro_skills'] * synergy +
                    skills['team1']['team1_full_support']['micro_skills'] * synergy >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_offlane']['micro_skills'] * synergy +
                    skills['team2']['team2_partial_support']['micro_skills'] * synergy):
                tokens[team1] += 2
                kills[team1] += random.randint(1, 2)
                _add(f"  Бот:  {team1}  выигрывает лайн  [{tokens[team1]}:{tokens[team2]}]", 'laning')
            else:
                tokens[team2] += 2
                kills[team2] += random.randint(1, 2)
                _add(f"  Бот:  {team2}  выигрывает лайн  [{tokens[team1]}:{tokens[team2]}]", 'laning')

    minute = 12
    _add(f"  Итог лайнстейджа:  {team1} {tokens[team1]}  —  {tokens[team2]} {team2}", 'laning')
    _add('─' * 46,                   'midgame')
    _add('  МИДГЕЙМ — КОМАНДНЫЕ БОИ','midgame')
    _add('─' * 46,                   'midgame')

    tick_params = [
        (['team1_mid', 'team1_partial_support', 'team1_full_support'],
         ['team2_mid', 'team2_partial_support', 'team2_full_support']),
        (['team1_mid', 'team1_partial_support', 'team1_offlane'],
         ['team2_mid', 'team2_partial_support', 'team2_offlane']),
        (['team1_mid', 'team1_carry', 'team1_offlane'],
         ['team2_mid', 'team2_carry', 'team2_offlane']),
    ]
    for i, (t1_roles, t2_roles) in enumerate(tick_params):
        minute = 15 + i * 5
        s1 = sum(skills['team1'][r][k] for r in t1_roles for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in t2_roles for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 4
            kills[team1] += random.randint(2, 4)
            _add(f"  Тимфайт:  {team1}  побеждает!  [{tokens[team1]}:{tokens[team2]}]", 'midgame')
        else:
            tokens[team2] += 4
            kills[team2] += random.randint(2, 4)
            _add(f"  Тимфайт:  {team2}  побеждает!  [{tokens[team1]}:{tokens[team2]}]", 'midgame')
        if abs(tokens[team1] - tokens[team2]) >= 24:
            winner = team1 if tokens[team1] > tokens[team2] else team2
            _add(f"  Ранняя победа: {winner}!", 'midgame')
            _add('─' * 46,               'midgame')
            _add(f"  ПОБЕДИТЕЛЬ: {winner}", 'midgame')
            return winner, lines, snaps

    _add('─' * 46,       'lategame')
    _add('  ЛЕЙТГЕЙМ',   'lategame')
    _add('─' * 46,       'lategame')

    late_events = [
        "забрала Рошана", "сломала бараки", "убила кора",
        "совершила смок-ганг", "уничтожила аутпост", "провела рош-ганг",
    ]
    minute = 30
    all_roles_t1 = [
        'team1_mid', 'team1_carry', 'team1_offlane',
        'team1_partial_support', 'team1_full_support',
    ]
    all_roles_t2 = [
        'team2_mid', 'team2_carry', 'team2_offlane',
        'team2_partial_support', 'team2_full_support',
    ]

    while abs(tokens[team1] - tokens[team2]) < 24:
        s1 = sum(skills['team1'][r][k] for r in all_roles_t1 for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in all_roles_t2 for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 8
            kills[team1] += random.randint(2, 5)
            _add(f"  {minute} мин:  {team1}  {random.choice(late_events)}  [{tokens[team1]}:{tokens[team2]}]", 'lategame')
        else:
            tokens[team2] += 8
            kills[team2] += random.randint(2, 5)
            _add(f"  {minute} мин:  {team2}  {random.choice(late_events)}  [{tokens[team1]}:{tokens[team2]}]", 'lategame')
        minute += 5

    winner = team1 if tokens[team1] > tokens[team2] else team2
    _add('─' * 46,                'lategame')
    _add(f"  ПОБЕДИТЕЛЬ: {winner}", 'lategame')
    return winner, lines, snaps


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
