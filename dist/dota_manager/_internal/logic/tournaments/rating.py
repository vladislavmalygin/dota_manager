import sqlite3


def get_ratingpool_worldcup_system(tournament_id, db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT ratingpool FROM tournaments WHERE id = ?", (tournament_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None:
        return None

    ratingpool = result[0] or 0
    # Top-4 get most; everyone who plays gets something
    shares = [0.35, 0.20, 0.11, 0.11,
              0.05, 0.05, 0.05, 0.05,
              0.012, 0.012, 0.012, 0.012,
              0.008, 0.008, 0.004, 0.004]
    return [int(ratingpool * s) for s in shares]
