"""
Migration 4: Add tier-2 free agents from 2026 tournaments.
Sources: Liquipedia — PARIVISION, Nemiga Gaming, MOUZ, Zero Tenacity,
         1w Team, L1GA TEAM, VP.Prodigy, HEROIC, REKONIX.
"""
import sqlite3

# (nickname, name, surname, country, role, micro, macro, soft, cap, competence, exp_wage)
_TIER2_PLAYERS = [
    # ── PARIVISION (CIS T2) ──────────────────────────────────────────────────
    ('Satanic',   'Alan',       'Gallyamov',   'Russia',  'carry',           75, 72, 68, 225, 7, 8_500),
    ('No[o]ne-',  'Volodymyr',  'Minenko',     'Ukraine', 'mid',             82, 80, 72, 242, 8, 11_000),
    ('SSS',       'Valery',     'Lazarev',     'Russia',  'offlane',         68, 70, 66, 215, 6, 7_000),
    ('9Class',    'Edgar',      'Naltakian',   'Russia',  'partial_support', 64, 68, 70, 210, 6, 6_500),
    ('Dukalis',   'Andrey',     'Kuropatkin',  'Russia',  'full_support',    62, 65, 72, 208, 5, 6_000),

    # ── Nemiga Gaming (CIS T2) ───────────────────────────────────────────────
    ('selfhate',  'Nikita',     'Ozhiganov',   'Russia',  'carry',           74, 70, 65, 222, 7, 8_000),
    ('young G',   'Nikita',     'Bochko',      'Belarus', 'mid',             68, 72, 65, 215, 6, 7_000),
    ('Covisnine', 'Nikita',     'Fedorov',     'Russia',  'offlane',         65, 67, 64, 210, 6, 6_500),
    ('hwoarang',  'Alexandr',   'Cernev',      'Moldova', 'partial_support', 62, 66, 68, 206, 5, 6_000),
    ('VaniLLl',   'Daniil',     'Sokolov',     'Russia',  'full_support',    60, 64, 70, 204, 5, 5_500),

    # ── MOUZ (EU T2) ─────────────────────────────────────────────────────────
    ('MidOne',    'Yeik Nai',   'Zheng',       'Malaysia','mid',             82, 84, 71, 238, 8, 11_000),
    ('BOOM',      'Miroslav',   'Bican',       'Czechia', 'offlane',         74, 77, 70, 228, 7, 8_500),
    ('yamich',    'Daniyal',    'Lazebnyy',    'Russia',  'partial_support', 64, 67, 68, 210, 6, 6_500),

    # ── Zero Tenacity (EU/CIS T2) ────────────────────────────────────────────
    ('dream`',    'Kyial',      'Tayirov',     'Kyrgyzstan','carry',         72, 70, 65, 218, 6, 7_500),
    ('Worick',    'Vitaliy',    'Brezgin',     'Russia',  'mid',             68, 70, 63, 213, 6, 7_000),
    ('nefrit',    'Dmitry',     'Tarasich',    'Ukraine', 'offlane',         64, 67, 63, 208, 5, 6_000),
    ('dEsire',    'Athanasios', 'Kartsabas',   'Greece',  'partial_support', 62, 65, 68, 205, 5, 5_500),

    # ── 1w Team (CIS T2/T3) ──────────────────────────────────────────────────
    ('v1olent',      'Alexander', 'Pak',          'Kazakhstan','carry',        64, 60, 58, 200, 5, 5_500),
    ('squad1x',      'Ilya',      'Kuvaldin',     'Russia',    'mid',          62, 65, 60, 200, 5, 5_500),
    ('Mr.Moral',     'Ivan',      'Ilichev',      'Russia',    'offlane',      60, 63, 60, 198, 5, 5_000),
    ('swedenstrong', 'Georgii',   'Zainalabidov', 'Russia',    'partial_support',60,62,65,198, 5, 5_000),
    ('Rein',         'Vladislav', 'Kosygin',      'Russia',    'full_support', 58, 62, 68, 196, 5, 5_000),

    # ── L1GA TEAM (CIS T2) ───────────────────────────────────────────────────
    ('Mirage`',   'Miras',      'Mutanov',     'Kazakhstan','mid',           65, 68, 62, 208, 5, 6_000),
    ('Vazya',     'Ivan',       'German',      'Russia',   'offlane',        62, 65, 62, 204, 5, 5_500),
    ('sayuw',     'Oleg',       'Kalenbet',    'Russia',   'partial_support',60, 64, 66, 202, 5, 5_000),
    ('RESPECT',   'Egor',       'Procurat',    'Belarus',  'full_support',   58, 62, 68, 200, 5, 4_500),

    # ── VP.Prodigy / CIS Academy (CIS T2) ───────────────────────────────────
    ('cutie',     'Stanislav',  'Korostelev',  'Russia',  'carry',           66, 62, 60, 206, 5, 6_000),
    ('takizawa',  'Andrey',     'Bondar',      'Russia',  'offlane',         62, 65, 62, 204, 5, 5_500),
    ('raregods',  'Ilya',       'Tryastsin',   'Russia',  'partial_support', 60, 63, 66, 202, 5, 5_000),
    ('JANTER',    'Dmitry',     'Nikulin',     'Russia',  'full_support',    58, 62, 68, 200, 5, 5_000),

    # ── HEROIC (LatAm T2) ────────────────────────────────────────────────────
    ('TaiLung',   'Santiago',   'Olivos',      'Peru',    'mid',             65, 68, 60, 208, 5, 5_500),
    ('Thiolicor', 'Thiago',     'Cordeiro',    'Brazil',  'partial_support', 60, 62, 65, 200, 5, 4_500),
    ('KJ',        'Matheus',    'Santos',      'Brazil',  'full_support',    58, 60, 68, 198, 5, 4_000),

    # ── REKONIX (SEA T2) ─────────────────────────────────────────────────────
    ('Jikroy',       'Musthofa', 'Pamungkas',   'Indonesia','carry',         60, 58, 58, 196, 5, 4_000),
    ('inYourdreaM',  'Muhammad', 'Anugrah',     'Indonesia','mid',           58, 62, 58, 196, 5, 4_000),
    ('dalul',        'Abdalla',  'Afemi',       'Indonesia','partial_support',56,60, 64, 192, 4, 3_500),
    ('Varizh',       'Rizki',    'Varizh',      'Indonesia','full_support',  54, 58, 65, 190, 4, 3_500),
]


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Idempotency: skip if No[o]ne- already inserted
    c.execute("SELECT COUNT(*) FROM players WHERE nickname='No[o]ne-'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    # Collect existing nicknames to avoid duplicates
    c.execute("SELECT LOWER(nickname) FROM players")
    existing = {r[0] for r in c.fetchall()}

    added = 0
    for nick, name, surname, country, role, micro, macro, soft, cap, comp, exp_wage in _TIER2_PLAYERS:
        if nick.lower() in existing:
            continue
        c.execute("""
            INSERT INTO players
              (nickname, name, surname, country, role, team_id,
               micro_skills, macro_skills, soft_skills, skill_cap,
               competence, morale, wage, expected_wage,
               fame, character)
            VALUES (?,?,?,?,?,0, ?,?,?,?, ?,5,0,?, 40,'balanced')
        """, (nick, name, surname, country, role,
              micro, macro, soft, cap,
              comp, exp_wage))
        added += 1

    conn.commit()
    conn.close()
    if added:
        print(f"[migrate4] Added {added} tier-2 free agents to {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate4] Error on {db}: {e}")
