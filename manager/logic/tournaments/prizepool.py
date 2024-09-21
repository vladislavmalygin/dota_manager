import sqlite3


def get_prizepool_worldcup_system(tournament_id):
    # Подключаемся к базе данных
    conn = sqlite3.connect('test_database.db')
    cursor = conn.cursor()

    # Получаем значение prizepool для указанного турнира
    cursor.execute("SELECT prizepool FROM tournaments WHERE id = ?", (tournament_id,))
    result = cursor.fetchone()

    # Закрываем соединение
    conn.close()

    if result is None:
        print("Турнир с таким ID не найден.")
        return None

    prizepool = result[0]

    # Распределяем призовой фонд
    distribution = {
        "1 место": prizepool * 0.40,
        "2 место": prizepool * 0.25,
        "3 место": prizepool * 0.075,
        "4 место": prizepool * 0.075,
        "5 место": prizepool * 0.025,
        "6 место": prizepool * 0.025,
        "7 место": prizepool * 0.025,
        "8 место": prizepool * 0.025,
        "9 место": prizepool * 0.00625,
        "10 место": prizepool * 0.00625,
        "11 место": prizepool * 0.00625,
        "12 место": prizepool * 0.00625,
        "13 место": prizepool * 0.00625,
        "14 место": prizepool * 0.00625,
        "15 место": prizepool * 0.00625,
        "16 место": prizepool * 0.00625,
    }

    return distribution



tournament_id = 1
prize_distribution = get_prizepool_worldcup_system(tournament_id)

if prize_distribution:
    for place, amount in prize_distribution.items():
        print(f"{place}: {amount:.2f}")
