"""
Migration 14:
  - players.comp_exp INTEGER — grows only from tournament matches
  - teams.last_scrimmage_date TEXT — daily scrimmage limit
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    for col, typ in [('comp_exp', 'INTEGER')]:
        try:
            conn.execute(f"ALTER TABLE players ADD COLUMN {col} {typ}")
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE teams ADD COLUMN last_scrimmage_date TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()
    print(f"[migrate14] done {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate14] Error on {db}: {e}")
