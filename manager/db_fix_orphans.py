"""Fix orphaned team slots, homeless players, and duplicate nicknames."""
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

    # 3. Fix homeless players: team_id != 0 but not in any slot → set free
    valid_pids = set()
    for col in ('carry', 'mid', 'offlane', 'partial_support', 'full_support'):
        for (pid,) in c.execute(f"SELECT {col} FROM teams WHERE {col} IS NOT NULL"):
            valid_pids.add(pid)
    if valid_pids:
        placeholders = ','.join('?' * len(valid_pids))
        c.execute(
            f"UPDATE players SET team_id=0, wage=0 "
            f"WHERE team_id != 0 AND id NOT IN ({placeholders})",
            list(valid_pids),
        )

    # 3b. Fix mismatched team_id: player is in a slot but has wrong team_id
    for col in ('carry', 'mid', 'offlane', 'partial_support', 'full_support'):
        c.execute(f"""
            UPDATE players SET team_id = (SELECT id FROM teams WHERE {col} = players.id)
            WHERE id IN (
                SELECT {col} FROM teams WHERE {col} IS NOT NULL
            )
            AND team_id != (SELECT id FROM teams WHERE {col} = players.id)
        """)

    # 4. Fix duplicate nicknames: keep lower id, clear higher id's team slot
    c.execute("""
        SELECT MIN(id), MAX(id), nickname FROM players
        GROUP BY LOWER(nickname) HAVING COUNT(*) > 1
    """)
    for keep_id, dup_id, nick in c.fetchall():
        # Remove dup_id from any slot
        for col in ('carry', 'mid', 'offlane', 'partial_support', 'full_support'):
            c.execute(f"UPDATE teams SET {col}=NULL WHERE {col}=?", (dup_id,))
        # Rename dup to avoid future conflicts
        c.execute("UPDATE players SET nickname=nickname||'_dup' WHERE id=?", (dup_id,))

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
