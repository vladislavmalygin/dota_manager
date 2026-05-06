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
    # Top-8 get significantly more; places 9-16 get nothing
    shares = [0.38, 0.22, 0.12, 0.12,
              0.055, 0.055, 0.055, 0.055,
              0, 0, 0, 0,
              0, 0, 0, 0]
    return [int(ratingpool * s) for s in shares]
