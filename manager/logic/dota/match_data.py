import sqlite3

def get_match_data(team1, team2, db_name):
    # Подключаемся к базе данных
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Получаем id игроков для первой команды
    cursor.execute("SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE name = ?", (team1,))
    team1_data = cursor.fetchone()

    if not team1_data:
        print(f"Команда {team1} не найдена.")
        conn.close()
        return

    # Получаем id игроков для второй команды
    cursor.execute("SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE name = ?", (team2,))
    team2_data = cursor.fetchone()

    if not team2_data:
        print(f"Команда {team2} не найдена.")
        conn.close()
        return

    # Получаем id игроков для каждой роли
    player_ids = {
        'team1_carry': team1_data[0],
        'team1_mid': team1_data[1],
        'team1_offlane': team1_data[2],
        'team1_partial_support': team1_data[3],
        'team1_full_support': team1_data[4],
        'team2_carry': team2_data[0],
        'team2_mid': team2_data[1],
        'team2_offlane': team2_data[2],
        'team2_partial_support': team2_data[3],
        'team2_full_support': team2_data[4],
    }

    # Словари для хранения навыков игроков
    skills = {
        'team1': {},
        'team2': {}
    }

    # Получаем значения полей micro_skills, macro_skills, soft_skills для каждого игрока
    for role, player_id in player_ids.items():
        cursor.execute("SELECT micro_skills, macro_skills, soft_skills FROM players WHERE id = ?", (player_id,))
        player_skills = cursor.fetchone()

        if player_skills:
            team_key = 'team1' if role.startswith('team1') else 'team2'
            skills[team_key][role] = {
                'micro_skills': player_skills[0],
                'macro_skills': player_skills[1],
                'soft_skills': player_skills[2]
            }
        else:
            print(f"Игрок с id {player_id} не найден.")

    # Закрываем соединение с базой данных
    conn.close()
    return skills





def get_teams_with_player_yes(db_name):
    # Подключаемся к базе данных
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Выполняем запрос для получения имен команд с player = 'yes'
    cursor.execute("SELECT name FROM teams WHERE player = 'yes'")
    teams = cursor.fetchall()

    # Закрываем соединение с базой данных
    conn.close()

    # Извлекаем имена команд из полученных данных
    team_names = [team[0].strip() for team in teams]  # Убираем лишние пробелы

    return team_names  # Возвращаем список команд\
