"""
Migration 8: Assign random career retirement age (24–31) to every player.
Idempotent: only fills NULL retirement_age values.
"""
import sqlite3
import random


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Add column if missing
    try:
        c.execute("ALTER TABLE players ADD COLUMN retirement_age INTEGER")
        conn.commit()
    except Exception:
        pass

    # Fill only players without a retirement_age yet
    c.execute("SELECT id, COALESCE(age, 22) FROM players WHERE retirement_age IS NULL")
    players = c.fetchall()

    for pid, age in players:
        # retirement age must be strictly after current age, within 24–31
        lo = max(24, age + 1)
        hi = 31
        if lo > hi:
            hi = lo  # edge: very old player — retire next year
        ret_age = random.randint(lo, hi)
        c.execute("UPDATE players SET retirement_age=? WHERE id=?", (ret_age, pid))

    if players:
        print(f"[migrate8] Set retirement_age for {len(players)} players in {db_name}")

    conn.commit()
    conn.close()


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate8] Error on {db}: {e}")
