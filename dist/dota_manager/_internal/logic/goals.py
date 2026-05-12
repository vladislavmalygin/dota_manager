import sqlite3
import random

# type → (description template, targets list, rewards dict {target: (rep, money)}, lower_is_better)
_GOAL_DEFS = [
    ('best_finish',
     'Занять топ-{t} хотя бы на одном турнире',
     [1, 2, 4],
     {1: (10, 100_000), 2: (7, 60_000), 4: (4, 30_000)},
     True),   # lower place = better

    ('win_tournament',
     'Выиграть {t} турнир(а) за сезон',
     [1, 2, 3],
     {1: (8, 50_000), 2: (12, 100_000), 3: (18, 200_000)},
     False),

    ('cohesion_target',
     'Сыгранность команды ≥ {t}',
     [50, 70, 85],
     {50: (3, 20_000), 70: (5, 40_000), 85: (8, 70_000)},
     False),

    ('sign_skill',
     'Подписать игрока со скиллом ≥ {t}',
     [130, 150, 165],
     {130: (3, 15_000), 150: (5, 30_000), 165: (8, 60_000)},
     False),

    ('earn_prize',
     'Заработать ${t:,} призовых за сезон',
     [100_000, 300_000, 600_000],
     {100_000: (3, 20_000), 300_000: (6, 50_000), 600_000: (10, 100_000)},
     False),
]

_LOWER_BETTER = {'best_finish'}

_DDL = """
    CREATE TABLE IF NOT EXISTS season_goals (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        year             INTEGER,
        type             TEXT,
        description      TEXT,
        target_value     INTEGER,
        current_value    INTEGER DEFAULT 0,
        completed        INTEGER DEFAULT 0,
        reward_rep       INTEGER DEFAULT 5,
        reward_money     INTEGER DEFAULT 0
    )
"""


def ensure_table(db_name):
    conn = sqlite3.connect(db_name)
    conn.execute(_DDL)
    conn.commit()
    conn.close()


def generate_season_goals(db_name, year):
    ensure_table(db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("DELETE FROM season_goals WHERE year=?", (year,))

    chosen = random.sample(_GOAL_DEFS, 3)
    for gtype, tmpl, targets, rewards, lower_is_better in chosen:
        t = random.choice(targets)
        rep, money = rewards[t]
        desc = tmpl.format(t=t)
        # For best_finish start at 999 (worst), all others start at 0
        init = 999 if lower_is_better else 0
        c.execute("""
            INSERT INTO season_goals
              (year, type, description, target_value, current_value, reward_rep, reward_money)
            VALUES (?,?,?,?,?,?,?)
        """, (year, gtype, desc, t, init, rep, money))

    conn.commit()
    conn.close()


def update_goal(db_name, year, gtype, value):
    """Update progress. value = new measurement (place, count increment, skill avg, etc.)."""
    ensure_table(db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("""SELECT id, description, target_value, current_value, reward_rep, reward_money
                 FROM season_goals WHERE year=? AND type=? AND completed=0""",
              (year, gtype))
    goals = c.fetchall()

    for gid, desc, target, cur, rep, money in goals:
        if gtype in _LOWER_BETTER:
            new_val = min(cur, value)         # best (lowest) place seen
            done    = new_val <= target
        elif gtype in ('cohesion_target', 'sign_skill'):
            new_val = max(cur, value)         # absolute max
            done    = new_val >= target
        else:
            new_val = cur + value             # accumulate (win_tournament, earn_prize)
            done    = new_val >= target

        c.execute("UPDATE season_goals SET current_value=? WHERE id=?", (new_val, gid))
        if done:
            c.execute("UPDATE season_goals SET completed=1 WHERE id=?", (gid,))
            conn.execute("UPDATE teams SET budget=budget+? WHERE player='yes'", (money,))
            conn.execute(
                "UPDATE characters SET reputation=MAX(0,COALESCE(reputation,0)+?)", (rep,)
            )
            conn.execute(
                "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
                (f"Цель выполнена: {desc}!  +{rep} репутации  +${money:,}", "Цели"),
            )

    conn.commit()
    conn.close()


def get_goals(db_name, year):
    ensure_table(db_name)
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("""SELECT type, description, target_value, current_value,
                        completed, reward_rep, reward_money
                 FROM season_goals WHERE year=? ORDER BY id""", (year,))
    rows = c.fetchall()
    conn.close()
    return rows


def year_from_date(date_str):
    try:
        return int(str(date_str)[:4])
    except Exception:
        return 2024
