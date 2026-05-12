import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate28'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    conn.execute("""
        CREATE TABLE IF NOT EXISTS h2h_records (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            opponent_team_id INTEGER NOT NULL,
            wins             INTEGER DEFAULT 0,
            losses           INTEGER DEFAULT 0,
            last_tournament  TEXT,
            UNIQUE(opponent_team_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            achievement_key TEXT NOT NULL UNIQUE,
            name            TEXT NOT NULL,
            description     TEXT,
            unlocked_date   TEXT,
            bonus_desc      TEXT
        )
    """)

    try:
        conn.execute("ALTER TABLE teams ADD COLUMN achievement_flags TEXT DEFAULT ''")
    except Exception:
        pass

    # Seed achievement definitions (not yet unlocked)
    achievements = [
        ('first_tournament',  'Первый турнир',        'Сыграть первый официальный турнир',           None, '— начало пути'),
        ('first_win',         'Первая победа',         'Выиграть любой турнир',                       None, '+10% доход от стриминга'),
        ('world_number_one',  'Топ мира',             'Занять 1-е место в мировом рейтинге',          None, '+5 репутации ежемесячно'),
        ('rival_dominator',   'Победитель соперников', '10 побед над назначенным соперником',         None, '-5% запросы зарплат FA'),
        ('iron_squad',        'Железный состав',      'Весь основной состав вместе 12+ месяцев',      None, 'Сыгранность теряется на 50% медленнее'),
        ('youth_movement',    'Молодёжное движение',  'Выиграть турнир с 3+ молодёжными игроками',    None, 'Юниоры академии начинают с +5 скиллам'),
        ('the_international', 'Чемпион TI',           'Выиграть The International',                   None, '+30 репутация организации навсегда'),
        ('ace_groups',        'Король группы',        'Пройти группу без поражений (3 раза)',          None, '+3 мораль в начале каждого турнира'),
        ('dynasty',           'Династия',             'Выиграть 3 разных Major-турнира',               None, '+$15,000/мес к стримингу'),
        ('headhunter',        'Охотник за талантами', 'Подписать 10 свободных агентов',               None, '-$1,000 к средней зарплате команды'),
    ]
    for row in achievements:
        conn.execute(
            "INSERT OR IGNORE INTO achievements "
            "(achievement_key, name, description, unlocked_date, bonus_desc) "
            "VALUES (?,?,?,?,?)", row
        )

    conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate28')")
    conn.commit()
    conn.close()
