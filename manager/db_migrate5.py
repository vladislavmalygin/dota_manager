"""
Migration 5: Create tier-2 teams and assign players added in migrate4.
Teams: Nemiga Gaming, PARIVISION, MOUZ, Zero Tenacity,
       1w Team, L1GA TEAM, VP.Prodigy, REKONIX
"""
import sqlite3

# (id, name, country, budget, rating)
_TEAMS = [
    (41, 'Nemiga Gaming',  'Belarus',   350_000, 550),
    (42, 'PARIVISION',     'Russia',    400_000, 650),
    (43, 'MOUZ',           'Germany',   500_000, 700),
    (44, 'Zero Tenacity',  'Europe',    350_000, 550),
    (45, '1w Team',        'Russia',    250_000, 420),
    (46, 'L1GA TEAM',      'Russia',    280_000, 480),
    (47, 'VP.Prodigy',     'Russia',    300_000, 500),
    (48, 'REKONIX',        'Indonesia', 200_000, 380),
]

# Roster: team_id → (carry, mid, offlane, partial_support, full_support)
# None = empty slot.  Player IDs from migrate4 + existing DB players.
_ROSTERS = {
    41: (337, 338, 339, 340, 341),   # Nemiga: selfhate/young G/Covisnine/hwoarang/VaniLLl
    42: (333, 334, 335,  35, 336),   # PARIVISION: Satanic/No[o]ne-/SSS/9class/Dukalis
    43: (229, 342, 343, 344, None),  # MOUZ: Crystallis/MidOne/BOOM/yamich/—
    44: (345, 346, 347, 348, None),  # Zero Tenacity: dream`/Worick/nefrit/dEsire/—
    45: (349, 350, 351, 352, 353),   # 1w Team: v1olent/squad1x/Mr.Moral/swedenstrong/Rein
    46: (None, 354, 355, 356, 357),  # L1GA TEAM: —/Mirage`/Vazya/sayuw/RESPECT
    47: (358, None, 359, 360, 361),  # VP.Prodigy: cutie/—/takizawa/raregods/JANTER
    48: (364, 365, None, 366, 367),  # REKONIX: Jikroy/inYourdreaM/—/dalul/Varizh
}

# Wages for assigned players: player_id → wage
_WAGES = {
    # Nemiga
    337: 8_000, 338: 7_000, 339: 6_500, 340: 6_000, 341: 5_500,
    # PARIVISION
    333: 8_500, 334: 11_000, 335: 7_000, 35: 6_500, 336: 6_000,
    # MOUZ
    229: 9_000, 342: 11_000, 343: 8_500, 344: 6_500,
    # Zero Tenacity
    345: 7_500, 346: 7_000, 347: 6_000, 348: 5_500,
    # 1w Team
    349: 5_500, 350: 5_500, 351: 5_000, 352: 5_000, 353: 5_000,
    # L1GA TEAM
    354: 6_000, 355: 5_500, 356: 5_000, 357: 4_500,
    # VP.Prodigy
    358: 6_000, 359: 5_500, 360: 5_000, 361: 5_000,
    # REKONIX
    364: 4_000, 365: 4_000, 366: 3_500, 367: 3_500,
}

_ROLES = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Idempotency: skip if already applied
    c.execute("SELECT COUNT(*) FROM teams WHERE name='Nemiga Gaming'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    # Fix Crystallis role (was 'partial_support' in old data, should be 'carry')
    c.execute("UPDATE players SET role='carry' WHERE id=229")

    for team_id, name, country, budget, rating in _TEAMS:
        roster = _ROSTERS[team_id]
        carry, mid, offlane, ps, fs = roster
        c.execute("""
            INSERT OR IGNORE INTO teams
              (id, name, country, budget, rating, player,
               carry, mid, offlane, partial_support, full_support,
               cohesion)
            VALUES (?,?,?,?,?,'no',?,?,?,?,?,0)
        """, (team_id, name, country, budget, rating, carry, mid, offlane, ps, fs))

        # Assign players to this team
        for pid in roster:
            if pid is None:
                continue
            wage = _WAGES.get(pid, 5_000)
            c.execute(
                "UPDATE players SET team_id=?, wage=? WHERE id=? AND team_id=0",
                (team_id, wage, pid),
            )

    conn.commit()
    conn.close()
    print(f"[migrate5] Tier-2 teams created in {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate5] Error on {db}: {e}")
