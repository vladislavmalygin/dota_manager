"""
Migration 16:
  - players.is_youth INTEGER DEFAULT 0  — tagged by academy
  - player_career_stats table           — career games/wins/MVP per season
  - ai_offers table                     — pending AI buy offers for player's players
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)

    # players.is_youth
    try:
        conn.execute("ALTER TABLE players ADD COLUMN is_youth INTEGER DEFAULT 0")
    except Exception:
        pass

    # messages.read
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN read INTEGER DEFAULT 0")
    except Exception:
        pass

    # player_career_stats
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_career_stats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id   INTEGER NOT NULL,
            season      INTEGER NOT NULL,
            games       INTEGER DEFAULT 0,
            wins        INTEGER DEFAULT 0,
            mvp_count   INTEGER DEFAULT 0,
            UNIQUE(player_id, season)
        )
    """)

    # ai_offers
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_offers (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            team_id   INTEGER NOT NULL,
            fee       INTEGER NOT NULL,
            created   TEXT NOT NULL,
            UNIQUE(player_id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"[migrate16] done {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate16] Error on {db}: {e}")
