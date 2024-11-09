import time
import random

# Импортируйте вашу функцию получения данных о матчах из нужного модуля
from manager.logic.dota.match_data import get_match_data

def dota_simulation(team1, team2, db_name):
    # Получаем данные о командах
    skills = get_match_data(team1, team2, db_name)

    # Инициализация токенов
    tokens = {team1: 0, team2: 0}
    synergy = 1  # Сыгранность (пока равна 1)

    # Симуляция ранней игры
    for tick in range(12):
        print(f"Минута {tick + 1}")
        time.sleep(5)  # Интервал в 5 секунд
        mid_roll = random.randint(0, 20)
        top_roll = random.randint(0, 20)
        bot_roll = random.randint(0, 20)

        # Мид линия (тик равен 2 минутам)
        if tick % 2 == 0:
            if mid_roll + skills['team1_mid_macro_skills'] * synergy > (random.randint(0, 20) + skills['team2_mid_macro_skills'] * synergy):
                tokens[team1] += 1
                print(f"{team1} получает преимущество на миду! Счёт: {tokens[team1]} - {tokens[team2]}")
            else:
                tokens[team2] += 1
                print(f"{team2} получает преимущество на миду! Счёт: {tokens[team1]} - {tokens[team2]}")

        # Топ линия (тик равен 3 минутам)
        if tick % 3 == 0:
            if top_roll + skills['team1_offlane_macro_skills'] * synergy > (random.randint(0, 20) + skills['team2_carry_macro_skills'] * synergy + skills['team2_full_support_macro_skills'] * synergy):
                tokens[team1] += 2
                print(f"{team1} получает преимущество на топе! Счёт: {tokens[team1]} - {tokens[team2]}")
            else:
                tokens[team2] += 2
                print(f"{team2} получает преимущество на топе! Счёт: {tokens[team1]} - {tokens[team2]}")

        # Бот линия (тик равен 3 минутам)
        if tick % 3 == 0:
            if bot_roll + skills['team2_carry_macro_skills'] * synergy + skills['team2_full_support_macro_skills'] * synergy > (random.randint(0, 100) + skills['team1_carry_macro_skills'] * synergy + skills['team1_full_support_macro_skills'] * synergy):
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
        time.sleep(10)  # Интервал в 10 секунд

        # Определяем roll в зависимости от тика
        if tick == 0:
            roll = (random.randint(0, 20) +
                    (skills.get('team1_mid_macro_skills', 0) + skills.get('team2_mid_macro_skills', 0)) * 0.8 +
                    (skills.get('team1_soft_skills', 0) + skills.get('team2_soft_skills', 0)) * 0.5)
        elif tick == 1:
            roll = (random.randint(0, 20) +
                    (skills.get('team1_offlane_macro_skills', 0) + skills.get('team2_offlane_macro_skills', 0)) * 0.8 +
                    (skills.get('team1_soft_skills', 0) + skills.get('team2_soft_skills', 0)) * 0.5)
        else:  # tick == 2
            roll = (random.randint(0, 20) +
                    (skills.get('team1_carry_macro_skills', 0) + skills.get('team2_carry_macro_skills', 0)) * 0.8 +
                    (skills.get('team1_soft_skills', 0) + skills.get('team2_soft_skills', 0)) * 0.5)

        # Определяем победителя в текущем тике
        if roll > random.randint(0, 20):
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
        roll_team1 = random.randint(0, 20) + (
                    skills.get('team1_macro_skills', 0) * 1 + skills.get('team1_micro_skills', 0) * 0.5 + skills.get(
                'team1_soft_skills', 0) * 0.8)
        roll_team2 = random.randint(0, 20) + (
                    skills.get('team2_macro_skills', 0) * 1 + skills.get('team2_micro_skills', 0) * 0.5 + skills.get(
                'team2_soft_skills', 0) * 0.8)

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

if __name__ == "__main__":
    team1 = "Team Spirit"
    team2 = "Team Falcons"
    db_name = "test_database.db"

    # Проведение симуляции
    dota_simulation(team1, team2, db_name)