"""
Migration 13:
  - injured_until TEXT  → player out until this date
  - is_temp INTEGER     → 1 = rented for 1 tournament, released after
  - player_history table: per-player tournament placement records
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)

    for col, typ in [('injured_until', 'TEXT'), ('is_temp', 'INTEGER')]:
        try:
            conn.execute(f"ALTER TABLE players ADD COLUMN {col} {typ}")
            conn.commit()
        except Exception:
            pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id       INTEGER NOT NULL,
            player_nick     TEXT,
            season          INTEGER,
            tournament_name TEXT,
            place           INTEGER,
            team_name       TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"[migrate13] done {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate13] Error on {db}: {e}")
