"""
Migration 18 fix: Remove retired/fictional players added in migrate18.

Retired by 2026:
  441 Miracle-     retired 2023
  442 KuroKy       retired 2021
  446 S4           retired 2020
  448 ALWAYSWANNAFLY  semi-retired ~2023
  449 n0tail       retired 2021
  450 Fata         retired ~2019
  452 JerAx        retired 2021
  456 hyhy         retired ~2018
  457 PieLieDie    retired 2016
  458 Fear         retired ~2019

Unconfirmed/fictional:
  453 Stormstormer
  455 XSvamp
  459 Nofear
  462 LeBronDota
  463 NetP
  465 Envy

Team fixes:
  Team Secret (53) mid: Miracle-(deleted) → Waga(451)
  Team IVY (10) partial_support: ALWAYSWANNAFLY(deleted) → BoBoka(55)
"""
import sqlite3

_REMOVE_IDS = [441, 442, 446, 448, 449, 450, 452, 453, 455, 456, 457, 458, 459, 462, 463, 465]


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    if c.execute("SELECT 1 FROM _migrations WHERE name='migrate18_fix'").fetchone():
        conn.close(); return

    # NULL out slots that reference deleted players
    slots = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
    for pid in _REMOVE_IDS:
        for slot in slots:
            c.execute(
                f"UPDATE teams SET {slot}=NULL WHERE {slot}=?", (pid,)
            )

    # Delete the players
    placeholders = ','.join('?' * len(_REMOVE_IDS))
    c.execute(f"DELETE FROM players WHERE id IN ({placeholders})", _REMOVE_IDS)

    # Fix Team Secret mid: 441 (deleted) → Waga (451)
    sec_mid = c.execute("SELECT mid FROM teams WHERE id=53").fetchone()
    if sec_mid and sec_mid[0] is None:
        # Waga currently on team? move to Secret
        c.execute("UPDATE teams SET mid=451 WHERE id=53")
        c.execute("UPDATE players SET team_id=53, wage=MAX(wage,expected_wage) WHERE id=451")

    # Fix IVY partial_support: 448 (deleted) → BoBoka (55)
    ivy_ps = c.execute("SELECT partial_support FROM teams WHERE id=10").fetchone()
    if ivy_ps and ivy_ps[0] is None:
        c.execute("UPDATE teams SET partial_support=55 WHERE id=10")
        c.execute("UPDATE players SET team_id=10, wage=MAX(wage,expected_wage) WHERE id=55")

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate18_fix')")
    conn.commit()
    conn.close()
    print(f"[migrate18_fix] done {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate18_fix] Error on {db}: {e}")
