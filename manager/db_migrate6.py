"""
Migration 6: Add tier-2/tier-3 free agents.
Sources: Liquipedia — Execration, Fnatic-era SEA vets, Entity, CIS independents,
         Winstrike, NA T2, LatAm T2-3, EU T2-3, CIS T3, SEA T3.
"""
import sqlite3

# (nickname, name, surname, country, role, micro, macro, soft, cap, competence, exp_wage)
_NEW_FA = [
    # ── SEA T2 (Philippine / Malaysian veterans) ─────────────────────────────
    ('Raven',     'Robinson', 'Galapon',     'Philippines', 'carry',           78, 76, 69, 230, 7,  9_000),
    ('March',     'Chong',    'Zhi Feen',    'Malaysia',    'full_support',    68, 70, 75, 220, 7,  8_000),
    ('Karl',      'Karl',     'Baldovino',   'Philippines', 'carry',           68, 70, 65, 210, 6,  7_000),
    ('1437',      'Pratama',  'Hadianto',    'Indonesia',   'full_support',    64, 62, 72, 208, 6,  6_000),

    # ── EU T2 ────────────────────────────────────────────────────────────────
    ('Monstterr', 'Sebastian','Thiemann',    'Germany',     'offlane',         76, 74, 68, 228, 7,  9_000),
    ('Nongrata',  'Vitalii',  'Aleksandrov', 'Ukraine',     'carry',           73, 71, 65, 220, 6,  7_500),
    ('Fng',       'Andrei',   'Filichtchev', 'Russia',      'full_support',    68, 74, 79, 228, 8,  9_000),
    ('Blød',      'Jacob',    'Svendsen',    'Denmark',     'mid',             66, 68, 62, 208, 5,  6_500),
    ('Tobi',      'Tobias',   'Buchner',     'Germany',     'full_support',    62, 65, 73, 208, 6,  6_500),

    # ── CIS T2 veterans ──────────────────────────────────────────────────────
    ('ALOHADANCE','Alexei',   'Solomonov',   'Russia',      'offlane',         75, 77, 71, 230, 7,  9_000),
    ('Iceberg',   'Ivan',     'Varavin',     'Russia',      'full_support',    65, 68, 76, 218, 6,  7_000),
    ('Palantimos','Alexander','Belov',       'Russia',      'offlane',         66, 70, 65, 210, 6,  6_500),
    ('Ghostik',   'Alexei',   'Zhigulin',    'Russia',      'carry',           70, 67, 62, 210, 6,  7_000),
    ('633',       'Fyodor',   'Shevchenko',  'Russia',      'carry',           68, 65, 60, 205, 5,  6_000),
    ('Jotm',      'Anton',    'Alimov',      'Russia',      'mid',             64, 68, 62, 205, 5,  6_000),
    ('Xakuwka',   'Alexander','Kucherov',    'Russia',      'offlane',         64, 67, 62, 206, 5,  5_500),
    ('33NE',      'Maxim',    'Abramovskiy', 'Russia',      'carry',           65, 63, 60, 200, 5,  5_500),

    # ── NA T2 ────────────────────────────────────────────────────────────────
    ('CCnC',      'Charles',  'Nguyen',      'USA',         'carry',           73, 71, 65, 220, 6,  7_500),
    ('Ryoya',     'Ryan',     'Honda',       'USA',         'mid',             68, 72, 63, 215, 6,  7_000),
    ('MSS',       'Maurice',  'Seleban',     'Canada',      'partial_support', 66, 68, 70, 212, 6,  6_500),

    # ── LatAm T2 ─────────────────────────────────────────────────────────────
    ('Chris Luck','Christian','Vargas',      'Peru',        'mid',             68, 70, 65, 215, 6,  7_000),
    ('Costabile', 'Matias',   'Fornaro',     'Uruguay',     'offlane',         62, 65, 62, 202, 5,  5_500),
    ('Matthew',   'Mathew',   'Arcentales',  'Peru',        'partial_support', 60, 62, 68, 202, 5,  5_000),

    # ── T3 CIS ───────────────────────────────────────────────────────────────
    ('ProPain',   'Alexei',   'Petrov',      'Russia',      'carry',           55, 52, 50, 175, 4,  4_000),
    ('ThuG',      'Dmitry',   'Morozov',     'Russia',      'mid',             53, 56, 50, 172, 4,  3_500),
    ('Vansen',    'Ivan',     'Vanshin',     'Russia',      'offlane',         50, 55, 52, 170, 3,  3_500),
    ('crit^',     'Egor',     'Dmitriev',    'Russia',      'partial_support', 48, 52, 56, 168, 3,  3_000),
    ('ELLIE',     'Elena',    'Sorokina',    'Russia',      'full_support',    46, 50, 62, 168, 3,  3_000),

    # ── T3 SEA ───────────────────────────────────────────────────────────────
    ('Palos',     'Paolo',    'Santos',      'Philippines', 'carry',           52, 50, 50, 168, 3,  3_500),
    ('Hyde',      'Kevin',    'Villanueva',  'Philippines', 'offlane',         50, 52, 50, 165, 3,  3_000),
    ('Boombacs',  'Omar',     'Al-Hariri',   'Malaysia',    'partial_support', 48, 50, 55, 165, 3,  3_000),
    ('Senzo',     'Enzo',     'Ramirez',     'Philippines', 'mid',             50, 54, 48, 165, 3,  3_500),
    ('Nawa',      'Nathan',   'Aguilar',     'Philippines', 'full_support',    44, 48, 58, 162, 3,  3_000),

    # ── T3 EU ────────────────────────────────────────────────────────────────
    ('Seweryn',   'Seweryn',  'Kowalski',    'Poland',      'mid',             52, 55, 50, 170, 3,  3_500),
    ('Artif1ce',  'Andrei',   'Ionescu',     'Romania',     'carry',           54, 50, 48, 168, 3,  3_500),
    ('LightOfHeaven','Marco', 'Bauer',       'Austria',     'full_support',    46, 50, 60, 165, 3,  3_000),

    # ── T3 NA ────────────────────────────────────────────────────────────────
    ('Doombringer','Tyler',   'Brooks',      'USA',         'carry',           50, 48, 48, 162, 3,  3_000),
    ('Clutch.gg', 'Jordan',   'Mills',       'USA',         'mid',             48, 52, 48, 160, 3,  3_000),
    ('Willo',     'William',  'Torres',      'USA',         'full_support',    44, 46, 58, 158, 3,  2_500),

    # ── T3 LatAm ─────────────────────────────────────────────────────────────
    ('Madara',    'Gabriel',  'Pereira',     'Brazil',      'carry',           52, 50, 48, 165, 3,  3_000),
    ('Pablito',   'Pablo',    'Gutierrez',   'Argentina',   'mid',             50, 53, 48, 162, 3,  3_000),
    ('Fury',      'Rodrigo',  'Sepulveda',   'Chile',       'partial_support', 46, 50, 54, 160, 3,  2_500),
]


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Idempotency: skip if Raven already inserted
    c.execute("SELECT COUNT(*) FROM players WHERE nickname='Raven'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    c.execute("SELECT LOWER(nickname) FROM players")
    existing = {r[0] for r in c.fetchall()}

    added = 0
    for nick, name, surname, country, role, micro, macro, soft, cap, comp, exp_wage in _NEW_FA:
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
        print(f"[migrate6] Added {added} tier-2/3 free agents to {db_name}")


if __name__ == '__main__':
    import sys
    from db_editor import get_all_dbs
    dbs = sys.argv[1:] or get_all_dbs()
    for db in dbs:
        try:
            migrate(db)
        except Exception as e:
            print(f"[migrate6] Error on {db}: {e}")
