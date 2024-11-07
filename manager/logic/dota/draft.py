import random


def draft_teams(team1, team2):
    # Генерация драфта
    heroes = ['Hero1', 'Hero2', 'Hero3', 'Hero4', 'Hero5', 'Hero6', 'Hero7', 'Hero8', 'Hero9', 'Hero10']

    # Случайный выбор героев для каждой роли
    team1_picks = random.sample(heroes, 5)
    team2_picks = random.sample(heroes, 5)

    print("Драфт завершен:")
    print(f"Команда {team1}: {team1_picks}")
    print(f"Команда {team2}: {team2_picks}")

    # Применение баффов
    buffs = apply_buffs(team1_picks, team2_picks)

    return team1_picks, team2_picks, buffs


def apply_buffs(team1_picks, team2_picks):
    buffs = {}

    # 20% шанс на +20% к микроскиллу
    for team in [team1_picks, team2_picks]:
        for hero in team:
            if random.random() < 0.2:  # 20% шанс
                buffs[hero] = {'micro_skill_buff': 0.2}
                print(f"{hero} получил +20% к микроскиллу!")
            else:
                buffs[hero] = {'micro_skill_buff': 0}

    # 10% шанс на +10% к микроскиллу всей команде
    if random.random() < 0.1:  # 10% шанс
        for hero in team1_picks:
            buffs[hero]['micro_skill_buff'] += 0.1
        print(f"{team1_picks} получили +10% к микроскиллу всей команды на ранней стадии!")

    if random.random() < 0.1:  # 10% шанс
        for hero in team2_picks:
            buffs[hero]['micro_skill_buff'] += 0.1
        print(f"{team2_picks} получили +10% к микроскиллу всей команды на ранней стадии!")

    return buffs
