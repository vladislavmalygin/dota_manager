import sqlite3


def get_prizepool_worldcup_system(tournament_id, db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT prizepool FROM tournaments WHERE id = ?", (tournament_id,))
    result = cursor.fetchone()
    conn.close()

    if result is None:
        return None

    prizepool = result[0]
    shares = [0.40, 0.25, 0.075, 0.075,
              0.025, 0.025, 0.025, 0.025,
              0.00625, 0.00625, 0.00625, 0.00625,
              0.00625, 0.00625, 0.00625, 0.00625]
    return [int(prizepool * s) for s in shares]
