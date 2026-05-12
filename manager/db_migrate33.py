"""
Migration 33:
  Add active_tournament table — stores ongoing tournament state so matches
  play out one per calendar day instead of all at once.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate33'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    c.execute("""
        CREATE TABLE IF NOT EXISTS active_tournament (
            id               INTEGER PRIMARY KEY DEFAULT 1,
            tourn_id         INTEGER NOT NULL,
            name             TEXT NOT NULL,
            match_queue_json TEXT NOT NULL,
            match_idx        INTEGER DEFAULT 0,
            standings_json   TEXT,
            final_ev_json    TEXT,
            minor_ev_json    TEXT,
            draw_ev_json     TEXT,
            player_teams_json TEXT
        )
    """)

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate33')")
    conn.commit()
    conn.close()


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
        print(f'[migrate33] done: {db}')
