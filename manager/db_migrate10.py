"""
Migration 10: Add form, micro_cap, macro_cap, soft_cap to players.
  form (1-10): hidden current performance level, updated monthly
  micro_cap, macro_cap, soft_cap: individual skill ceilings (random per player)
"""
import sqlite3
import random


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    for col, typ in [('form', 'INTEGER'), ('micro_cap', 'INTEGER'),
                     ('macro_cap', 'INTEGER'), ('soft_cap', 'INTEGER')]:
        try:
            c.execute(f"ALTER TABLE players ADD COLUMN {col} {typ}")
            conn.commit()
        except Exception:
            pass

    # Assign form to players without it
    c.execute("SELECT id FROM players WHERE form IS NULL")
    for (pid,) in c.fetchall():
        c.execute("UPDATE players SET form=? WHERE id=?", (random.randint(3, 7), pid))

    # Assign per-skill caps derived from total skill_cap with random variance
    c.execute(
        "SELECT id, COALESCE(skill_cap, 240), "
        "COALESCE(micro_skills, 0), COALESCE(macro_skills, 0), COALESCE(soft_skills, 0) "
        "FROM players WHERE micro_cap IS NULL"
    )
    for pid, total_cap, micro, macro, soft in c.fetchall():
        base = total_cap // 3
        mc = max(micro + 5, min(98, base + random.randint(-10, 22)))
        xc = max(macro + 5, min(98, base + random.randint(-10, 22)))
        sc = max(soft  + 5, min(92, base + random.randint(-14, 18)))
        c.execute(
            "UPDATE players SET micro_cap=?, macro_cap=?, soft_cap=? WHERE id=?",
            (mc, xc, sc, pid),
        )

    conn.commit()
    conn.close()
    print(f"[migrate10] form + per-skill caps applied to {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate10] Error on {db}: {e}")
