import random


def draft(team_a_name, team_b_name):
    roles = ['carry', 'mid', 'offlane', 'partial_support', 'soft_support']
    buffs = {
        'favorite': 20,
        'inconvenient': -30,
        'staging': 20
    }
    stages = ['лайнинг', 'мидгейм', 'лейтгейм']

    results = []

    # Определяем, какой бафф получит команда A
    if random.random() < 0.5:  # 50% шанс получить бафф
        stage_buff = random.choice(stages)
        results.append(f"Драфт команды {team_a_name} хорош на стадии {stage_buff}")

    # Определяем, какой бафф получит команда B
    if random.random() < 0.5:  # 50% шанс получить бафф
        stage_buff = random.choice(stages)
        results.append(f"Драфт команды {team_b_name} хорош на стадии {stage_buff}")

    # Определяем баффы для игроков команды A
    for role in roles:
        if random.random() < 0.3:  # 30% шанс получить любимого героя
            results.append(f"{role.capitalize()} команды {team_a_name} получил сигнатурного героя")
        elif random.random() < 0.3:  # 30% шанс получить неудобного героя
            results.append(f"{role.capitalize()} команды {team_a_name} получил контрпик")

    # Определяем баффы для игроков команды B
    for role in roles:
        if random.random() < 0.3:  # 30% шанс получить любимого героя
            results.append(f"{role.capitalize()} команды {team_b_name} получил сигнатурного героя")
        elif random.random() < 0.3:  # 30% шанс получить неудобного героя
            results.append(f"{role.capitalize()} команды {team_b_name} получил контрпик")

    return results


# Пример использования функции
team_a = 'Team Spirit'
team_b = 'Team Falcons'
results = draft(team_a, team_b)

for result in results:
    print(result)
