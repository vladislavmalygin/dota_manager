import sqlite3

def invites(db_name):
    # Подключаемся к базе данных
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Сначала пробуем получить топ 16 команд по ненулевому рейтингу
    cursor.execute("SELECT name FROM teams WHERE rating IS NOT NULL ORDER BY rating DESC LIMIT 16;")
    top_teams = cursor.fetchall()

    # Если нет команд с ненулевым рейтингом или все рейтинги равны, выбираем по id
    if len(top_teams) < 16:
        cursor.execute("SELECT name FROM teams ORDER BY id ASC LIMIT 16;")
        top_teams = cursor.fetchall()

    # Закрываем соединение
    conn.close()

    # Преобразуем список кортежей в список строк
    return [team[0] for team in top_teams]

# Пример использования функции
if __name__ == "__main__":
    team_list = invites('test_database.db')
    print(team_list)
