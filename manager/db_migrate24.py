"""
Migration 24: fans, loan-out, watchlist.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    if c.execute("SELECT 1 FROM _migrations WHERE name='migrate24'").fetchone():
        conn.close(); return

    for ddl in [
        "ALTER TABLE teams   ADD COLUMN fans         INTEGER DEFAULT 0",
        "ALTER TABLE players ADD COLUMN loan_team_id INTEGER DEFAULT 0",
        "ALTER TABLE players ADD COLUMN loan_until   TEXT",
        "ALTER TABLE players ADD COLUMN loan_fee     INTEGER DEFAULT 0",
    ]:
        try:
            c.execute(ddl)
        except Exception:
            pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL UNIQUE
        )
    """)

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate24')")
    conn.commit()
    conn.close()
    print(f"[migrate24] fans + loan + watchlist in {db_name}")


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
