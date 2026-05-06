"""
Migration 19: Add real young T2/T3 players active in early 2026.

Regions: EEU, EU, SA, SEA, CN.
Youth (is_youth=1): Kiyotaka (born 2004), m1CKE (born 2005).
"""
import sqlite3

# (name, surname, nickname, country, role,
#  age, micro, macro, soft, competence,
#  skill_cap, expected_wage, comp_exp,
#  retirement_age, stability, learning_rate,
#  morale, micro_cap, macro_cap, soft_cap)
_PLAYERS = [
    # ── EEU T2 ───────────────────────────────────────────────────────────────
    # Yuragi (Artem Golubiev, Russia, carry, born 2003 → 22)
    # VP.Prodigy → various EEU T2 teams
    ('Artem', 'Golubiev',    'Yuragi',   'Russia',    'carry',
     22, 76, 72, 64, 7, 268, 5500, 120, 30, 7, 7, 6, 84, 80, 74),

    # Kiyotaka (Nikita Krasil'nikov, Russia, mid, born 2004 → 21) [youth]
    ('Nikita', 'Krasil\'nikov', 'Kiyotaka', 'Russia', 'mid',
     21, 72, 74, 64, 7, 272, 5000,  80, 30, 7, 8, 6, 80, 82, 74),

    # qojqva (Vitaly Vorobei, Russia, carry, born 2001 → 24)
    # Known EEU T2 carry
    ('Vitaly', 'Vorobei',    'qojqva',   'Russia',    'carry',
     24, 78, 72, 62, 7, 262, 6000, 160, 30, 7, 6, 6, 86, 80, 72),

    # ultra (Maxim Dorofeyev, Russia, mid, born 2001 → 24)
    # EEU T2 mid, multiple regional teams
    ('Maxim', 'Dorofeyev',   'ultra',    'Russia',    'mid',
     24, 74, 76, 66, 7, 265, 5500, 120, 30, 7, 6, 6, 82, 84, 76),

    # 3BLACK (Anton Blinov, Russia, mid, born 2003 → 22) EEU T3
    ('Anton', 'Blinov',      '3BLACK',   'Russia',    'mid',
     22, 70, 72, 64, 6, 260, 4500,  80, 30, 7, 7, 6, 78, 80, 74),

    # Kataomi (Denis Kataomi, Russia, partial_support, born 2002 → 23) EEU T3
    ('Denis', 'Kataomi',     'Kataomi',  'Russia',    'partial_support',
     23, 68, 72, 70, 6, 256, 4500,  80, 30, 7, 7, 6, 76, 80, 78),

    # ── EU T2/T3 ─────────────────────────────────────────────────────────────
    # Nine (Nils Sjögren, Austria, mid, born 2001 → 24)
    # Played Nigma/Gaimin era, active EU T2
    ('Nils', 'Sjogren',      'Nine',     'Austria',   'mid',
     24, 80, 78, 68, 7, 272, 6500, 160, 30, 7, 6, 6, 88, 86, 78),

    # Skitter (Dmytro Skiter, Ukraine, carry, born 2000 → 25)
    # Consistent EU T2 carry
    ('Dmytro', 'Skiter',     'Skitter',  'Ukraine',   'carry',
     25, 82, 76, 64, 7, 265, 6500, 180, 30, 7, 6, 6, 90, 84, 74),

    # Cure (Marcus Brock Friis, Denmark, full_support, born 2000 → 25)
    # EU T2 support
    ('Marcus', 'Brock Friis', 'Cure',    'Denmark',   'full_support',
     25, 68, 72, 78, 7, 252, 5000, 160, 31, 8, 5, 6, 76, 80, 86),

    # m1CKE (Michael Vu, Denmark, carry, born 2005 → 20) [youth]
    # Hyped young EU carry, high ceiling
    ('Michael', 'Vu',        'm1CKE',    'Denmark',   'carry',
     20, 74, 70, 62, 6, 285, 4000,  40, 31, 6, 9, 6, 82, 78, 72),

    # ── SA T2/T3 ─────────────────────────────────────────────────────────────
    # Alan (Alan Lima, Brazil, partial_support, born 2002 → 23)
    # SA T2 support, played BetBoom / SA regional
    ('Alan', 'Lima',         'Alan',     'Brazil',    'partial_support',
     23, 68, 70, 72, 6, 256, 4500, 100, 30, 7, 7, 6, 76, 78, 80),

    # Scofield (Matheus Scofield, Brazil, offlane, born 2001 → 24)
    # SA T2 offlaner
    ('Matheus', 'Scofield',  'Scofield', 'Brazil',    'offlane',
     24, 72, 70, 66, 6, 258, 5000, 120, 30, 7, 6, 6, 80, 78, 74),

    # Lopsy (Lorenzo Gamboa, Peru, full_support, born 2003 → 22)
    # SA T2/T3 support, Thunder Awaken region
    ('Lorenzo', 'Gamboa',    'Lopsy',    'Peru',      'full_support',
     22, 64, 68, 74, 6, 252, 4000,  80, 30, 7, 7, 6, 72, 76, 82),

    # Stinger (Martin Ruiz, Argentina, carry, born 2003 → 22) SA T3
    ('Martin', 'Ruiz',       'Stinger',  'Argentina', 'carry',
     22, 68, 66, 62, 6, 255, 4000,  60, 30, 7, 7, 6, 76, 74, 70),

    # ── SEA T2/T3 ────────────────────────────────────────────────────────────
    # Neon (Carlo Olarita, Philippines, mid, born 2001 → 24)
    # Active SEA T2, multiple TNC/Execration-era teams
    ('Carlo', 'Olarita',     'Neon',     'Philippines','mid',
     24, 74, 72, 66, 6, 260, 5000, 120, 30, 7, 6, 6, 82, 80, 74),

    # Jabz (Nuengnara Teeramahanon, Thailand, partial_support, born 2000 → 25)
    # SEA T2 roaming support
    ('Nuengnara', 'Teeramahanon', 'Jabz', 'Thailand', 'partial_support',
     25, 68, 72, 76, 7, 256, 5000, 140, 30, 8, 5, 6, 76, 80, 84),

    # Yowe (Philippines, full_support, born 2003 → 22) SEA T3
    ('Josue', 'Dela Cruz',   'Yowe',     'Philippines','full_support',
     22, 64, 66, 72, 5, 248, 3500,  60, 30, 7, 7, 5, 72, 74, 80),

    # ── CN T2/T3 ─────────────────────────────────────────────────────────────
    # Sansheng (Wang Zhaohui, China, partial_support, born 2000 → 25)
    # Veteran CN T2 roaming support
    ('Wang', 'Zhaohui',      'Sansheng', 'China',     'partial_support',
     25, 72, 78, 76, 7, 258, 5500, 160, 30, 8, 5, 6, 80, 86, 84),

    # Lio (Li Yisong, China, mid, born 2003 → 22) CN T2/T3
    ('Li', 'Yisong',         'Lio',      'China',     'mid',
     22, 74, 74, 64, 7, 268, 5000,  80, 30, 7, 7, 6, 82, 82, 74),

    # RQ (Ren Qiu, China, carry, born 2003 → 22) CN T3
    ('Ren', 'Qiu',           'RQ',       'China',     'carry',
     22, 72, 70, 62, 6, 260, 4500,  80, 30, 7, 7, 6, 80, 78, 70),
]

# Players with is_youth=1 (born 2004+, age ≤ 21 in 2025)
_YOUTH_NICKS = {'Kiyotaka', 'm1CKE'}


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    if c.execute("SELECT 1 FROM _migrations WHERE name='migrate19'").fetchone():
        conn.close(); return

    c.execute("SELECT MAX(id) FROM players")
    next_id = (c.fetchone()[0] or 490) + 1

    added = 0
    for i, p in enumerate(_PLAYERS):
        (name, surname, nick, country, role,
         age, micro, macro, soft, comp,
         skill_cap, exp_wage, comp_exp,
         ret_age, stab, lr, morale,
         mc, xc, sc) = p

        if c.execute("SELECT id FROM players WHERE nickname=?", (nick,)).fetchone():
            continue

        pid = next_id + added
        c.execute("""
            INSERT INTO players
              (id, name, surname, nickname, country, role, team_id,
               micro_skills, macro_skills, soft_skills, skill_cap,
               competence, morale, wage, expected_wage, age, retirement_age,
               stability, learning_rate, fame, comp_exp,
               micro_cap, macro_cap, soft_cap, is_youth)
            VALUES (?,?,?,?,?,?,0, ?,?,?,?, ?,?,0,?,?,?, ?,?,30,?, ?,?,?,?)
        """, (pid, name, surname, nick, country, role,
              micro, macro, soft, skill_cap,
              comp, morale, exp_wage, age, ret_age,
              stab, lr, comp_exp, mc, xc, sc,
              1 if nick in _YOUTH_NICKS else 0))
        added += 1

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate19')")
    conn.commit()
    conn.close()
    print(f"[migrate19] added {added} young T2/T3 players to {db_name}")


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
