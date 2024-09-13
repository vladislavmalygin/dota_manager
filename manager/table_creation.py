import sqlite3

def create_tables():
    conn = sqlite3.connect('start_database.db')
    cursor = conn.cursor()

    # Создание таблицы для команд
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country TEXT NOT NULL,
        fame INTEGER NOT NULL,
        owner_character TEXT NOT NULL,
        logo_id INTEGER,
        achievements TEXT,
        budget REAL NOT NULL
    )
    ''')

    # Создание таблицы для менеджеров
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Managers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        name TEXT NOT NULL,
        surname TEXT NOT NULL,
        nickname TEXT NOT NULL,
        fame INTEGER NOT NULL,
        FOREIGN KEY (team_id) REFERENCES Teams (id)
    )
    ''')

    # Создание таблицы для сохранений игры
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS GameSaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        save_data TEXT,
        FOREIGN KEY (team_id) REFERENCES Teams (id)
    )
    ''')

    # Создание таблицы для логотипов (если нужно)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Logos (
        id INTEGER PRIMARY KEY AUTOINCREMENT
        -- Добавьте другие поля, если необходимо
    )
    ''')

    # Создание таблицы для спонсоров
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Sponsors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        money REAL NOT NULL,
        fame INTEGER NOT NULL,
        expected_results TEXT
    )
    ''')
    # Создание таблицы игроков
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        name TEXT NOT NULL,
        surname TEXT NOT NULL,
        nickname TEXT NOT NULL,
        country TEXT NOT NULL,
        fame INTEGER CHECK(fame BETWEEN 10 AND 100),
        character TEXT,
        micro_skills INTEGER CHECK(micro_skills BETWEEN 10 AND 100),
        macro_skills INTEGER CHECK(macro_skills BETWEEN 10 AND 100),
        soft_skills INTEGER CHECK(soft_skills BETWEEN 10 AND 100),
        skill_cap INTEGER CHECK(skill_cap BETWEEN 30 AND 300),
        wage INTEGER,
        expected_wage INTEGER,
        achievements TEXT,
        languages TEXT,
        role TEXT CHECK(role IN ('carry', 'mid', 'offlane', 'partial_support', 'full_support')),
        FOREIGN KEY (team_id) REFERENCES Teams(id) ON DELETE SET NULL
    );
    ''')




    conn.commit()
    conn.close()

# Вызов функции для создания таблиц
create_tables()
