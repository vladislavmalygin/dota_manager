"""
Roster update — early 2026 season.
Updates T1 team rosters from Liquipedia, releases disbanded-team players.
"""

import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    # Idempotency check: if 'rue' already exists as a player, migration was applied
    c.execute("SELECT COUNT(*) FROM players WHERE nickname='rue' AND name='Alexandr'")
    if c.fetchone()[0] > 0:
        conn.close()
        return
    conn.close()
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # ── 1. Fix player names / countries ──────────────────────────────────────

    fixes = [
        # (id,  field,        value)
        (2,   'surname',     'Sigitov'),          # Larl
        (4,   'name',        'Myroslav'),         # Mira (Ukrainian)
        (13,  'nickname',    'Malr1ne'),
        (15,  'nickname',    'Cr1t-'),
        (17,  'nickname',    'miCKe'),
        (18,  'nickname',    'Nisha'),
        (18,  'name',        'Michal'),
        (37,  'surname',     'Grigorenko'),        # Nightfall
        (40,  'name',        'Vitalie'),           # Save- (Moldovan)
        (40,  'country',     'Moldova'),
        (60,  'name',        'Rafli'),             # Mikoto
        (61,  'name',        'Chung'),             # Ws
        (89,  'name',        'Abed'),              # Abed (just first name)
        (89,  'surname',     'Yusop'),
        (129, 'name',        'Xu'),                # fy
        (129, 'surname',     'Linsen'),
        (138, 'name',        'Erin'),              # Yopaj
        (138, 'surname',     'Ferrer'),
        (140, 'name',        'Timothy'),           # TIMS
        (140, 'surname',     'Randrup'),
        (140, 'nickname',    'TIMS'),
        (41,  'role',        'offlane'),           # TORONTOTOKYO → offlane at OG
    ]
    for pid, field, val in fixes:
        c.execute(f"UPDATE players SET {field}=? WHERE id=?", (val, pid))

    # ── 2. Release disbanded-team players to FA ──────────────────────────────
    # Compute expected_wage = max(avg_skill*180, current_wage*0.85)

    def release_to_fa(player_ids):
        for pid in player_ids:
            c.execute(
                "SELECT micro_skills, macro_skills, wage FROM players WHERE id=?", (pid,)
            )
            row = c.fetchone()
            if not row:
                continue
            micro, macro, wage = (v or 0 for v in row)
            avg = (micro + macro) // 2
            exp = max(avg * 180, int(wage * 0.85))
            c.execute(
                "UPDATE players SET team_id=0, wage=0, expected_wage=? WHERE id=?",
                (exp, pid),
            )

    # --- Gaming Gladiators (id=5, ex-Gaimin players) ---
    # Watson/Quinn/Seleri → FA; Ace/tOfu → moved to Liquid
    release_to_fa([23, 26, 27])  # Quinn, Seleri, Watson
    c.execute("UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,partial_support=NULL,full_support=NULL WHERE id=5")

    # --- Gaimin Gladiators (id=18) ---
    release_to_fa([105])  # Lantti
    c.execute("UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,partial_support=NULL,full_support=NULL WHERE id=18")

    # --- 9Pandas (id=20) ---
    release_to_fa([112])  # Ar1se (others already FA)
    c.execute("UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,partial_support=NULL,full_support=NULL WHERE id=20")

    # --- Team Secret (id=22) — on hiatus ---
    release_to_fa([122, 123, 124, 125])  # YapzOr, matumbaman, Zai, puppey (Nikki 121 already FA)
    c.execute("UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,partial_support=NULL,full_support=NULL WHERE id=22")

    # --- PSG.LGD (id=23) — disbanded ---
    release_to_fa([126, 127, 128, 130])  # Shiro, Chalice, LaNm, Inflame  (fy→XG)
    c.execute("UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,partial_support=NULL,full_support=NULL WHERE id=23")

    # --- BOOM Esports (id=25) — disbanded ---
    release_to_fa([136, 137, 139])  # Fbz, Hyde, Uno  (Yopaj/TIMS→OG)
    c.execute("UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,partial_support=NULL,full_support=NULL WHERE id=25")

    # --- Talon Esports (id=12) — disbanded ---
    release_to_fa([57, 59, 91])  # jhocam, Akashi, Kuku  (Mikoto/Ws→Aurora)
    c.execute("UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,partial_support=NULL,full_support=NULL WHERE id=12")

    # --- BetBoom Team duplicate (id=19) — old roster entry ---
    release_to_fa([110])  # RodjER
    c.execute("UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,partial_support=NULL,full_support=NULL WHERE id=19")

    # ── 3. Release displaced T1 players ──────────────────────────────────────

    # Spirit: Miposhka → FA (rue/panto will fill)
    release_to_fa([5])   # Miposhka

    # Tundra: lorenof, durachyo → FA  (Nightfall→Aurora, Pure→Tundra)
    release_to_fa([65, 22])  # lorenof, durachyo

    # Liquid: Insania → FA  (SaberLight→VP, Ace/tOfu coming in)
    release_to_fa([21])  # Insania

    # XG: Xm, Xinq, Dy → FA  (NothingToSay/fy/xNova coming in)
    release_to_fa([7, 9, 10])  # Xm, Xinq, Dy

    # Aurora: TA2000, Jabz, Q → FA  (Nightfall/Mikoto/Ws/Mira coming in)
    release_to_fa([88, 66, 63])  # TA2000, Jabz, Q

    # OG: ana, Topson, Ceb, JerAx, N0tail → FA
    release_to_fa([96, 97, 98, 99, 100])

    # Nigma: Miracle-, w33, MC, KuroKy → FA  (GH stays, No!ob/OmaR coming in)
    release_to_fa([116, 117, 118, 120])

    # VP: full old roster → FA
    release_to_fa([131, 132, 133, 134, 135])  # Massacre, SoNNeikO, Daxak, God, Immersion

    # ── 4. Move existing players to new teams ────────────────────────────────

    def move_player(pid, new_team_id, new_role, new_wage):
        c.execute(
            "UPDATE players SET team_id=?, role=?, wage=? WHERE id=?",
            (new_team_id, new_role, new_wage, pid),
        )

    CONTRACT_2028 = '2028-01-01'

    # Mira (id=4): Spirit pos4 → Aurora pos4
    move_player(4, 13, 'partial_support', 10000)
    c.execute("UPDATE players SET contract_end=? WHERE id=4", (CONTRACT_2028,))

    # Pure (id=32): BB Team pos1 → Tundra pos1
    move_player(32, 7, 'carry', 9000)
    c.execute("UPDATE players SET contract_end=? WHERE id=32", (CONTRACT_2028,))

    # Nightfall (id=37): Tundra pos1 → Aurora pos1
    move_player(37, 13, 'carry', 10000)
    c.execute("UPDATE players SET contract_end=? WHERE id=37", (CONTRACT_2028,))

    # Mikoto (id=60): Talon pos2 → Aurora pos2
    move_player(60, 13, 'mid', 9000)
    c.execute("UPDATE players SET contract_end=? WHERE id=60", (CONTRACT_2028,))

    # Ws (id=61): Talon pos3 → Aurora pos3
    move_player(61, 13, 'offlane', 7000)
    c.execute("UPDATE players SET contract_end=? WHERE id=61", (CONTRACT_2028,))

    # Ace (id=24): GG pos3 → Liquid pos3
    move_player(24, 4, 'offlane', 10000)
    c.execute("UPDATE players SET contract_end=? WHERE id=24", (CONTRACT_2028,))

    # tOfu (id=25): GG pos4 → Liquid pos5
    move_player(25, 4, 'full_support', 9000)
    c.execute("UPDATE players SET contract_end=? WHERE id=25", (CONTRACT_2028,))

    # SaberLight (id=87): Liquid pos3 → VP pos3
    move_player(87, 24, 'offlane', 9000)
    c.execute("UPDATE players SET contract_end=? WHERE id=87", (CONTRACT_2028,))

    # Abed (id=89): Aurora pos2 → VP pos2
    move_player(89, 24, 'mid', 14000)
    c.execute("UPDATE players SET contract_end=? WHERE id=89", (CONTRACT_2028,))

    # fy (id=129): PSG.LGD pos5 → XG pos4 (role change)
    move_player(129, 2, 'partial_support', 11000)
    c.execute("UPDATE players SET contract_end=? WHERE id=129", (CONTRACT_2028,))

    # Yopaj (id=138): BOOM pos3 → OG pos2 (role change)
    move_player(138, 17, 'mid', 9000)
    c.execute("UPDATE players SET contract_end=? WHERE id=138", (CONTRACT_2028,))

    # TIMS (id=140): BOOM pos5 → OG pos4 (role change)
    move_player(140, 17, 'partial_support', 8000)
    c.execute("UPDATE players SET contract_end=? WHERE id=140", (CONTRACT_2028,))

    # GH (id=119): Nigma pos4 → Nigma pos5 (role change)
    move_player(119, 21, 'full_support', 10000)
    c.execute("UPDATE players SET contract_end=? WHERE id=119", (CONTRACT_2028,))

    # Fly (id=67): nouns pos5 → VP pos5
    move_player(67, 24, 'full_support', 9000)
    c.execute("UPDATE players SET contract_end=? WHERE id=67", (CONTRACT_2028,))

    # skem (id=175): Execration pos5 → OG pos5
    move_player(175, 17, 'full_support', 9000)
    c.execute("UPDATE players SET contract_end=? WHERE id=175", (CONTRACT_2028,))

    # TORONTOTOKYO (id=41): FA → OG pos3
    move_player(41, 17, 'offlane', 10000)
    c.execute("UPDATE players SET contract_end=? WHERE id=41", (CONTRACT_2028,))

    # Keep Boxi at Liquid (stays)
    c.execute("UPDATE players SET contract_end=? WHERE id=20", (CONTRACT_2028,))
    # Keep gpk, Miero, Save-, Kataomi at BB Team
    for pid in [38, 39, 40, 30]:
        c.execute("UPDATE players SET contract_end=? WHERE id=?", (CONTRACT_2028, pid))
    # Keep 33, Whitemon at Tundra
    for pid in [19, 36]:
        c.execute("UPDATE players SET contract_end=? WHERE id=?", (CONTRACT_2028, pid))
    # Keep kaori at Aurora
    c.execute("UPDATE players SET contract_end=? WHERE id=90", (CONTRACT_2028,))

    # ── 5. Create new players ──────────────────────────────────────────────────

    def new_player(nickname, name, surname, country, role, team_id,
                   micro, macro, soft, skill_cap, competence, wage):
        c.execute("""
            INSERT INTO players
              (nickname, name, surname, country, role, team_id,
               micro_skills, macro_skills, soft_skills, skill_cap,
               competence, morale, wage, expected_wage, contract_end,
               fame, character)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,6,?,?,?,55,'balanced')
        """, (nickname, name, surname, country, role, team_id,
              micro, macro, soft, skill_cap, competence,
              wage, wage, CONTRACT_2028))
        return c.lastrowid

    # Team Spirit pos4/pos5 replacements
    rue_id   = new_player('rue',   'Alexandr', 'Filin',    'Russia',  'partial_support', 1, 72, 70, 68, 220, 7, 12000)
    panto_id = new_player('panto', 'Nikita',   'Balaganin','Belarus', 'full_support',    1, 68, 66, 70, 200, 6, 10000)

    # Xtreme Gaming
    nts_id   = new_player('NothingToSay', 'Cheng', 'Jinxiang', 'Malaysia', 'mid',          2, 85, 82, 72, 255, 8, 13000)
    xnova_id = new_player('xNova',        'Yap',   'Jianwei',  'Malaysia', 'full_support', 2, 72, 74, 75, 225, 7, 10000)

    # Tundra
    bzm_id = new_player('bzm', 'Bozhidar', 'Bogdanov', 'Bulgaria',      'mid',          7, 85, 82, 72, 250, 8, 12000)
    ari_id = new_player('Ari', 'Matthew',  'Walker',   'United Kingdom','partial_support',7, 68, 72, 75, 215, 6, 10000)

    # BetBoom
    kiritych_id = new_player('Kiritych', 'Ilya',  'Ulyanov',  'Russia', 'carry', 8, 78, 74, 68, 230, 7, 11000)

    # Virtus.pro
    timado_id    = new_player('Timado',    'Enzo',   'Gianoli',  'Peru',    'carry',          24, 86, 80, 70, 250, 8, 13000)
    hellscream_id= new_player('Hellscream','Kirill', 'Lagutik',  'Belarus', 'partial_support',24, 70, 74, 76, 220, 6, 10000)

    # OG carry
    natsumi_id = new_player('Natsumi', 'John Anthony', 'Vargas', 'Philippines', 'carry', 17, 82, 76, 68, 240, 7, 11000)

    # Nigma Galaxy
    noob_id = new_player('No!ob', 'Tony',  'Assaf',    'Lebanon', 'offlane',        21, 72, 70, 68, 210, 6, 8000)
    omar_id = new_player('OmaR',  'Omar',  'Moughrabi','Lebanon', 'partial_support',21, 65, 68, 72, 205, 5, 7000)

    # ── 6. Rebuild team slot assignments ─────────────────────────────────────

    # Team Spirit (id=1): Yatoro/Larl/Collapse/rue/panto
    c.execute("UPDATE teams SET partial_support=?, full_support=? WHERE id=1",
              (rue_id, panto_id))

    # Xtreme Gaming (id=2): Ame/NothingToSay/Xxs/fy/xNova
    c.execute("UPDATE teams SET mid=?, partial_support=?, full_support=? WHERE id=2",
              (nts_id, 129, xnova_id))   # fy=129

    # Team Falcons (id=3): skiter/Malr1ne/ATF/Cr1t-/Sneyking (no slot changes)

    # Team Liquid (id=4): miCKe/Nisha/Ace/Boxi/tOfu
    c.execute("UPDATE teams SET offlane=?, full_support=? WHERE id=4",
              (24, 25))   # Ace=24, tOfu=25

    # Tundra (id=7): Pure/bzm/33/Ari/Whitemon
    c.execute("UPDATE teams SET carry=?, mid=?, partial_support=? WHERE id=7",
              (32, bzm_id, ari_id))   # Pure=32

    # BetBoom (id=8): Kiritych/gpk/Miero/Save-/Kataomi
    c.execute("UPDATE teams SET carry=? WHERE id=8", (kiritych_id,))

    # Aurora (id=13): Nightfall/Mikoto/Ws/Mira/kaori
    c.execute("""UPDATE teams SET carry=?, mid=?, offlane=?, partial_support=?, full_support=?
                 WHERE id=13""", (37, 60, 61, 4, 90))

    # OG (id=17): Natsumi/Yopaj/TORONTOTOKYO/TIMS/skem
    c.execute("""UPDATE teams SET carry=?, mid=?, offlane=?, partial_support=?, full_support=?
                 WHERE id=17""", (natsumi_id, 138, 41, 140, 175))

    # Nigma Galaxy (id=21): [empty]/[empty]/No!ob/OmaR/GH
    c.execute("""UPDATE teams SET carry=NULL, mid=NULL, offlane=?, partial_support=?, full_support=?
                 WHERE id=21""", (noob_id, omar_id, 119))

    # Virtus.pro (id=24): Timado/Abed/SaberLight/Hellscream/Fly
    c.execute("""UPDATE teams SET carry=?, mid=?, offlane=?, partial_support=?, full_support=?
                 WHERE id=24""", (timado_id, 89, 87, hellscream_id, 67))

    # nouns (id=14): Fly moved to VP → clear full_support slot
    c.execute("UPDATE teams SET full_support=NULL WHERE id=14")

    # Execration (id=32): skem moved to OG → clear full_support slot
    c.execute("UPDATE teams SET full_support=NULL WHERE id=32")

    # ── 7. Fix inconsistent team_id on orphaned players ──────────────────────
    # Players with team_id=0 but referenced in a team slot need cleanup
    # (We already handled the ones we moved; just ensure old Spirit/Tundra/etc slots cleared)

    # Spirit: Mira slot was partial_support; now rue. Old partial_support player cleared:
    c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=4 AND team_id=1")  # safety

    # Actually Mira (id=4) should now have team_id=13 (Aurora) — set above. Verify:
    # (migration already set it via move_player)

    conn.commit()
    conn.close()
    print(f"[migrate3] Roster update applied to {db_name}")


if __name__ == '__main__':
    import sys
    dbs = sys.argv[1:] or ['start_database.db', 'saves/asd_asd.db']
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate3] Error on {db}: {e}")
