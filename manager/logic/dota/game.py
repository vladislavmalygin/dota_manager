import time
import random

# Импортируйте вашу функцию получения данных о матчах из нужного модуля
from match_data import get_match_data

def simulate_early_game(team1, team2, db_name):
    # Получаем данные о командах
    skills = get_match_data(team1, team2, db_name)

    # Инициализация токенов
    tokens = {team1: 0, team2: 0}
    synergy = 1  # Сыгранность (пока равна 1)

    # Симуляция ранней игры
    for tick in range(12):
        print(f"Минута {tick + 1}")
        time.sleep(5)  # Интервал в 5 секунд

        # Генерация случайных значений для каждой линии
        mid_roll = random.randint(0, 100)
        top_roll = random.randint(0, 100)
        bot_roll = random.randint(0, 100)

        # Мид линия (тик равен 2 минутам)
        if tick % 2 == 0:
            if mid_roll + skills['team1_mid_macro_skills'] * synergy > (random.randint(0, 100) + skills['team2_mid_macro_skills'] * synergy):
                tokens[team1] += 1
                print(f"{team1} получает преимущество на миду! Счёт: {tokens[team1]} - {tokens[team2]}")
            else:
                tokens[team2] += 1
                print(f"{team2} получает преимущество на миду! Счёт: {tokens[team1]} - {tokens[team2]}")

        # Топ линия (тик равен 3 минутам)
        if tick % 3 == 0:
            if top_roll + skills['team1_offlane_macro_skills'] * synergy > (random.randint(0, 100) + skills['team2_carry_macro_skills'] * synergy + skills['team2_full_support_macro_skills'] * synergy):
                tokens[team1] += 1
                print(f"{team1} получает преимущество на топе! Счёт: {tokens[team1]} - {tokens[team2]}")
            else:
                tokens[team2] += 1
                print(f"{team2} получает преимущество на топе! Счёт: {tokens[team1]} - {tokens[team2]}")

        # Бот линия (тик равен 3 минутам)
        if tick % 3 == 0:
            if bot_roll + skills['team2_carry_macro_skills'] * synergy + skills['team2_full_support_macro_skills'] * synergy > (random.randint(0, 100) + skills['team1_carry_macro_skills'] * synergy + skills['team1_full_support_macro_skills'] * synergy):
                tokens[team2] += 1
                print(f"{team2} получает преимущество на боте! Счёт: {tokens[team1]} - {tokens[team2]}")
            else:
                tokens[team1] += 1
                print(f"{team1} получает преимущество на боте! Счёт: {tokens[team1]} - {tokens[team2]}")

    print("Результаты ранней игры:")
    print(f"Токены команды {team1}: {tokens[team1]}")
    print(f"Токены команды {team2}: {tokens[team2]}")

    return tokens, skills

def simulate_mid_game(tokens, skills):
    mid_game_ticks = 3
    team1, team2 = list(tokens.keys())

    for tick in range(mid_game_ticks):
        print(f"Мидгейм начался")
        time.sleep(10)  # Интервал в 10 секунд

        # Определяем roll в зависимости от тика
        if tick == 0:
            roll = (random.randint(0, 100) +
                    (skills.get('team1_mid_macro_skills', 0) + skills.get('team2_mid_macro_skills', 0)) * 0.8 +
                    (skills.get('team1_soft_skills', 0) + skills.get('team2_soft_skills', 0)) * 0.5)
        elif tick == 1:
            roll = (random.randint(0, 100) +
                    (skills.get('team1_offlane_macro_skills', 0) + skills.get('team2_offlane_macro_skills', 0)) * 0.8 +
                    (skills.get('team1_soft_skills', 0) + skills.get('team2_soft_skills', 0)) * 0.5)
        else:  # tick == 2
            roll = (random.randint(0, 100) +
                    (skills.get('team1_carry_macro_skills', 0) + skills.get('team2_carry_macro_skills', 0)) * 0.8 +
                    (skills.get('team1_soft_skills', 0) + skills.get('team2_soft_skills', 0)) * 0.5)

        # Определяем победителя в текущем тике
        if roll > random.randint(0, 100):
            tokens[team1] += 4
            print(f"{team1} выигрывает тимфайт! Счёт: {tokens[team1]} - {tokens[team2]}")
        else:
            tokens[team2] += 4
            print(f"{team2} выигрывает тимфайт! Счёт: {tokens[team1]} - {tokens[team2]}")

        # Проверяем условие окончания игры
        if abs(tokens[team1] - tokens[team2]) >= 18:
            winner = team1 if tokens[team1] > tokens[team2] else team2
            print(f"Игра закончена! Победила команда: {winner} со счётом {tokens[winner]}.")
            return

    print("Результаты мидгейма:")
    print(f"Токены команды {team1}: {tokens[team1]}")
    print(f"Токены команды {team2}: {tokens[team2]}")

if __name__ == "__main__":
    team1 = "Team Spirit"
    team2 = "Team Falcons"
    db_name = "test_database.db"

    # Проведение драфта и симуляция ранней игры
    tokens, skills = simulate_early_game(team1, team2, db_name)

    # Симуляция мидгейма
    simulate_mid_game(tokens, skills)
