import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate26'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    for ddl in [
        "ALTER TABLE teams ADD COLUMN rival_team_id INTEGER",
        "ALTER TABLE teams ADD COLUMN rival_wins    INTEGER DEFAULT 0",
        "ALTER TABLE teams ADD COLUMN rival_losses  INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(ddl)
        except Exception:
            pass

    conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate26')")
    conn.commit()
    conn.close()
