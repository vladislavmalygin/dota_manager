"""
One-time migration: adds 16 new teams (IDs 17-32), their rosters (IDs 96-175),
and extra free agents (IDs 176-200).  Extended tournament calendar 2025-2027.
Safe to run multiple times (INSERT OR IGNORE).
"""
import sqlite3, sys

NEW_TEAMS = [
    # (id, name, budget, rating)
    (17, 'OG',                    500_000, 1200),
    (18, 'Gaimin Gladiators',     600_000, 1100),
    (19, 'BetBoom Team',          400_000,  900),
    (20, '9Pandas',               400_000,  800),
    (21, 'Nigma Galaxy',          500_000, 1000),
    (22, 'Team Secret',           600_000, 1100),
    (23, 'PSG.LGD',               800_000, 1000),
    (24, 'Virtus.pro',            400_000,  800),
    (25, 'BOOM Esports',          300_000,  700),
    (26, 'Entity',                400_000,  750),
    (27, 'Alliance',              300_000,  600),
    (28, 'Quest Esports',         300_000,  650),
    (29, 'Shopify Rebellion',     400_000,  700),
    (30, 'TSM',                   400_000,  650),
    (31, 'Wildcard Gaming',       250_000,  500),
    (32, 'Execration',            200_000,  450),
]

# (id, name, surname, nick, team_id, role, micro, macro, soft, cap, wage, exp_wage, country, fame, comp, morale, time_in_team)
NEW_PLAYERS = [
    # ── OG (17) ───────────────────────────────────────────
    ( 96,'Anathan','Pham','ana',       17,'carry',          88,85,75,275,12000,12000,'Australia',85,8,7,2),
    ( 97,'Topias','Taavitsainen','Topson2',17,'mid',        83,82,78,265,11000,11000,'Finland',  80,7,7,2),
    ( 98,'Sebastien','Debs','Ceb',     17,'offlane',        82,82,80,260,10000,10000,'France',   80,8,7,3),
    ( 99,'Jesse','Vainikka','JerAx',   17,'partial_support',85,82,80,265,10000,10000,'Finland',  82,8,7,3),
    (100,'Johan','Sundstein','N0tail', 17,'full_support',   78,82,82,255,10000,10000,'Denmark',  85,8,7,3),
    # ── Gaimin Gladiators (18) ───────────────────────────
    (101,'Quinn','Callahan','Quinn2',  18,'carry',          82,78,75,255, 9000, 9000,'USA',      72,7,7,2),
    (102,'Roman','Dvoryankin','Ace',   18,'mid',            80,80,75,255, 9000, 9000,'Russia',   70,7,7,2),
    (103,'Danylo','Kondratiev','dyrachyo',18,'offlane',     80,78,72,250, 8500, 8500,'Ukraine',  68,7,7,2),
    (104,'Syed','Hassan','tOfu2',      18,'partial_support',80,80,75,255, 9000, 9000,'Malaysia', 70,7,7,2),
    (105,'Jonas','Volek','Palantimos', 18,'full_support',   78,80,75,250, 8500, 8500,'Czech',    68,7,7,2),
    # ── BetBoom Team (19) ────────────────────────────────
    (106,'Egor','Andreev','Pure_',     19,'carry',          82,80,75,255, 9000, 9000,'Russia',   72,7,7,2),
    (107,'Denis','Sharipov','Storm2',  19,'mid',            80,78,72,250, 8500, 8500,'Russia',   68,7,7,2),
    (108,'Ilya','Mulyarchuk','Illidan',19,'offlane',        78,78,72,248, 8000, 8000,'Ukraine',  65,7,7,2),
    (109,'Yaroslav','Naidenov','SilverEdge',19,'partial_support',78,75,72,245,7500,7500,'Russia',62,7,7,2),
    (110,'Alexey','Berezin','RodjER',  19,'full_support',   80,78,75,252, 8500, 8500,'Russia',   70,7,7,2),
    # ── 9Pandas (20) ─────────────────────────────────────
    (111,'Nikita','Seledkov','Antares',20,'carry',          78,76,72,248, 8000, 8000,'Russia',   65,7,7,2),
    (112,'Artem','Ushakov','Ar1se',    20,'mid',            80,78,74,250, 8500, 8500,'Russia',   68,7,7,2),
    (113,'Idan','Generalov','Nightfall2',20,'offlane',      80,80,75,255, 9000, 9000,'Israel',   70,7,7,2),
    (114,'Alexei','Chernikov','Solo',  20,'partial_support',78,80,75,252, 8500, 8500,'Russia',   72,7,7,2),
    (115,'Ilya','Filatov','iLTW',      20,'full_support',   76,75,72,245, 7500, 7500,'Russia',   62,7,7,2),
    # ── Nigma Galaxy (21) ────────────────────────────────
    (116,'Amer','Al-Barkawi','Miracle-',21,'carry',         90,82,78,270,12000,12000,'Jordan',   90,9,7,2),
    (117,'Omar','Aliwi','w33',         21,'mid',            84,80,78,260,10500,10500,'Iraq',     82,8,7,2),
    (118,'Ivan','Borislavov','MC',     21,'offlane',        82,80,78,258,10000,10000,'Bulgaria', 78,8,7,3),
    (119,'Maroun','Merhej','GH',       21,'partial_support',84,82,80,262,10000,10000,'Lebanon',  82,8,7,3),
    (120,'Kuro','Salehi','KuroKy',     21,'full_support',   80,84,85,262,10000,10000,'Germany',  88,9,7,4),
    # ── Team Secret (22) ─────────────────────────────────
    (121,'Nikolay','Nikolov','Nisha',  22,'mid',            86,82,78,265,11000,11000,'Bulgaria', 82,8,7,2),
    (122,'Yazied','Jaradat','YapzOr',  22,'partial_support',85,82,80,262,10500,10500,'Jordan',   82,8,7,3),
    (123,'Lasse','Urpalainen','matumbaman',22,'carry',      84,80,78,260,10500,10500,'Finland',  80,8,7,3),
    (124,'Ludwig','Wahlberg','Zai',    22,'offlane',        82,80,78,258,10000,10000,'Sweden',   78,8,7,2),
    (125,'Clement','Ivanov','puppey',  22,'full_support',   78,88,88,268,11000,11000,'Estonia',  92,9,7,5),
    # ── PSG.LGD (23) ─────────────────────────────────────
    (126,'Wang','Chun','Shiro',        23,'carry',          82,78,74,252, 9000, 9000,'China',    70,7,7,2),
    (127,'Zhao','Jie','Chalice',       23,'offlane',        80,78,74,250, 8500, 8500,'China',    68,7,7,2),
    (128,'Zhang','Ruida','LaNm',       23,'partial_support',78,80,76,252, 8500, 8500,'China',    70,7,8,3),
    (129,'Xu','Zhaohao','fy',          23,'full_support',   80,82,78,258, 9500, 9500,'China',    75,8,7,4),
    (130,'Ye','Wenjun','Inflame',      23,'mid',            82,78,74,252, 9000, 9000,'China',    72,7,7,2),
    # ── Virtus.pro (24) ──────────────────────────────────
    (131,'Vitaly','Vorobei','Ramzes2', 24,'carry',          80,78,74,250, 8500, 8500,'Russia',   70,7,7,2),
    (132,'Maxim','Grigoriev','SoNNeikO',24,'mid',           80,76,72,248, 8000, 8000,'Russia',   68,7,7,2),
    (133,'Dmitry','Kostylev','Daxak',  24,'offlane',        78,76,72,245, 7500, 7500,'Russia',   65,7,7,2),
    (134,'Sergey','Bragin','God',      24,'partial_support',76,75,72,244, 7500, 7500,'Russia',   62,7,7,2),
    (135,'Anton','Berestnev','Immersion',24,'full_support', 76,76,74,245, 7500, 7500,'Russia',   62,7,7,2),
    # ── BOOM Esports (25) ────────────────────────────────
    (136,'Saieful','Ilham','Fbz',      25,'carry',          76,74,72,244, 7000, 7000,'Indonesia',62,7,7,2),
    (137,'Ahmad','Nourdeen','Hyde',    25,'mid',            78,74,72,245, 7500, 7500,'Malaysia', 64,7,7,2),
    (138,'Erin','Jaspe','Yopaj',       25,'offlane',        76,74,72,244, 7000, 7000,'Philippines',62,7,7,2),
    (139,'Rafli','Ahmad','1nverse',    25,'partial_support',76,76,72,245, 7000, 7000,'Indonesia',62,7,7,2),
    (140,'Gio','Badoyos','Tims',       25,'full_support',   76,76,74,245, 7000, 7000,'Philippines',62,7,7,2),
    # ── Entity (26) ──────────────────────────────────────
    (141,'Igor','Mnatsakanov','Tobi',  26,'carry',          76,74,72,244, 7000, 7000,'Russia',   62,7,7,2),
    (142,'Bozhidar','Bogdanov','bzm2', 26,'mid',            78,76,72,248, 8000, 8000,'Bulgaria', 65,7,7,2),
    (143,'Grigory','Komok','Tobi2',    26,'offlane',        76,74,72,244, 7000, 7000,'Russia',   62,7,7,2),
    (144,'Stanislav','Shevchenko','Fsh2',26,'partial_support',76,76,74,245,7000,7000,'Russia',  62,7,7,2),
    (145,'Magnus','Vilhjalmsson','MagE',26,'full_support',  75,78,76,248, 7500, 7500,'Iceland',  65,7,7,2),
    # ── Alliance (27) ────────────────────────────────────
    (146,'Jonathan','Berg','Loda',     27,'carry',          75,76,76,248, 7500, 7500,'Sweden',   78,7,7,3),
    (147,'Henrik','Ahnberg','Bulldog', 27,'offlane',        74,75,74,245, 7000, 7000,'Sweden',   72,7,7,3),
    (148,'Rasmus','Fillipsen','Chessie',27,'mid',           76,74,72,245, 7000, 7000,'Denmark',  64,7,7,2),
    (149,'Simon','Eliasson','Handsken',27,'partial_support',74,74,72,244, 6500, 6500,'Sweden',   62,7,7,2),
    (150,'Marcus','Croft','Limmp',     27,'full_support',   74,75,74,245, 6500, 6500,'Sweden',   62,7,7,2),
    # ── Quest Esports (28) ───────────────────────────────
    (151,'Amir','Karimov','Arabb',     28,'carry',          74,72,70,242, 6500, 6500,'Kazakhstan',60,7,7,2),
    (152,'Omar','Bishr','Yatoro4',     28,'mid',            74,72,70,242, 6500, 6500,'Egypt',    58,7,7,2),
    (153,'Faisal','Al-Yousif','tOfu3', 28,'offlane',        72,74,72,242, 6500, 6500,'Saudi Arabia',60,7,7,2),
    (154,'Tariq','Hameed','Nadir',     28,'partial_support',72,72,70,240, 6000, 6000,'Pakistan', 58,7,7,2),
    (155,'Ali','Hassan','Beastmaster', 28,'full_support',   72,74,72,242, 6000, 6000,'UAE',      58,7,7,2),
    # ── Shopify Rebellion (29) ───────────────────────────
    (156,'Clinton','Loomis','Fear',    29,'carry',          76,76,78,248, 8000, 8000,'USA',      78,7,7,3),
    (157,'David','Godoy','MoonMeander',29,'offlane',        74,76,75,247, 7500, 7500,'Brazil',   68,7,7,2),
    (158,'Pierre','Gagnon','Maelk',    29,'mid',            76,74,74,246, 7500, 7500,'Canada',   65,7,7,2),
    (159,'Thomas','Huynh','Bryle2',    29,'partial_support',74,74,72,244, 7000, 7000,'Canada',   62,7,7,2),
    (160,'Rodrigo','Vilardi','Lelis2', 29,'full_support',   72,75,74,244, 7000, 7000,'Brazil',   62,7,7,2),
    # ── TSM (30) ─────────────────────────────────────────
    (161,'Malthe','Jakobsen','Xerxes', 30,'carry',          74,72,70,242, 7000, 7000,'Denmark',  62,7,7,2),
    (162,'Marcus','Valiaho','Stizzy',  30,'mid',            74,72,70,242, 7000, 7000,'Sweden',   60,7,7,2),
    (163,'Oliver','Lepko','DuA',       30,'offlane',        72,72,70,240, 6500, 6500,'Czech',    58,7,7,2),
    (164,'Adrian','Chmielewski','Cr1t3',30,'partial_support',72,74,72,242,6500, 6500,'Poland',   60,7,7,2),
    (165,'William','Cho','w33_2',      30,'full_support',   72,74,72,242, 6500, 6500,'Korea',    58,7,7,2),
    # ── Wildcard Gaming (31) ─────────────────────────────
    (166,'Chad','Seltzer','Gunnar2',   31,'carry',          70,70,70,238, 6000, 6000,'USA',      58,6,7,2),
    (167,'Justin','Saez','MSS',        31,'mid',            72,70,70,238, 6000, 6000,'USA',      58,6,7,2),
    (168,'Sean','Carmichael','BuLba',  31,'offlane',        70,72,70,240, 6000, 6000,'USA',      60,6,7,3),
    (169,'Matej','Dolinar','BOOM2',    31,'partial_support',70,70,70,238, 5500, 5500,'Slovenia', 56,6,7,2),
    (170,'Ryan','Kirwin','Ammar2',     31,'full_support',   70,72,70,240, 5500, 5500,'USA',      56,6,7,2),
    # ── Execration (32) ──────────────────────────────────
    (171,'Karl','Baldovino','Karl',    32,'carry',          68,68,68,235, 5500, 5500,'Philippines',55,6,7,2),
    (172,'Nikki','Dionisio','Nikki',   32,'mid',            70,68,68,236, 5500, 5500,'Philippines',55,6,7,2),
    (173,'Gerald','Hernan','Dooms',    32,'offlane',        68,68,68,235, 5000, 5000,'Philippines',52,6,7,2),
    (174,'Jaunuel','Arcilla','Jaunuel',32,'partial_support',68,70,68,236, 5000, 5000,'Philippines',52,6,7,2),
    (175,'Mark','Lino','skem',         32,'full_support',   68,70,70,238, 5000, 5000,'Philippines',52,6,7,2),
]

# Free agents (team_id=0)
FREE_AGENTS = [
    # (id, name, surname, nick, team_id=0, role, micro, macro, soft, cap, wage=0, exp_wage, country, fame, comp, morale, time_in_team)
    (176,'Artour','Babaev','Arteezy',         0,'carry',          86,82,78,264,0,12000,'Azerbaijan',85,8,6,1),
    (177,'Anathan','Pham2','mp',              0,'carry',          82,80,76,258,0,10000,'Australia', 78,7,6,1),
    (178,'Nikolay','Vorobei','Nikobaby',      0,'carry',          84,80,76,260,0,11000,'Bulgaria',  80,8,6,1),
    (179,'Yeik','Nai','Jhocam2',              0,'carry',          76,74,72,244,0, 7000,'Malaysia',  62,7,6,1),
    (180,'Marcus','Larsson','icex3',          0,'carry',          80,78,74,252,0, 9000,'Sweden',    72,7,6,1),
    (181,'Vincent','Wang','iceiceice',        0,'offlane',        82,80,78,258,0,10000,'Singapore', 80,8,6,1),
    (182,'Rasmus','Blomdin','Black^',         0,'offlane',        78,76,74,248,0, 8000,'Sweden',    68,7,6,1),
    (183,'Tal','Aizik','Fly2',                0,'offlane',        76,76,74,246,0, 7500,'Israel',    65,7,6,1),
    (184,'Saahil','Arora','UNiVeRsE',         0,'offlane',        80,80,78,256,0,10000,'USA',       78,8,6,1),
    (185,'David','Fridberg','Moonmeander2',   0,'offlane',        76,74,72,244,0, 7000,'Denmark',   62,7,6,1),
    (186,'Theeban','Siva','1437',             0,'partial_support',80,82,80,258,0,10000,'Canada',    78,8,6,1),
    (187,'Johan','Sorensen','Naiman',         0,'partial_support',76,76,74,246,0, 7500,'Denmark',   65,7,6,1),
    (188,'Rasmus','Bjaerre','Chessie2',       0,'partial_support',74,74,72,244,0, 6500,'Denmark',   60,7,6,1),
    (189,'Wang','Jiao','Emo',                 0,'mid',            84,82,78,262,0,11000,'China',     82,8,6,1),
    (190,'Roman','Kushnarev','RAMZES',        0,'mid',            82,78,74,252,0, 9000,'Russia',    72,7,6,1),
    (191,'Adrian','Chmielewski2','Resolut1on',0,'mid',            82,80,76,256,0,10000,'Ukraine',   76,8,6,1),
    (192,'Michal','Jankowski','Nisha2',       0,'mid',            80,78,74,250,0, 9000,'Poland',    70,7,6,1),
    (193,'Daniil','Ishutin','Dendi',          0,'mid',            76,75,80,256,0, 8000,'Ukraine',   90,8,6,1),
    (194,'Koh','Zheng','Xepher',              0,'full_support',   80,82,78,258,0,10000,'Malaysia',  75,8,6,1),
    (195,'Magnus','Jepsen','Ryoya',           0,'full_support',   78,80,76,252,0, 9000,'Norway',    70,7,6,1),
    (196,'Rasmus','Lursen','paank',           0,'full_support',   76,76,74,246,0, 7500,'Denmark',   62,7,6,1),
    (197,'Ivan','Ivanov','GeneRaL',           0,'full_support',   78,78,76,250,0, 8500,'Russia',    68,7,6,1),
    (198,'Sebastien','Debs2','Sockshka',      0,'partial_support',74,76,74,246,0, 7000,'France',    62,7,6,1),
    (199,'Alexei','Lipai','KingR',            0,'carry',          78,74,72,246,0, 8000,'Belarus',   66,7,6,1),
    (200,'Leon','Goh','kpii',                 0,'full_support',   80,80,78,256,0, 9500,'Malaysia',  74,8,6,1),
]

EXTRA_TOURNAMENTS = [
    # (name, start_date, end_date, prizepool, ratingpool)
    # 2025 continuation
    ("PGL Bucharest 2025",         "2025-09-21", "2025-09-28", 500_000,   500),
    ("ESL One Kuala Lumpur 2025",  "2025-11-02", "2025-11-09", 500_000,   500),
    ("DreamLeague Season 26",      "2025-12-07", "2025-12-14", 1_000_000, 1000),
    # 2026
    ("ESL One Bangkok 2026",       "2026-01-25", "2026-02-01", 500_000,   500),
    ("PGL Wallachia Season 4",     "2026-03-08", "2026-03-15", 1_000_000, 1000),
    ("DreamLeague Season 27",      "2026-04-26", "2026-05-03", 1_000_000, 1000),
    ("ESL One Birmingham 2026",    "2026-06-07", "2026-06-14", 500_000,   500),
    ("PGL Bucharest 2026",         "2026-09-20", "2026-09-27", 500_000,   500),
    ("The International 2026",     "2026-08-01", "2026-08-13", 1_600_000, 1500),
    ("ESL One Kuala Lumpur 2026",  "2026-11-01", "2026-11-08", 500_000,   500),
    ("DreamLeague Season 28",      "2026-12-06", "2026-12-13", 1_000_000, 1000),
    # 2027
    ("ESL One Bangkok 2027",       "2027-01-24", "2027-01-31", 500_000,   500),
    ("PGL Wallachia Season 5",     "2027-03-07", "2027-03-14", 1_000_000, 1000),
    ("DreamLeague Season 29",      "2027-04-25", "2027-05-02", 1_000_000, 1000),
    ("ESL One Birmingham 2027",    "2027-06-06", "2027-06-13", 500_000,   500),
    ("The International 2027",     "2027-08-07", "2027-08-19", 1_800_000, 1500),
]


def migrate(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ── Teams ────────────────────────────────────────────────────
    for tid, name, budget, rating in NEW_TEAMS:
        cur.execute(
            "INSERT OR IGNORE INTO teams (id, name, budget, rating, player) "
            "VALUES (?, ?, ?, ?, 'no')",
            (tid, name, budget, rating),
        )

    # ── Players ──────────────────────────────────────────────────
    existing_ids = {r[0] for r in cur.execute("SELECT id FROM players").fetchall()}

    for p in NEW_PLAYERS + FREE_AGENTS:
        pid = p[0]
        if pid in existing_ids:
            continue
        (pid, name, surname, nick, team_id, role,
         micro, macro, soft, cap, wage, exp_wage,
         country, fame, comp, morale, time_in_team) = p
        cur.execute(
            """INSERT INTO players
               (id, name, surname, nickname, team_id, role,
                micro_skills, macro_skills, soft_skills, skill_cap,
                wage, expected_wage, country, fame, competence, morale, time_in_team)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, name, surname, nick, team_id, role,
             micro, macro, soft, cap, wage, exp_wage,
             country, fame, comp, morale, time_in_team),
        )

    # ── Wire team slots ──────────────────────────────────────────
    for p in NEW_PLAYERS:
        pid, *_, team_id, role = p[0], *p[1:4], p[4], p[5]
        col = role  # column name matches role name
        # Only update if slot is still empty
        cur.execute(f"UPDATE teams SET {col}=? WHERE id=? AND ({col} IS NULL OR {col}='')",
                    (pid, team_id))

    # ── Tournaments ──────────────────────────────────────────────
    existing_t = {r[0] for r in cur.execute("SELECT name FROM tournaments").fetchall()}
    for name, start, end, prize, rpool in EXTRA_TOURNAMENTS:
        if name not in existing_t:
            cur.execute(
                "INSERT INTO tournaments (name, start_date, end_date, prizepool, ratingpool) "
                "VALUES (?,?,?,?,?)",
                (name, start, end, prize, rpool),
            )

    conn.commit()
    conn.close()
    print(f"Migrated: {db_path}")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else [
        "start_database.db",
    ]
    for path in targets:
        migrate(path)
