import sqlite3

_DEFAULT_OFFERS = [
    # (name, description, monthly_income, condition_type, condition_bonus, condition_penalty, term_months)
    ('Red Bull Gaming',  'Стабильный доход, без дополнительных условий',               20_000, 'always',   0,         0,       12),
    ('ASUS ROG',         'Бонус за попадание в топ-4 The International',               30_000, 'top4_ti',  450_000,   0,       12),
    ('Monster Energy',   'Бонус за победу на любом турнире',                           25_000, 'win_any',  300_000,   0,       12),
    ('HyperX',           'Крупный бонус за TI, но штраф при вылете на группе TI',     40_000, 'top4_ti',  700_000,   150_000, 12),
    ('Logitech G',       'Стабильный доход + ежегодный бонус',                         18_000, 'always',   120_000,   0,       12),
    ('Secretlab',        'Бонус за топ-8 на любом крупном турнире',                    28_000, 'top8_any', 250_000,   0,       12),
    ('Intel',            'Крупные выплаты — требует попасть в топ-8 на TI',            55_000, 'top8_ti',  600_000,   200_000, 12),
]

_COND_LABELS = {
    'always':   'Без условий',
    'top4_ti':  'Топ-4 на The International',
    'top8_ti':  'Топ-8 на The International',
    'top8_any': 'Топ-8 на любом турнире',
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
    # Upsert all default offers (update income if sponsor already exists)
    existing = {r[0] for r in cur.execute("SELECT name FROM sponsors").fetchall()}
    for offer in _DEFAULT_OFFERS:
        sname = offer[0]
        if sname not in existing:
            cur.execute(
                "INSERT INTO sponsors (name, description, monthly_income, condition_type, "
                "condition_bonus, condition_penalty, term_months) VALUES (?,?,?,?,?,?,?)",
                offer,
            )
        else:
            # Update income/bonus on existing non-active sponsors to reflect rebalance
            cur.execute(
                "UPDATE sponsors SET monthly_income=?, condition_bonus=?, condition_penalty=? "
                "WHERE name=? AND is_active=0",
                (offer[2], offer[4], offer[5], sname),
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


def get_market_offers(db_name, n=4):
    """Return n shuffled available sponsor offers for bidding."""
    import random as _r
    conn = sqlite3.connect(db_name)
    rows = conn.execute(
        "SELECT id, name, description, monthly_income, condition_type, "
        "condition_bonus, condition_penalty, term_months "
        "FROM sponsors WHERE is_active=0 ORDER BY RANDOM() LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return rows


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

    elif cond == 'top8_ti':
        met = player_ti_place is not None and player_ti_place <= 8
        if met and bonus:
            conn.execute("UPDATE teams SET budget=budget+? WHERE player='yes'", (bonus,))
            result = (name, f'Условие выполнено (топ-8 TI): +${bonus:,}', bonus)
        elif not met and penalty:
            conn.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE player='yes'", (penalty,))
            result = (name, f'Условие не выполнено (топ-8 TI): −${penalty:,}', -penalty)

    elif cond in ('win_any', 'top8_any'):
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM teams WHERE player='yes'")
        row = cur.fetchone()
        if row:
            ptid, pname = row[0], row[1].strip()
            if cond == 'win_any':
                cur.execute(
                    "SELECT COUNT(*) FROM tournaments t JOIN teams te ON te.id=t.place1 "
                    "WHERE te.name=? AND t.place1 IS NOT NULL AND strftime('%Y',t.start_date)=?",
                    (pname, str(year))
                )
                met = cur.fetchone()[0] > 0
                label = 'победа в турнире'
            else:  # top8_any
                # Check if team placed 1-8 in any tournament this year
                place_cols = ','.join(f'place{i}' for i in range(1, 9))
                cur.execute(
                    f"SELECT COUNT(*) FROM tournaments WHERE ({place_cols}) "
                    f"= ? OR place1=? OR place2=? OR place3=? OR place4=? "
                    f"OR place5=? OR place6=? OR place7=? OR place8=? "
                    f"AND strftime('%Y',start_date)=?",
                    (ptid,) * 8 + (str(year),)
                )
                # Simpler approach: check placements table
                cur.execute(
                    "SELECT COUNT(*) FROM tournaments "
                    "WHERE strftime('%Y',start_date)=? AND ("
                    "place1=? OR place2=? OR place3=? OR place4=? "
                    "OR place5=? OR place6=? OR place7=? OR place8=?)",
                    (str(year), ptid, ptid, ptid, ptid, ptid, ptid, ptid, ptid)
                )
                met = cur.fetchone()[0] > 0
                label = 'топ-8 на турнире'

            if met and bonus:
                conn.execute("UPDATE teams SET budget=budget+? WHERE player='yes'", (bonus,))
                result = (name, f'Условие выполнено ({label}): +${bonus:,}', bonus)
            elif not met and penalty:
                conn.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE player='yes'", (penalty,))
                result = (name, f'Условие не выполнено ({label}): −${penalty:,}', -penalty)

    conn.commit()
    conn.close()
    return result
