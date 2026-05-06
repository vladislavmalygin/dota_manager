"""
Migration 12: Add strat_early, strat_mid, strat_late to teams.
AI teams get auto-assigned strategies based on skill profile.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    for col in ('strat_early', 'strat_mid', 'strat_late'):
        try:
            c.execute(f"ALTER TABLE teams ADD COLUMN {col} TEXT")
            conn.commit()
        except Exception:
            pass

    # Auto-assign to teams without strategies
    c.execute(
        "SELECT t.id, t.carry, t.mid, t.offlane, t.partial_support, t.full_support "
        "FROM teams t WHERE t.strat_early IS NULL"
    )
    teams = c.fetchall()

    for row in teams:
        tid = row[0]
        pids = [p for p in row[1:] if p]
        avg_micro = avg_macro = avg_soft = 50  # defaults

        if pids:
            ph = ','.join('?' * len(pids))
            c.execute(
                f"SELECT AVG(COALESCE(micro_skills,0)), AVG(COALESCE(macro_skills,0)), "
                f"AVG(COALESCE(soft_skills,0)) FROM players WHERE id IN ({ph})",
                pids,
            )
            vals = c.fetchone()
            if vals and vals[0] is not None:
                avg_micro, avg_macro, avg_soft = vals

        from logic.dota.strategies import ai_pick_strategy
        early, mid, late = ai_pick_strategy(avg_micro, avg_macro, avg_soft)
        c.execute(
            "UPDATE teams SET strat_early=?, strat_mid=?, strat_late=? WHERE id=?",
            (early, mid, late, tid),
        )

    conn.commit()
    conn.close()
    print(f"[migrate12] strat columns assigned in {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate12] Error on {db}: {e}")
