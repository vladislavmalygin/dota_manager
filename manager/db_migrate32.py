"""
Migration 32:
  Add youth_camp_count INTEGER DEFAULT 0 to teams — tracks camps used this season.
  Reset to 0 at season end via season_end.py.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate32'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    try:
        c.execute("ALTER TABLE teams ADD COLUMN youth_camp_count INTEGER DEFAULT 0")
    except Exception:
        pass

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate32')")
    conn.commit()
    conn.close()


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
        print(f'[migrate32] done: {db}')
