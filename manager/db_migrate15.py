"""
Migration 15:
  - players.wants_to_leave INTEGER DEFAULT 0 — player demands release
  - teams.conflict_targets TEXT — comma-separated player IDs being "voted out"
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    for col, typ, default in [
        ('wants_to_leave', 'INTEGER', '0'),
    ]:
        try:
            conn.execute(f"ALTER TABLE players ADD COLUMN {col} {typ} DEFAULT {default}")
        except Exception:
            pass
    try:
        conn.execute("ALTER TABLE teams ADD COLUMN conflict_targets TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()
    print(f"[migrate15] done {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate15] Error on {db}: {e}")
