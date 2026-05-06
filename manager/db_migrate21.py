"""
Migration 21: Add players from 1win Essence I tournament not yet in DB.

New players (T2/T3 level):
  No[o]one-, rincyq, Davai, ssnovv1, Mirage`, dream`, MikSa`,
  shigetsu, Rain, Batyuk, not me, Xakoda, ariel,
  Wits, DarkMago, Frank, rubikon155, Yamsun
"""
import sqlite3

# (name, surname, nickname, country, role,
#  age, micro, macro, soft, competence,
#  skill_cap, expected_wage, comp_exp,
#  retirement_age, stability, learning_rate,
#  morale, micro_cap, macro_cap, soft_cap,
#  is_youth, face)
_PLAYERS = [
    # ── PARIVISION ────────────────────────────────────────────────────────────
    ('Volodymyr', 'Minenko',          'No[o]one-',  'Ukraine',     'mid',
     29, 84, 86, 70, 8, 255, 9000, 200, 33, 7, 5, 6, 92, 94, 80, 0,
     'players/noone.png'),

    # ── Nigma Galaxy ─────────────────────────────────────────────────────────
    ('Denys',    'Bohushev',          'rincyq',     'Ukraine',     'carry',
     21, 68, 65, 58, 5, 225, 3000,  30, 30, 6, 8, 6, 78, 75, 68, 1,
     'players/rincyq.png'),
    ('Cedric',   'Deckmyn',           'Davai',      'Belgium',     'offlane',
     26, 72, 70, 68, 6, 230, 5000,  80, 31, 6, 6, 6, 82, 80, 78, 0,
     'players/davai.png'),

    # ── L1GA TEAM ─────────────────────────────────────────────────────────────
    ('Ilya',     'Kondrashov',        'ssnovv1',    'Russia',      'carry',
     22, 64, 62, 58, 5, 205, 3000,  40, 29, 5, 7, 6, 74, 72, 68, 0,
     'players/ssnovv1.png'),
    ('Miras',    'Mutanov',           'Mirage`',    'Kazakhstan',  'mid',
     25, 66, 68, 60, 5, 212, 3500,  50, 30, 6, 6, 6, 76, 78, 70, 0,
     'players/mirage.png'),

    # ── Zero Tenacity ─────────────────────────────────────────────────────────
    ('Kyial',    'Tayirov',           'dream`',     'Kyrgyzstan',  'carry',
     26, 65, 63, 58, 5, 208, 3000,  55, 30, 5, 6, 6, 75, 73, 68, 0,
     'players/dream.png'),
    ('Mihajlo',  'Jovanovic',         'MikSa`',     'Serbia',      'offlane',
     26, 67, 65, 62, 5, 215, 3500,  60, 30, 6, 6, 6, 77, 75, 72, 0,
     'players/miksa.png'),

    # ── Yellow Submarine ──────────────────────────────────────────────────────
    ('Maxim',    'Popadinec',         'shigetsu',   'Ukraine',     'carry',
     23, 70, 68, 62, 6, 225, 4000,  60, 30, 6, 7, 6, 80, 78, 72, 0,
     'players/shigetsu.png'),
    ('Ivan',     'Dymin',             'Rain',       'Russia',      'mid',
     24, 64, 66, 58, 5, 205, 3000,  35, 29, 5, 7, 6, 74, 76, 68, 0,
     None),
    ('Bohdan',   'Batiuk',            'Batyuk',     'Ukraine',     'offlane',
     22, 64, 62, 60, 5, 208, 3000,  40, 29, 5, 7, 6, 74, 72, 70, 0,
     'players/batyuk.png'),
    ('Alexey',   'Kosmynin',          'not me',     'Russia',      'partial_support',
     22, 60, 62, 62, 5, 200, 2500,  30, 29, 5, 7, 6, 70, 72, 72, 0,
     None),
    ('Egor',     'Lipartiya',         'Xakoda',     'Russia',      'full_support',
     24, 65, 66, 68, 5, 215, 3500,  75, 30, 6, 6, 6, 75, 76, 78, 0,
     'players/xakoda.png'),

    # ── Nemiga Gaming ─────────────────────────────────────────────────────────
    ('Alexander', 'Kolyasev',         'ariel',      'Russia',      'partial_support',
     27, 66, 68, 66, 6, 218, 4000,  80, 31, 6, 5, 6, 76, 78, 76, 0,
     'players/ariel.png'),

    # ── PlayTime ──────────────────────────────────────────────────────────────
    ('Máximo',   'Orozco Alza',       'Wits',       'Peru',        'carry',
     18, 58, 60, 54, 4, 228, 2000,  20, 29, 4, 9, 6, 68, 70, 64, 1,
     'players/wits.png'),
    ('Oswaldo',  'Herrera Martínez',  'DarkMago',   'Peru',        'mid',
     27, 64, 68, 60, 5, 210, 3000,  75, 31, 5, 5, 6, 74, 78, 70, 0,
     'players/darkmago.png'),
    ('Frank',    'Arias Ayala',       'Frank',      'Peru',        'offlane',
     26, 62, 62, 60, 5, 205, 3000,  55, 30, 5, 6, 6, 72, 72, 70, 0,
     'players/frank.png'),

    # ── Team Nemesis ──────────────────────────────────────────────────────────
    ('Andrei',   'Ruban',             'rubikon155', 'Moldova',     'carry',
     24, 62, 60, 58, 5, 200, 2500,  35, 29, 5, 6, 6, 72, 70, 68, 0,
     None),
    ('Luke',     'Wang',              'Yamsun',     'USA',         'full_support',
     25, 70, 72, 68, 6, 228, 5000,  90, 31, 6, 6, 6, 80, 82, 78, 0,
     'players/yamsun.png'),
]


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    if c.execute("SELECT 1 FROM _migrations WHERE name='migrate21'").fetchone():
        conn.close(); return

    c.execute("SELECT MAX(id) FROM players")
    next_id = (c.fetchone()[0] or 500) + 1

    added = 0
    for i, p in enumerate(_PLAYERS):
        (name, surname, nick, country, role,
         age, micro, macro, soft, comp,
         skill_cap, exp_wage, comp_exp,
         ret_age, stab, lr, morale,
         mc, xc, sc, is_youth, face) = p

        if c.execute("SELECT id FROM players WHERE nickname=?", (nick,)).fetchone():
            continue

        pid = next_id + added
        c.execute("""
            INSERT INTO players
              (id, name, surname, nickname, country, role, team_id,
               micro_skills, macro_skills, soft_skills, skill_cap,
               competence, morale, wage, expected_wage, age, retirement_age,
               stability, learning_rate, fame, comp_exp,
               micro_cap, macro_cap, soft_cap, is_youth, face)
            VALUES (?,?,?,?,?,?,0, ?,?,?,?, ?,?,0,?,?,?, ?,?,30,?, ?,?,?,?,?)
        """, (pid, name, surname, nick, country, role,
              micro, macro, soft, skill_cap,
              comp, morale, exp_wage, age, ret_age,
              stab, lr, comp_exp, mc, xc, sc, is_youth, face))
        added += 1

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate21')")
    conn.commit()
    conn.close()
    print(f"[migrate21] added {added} players from 1win Essence I to {db_name}")


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
