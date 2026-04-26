"""
Roster migration: post-TI13 2024 (October 2024)
Updates all save files and start_database.db.
Sources: Liquipedia
"""
import sqlite3
import os

DB_FILES = [
    os.path.join(os.path.dirname(__file__), 'start_database.db'),
    os.path.join(os.path.dirname(__file__), 'saves', 'asd_asd.db'),
    os.path.join(os.path.dirname(__file__), 'saves', 'adasd_dassd.db'),
    os.path.join(os.path.dirname(__file__), 'saves', 'yggti_uikuik.db'),
]

# New players to INSERT (team_id will be set after insert)
# (name, surname, nickname, country, fame, micro, macro, soft, skill_cap, wage, expected_wage, role, other_role, competence, morale, time_in_team, team_placeholder)
NEW_PLAYERS = [
    # SaberLight – Team Liquid offlane
    ('Jonáš', 'Volek', 'SaberLight', 'Czech Republic', 55,  80, 78, 72, 235, 8000, 10000, 'offlane', None,         7, 7, 1, 'Team Liquid'),
    # TA2000 – Aurora carry
    ('Aybek', 'Tokayev', 'TA2000',    'Kazakhstan',    50,  76, 68, 65, 210, 7000,  8000, 'carry',   None,         6, 7, 1, 'Aurora'),
    # Abed – Aurora mid
    ('Abed Azel', 'Yusop', 'Abed',   'Philippines',   80,  92, 82, 74, 270, 12000, 15000, 'mid',     'carry',     9, 8, 1, 'Aurora'),
    # kaori – Aurora full_support
    ('Oleh', 'Medvedok', 'kaori',     'Ukraine',       45,  75, 70, 72, 215, 7000,  8000, 'full_support', None,   7, 7, 1, 'Aurora'),
    # Kuku – Talon full_support
    ('Carlo', 'Palad', 'Kuku',        'Philippines',   75,  78, 72, 82, 230, 7000,  8000, 'full_support', None,   8, 8, 1, 'Talon Esports'),
    # Parker – Heroic carry
    ('David', 'Nicho Flores', 'Parker', 'Peru',        45,  73, 66, 65, 200, 5000,  6000, 'carry',   None,         6, 7, 1, 'Heroic'),
    # bzm – free agent (OG mid)
    ('Bogdan', 'Lesiuk', 'bzm',       'Ukraine',       65,  88, 75, 70, 245, 0,    10000, 'mid',     None,         8, 6, 1, None),
    # Faith_bian – free agent (Azure Ray offlane)
    ('', 'faith_bian', 'Faith_bian',  'China',         60,  85, 78, 70, 240, 0,    10000, 'offlane', None,         8, 7, 1, None),
    # Kiritych – free agent (BetBoom carry, unsigned after Pure returned)
    ('Ilya', 'Ulyanov', 'Kiritych',   'Russia',        50,  82, 72, 68, 225, 0,    9000,  'carry',   None,         7, 7, 1, None),
]


def migrate(db_path):
    if not os.path.exists(db_path):
        print(f"  SKIP (not found): {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # ── helper: team_id from name ────────────────────────────────────────
    def team_id(name):
        row = c.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

    # ─────────────────────────────────────────────────────────────────────
    # 1. Fix player name/nickname typos
    # ─────────────────────────────────────────────────────────────────────
    c.execute("UPDATE players SET nickname='Yatoro' WHERE nickname='Raddan'")
    c.execute("UPDATE players SET surname='Hongcheng' WHERE nickname='Xm' AND surname LIKE '%\n%'")
    c.execute("UPDATE players SET surname='Sagitov' WHERE nickname='Larl'")
    c.execute("UPDATE players SET name='Neta', surname='Shapira' WHERE nickname='33'")
    c.execute("UPDATE players SET name='Ammar', surname='Al-Assaf' WHERE nickname='ATF'")
    c.execute("UPDATE players SET name='Samuel', surname='Svahn' WHERE nickname='Boxi'")
    c.execute("UPDATE players SET name='Melchior', surname='Hillenkamp' WHERE nickname='Seleri'")
    c.execute("UPDATE players SET name='Michael', surname='Vu' WHERE nickname='Micke'")

    # ─────────────────────────────────────────────────────────────────────
    # 2. Cloud9 disbands – free all 5 players
    # ─────────────────────────────────────────────────────────────────────
    cid = team_id('Cloud 9')
    if cid:
        c.execute("UPDATE players SET team_id=0, wage=0 WHERE team_id=?", (cid,))
        c.execute("UPDATE teams SET carry=NULL, mid=NULL, offlane=NULL, partial_support=NULL, full_support=NULL WHERE id=?", (cid,))

    # ─────────────────────────────────────────────────────────────────────
    # 3. Team Zero disbands
    # ─────────────────────────────────────────────────────────────────────
    tzid = team_id('Team Zero')
    if tzid:
        c.execute("UPDATE players SET team_id=0, wage=0 WHERE team_id=?", (tzid,))
        c.execute("UPDATE teams SET carry=NULL, mid=NULL, offlane=NULL, partial_support=NULL, full_support=NULL WHERE id=?", (tzid,))

    # ─────────────────────────────────────────────────────────────────────
    # 4. G2 IG disbands
    # ─────────────────────────────────────────────────────────────────────
    g2id = team_id('G2 IG')
    if g2id:
        c.execute("UPDATE players SET team_id=0, wage=0 WHERE team_id=?", (g2id,))
        c.execute("UPDATE teams SET carry=NULL, mid=NULL, offlane=NULL, partial_support=NULL, full_support=NULL WHERE id=?", (g2id,))

    # ─────────────────────────────────────────────────────────────────────
    # 5. Xtreme Gaming – Dy retires
    # ─────────────────────────────────────────────────────────────────────
    xg = team_id('Xtreme Gaming')
    if xg:
        dy = c.execute("SELECT id FROM players WHERE nickname='Dy'").fetchone()
        if dy:
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (dy[0],))
            c.execute("UPDATE teams SET full_support=NULL WHERE id=?", (xg,))

    # ─────────────────────────────────────────────────────────────────────
    # 6. Gaming Gladiators – durachyo leaves, Watson joins (carry)
    # ─────────────────────────────────────────────────────────────────────
    gg = team_id('Gaming Gladiators')
    if gg:
        # Free durachyo from slot
        dur = c.execute("SELECT id FROM players WHERE nickname='durachyo'").fetchone()
        if dur:
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (dur[0],))
            c.execute("UPDATE teams SET carry=NULL WHERE id=?", (gg,))
        # Watson (Alimzhan Islambekov, ex-Cloud9) → carry
        watson = c.execute("SELECT id FROM players WHERE nickname='Watson'").fetchone()
        if watson:
            c.execute("UPDATE teams SET carry=? WHERE id=?", (watson[0], gg))
            c.execute("UPDATE players SET team_id=?, wage=7000, role='carry' WHERE id=?", (gg, watson[0]))

    # ─────────────────────────────────────────────────────────────────────
    # 7. Team Liquid – 33 leaves (→ Tundra), SaberLight joins later via INSERT
    # ─────────────────────────────────────────────────────────────────────
    tl = team_id('Team Liquid')
    if tl:
        p33 = c.execute("SELECT id FROM players WHERE nickname='33'").fetchone()
        if p33:
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (p33[0],))
            c.execute("UPDATE teams SET offlane=NULL WHERE id=?", (tl,))

    # ─────────────────────────────────────────────────────────────────────
    # 8. BetBoom – Nightfall leaves (→ Tundra), TORONTOTOKYO leaves,
    #              Pure returns (carry), Kataomi joins (full_support)
    # ─────────────────────────────────────────────────────────────────────
    bb = team_id('BB Team')
    if bb:
        nf = c.execute("SELECT id FROM players WHERE nickname='Nightfall'").fetchone()
        tt = c.execute("SELECT id FROM players WHERE nickname='TORONTOTOKYO'").fetchone()
        pure = c.execute("SELECT id FROM players WHERE nickname='Pure'").fetchone()
        kataomi = c.execute("SELECT id FROM players WHERE nickname='Kataomi'").fetchone()

        if nf:
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (nf[0],))
            c.execute("UPDATE teams SET carry=NULL WHERE id=?", (bb,))
        if tt:
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (tt[0],))
            c.execute("UPDATE teams SET full_support=NULL WHERE id=?", (bb,))
        if pure:
            c.execute("UPDATE teams SET carry=? WHERE id=?", (pure[0], bb))
            c.execute("UPDATE players SET team_id=?, wage=7000 WHERE id=?", (bb, pure[0]))
        if kataomi:
            c.execute("UPDATE teams SET full_support=? WHERE id=?", (kataomi[0], bb))
            c.execute("UPDATE players SET team_id=?, wage=6000, role='full_support' WHERE id=?", (bb, kataomi[0]))

    # ─────────────────────────────────────────────────────────────────────
    # 9. Tundra Esports – full rebuild
    #    IN:  Nightfall(carry), lorenof(mid/loan), 33(offlane), dyrachyo(pos4), Whitemon(pos5)
    #    OUT: Pure, Topson(retired), Ramzes666, 9class
    # ─────────────────────────────────────────────────────────────────────
    tu = team_id('Tundra Esports')
    if tu:
        # Free old core (Pure already reassigned to BB above)
        for nick in ('Topson', 'Ramzes666', '9class'):
            row = c.execute("SELECT id FROM players WHERE nickname=?", (nick,)).fetchone()
            if row:
                c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (row[0],))
        c.execute("UPDATE teams SET carry=NULL, mid=NULL, offlane=NULL, partial_support=NULL WHERE id=?", (tu,))

        # Fix Ramzes666 stored role (was 'carry', should be 'offlane')
        c.execute("UPDATE players SET role='offlane' WHERE nickname='Ramzes666'")

        # Assign new roster
        nf = c.execute("SELECT id FROM players WHERE nickname='Nightfall'").fetchone()
        lorenof = c.execute("SELECT id FROM players WHERE nickname='lorenof'").fetchone()
        p33 = c.execute("SELECT id FROM players WHERE nickname='33'").fetchone()
        dur = c.execute("SELECT id FROM players WHERE nickname='durachyo'").fetchone()

        if nf:
            c.execute("UPDATE teams SET carry=? WHERE id=?", (nf[0], tu))
            c.execute("UPDATE players SET team_id=?, wage=9000, role='carry' WHERE id=?", (tu, nf[0]))
        if lorenof:
            c.execute("UPDATE teams SET mid=? WHERE id=?", (lorenof[0], tu))
            c.execute("UPDATE players SET team_id=?, wage=7000 WHERE id=?", (tu, lorenof[0]))
        if p33:
            c.execute("UPDATE teams SET offlane=? WHERE id=?", (p33[0], tu))
            c.execute("UPDATE players SET team_id=?, wage=9000, role='offlane' WHERE id=?", (tu, p33[0]))
        if dur:
            c.execute("UPDATE teams SET partial_support=? WHERE id=?", (dur[0], tu))
            c.execute("UPDATE players SET team_id=?, wage=7000, role='partial_support' WHERE id=?", (tu, dur[0]))
        # Whitemon stays (just make sure team_id is correct)
        wm = c.execute("SELECT id FROM players WHERE nickname='Whitemon'").fetchone()
        if wm:
            c.execute("UPDATE players SET team_id=? WHERE id=?", (tu, wm[0]))

    # ─────────────────────────────────────────────────────────────────────
    # 10. Aurora – 64 & Oli out, lorenof goes to Tundra (handled above),
    #              Jabz stays, Q stays (fix role), new players via INSERT
    # ─────────────────────────────────────────────────────────────────────
    au = team_id('Aurora')
    if au:
        for nick in ('64', 'Oli'):
            row = c.execute("SELECT id FROM players WHERE nickname=? AND team_id=?", (nick, au)).fetchone()
            if row:
                c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (row[0],))
        c.execute("UPDATE teams SET carry=NULL, mid=NULL, full_support=NULL WHERE id=?", (au,))
        # lorenof slot also needs clearing (he moved to Tundra)
        c.execute("UPDATE teams SET mid=NULL WHERE id=?", (au,))
        # Fix Q role
        c.execute("UPDATE players SET role='partial_support' WHERE nickname='Q' AND team_id=?", (au,))
        # Fix Jabz slot (make sure partial stays correct)
        jabz = c.execute("SELECT id FROM players WHERE nickname='Jabz'").fetchone()
        q = c.execute("SELECT id FROM players WHERE nickname='Q'").fetchone()
        if jabz:
            c.execute("UPDATE teams SET offlane=? WHERE id=?", (jabz[0], au))
        if q:
            c.execute("UPDATE teams SET partial_support=? WHERE id=?", (q[0], au))

    # ─────────────────────────────────────────────────────────────────────
    # 11. Talon Esports – ponyo out, Kuku in via INSERT
    # ─────────────────────────────────────────────────────────────────────
    ta = team_id('Talon Esports')
    if ta:
        ponyo = c.execute("SELECT id FROM players WHERE nickname='ponyo'").fetchone()
        if ponyo:
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (ponyo[0],))
            c.execute("UPDATE teams SET full_support=NULL WHERE id=?", (ta,))

    # ─────────────────────────────────────────────────────────────────────
    # 12. Heroic – K1 retires, Parker in via INSERT
    # ─────────────────────────────────────────────────────────────────────
    he = team_id('Heroic')
    if he:
        k1 = c.execute("SELECT id FROM players WHERE nickname='K1'").fetchone()
        if k1:
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (k1[0],))
            c.execute("UPDATE teams SET carry=NULL WHERE id=?", (he,))

    # ─────────────────────────────────────────────────────────────────────
    # 13. INSERT new players
    # ─────────────────────────────────────────────────────────────────────
    for (name, surname, nick, country, fame,
         micro, macro, soft, skill_cap, wage, exp_wage,
         role, other_role, comp, morale, time_in, team_name) in NEW_PLAYERS:

        # Skip if nickname already in DB
        exists = c.execute("SELECT id FROM players WHERE nickname=?", (nick,)).fetchone()
        if exists:
            print(f"  SKIP existing: {nick}")
            continue

        tid = team_id(team_name) if team_name else 0

        c.execute("""
            INSERT INTO players
              (name, surname, nickname, country, fame,
               micro_skills, macro_skills, soft_skills, skill_cap,
               wage, expected_wage, role, other_role,
               competence, morale, time_in_team, team_id)
            VALUES (?,?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?,?)
        """, (name, surname, nick, country, fame,
              micro, macro, soft, skill_cap,
              wage, exp_wage, role, other_role,
              comp, morale, time_in, tid or 0))

        new_pid = c.lastrowid

        if tid:
            # Map role to team column
            role_col = role  # carry/mid/offlane/partial_support/full_support
            c.execute(f"UPDATE teams SET {role_col}=? WHERE id=?", (new_pid, tid))

    conn.commit()
    conn.close()
    print(f"  OK: {os.path.basename(db_path)}")


if __name__ == '__main__':
    for db in DB_FILES:
        print(f"Migrating {os.path.basename(db)} ...")
        migrate(db)
    print("Done.")
