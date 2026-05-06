"""
Migration 7: Set initial player ages based on competence.
Idempotent via _migrations table.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate7'")
    if c.fetchone()[0]:
        conn.close()
        return

    # age column may not exist yet — ignore if missing
    try:
        c.execute("ALTER TABLE players ADD COLUMN age INTEGER DEFAULT 22")
        conn.commit()
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE teams ADD COLUMN tactic TEXT DEFAULT 'balanced'")
        conn.commit()
    except Exception:
        pass

    # Assign ages based on competence: elite players prime 23-27, lower comp wider range
    c.execute("SELECT id, competence FROM players")
    players = c.fetchall()
    for pid, comp in players:
        comp = comp or 5
        base = 15 + comp          # comp3→18, comp5→20, comp7→22, comp8→23, comp9→24
        spread = max(3, 10 - comp) # comp3→7, comp5→5, comp7→3, comp8→2, comp9→1
        age = base + (pid % (spread + 1))
        c.execute("UPDATE players SET age=? WHERE id=?", (age, pid))

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate7')")
    conn.commit()
    conn.close()
    print(f"[migrate7] Initialised ages for {len(players)} players in {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate7] Error on {db}: {e}")
