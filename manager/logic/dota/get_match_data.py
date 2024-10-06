import sqlite3

def get_match_data(team1, team2, db_name):
    # Подключаемся к базе данных
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Находим id команд
    cursor.execute("SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE name IN (?, ?)",
                   (team1, team2))
    team_data = cursor.fetchall()

    if len(team_data) != 2:
        print("Одна или обе команды не найдены.")
        conn.close()
        return

    # Извлекаем id игроков для каждой роли
    team1_ids = team_data[0]
    team2_ids = team_data[1]

    # Получаем id игроков
    player_ids = {
        'team1_carry': team1_ids[0],
        'team1_mid': team1_ids[1],
        'team1_offlane': team1_ids[2],
        'team1_partial_support': team1_ids[3],
        'team1_full_support': team1_ids[4],
        'team2_carry': team2_ids[0],
        'team2_mid': team2_ids[1],
        'team2_offlane': team2_ids[2],
        'team2_partial_support': team2_ids[3],
        'team2_full_support': team2_ids[4],
    }

    # Словарь для хранения навыков игроков
    skills = {}

    # Получаем значения полей micro_skills, macro_skills, soft_skills для каждого игрока
    for role, player_id in player_ids.items():
        cursor.execute("SELECT micro_skills, macro_skills, soft_skills FROM players WHERE id = ?", (player_id,))
        player_skills = cursor.fetchone()

        if player_skills:
            skills[f'{role}_micro_skills'] = player_skills[0]
            skills[f'{role}_macro_skills'] = player_skills[1]
            skills[f'{role}_soft_skills'] = player_skills[2]
        else:
            print(f"Игрок с id {player_id} не найден.")

    # Закрываем соединение с базой данных
    conn.close()

    return skills


# Пример использования
match_data = get_match_data('Team Spirit', 'Team Falcons', 'test_database.db')
print(match_data)


