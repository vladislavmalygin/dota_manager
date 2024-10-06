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
        f'{team1}_carry': team1_ids[0],
        f'{team1}_mid': team1_ids[1],
        f'{team1}_offlane': team1_ids[2],
        f'{team1}_partial_support': team1_ids[3],
        f'{team1}_full_support': team1_ids[4],
        f'{team2}_carry': team2_ids[0],
        f'{team2}_mid': team2_ids[1],
        f'{team2}_offlane': team2_ids[2],
        f'{team2}_partial_support': team2_ids[3],
        f'{team2}_full_support': team2_ids[4],
    }

    # Словарь для хранения навыков игроков
    skills = {}

    # Получаем значения полей micro_skills, macro_skills, soft_skills для каждого игрока
    for role, player_id in player_ids.items():
        cursor.execute("SELECT micro_skills, macro_skills, soft_skills FROM players WHERE id = ?", (player_id,))
        player_skills = cursor.fetchone()

        if player_skills:
            skills[f'{role}'] = {
                'micro_skills': player_skills[0],
                'macro_skills': player_skills[1],
                'soft_skills': player_skills[2]
            }
        else:
            print(f"Игрок с id {player_id} не найден.")

    # Закрываем соединение с базой данных
    conn.close()

    return skills


# Пример использования
match_data = get_match_data('Team Spirit', 'Team Falcons', 'test_database.db')
print(match_data)



