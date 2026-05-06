"""
Migration 9: Add stability and learning_rate to all players.
Both are random 1-10, assigned once per player (idempotent: fills NULLs only).
"""
import sqlite3
import random


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    for col, default in [('stability', None), ('learning_rate', None)]:
        try:
            c.execute(f"ALTER TABLE players ADD COLUMN {col} INTEGER")
            conn.commit()
        except Exception:
            pass

    c.execute("SELECT id FROM players WHERE stability IS NULL OR learning_rate IS NULL")
    pids = [r[0] for r in c.fetchall()]

    for pid in pids:
        c.execute(
            "UPDATE players SET stability=?, learning_rate=? WHERE id=?",
            (random.randint(1, 10), random.randint(1, 10), pid),
        )

    if pids:
        print(f"[migrate9] Assigned stability/learning_rate for {len(pids)} players in {db_name}")

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
            print(f"[migrate9] Error on {db}: {e}")
