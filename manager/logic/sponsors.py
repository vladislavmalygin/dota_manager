import sqlite3

_DEFAULT_OFFERS = [
    # (name, description, monthly_income, condition_type, condition_bonus, condition_penalty, term_months)
    ('Red Bull Gaming',  'Стабильный доход, без дополнительных условий',               8_000,  'always',   0,         0,       12),
    ('ASUS ROG',         'Бонус за попадание в топ-4 The International',               12_000, 'top4_ti',  200_000,   0,       12),
    ('Monster Energy',   'Бонус за победу на любом турнире',                           10_000, 'win_any',  150_000,   0,       12),
    ('HyperX',           'Крупный бонус за TI, но штраф при вылете на группе TI',     15_000, 'top4_ti',  350_000,   80_000,  12),
    ('Logitech G',       'Стабильный доход + небольшой ежегодный бонус',               6_000,  'always',   50_000,    0,       12),
]

_COND_LABELS = {
    'always':   'Без условий',
    'top4_ti':  'Топ-4 на The International',
    'win_any':  'Победа на любом турнире',
}


def ensure_sponsors_table(db_name):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    # Drop old sponsors table if it has the wrong schema (money/fame columns)
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Sponsors'")
    row = cur.fetchone()
    if row and 'money' in row[0]:
        conn.execute("DROP TABLE Sponsors")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sponsors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            monthly_income INTEGER DEFAULT 0,
            condition_type TEXT DEFAULT 'always',
            condition_bonus INTEGER DEFAULT 0,
            condition_penalty INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 0,
            signed_date TEXT,
            term_months INTEGER DEFAULT 12
        )
    """)
    cur.execute("SELECT COUNT(*) FROM sponsors")
    if cur.fetchone()[0] == 0:
        conn.executemany(
            """INSERT INTO sponsors
               (name, description, monthly_income, condition_type,
                condition_bonus, condition_penalty, term_months)
               VALUES (?,?,?,?,?,?,?)""",
            _DEFAULT_OFFERS,
        )
    conn.commit()
    conn.close()


def get_active_sponsor(db_name):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, description, monthly_income, condition_type, "
        "condition_bonus, condition_penalty, signed_date "
        "FROM sponsors WHERE is_active=1 LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_available_offers(db_name):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, description, monthly_income, condition_type, "
        "condition_bonus, condition_penalty "
        "FROM sponsors WHERE is_active=0 ORDER BY monthly_income DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def sign_sponsor(db_name, sponsor_id, game_date_str):
    conn = sqlite3.connect(db_name)
    conn.execute("UPDATE sponsors SET is_active=0, signed_date=NULL WHERE is_active=1")
    conn.execute(
        "UPDATE sponsors SET is_active=1, signed_date=? WHERE id=?",
        (game_date_str, sponsor_id),
    )
    conn.commit()
    conn.close()


def drop_sponsor(db_name):
    conn = sqlite3.connect(db_name)
    conn.execute("UPDATE sponsors SET is_active=0, signed_date=NULL WHERE is_active=1")
    conn.commit()
    conn.close()


def pay_monthly_income(db_name):
    """Add sponsor monthly income to player team budget. Returns (name, amount) or None."""
    active = get_active_sponsor(db_name)
    if not active:
        return None
    _, name, _, income, *_ = active
    if not income:
        return None
    conn = sqlite3.connect(db_name)
    conn.execute("UPDATE teams SET budget=budget+? WHERE player='yes'", (income,))
    conn.commit()
    conn.close()
    return (name, income)


def condition_label(ctype):
    return _COND_LABELS.get(ctype, ctype)


def check_and_pay_season_bonus(db_name, year, player_ti_place):
    """
    Check sponsor condition at season end and pay bonus/penalty.
    Returns (name, message, amount) or None.
    """
    active = get_active_sponsor(db_name)
    if not active:
        return None
    _, name, _, income, cond, bonus, penalty, signed = active

    conn = sqlite3.connect(db_name)
    result = None

    if cond == 'always':
        if bonus:
            conn.execute("UPDATE teams SET budget=budget+? WHERE player='yes'", (bonus,))
            result = (name, f'Ежегодный бонус: +${bonus:,}', bonus)

    elif cond == 'top4_ti':
        met = player_ti_place is not None and player_ti_place <= 4
        if met and bonus:
            conn.execute("UPDATE teams SET budget=budget+? WHERE player='yes'", (bonus,))
            result = (name, f'Условие выполнено (топ-4 TI): +${bonus:,}', bonus)
        elif not met and penalty:
            conn.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE player='yes'", (penalty,))
            result = (name, f'Условие не выполнено (топ-4 TI): −${penalty:,}', -penalty)

    elif cond == 'win_any':
        cur = conn.cursor()
        cur.execute("SELECT name FROM teams WHERE player='yes'")
        row = cur.fetchone()
        pname = row[0].strip() if row else ''
        cur.execute(
            """SELECT COUNT(*) FROM tournaments t
               JOIN teams te ON te.id = t.place1
               WHERE te.name=? AND t.place1 IS NOT NULL
                 AND strftime('%Y', t.start_date)=?""",
            (pname, str(year))
        )
        wins = cur.fetchone()[0]
        if wins > 0 and bonus:
            conn.execute("UPDATE teams SET budget=budget+? WHERE player='yes'", (bonus,))
            result = (name, f'Условие выполнено (победа в турнире): +${bonus:,}', bonus)
        elif wins == 0 and penalty:
            conn.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE player='yes'", (penalty,))
            result = (name, f'Условие не выполнено (не выиграли турнир): −${penalty:,}', -penalty)

    conn.commit()
    conn.close()
    return result
