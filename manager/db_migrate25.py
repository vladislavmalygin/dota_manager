import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate25'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    for ddl in [
        "ALTER TABLE players ADD COLUMN fatigue INTEGER DEFAULT 0",
        "ALTER TABLE teams   ADD COLUMN org_reputation INTEGER DEFAULT 20",
        "ALTER TABLE teams   ADD COLUMN investor_name TEXT",
        "ALTER TABLE teams   ADD COLUMN investor_end_date TEXT",
        "ALTER TABLE teams   ADD COLUMN investor_cut_pct INTEGER DEFAULT 0",
        "ALTER TABLE teams   ADD COLUMN investor_bonus INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(ddl)
        except Exception:
            pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta_patches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            season      INTEGER NOT NULL,
            patch_name  TEXT NOT NULL,
            favored_role TEXT NOT NULL,
            bonus_pct   INTEGER DEFAULT 12,
            start_date  TEXT NOT NULL,
            active      INTEGER DEFAULT 1
        )
    """)

    # Seed initial patch
    c.execute("SELECT COUNT(*) FROM meta_patches")
    if c.fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO meta_patches (season, patch_name, favored_role, bonus_pct, start_date, active) "
            "VALUES (2024, '7.36', 'carry', 12, '2024-01-01', 1)"
        )

    conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate25')")
    conn.commit()
    conn.close()
