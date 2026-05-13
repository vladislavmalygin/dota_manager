"""
Migration 34: Add signature_heroes TEXT column to players.
3 hero names per player (JSON list), changes with patches.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate34'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    try:
        c.execute("ALTER TABLE players ADD COLUMN signature_heroes TEXT DEFAULT NULL")
    except Exception:
        pass

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate34')")
    conn.commit()
    conn.close()


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
        print(f'[migrate34] done: {db}')
