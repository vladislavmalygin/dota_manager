"""
Migration 20: Set comp_exp for ALL players based on age + skill tier.

Formula:
  career_years = max(0, age - 18)
  rate = games/year by skill bracket:
    skill >= 175 → 30  (elite T1, TI contenders)
    skill >= 160 → 28  (T1 regular)
    skill >= 145 → 22  (T2 upper)
    skill >= 130 → 16  (T2 lower / T3 upper)
    skill >= 110 → 10  (T3)
    else         →  6  (amateur / youth)

Overwrites ALL players for consistency.
"""
import sqlite3


_SQL = """
UPDATE players
SET comp_exp = MAX(0, (COALESCE(age, 22) - 18)) *
    CASE
        WHEN COALESCE(micro_skills,0) + COALESCE(macro_skills,0) >= 175 THEN 30
        WHEN COALESCE(micro_skills,0) + COALESCE(macro_skills,0) >= 160 THEN 28
        WHEN COALESCE(micro_skills,0) + COALESCE(macro_skills,0) >= 145 THEN 22
        WHEN COALESCE(micro_skills,0) + COALESCE(macro_skills,0) >= 130 THEN 16
        WHEN COALESCE(micro_skills,0) + COALESCE(macro_skills,0) >= 110 THEN 10
        ELSE 6
    END
WHERE COALESCE(comp_exp, 0) = 0
"""


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    if c.execute("SELECT 1 FROM _migrations WHERE name='migrate20'").fetchone():
        conn.close(); return
    conn.execute(_SQL)
    affected = conn.execute("SELECT changes()").fetchone()[0]
    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate20')")
    conn.commit()
    conn.close()
    print(f"[migrate20] comp_exp set for {affected} players in {db_name}")


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
