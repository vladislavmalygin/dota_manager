"""
Migration 35: Ensure match_history table exists at game start.
Previously created lazily in finalize_tournament; now guaranteed from first load.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate35'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    c.execute("""
        CREATE TABLE IF NOT EXISTS match_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            played_date TEXT,
            tournament  TEXT,
            stage       TEXT,
            team1       TEXT,
            team2       TEXT,
            winner      TEXT,
            score_t1    INTEGER DEFAULT 0,
            score_t2    INTEGER DEFAULT 0,
            best_of     INTEGER DEFAULT 1,
            log_json    TEXT
        )
    """)

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate35')")
    conn.commit()
    conn.close()


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
        print(f'[migrate35] done: {db}')
