"""
Migration 17:
  - teams.loan_amount INTEGER DEFAULT 0    — current loan balance
  - teams.loan_monthly INTEGER DEFAULT 0   — monthly repayment
  - player_skill_snapshot table            — skills per season for chart
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    for col, typ in [('loan_amount', 'INTEGER'), ('loan_monthly', 'INTEGER')]:
        try:
            conn.execute(f"ALTER TABLE teams ADD COLUMN {col} {typ} DEFAULT 0")
        except Exception:
            pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_skill_snapshot (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            season    INTEGER NOT NULL,
            micro     INTEGER DEFAULT 0,
            macro     INTEGER DEFAULT 0,
            soft      INTEGER DEFAULT 0,
            UNIQUE(player_id, season)
        )
    """)
    conn.commit()
    conn.close()
    print(f"[migrate17] done {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate17] Error on {db}: {e}")
