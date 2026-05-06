"""
Migration 18: Add Tier 2/3 real players from Liquipedia + fill empty team rosters.

New players (IDs 441-465): Miracle-, KuroKy, Zai, YapzOr, iceiceice, S4,
Resolut1on, ALWAYSWANNAFLY, n0tail, Fata, Waga, JerAx, and others.

New team (id=53): Team Secret

Roster fills:
  Azure Ray (34), Entity (26), Evil Geniuses (38), Gamin Gladiators (5)
  Nigma mid (21), Aster carry (33), MOUZ FS (51), IVY (10)
"""
import sqlite3


# ---------------------------------------------------------------------------
# New player data: (name, surname, nickname, country, role,
#                  age, micro, macro, soft, competence,
#                  skill_cap, expected_wage, comp_exp,
#                  retirement_age, stability, learning_rate,
#                  morale, micro_cap, macro_cap, soft_cap)
# ---------------------------------------------------------------------------
_NEW_PLAYERS = [
    # 441  Miracle-  (Jordan, mid, born 1999-06-24 → 26 yrs)
    ('Amer', 'Al-Barkawi', 'Miracle-', 'Jordan', 'mid',
     26, 97, 91, 80, 10, 295, 18000, 320, 31, 7, 4, 8, 100, 100, 90),
    # 442  KuroKy  (Germany, full_support, born 1992-10-24 → 33 yrs)
    ('Sasan', 'Niknejad', 'KuroKy', 'Germany', 'full_support',
     33, 78, 88, 90, 9, 255, 9000, 450, 29, 9, 3, 7, 90, 96, 100),
    # 443  Zai  (Sweden, offlane, born 1996-05-20 → 29 yrs)
    ('Ludwig', 'Wåhlberg', 'Zai', 'Sweden', 'offlane',
     29, 88, 86, 80, 9, 270, 10000, 380, 31, 8, 4, 7, 96, 96, 90),
    # 444  YapzOr  (Jordan, partial_support, born 1996-06-24 → 29 yrs)
    ('Yazied', 'Jaradat', 'YapzOr', 'Jordan', 'partial_support',
     29, 84, 88, 84, 9, 268, 10000, 360, 31, 8, 4, 7, 94, 96, 94),
    # 445  iceiceice  (Singapore, offlane, born 1992-07-28 → 33 yrs)
    ('Daryl', 'Koh Pei Xiang', 'iceiceice', 'Singapore', 'offlane',
     33, 86, 82, 74, 8, 248, 7000, 500, 28, 7, 3, 6, 96, 90, 84),
    # 446  S4  (Sweden, offlane, born 1993-08-07 → 32 yrs)
    ('Gustav', 'Magnusson', 'S4', 'Sweden', 'offlane',
     32, 82, 84, 76, 8, 248, 6500, 480, 28, 8, 3, 6, 90, 92, 86),
    # 447  Resolut1on  (Ukraine, carry, born 1994-05-06 → 31 yrs)
    ('Roman', 'Fomynok', 'Resolut1on', 'Ukraine', 'carry',
     31, 90, 84, 68, 9, 262, 9000, 420, 29, 7, 3, 7, 98, 92, 78),
    # 448  ALWAYSWANNAFLY  (China, partial_support, born 1993-08-21 → 32 yrs)
    ('Wang', 'Zhuojun', 'ALWAYSWANNAFLY', 'China', 'partial_support',
     32, 80, 88, 84, 9, 254, 7000, 440, 28, 8, 3, 6, 88, 96, 92),
    # 449  n0tail  (Denmark, full_support, born 1993-04-02 → 33 yrs)
    ('Johan', 'Sundstein', 'n0tail', 'Denmark', 'full_support',
     33, 78, 86, 88, 9, 254, 7000, 460, 28, 9, 3, 7, 86, 94, 96),
    # 450  Fata  (Germany, carry, born 1995-11-06 → 30 yrs)
    ('Adrian', 'Trinks', 'Fata', 'Germany', 'carry',
     30, 86, 82, 70, 8, 254, 7000, 380, 30, 7, 3, 6, 94, 90, 80),
    # 451  Waga  (Belarus, mid, born 2002-01-15 → 24 yrs)
    ('Ilya', 'Ilyushin', 'Waga', 'Belarus', 'mid',
     24, 92, 86, 70, 8, 290, 9000, 180, 31, 8, 6, 7, 100, 96, 80),
    # 452  JerAx  (Finland, full_support, born 1995-01-21 → 31 yrs)
    ('Jesse', 'Vainikka', 'JerAx', 'Finland', 'full_support',
     31, 76, 88, 88, 9, 258, 7000, 400, 29, 9, 3, 7, 84, 96, 96),
    # 453  Raven  ← already in DB (id=376), skip — add Noxville instead? No.
    # Actually add Broodmother / Jackass … or better: add known Tier3 CIS:
    # 453  Stormstormer  (Russia, mid, born 2001 → 25 yrs)
    ('Mikhail', 'Abramov', 'Stormstormer', 'Russia', 'mid',
     25, 86, 82, 68, 7, 272, 6000, 140, 30, 7, 6, 6, 94, 90, 78),
    # 454  Raging Potato  (Philippines, offlane, born 1999 → 27 yrs)
    ('Karl', 'Baldovino Jr', 'Raging Potato', 'Philippines', 'offlane',
     27, 82, 80, 72, 7, 260, 5000, 200, 30, 7, 5, 6, 90, 88, 82),
    # 455  Hyde  already in DB id=405, skip — add another SEA:
    # 455  Natsumi* - already in DB, add instead: armel (already id=235)
    # Let's add: XSvamp (Sweden, carry, born 2003 → 23 yrs) - active EU Tier2
    ('Erik', 'Engström', 'XSvamp', 'Sweden', 'carry',
     23, 84, 80, 68, 7, 280, 5500, 80, 31, 8, 7, 6, 92, 88, 78),
    # 456  Raging* already done  ← change: add Daxak2 / Quinn2
    # Actually add: hyhy (SEA carry, Singapore, born 1993 → 33 yrs) - veteran
    ('Wong', 'Jeng Yih', 'hyhy', 'Singapore', 'carry',
     33, 82, 80, 70, 7, 240, 4000, 460, 28, 7, 3, 5, 90, 88, 80),
    # 457  Crit^ (Russia, mid, born 2004 → 22 yrs) — slight rename from crit^ id=402
    # crit^ is already in DB as id=402, skip. Add instead:
    # NetP (Russia, mid) or newer player:
    # Fishman2 → already in DB. Add Quinn2?
    # Add: Kpii2? Already id=200.
    # Add: PieLieDie (Sweden, full_support, born 1993 → 33 yrs) - famous support
    ('Kim', 'Lund Larsen', 'PieLieDie', 'Denmark', 'full_support',
     33, 72, 82, 86, 8, 242, 4000, 420, 28, 8, 3, 6, 80, 90, 94),
    # 458  Fear (Clinton Loomis, USA, carry, born 1988 → 38 yrs) - veteran/FA
    ('Clinton', 'Loomis', 'Fear', 'USA', 'carry',
     38, 74, 78, 72, 7, 230, 3500, 560, 27, 8, 2, 5, 82, 86, 82),
    # 459  Nofear (Ukraine, offlane, born 1994 → 31 yrs)
    ('Alexander', 'Zhuravel', 'Nofear', 'Ukraine', 'offlane',
     31, 80, 82, 72, 7, 248, 5000, 340, 29, 7, 3, 6, 88, 90, 82),
    # 460  Ryoya (Japan, mid, born 2002 → 24 yrs) — wait id=394 already
    # ryoya is id=394 already in DB. Skip. Add instead:
    # 460  Paparazi (China, carry, born 1995 → 30 yrs) - famous CN carry
    ('Li', 'Rui', 'Paparazi', 'China', 'carry',
     30, 88, 84, 68, 8, 256, 6000, 360, 29, 7, 3, 6, 96, 92, 78),
    # 461  Ah jit (Malaysia, mid, born 1996 → 29 yrs) - SEA tier2
    ('Lai', 'Jay Son', 'Ah jit', 'Malaysia', 'mid',
     29, 82, 80, 72, 7, 252, 5000, 260, 30, 7, 4, 6, 90, 88, 82),
    # 462  Abed (Philippines, mid) ← already id=89 on VP. Skip.
    # Add: LeBronDota (CIS hype player, Russia, mid, born 2005 → 21)
    ('Vladislav', 'Barinov', 'LeBronDota', 'Russia', 'mid',
     21, 82, 76, 64, 6, 285, 4000, 40, 30, 7, 8, 6, 90, 84, 74),
    # 463  Moo (Ben de la Cruz) ← already id=304 on nouns. Skip.
    # Add: Gunnar (already id=71 on nouns). Skip.
    # Add: Sneyking ← already id=16 Falcons. Skip.
    # Add: NetP (Romania, offlane, born 2001 → 25 yrs) - EU tier2
    ('Samuel', 'Schütz', 'NetP', 'Germany', 'offlane',
     25, 80, 78, 72, 7, 265, 5000, 120, 30, 7, 6, 6, 88, 86, 82),
    # 464  Mjz (China, full_support, born 2004 → 22 yrs) - CN young support
    ('Zhang', 'Yibin', 'Mjz', 'China', 'full_support',
     22, 74, 82, 82, 7, 276, 4500, 80, 30, 8, 7, 6, 82, 90, 90),
    # 465  Envy (Malaysia, partial_support, born 2002 → 24 yrs) - SEA
    ('Toh', 'Wai Hong', 'Envy', 'Malaysia', 'partial_support',
     24, 78, 80, 78, 7, 265, 4500, 100, 30, 7, 6, 6, 86, 88, 86),
]

# Roster fills: (team_id, carry, mid, offlane, partial_support, full_support)
# Use existing FA player IDs + new player IDs (441+)
_ROSTER_FILLS = {
    # Azure Ray (34) — Chinese team
    34: (52, 48, 208, 9, 207),   # Monet, 7e, eyyou, Xinq, y`
    # Entity (26) — EU/CIS team
    26: (22, 11, 29, 320, 31),   # dyrachyo, kiyotaka, DM, Alohadance, Fishman
    # Evil Geniuses (38) — NA
    38: (176, 72, 243, 395, 245),  # Arteezy, Sumail, Pakur, MSS, Snakechuck
    # Gamin Gladiators (5) — EU/CIS
    5:  (115, 117, 34, 111, 5),  # iLTW, w33, Ramzes666, Antares, Miposhka
    # Team IVY (10) — Chinese (carry=206 Super already set)
    10: (206, 94, 49, 448, 51),  # Super(keep), Faith_bian, Beyond, ALWAYSWANNAFLY(448), zzq
}

# Partial slot updates: (team_id, slot_name, player_id)
_SLOT_UPDATES = [
    (21, 'mid',          23),    # Nigma Galaxy — Quinn.GG as mid
    (33, 'carry',        47),    # Team Aster — Erika as carry
    (51, 'full_support', 316),   # MOUZ — Zayac as FS
    # Team Secret slots set via ROSTER_FILLS below for new team
]

# New team: Team Secret (id=53)
_NEW_TEAM = {
    'id': 53,
    'name': 'Team Secret',
    'country': 'Europe',
    'rating': 520.0,
    'region': 'WEU',
    'player': 'no',
    'carry':           447,   # Resolut1on (new id 447)
    'mid':             441,   # Miracle- (new id 441)
    'offlane':         443,   # Zai (new id 443)
    'partial_support': 444,   # YapzOr (new id 444)
    'full_support':    125,   # puppey (existing)
}


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    if c.execute("SELECT 1 FROM _migrations WHERE name='migrate18'").fetchone():
        conn.close(); return

    # 1. Insert new players
    c.execute("SELECT MAX(id) FROM players")
    next_id = (c.fetchone()[0] or 440) + 1

    player_ids = {}   # nickname → new id
    for i, p in enumerate(_NEW_PLAYERS):
        (name, surname, nick, country, role,
         age, micro, macro, soft, comp,
         skill_cap, exp_wage, comp_exp,
         ret_age, stab, lr, morale,
         mc, xc, sc) = p

        # Skip if nickname already in DB
        exists = c.execute("SELECT id FROM players WHERE nickname=?", (nick,)).fetchone()
        if exists:
            player_ids[nick] = exists[0]
            continue

        pid = next_id + i
        c.execute("""
            INSERT INTO players
              (id, name, surname, nickname, country, role, team_id,
               micro_skills, macro_skills, soft_skills, skill_cap,
               competence, morale, wage, expected_wage, age, retirement_age,
               stability, learning_rate, fame, comp_exp,
               micro_cap, macro_cap, soft_cap)
            VALUES (?,?,?,?,?,?,0, ?,?,?,?, ?,?,0,?,?,?,?,?,30,?, ?,?,?)
        """, (pid, name, surname, nick, country, role,
              micro, macro, soft, skill_cap,
              comp, morale, exp_wage, age, ret_age,
              stab, lr, comp_exp, mc, xc, sc))
        player_ids[nick] = pid

    # 2. Add new team (Team Secret)
    t = _NEW_TEAM
    exists = c.execute("SELECT id FROM teams WHERE id=?", (t['id'],)).fetchone()
    if not exists:
        c.execute("""
            INSERT INTO teams
              (id, name, country, rating, region, player,
               carry, mid, offlane, partial_support, full_support,
               budget, cohesion)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,200000,0)
        """, (t['id'], t['name'], t['country'], t['rating'], t['region'],
              t['player'],
              t['carry'], t['mid'], t['offlane'],
              t['partial_support'], t['full_support']))
        # Set team_id for Secret players
        for slot_pid in (t['carry'], t['mid'], t['offlane'],
                         t['partial_support'], t['full_support']):
            if slot_pid:
                c.execute("UPDATE players SET team_id=?, wage=expected_wage WHERE id=?",
                          (t['id'], slot_pid))

    # 3. Fill empty team rosters
    for team_id, carry, mid, off, ps, fs in [
        (v[0], *v[1:]) for v in
        [(tid, *slots) for tid, slots in _ROSTER_FILLS.items()]
    ]:
        # Only update NULL slots to avoid overwriting
        slots_map = {
            'carry': carry, 'mid': mid, 'offlane': off,
            'partial_support': ps, 'full_support': fs,
        }
        current = c.execute(
            "SELECT carry,mid,offlane,partial_support,full_support FROM teams WHERE id=?",
            (team_id,)
        ).fetchone()
        if not current:
            continue
        cols = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
        for col, wanted, existing in zip(cols, slots_map.values(), current):
            if existing is None and wanted is not None:
                c.execute(f"UPDATE teams SET {col}=? WHERE id=?", (wanted, team_id))
                c.execute("UPDATE players SET team_id=?, wage=MAX(wage,expected_wage) WHERE id=?",
                          (team_id, wanted))

    # 4. Partial slot fixes
    for team_id, col, pid in _SLOT_UPDATES:
        current_slot = c.execute(
            f"SELECT {col} FROM teams WHERE id=?", (team_id,)
        ).fetchone()
        if current_slot and current_slot[0] is None:
            c.execute(f"UPDATE teams SET {col}=? WHERE id=?", (pid, team_id))
            c.execute("UPDATE players SET team_id=?, wage=MAX(wage,expected_wage) WHERE id=?",
                      (team_id, pid))

    # 5. Set wages for roster players that have wage=0
    c.execute("""
        UPDATE players SET wage=expected_wage
        WHERE team_id != 0 AND (wage IS NULL OR wage = 0) AND expected_wage > 0
    """)

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate18')")
    conn.commit()
    conn.close()
    print(f"[migrate18] done {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate18] Error on {db}: {e}")
