"""Fix orphaned team slots and delete empty team shells."""
import sqlite3

EMPTY_TEAMS = [6, 28, 31, 42, 43, 44, 45, 46, 47]  # Cloud9 and fully empty defunct orgs

def fix(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # 1. Delete teams that have no players and no purpose
    c.executemany("DELETE FROM teams WHERE id=?", [(t,) for t in EMPTY_TEAMS])

    # 2. Fix orphaned slot references: if slot ID has no matching player, set NULL
    for col in ('carry', 'mid', 'offlane', 'partial_support', 'full_support'):
        c.execute(f"""
            UPDATE teams SET {col} = NULL
            WHERE {col} IS NOT NULL
              AND {col} NOT IN (SELECT id FROM players)
        """)

    conn.commit()
    conn.close()

    remaining = sqlite3.connect(db_name).execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    print(f"[fix] Done: {remaining} teams — {db_name}")

if __name__ == '__main__':
    import sys
    dbs = sys.argv[1:] or ['start_database.db', 'saves/asd_asd.db']
    for db in dbs:
        try: fix(db)
        except Exception as e: print(f"[fix] Error on {db}: {e}")
