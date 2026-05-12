"""
Migration 30: Remove duplicate Noone.
Migration 4 added 'No[o]ne-' (single-o); migration 21 added 'No[o]one-' (double-o).
Both are the same real player (Volodymyr Minenko). Keep the double-o version on PARIVISION,
delete the single-o free agent.
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate30'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    # Remove the single-o free agent duplicate if it exists
    c.execute("SELECT id, team_id FROM players WHERE nickname='No[o]ne-'")
    row = c.execute("SELECT id, team_id FROM players WHERE nickname='No[o]ne-'").fetchone()
    if row:
        pid, tid = row
        # If on a team roster, unassign first
        if tid and tid != 0:
            c.execute("""
                UPDATE teams SET
                  carry = CASE WHEN carry=? THEN NULL ELSE carry END,
                  mid   = CASE WHEN mid=?   THEN NULL ELSE mid   END,
                  offlane = CASE WHEN offlane=? THEN NULL ELSE offlane END,
                  partial_support = CASE WHEN partial_support=? THEN NULL ELSE partial_support END,
                  full_support    = CASE WHEN full_support=?    THEN NULL ELSE full_support    END
                WHERE id=?
            """, (pid, pid, pid, pid, pid, tid))
        c.execute("DELETE FROM players WHERE id=?", (pid,))

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate30')")
    conn.commit()
    conn.close()


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
        print(f'[migrate30] done: {db}')
