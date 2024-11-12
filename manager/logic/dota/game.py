import time
import random

from manager.logic.dota.match_data import get_match_data


dispersion = 200

def dota_simulation(team1, team2, skills):
    # Получаем данные о командах

    # Инициализация токенов
    tokens = {team1: 0, team2: 0}
    synergy = 1  # Сыгранность (пока равна 1)

    # Симуляция ранней игры
    for tick in range(12):
        print(f"Минута {tick + 1}")
        time.sleep(5)  # Интервал в 5 секунд
        mid_roll = random.randint(0, dispersion)
        top_roll = random.randint(0, dispersion)
        bot_roll = random.randint(0, dispersion)

        # Мид линия (тик равен 2 минутам)
        for tick in range(12):
            # Мид линия (тик равен 2 минутам)
            if tick % 2 == 0:
                if mid_roll + skills['team1']['mid']['micro_skills'] > (
                        random.randint(0, dispersion) + skills['team2']['mid']['micro_skills']):
                    tokens[team1] += 1
                    print(f"{team1} получает преимущество на миду! Счёт: {tokens[team1]} - {tokens[team2]}")
                else:
                    tokens[team2] += 1
                    print(f"{team2} получает преимущество на миду! Счёт: {tokens[team1]} - {tokens[team2]}")

            # Топ линия (тик равен 3 минутам)
            if tick % 3 == 0:
                if top_roll + skills['team1']['offlane']['micro_skills'] * synergy + skills['team1']['partial_support'][
                    'micro_skills'] > (
                        random.randint(0, dispersion) + skills['team2']['carry']['micro_skills'] * synergy +
                        skills['team2']['full_support']['micro_skills'] * synergy):
                    tokens[team1] += 2
                    print(f"{team1} получает преимущество на топе! Счёт: {tokens[team1]} - {tokens[team2]}")
                else:
                    tokens[team2] += 2
                    print(f"{team2} получает преимущество на топе! Счёт: {tokens[team1]} - {tokens[team2]}")

            # Бот линия (тик равен 3 минутам)
            if tick % 3 == 0:
                if bot_roll + skills['team2']['carry']['micro_skills'] * synergy + skills['team2']['full_support'][
                    'micro_skills'] * synergy > (
                        random.randint(0, dispersion) + skills['team2']['offlane']['micro_skills'] * synergy +
                        skills['team2']['partial_support']['micro_skills'] * synergy):
                    tokens[team2] += 2
                    print(f"{team2} получает преимущество на боте! Счёт: {tokens[team1]} - {tokens[team2]}")
                else:
                    tokens[team1] += 2
                    print(f"{team1} получает преимущество на боте! Счёт: {tokens[team1]} - {tokens[team2]}")

    print("Результаты ранней игры:")
    print(f"Токены команды {team1}: {tokens[team1]}")
    print(f"Токены команды {team2}: {tokens[team2]}")

    print("Мидгейм начался")
    # Симуляция мидгейма
    mid_game_ticks = 3
    for tick in range(mid_game_ticks):

        # Определяем roll в зависимости от тика
        if tick == 0:
            roll_team1 = (random.randint(0, dispersion) +
                          skills['team1']['mid']['macro_skills'] +
                          skills['team1']['mid']['micro_skills'] +
                          skills['team1']['partial_support']['macro_skills'] +
                          skills['team1']['partial_support']['micro_skills'] +
                          skills['team1']['full_support']['macro_skills'] +
                          skills['team1']['full_support']['micro_skills'])

            roll_team2 = (random.randint(0, dispersion) +
                          skills['team2']['mid']['macro_skills'] +
                          skills['team2']['mid']['micro_skills'] +
                          skills['team2']['partial_support']['macro_skills'] +
                          skills['team2']['partial_support']['micro_skills'] +
                          skills['team2']['full_support']['macro_skills'] +
                          skills['team2']['full_support']['micro_skills'])

        elif tick == 1:
            roll_team1 = (random.randint(0, dispersion) +
                          skills['team1']['mid']['macro_skills'] +
                          skills['team1']['mid']['micro_skills'] +
                          skills['team1']['partial_support']['macro_skills'] +
                          skills['team1']['partial_support']['micro_skills'] +
                          skills['team1']['offlane']['macro_skills'] +
                          skills['team1']['offlane']['micro_skills'])

            roll_team2 = (random.randint(0, dispersion) +
                          skills['team2']['mid']['macro_skills'] +
                          skills['team2']['mid']['micro_skills'] +
                          skills['team2']['partial_support']['macro_skills'] +
                          skills['team2']['partial_support']['micro_skills'] +
                          skills['team2']['offlane']['macro_skills'] +
                          skills['team2']['offlane']['micro_skills'])

        else:  # tick == 2
            roll_team1 = (random.randint(0, dispersion) +
                          skills['team1']['mid']['macro_skills'] +
                          skills['team1']['mid']['micro_skills'] +
                          skills['team1']['carry']['macro_skills'] +
                          skills['team1']['carry']['micro_skills'] +
                          skills['team1']['offlane']['macro_skills'] +
                          skills['team1']['offlane']['micro_skills'])

            roll_team2 = (random.randint(0, dispersion) +
                          skills['team2']['mid']['macro_skills'] +
                          skills['team2']['mid']['micro_skills'] +
                          skills['team2']['carry']['macro_skills'] +
                          skills['team2']['carry']['micro_skills'] +
                          skills['team2']['offlane']['macro_skills'] +
                          skills['team2']['offlane']['micro_skills'])

        # Определяем победителя в текущем тике
        if roll_team1 > roll_team2:
            tokens[team1] += 4
            print(f"{team1} выигрывает тимфайт! Счёт: {tokens[team1]} - {tokens[team2]}")
        else:
            tokens[team2] += 4
            print(f"{team2} выигрывает тимфайт! Счёт: {tokens[team1]} - {tokens[team2]}")

        # Проверяем условие окончания игры
        if abs(tokens[team1] - tokens[team2]) >= 18:
            winner = team1 if tokens[team1] > tokens[team2] else team2
            print(f"Игра закончена! Победила команда: {winner} со счётом {tokens[winner]}.")
            return winner

    print("Результаты мидгейма:")
    print(f"Токены команды {team1}: {tokens[team1]}")
    print(f"Токены команды {team2}: {tokens[team2]}")

    print("30-я минута, игра переходит в стадию лейтгейма.")

    ley_game_time = 30  # Начальная минута лейтгейма
    events = [
        f"забрала Рошана.",
        f"сломала бараки.",
        f"убила кора противника без байбека.",
        f"совершила отличное командное действие.",
        f"реализует смок-ганг трон.",
        f"убивает героев противника."
    ]

    # Создаем отдельные списки событий для каждой команды
    team1_events = [f"{team1} {event}" for event in events]
    team2_events = [f"{team2} {event}" for event in events]

    while abs(tokens[team1] - tokens[team2]) < 24:
        print(f"{ley_game_time}-я минута.")  # Вывод текущей минуты
        time.sleep(5)  # Интервал в 5 секунд

        # Генерация бросков для обеих команд
        roll_team1 = (
                random.randint(0, dispersion) +
                skills['team1']['team1_mid']['macro_skills'] +
                skills['team1']['team1_mid']['micro_skills'] +
                skills['team1']['team1_carry']['macro_skills'] +
                skills['team1']['team1_carry']['micro_skills'] +
                skills['team1']['team1_offlane']['micro_skills'] +
                skills['team1']['team1_offlane']['macro_skills'] +
                skills['team1']['team1_partial_support']['micro_skills'] +
                skills['team1']['team1_partial_support']['macro_skills'] +
                skills['team1']['team1_full_support']['micro_skills'] +
                skills['team1']['team1_full_support']['macro_skills']
        )

        roll_team2 = (
                random.randint(0, dispersion) +
                skills['team2']['team2_mid']['macro_skills'] +
                skills['team2']['team2_mid']['micro_skills'] +
                skills['team2']['team2_carry']['macro_skills'] +
                skills['team2']['team2_carry']['micro_skills'] +
                skills['team2']['team2_offlane']['micro_skills'] +
                skills['team2']['team2_offlane']['macro_skills'] +
                skills['team2']['team2_partial_support']['micro_skills'] +
                skills['team2']['team2_partial_support']['macro_skills'] +
                skills['team2']['team2_full_support']['micro_skills'] +
                skills['team2']['team2_full_support']['macro_skills']
        )

        # Определяем победителя в текущем тике
        if roll_team1 > roll_team2:
            tokens[team1] += 8
            event_message = random.choice(team1_events)
            print(f"{team1} выиграла тик! {event_message}")
            print(f"Счёт: {tokens[team1]} - {tokens[team2]}")
        else:
            tokens[team2] += 8
            event_message = random.choice(team2_events)
            print(f"{team2} выиграла тик! {event_message}")
            print(f"Счёт: {tokens[team1]} - {tokens[team2]}")

        ley_game_time += 5  # Увеличиваем минуту на 5

    # Определяем победителя
    winner = team1 if tokens[team1] > tokens[team2] else team2
    print(f"Игра закончена! Победила команда: {winner} со счётом {tokens[winner]}.")
    return winner



def dota_simulation_for_bots(team1, team2, skills):

    # Инициализация токенов
    tokens = {team1: 0, team2: 0}
    synergy = 1  # Сыгранность (пока равна 1)

    # Симуляция ранней игры
    for tick in range(12):
        # Мид линия (тик равен 2 минутам)
        if tick % 2 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_mid']['micro_skills'] >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_mid']['micro_skills']):
                tokens[team1] += 1
            else:
                tokens[team2] += 1

        # Топ линия (тик равен 3 минутам)
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

        # Бот линия (тик равен 3 минутам)
        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_carry']['micro_skills'] * synergy +
                    skills['team1']['team1_full_support']['micro_skills'] * synergy >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_offlane']['micro_skills'] * synergy +
                    skills['team2']['team2_partial_support']['micro_skills'] * synergy):
                tokens[team2] += 2
            else:
                tokens[team1] += 2

    mid_game_ticks = 3

    for tick in range(mid_game_ticks):
        # Определяем параметры для команды в зависимости от тика
        if tick == 0:
            skills_team1 = [
                skills['team1']['team1_mid']['macro_skills'],
                skills['team1']['team1_mid']['micro_skills'],
                skills['team1']['team1_partial_support']['micro_skills'],
                skills['team1']['team1_partial_support']['macro_skills'],
                skills['team1']['team1_full_support']['micro_skills'],
                skills['team1']['team1_full_support']['macro_skills']
            ]
            skills_team2 = [
                skills['team2']['team2_mid']['macro_skills'],
                skills['team2']['team2_mid']['micro_skills'],
                skills['team2']['team2_partial_support']['micro_skills'],
                skills['team2']['team2_partial_support']['macro_skills'],
                skills['team2']['team2_full_support']['micro_skills'],
                skills['team2']['team2_full_support']['macro_skills']
            ]
        elif tick == 1:
            skills_team1 = [
                skills['team1']['team1_mid']['macro_skills'],
                skills['team1']['team1_mid']['micro_skills'],
                skills['team1']['team1_partial_support']['micro_skills'],
                skills['team1']['team1_partial_support']['macro_skills'],
                skills['team1']['team1_offlane']['micro_skills'],
                skills['team1']['team1_offlane']['macro_skills']
            ]
            skills_team2 = [
                skills['team2']['team2_mid']['macro_skills'],
                skills['team2']['team2_mid']['micro_skills'],
                skills['team2']['team2_partial_support']['micro_skills'],
                skills['team2']['team2_partial_support']['macro_skills'],
                skills['team2']['team2_offlane']['micro_skills'],
                skills['team2']['team2_offlane']['macro_skills']
            ]
        else:  # tick == 2
            skills_team1 = [
                skills['team1']['team1_mid']['macro_skills'],
                skills['team1']['team1_mid']['micro_skills'],
                skills['team1']['team1_carry']['micro_skills'],
                skills['team1']['team1_carry']['macro_skills'],
                skills['team1']['team1_offlane']['micro_skills'],
                skills['team1']['team1_offlane']['macro_skills']
            ]
            skills_team2 = [
                skills['team2']['team2_mid']['macro_skills'],
                skills['team2']['team2_mid']['micro_skills'],
                skills['team2']['team2_carry']['micro_skills'],
                skills['team2']['team2_carry']['macro_skills'],
                skills['team2']['team2_offlane']['micro_skills'],
                skills['team2']['team2_offlane']['macro_skills']
            ]

        roll_team1 = random.randint(0, dispersion) + sum(skills_team1)
        roll_team2 = random.randint(0, dispersion) + sum(skills_team2)

        # Определяем победителя в текущем тике
        if roll_team1 > roll_team2:
            tokens[team1] += 4
        else:
            tokens[team2] += 4
        # Проверяем условие окончания игры
        if abs(tokens[team1] - tokens[team2]) >= 24:
            winner = team1 if tokens[team1] > tokens[team2] else team2
            print(f"Игра закончена! Победила команда: {winner} со счётом {tokens[winner]}.")
            return winner

    while abs(tokens[team1] - tokens[team2])  < 24:

        # Генерация бросков для обеих команд
        roll_team1 = (
                random.randint(0, dispersion) +
                skills['team1']['team1_mid']['macro_skills'] +
                skills['team1']['team1_mid']['micro_skills'] +
                skills['team1']['team1_carry']['macro_skills'] +
                skills['team1']['team1_carry']['micro_skills'] +
                skills['team1']['team1_offlane']['micro_skills'] +
                skills['team1']['team1_offlane']['macro_skills'] +
                skills['team1']['team1_partial_support']['micro_skills'] +
                skills['team1']['team1_partial_support']['macro_skills'] +
                skills['team1']['team1_full_support']['micro_skills'] +
                skills['team1']['team1_full_support']['macro_skills']
        )

        roll_team2 = (
                random.randint(0, dispersion) +
                skills['team2']['team2_mid']['macro_skills'] +
                skills['team2']['team2_mid']['micro_skills'] +
                skills['team2']['team2_carry']['macro_skills'] +
                skills['team2']['team2_carry']['micro_skills'] +
                skills['team2']['team2_offlane']['micro_skills'] +
                skills['team2']['team2_offlane']['macro_skills'] +
                skills['team2']['team2_partial_support']['micro_skills'] +
                skills['team2']['team2_partial_support']['macro_skills'] +
                skills['team2']['team2_full_support']['micro_skills'] +
                skills['team2']['team2_full_support']['macro_skills']
        )

        # Определяем победителя в текущем тике
        if roll_team1 > roll_team2:
            tokens[team1] += 8
        else:
            tokens[team2] += 8

    # Определяем победителя
    winner = team1 if tokens[team1] > tokens[team2] else team2
    print(f"Игра закончена! Победила команда: {winner} со счётом {tokens[winner]}.")
    return winner

team2 = 'Aurora'
team1 = 'Team Spirit'
db_name = 'test_database.db'
skills = get_match_data(team1, team2,  db_name)
dota_simulation_for_bots(team1, team2 , skills)
