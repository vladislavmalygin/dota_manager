"""
Migration 23: Recreate team_snapshots with UNIQUE(team_id, snap_date).
Prevents duplicate monthly snapshots if save is loaded on the same date.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    if c.execute("SELECT 1 FROM _migrations WHERE name='migrate23'").fetchone():
        conn.close(); return

    c.execute("""
        CREATE TABLE IF NOT EXISTS team_snapshots_new (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id   INTEGER NOT NULL,
            snap_date TEXT NOT NULL,
            rating    REAL DEFAULT 0,
            budget    INTEGER DEFAULT 0,
            UNIQUE(team_id, snap_date)
        )
    """)
    try:
        c.execute("""
            INSERT OR IGNORE INTO team_snapshots_new (id, team_id, snap_date, rating, budget)
            SELECT id, team_id, snap_date, rating, budget FROM team_snapshots
        """)
    except Exception:
        pass
    try:
        c.execute("DROP TABLE IF EXISTS team_snapshots")
    except Exception:
        pass
    c.execute("ALTER TABLE team_snapshots_new RENAME TO team_snapshots")

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate23')")
    conn.commit()
    conn.close()
    print(f"[migrate23] team_snapshots rebuilt with UNIQUE constraint in {db_name}")


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
