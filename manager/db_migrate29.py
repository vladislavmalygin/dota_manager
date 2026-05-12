import sqlite3


MINOR_RATINGPOOL    = 2858   # 1st place = 1000 pts
MAJOR_RATINGPOOL    = 5715   # 1st place = 2000 pts
TI_RATINGPOOL       = 8572   # 1st place = 3000 pts
REGIONAL_RATINGPOOL = 1429   # 1st place =  500 pts

MINOR_KEYWORDS    = ("ESL One", "PGL Bucharest")
MAJOR_KEYWORDS    = ("DreamLeague", "PGL Wallachia")
TI_KEYWORD        = "The International"
REGIONAL_KEYWORD  = "DPC"


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate29'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    c.execute("SELECT id, name FROM tournaments")
    for tid, name in c.fetchall():
        if TI_KEYWORD in name:
            pool = TI_RATINGPOOL
        elif any(kw in name for kw in MAJOR_KEYWORDS):
            pool = MAJOR_RATINGPOOL
        elif REGIONAL_KEYWORD in name:
            pool = REGIONAL_RATINGPOOL
        elif any(kw in name for kw in MINOR_KEYWORDS):
            pool = MINOR_RATINGPOOL
        else:
            continue
        c.execute("UPDATE tournaments SET ratingpool = ? WHERE id = ?", (pool, tid))

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate29')")
    conn.commit()
    conn.close()
