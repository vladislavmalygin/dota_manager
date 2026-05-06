"""
Migration 11: Add scouted column to players.
0 = stats hidden in transfers; 1 = player has been scouted by player team.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    try:
        conn.execute("ALTER TABLE players ADD COLUMN scouted INTEGER DEFAULT 0")
        conn.commit()
        print(f"[migrate11] scouted column added to {db_name}")
    except Exception:
        pass
    conn.close()


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate11] Error on {db}: {e}")
