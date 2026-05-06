"""
Migration 2: Add ratings to teams 1-16, rosters for empty teams,
16 new teams (IDs 33-48), players (IDs 201-320), extended tournament calendar.
Safe to run multiple times.
"""
import sqlite3, sys

# ── Ratings for existing teams 1-16 ────────────────────────────────────────
TEAM_RATINGS = [
    (1,  'Team Spirit',       1500, 1_500_000),
    (2,  'Xtreme Gaming',     1500, 1_500_000),
    (3,  'Team Falcons',      1400, 2_000_000),
    (4,  'Team Liquid',       1300, 1_200_000),
    (5,  'Gaming Gladiators',  700,   500_000),
    (6,  'Cloud9',             550,   800_000),
    (7,  'Tundra Esports',     950,   700_000),
    (8,  'BB Team',            820,   600_000),
    (9,  '1w Team',            580,   300_000),
    (10, 'Team Zero',          520,   200_000),
    (11, 'G2 IG',              730,   700_000),
    (12, 'Talon Esports',      800,   500_000),
    (13, 'Aurora',             920,   600_000),
    (14, 'nouns',              680,   400_000),
    (15, 'Heroic',             660,   400_000),
    (16, 'Beastcoast',         580,   300_000),
]

# ── New teams (IDs 33-48) ───────────────────────────────────────────────────
NEW_TEAMS = [
    (33, 'Team Aster',           'China',            1_000_000, 1050),
    (34, 'Azure Ray',            'China',              800_000,  950),
    (35, 'Natus Vincere',        'Ukraine',            900_000,  870),
    (36, 'Fnatic',               'Malaysia',           600_000,  790),
    (37, 'T1',                   'South Korea',        700_000,  840),
    (38, 'Evil Geniuses',        'USA',                800_000,  760),
    (39, 'Thunder Awaken',       'Peru',               300_000,  640),
    (40, 'Blacklist International','Philippines',      400_000,  760),
    (41, 'Team Zero',            'Russia',             250_000,  490),  # second tier
    (42, 'RNG',                  'China',              600_000,  680),
    (43, 'Yellow Submarine',     'CIS',                300_000,  560),
    (44, 'Parivision',           'CIS',                350_000,  620),
    (45, 'Hokori',               'South America',      250_000,  520),
    (46, 'Azure',                'Southeast Asia',     300_000,  540),
    (47, 'NaVi Junior',          'Europe',             300_000,  480),
    (48, 'Team Tickles',         'Europe',             250_000,  460),
]

# ── Players ─────────────────────────────────────────────────────────────────
# Format: (id, name, surname, nick, team_id, role, micro, macro, soft, cap, wage, exp_wage, country)
NEW_PLAYERS = [
    # ── Cloud9 (6) – add roster ───────────────────────────────────────────
    (201, 'Kyle',   'Freedman',  'Kyle',      6, 'carry',           76, 74, 75, 245, 7500, 7500, 'USA'),
    (202, 'Peter',  'Dager',     'ppd',       6, 'mid',             74, 78, 82, 248, 7500, 7500, 'USA'),
    (203, 'Michael','Jankowski', 'DJ',        6, 'offlane',         74, 74, 72, 245, 7000, 7000, 'Denmark'),
    (204, 'Jio',    'Madayag',   'Jeyo',      6, 'partial_support', 72, 74, 72, 242, 6500, 6500, 'Philippines'),
    (205, 'Dmitry', 'Zubenko',   'DM2',       6, 'full_support',    72, 74, 74, 244, 6500, 6500, 'Russia'),

    # ── Team Zero (10) – add roster ───────────────────────────────────────
    (206, 'Hu',     'Liangzhi',  'Super',    10, 'carry',           74, 72, 70, 242, 6500, 6500, 'China'),
    (207, 'Zhang',  'Tianqi',    'y`',       10, 'mid',             76, 74, 72, 244, 7000, 7000, 'China'),
    (208, 'Liu',    'Zhibing',   'eyyou',    10, 'offlane',         72, 72, 70, 240, 6000, 6000, 'China'),
    (209, 'Ye',     'Jing',      'Boboka2',  10, 'partial_support', 72, 72, 70, 240, 6000, 6000, 'China'),
    (210, 'Wang',   'Yang',      'rOtK',     10, 'full_support',    74, 76, 76, 248, 7000, 7000, 'China'),

    # ── G2 IG (11) – add roster ───────────────────────────────────────────
    (211, 'Zhang',  'Pan',       'Inflame2', 11, 'carry',           76, 74, 72, 244, 7000, 7000, 'China'),
    (212, 'Luo',    'Feichi',    'somnus',   11, 'mid',             82, 80, 76, 258, 9500, 9500, 'China'),
    (213, 'Ren',    'Haozhong',  'maybe',    11, 'offlane',         80, 78, 75, 255, 9000, 9000, 'China'),
    (214, 'Xu',     'Zhenyu',    'Ghost',    11, 'partial_support', 76, 76, 72, 246, 7500, 7500, 'China'),
    (215, 'Zhang',  'Bicheng',   'Faith2',   11, 'full_support',    78, 80, 76, 252, 8500, 8500, 'China'),

    # ── Team Aster (33) ───────────────────────────────────────────────────
    (216, 'Bai',    'Fan',       'Ame2',     33, 'carry',           84, 80, 76, 258, 9500, 9500, 'China'),
    (217, 'An',     'Jiansheng', 'Ori',      33, 'mid',             82, 82, 78, 260, 10000,10000, 'China'),
    (218, 'Sun',    'Chao',      'Sccc',     33, 'offlane',         80, 78, 75, 255, 8500, 8500, 'China'),
    (219, 'Li',     'Hua',       'poyoyo',   33, 'partial_support', 78, 78, 74, 250, 8000, 8000, 'China'),
    (220, 'Xu',     'Chengjie',  'XCJ',      33, 'full_support',    78, 80, 76, 252, 8500, 8500, 'China'),

    # ── Azure Ray (34) ────────────────────────────────────────────────────
    (221, 'Xie',    'Bin',       'Super2',   34, 'carry',           82, 78, 75, 254, 9000, 9000, 'China'),
    (222, 'Zheng',  'Lihong',    'ponlo2',   34, 'mid',             80, 80, 76, 254, 9000, 9000, 'China'),
    (223, 'Chen',   'Zhihao',    'Pyw',      34, 'offlane',         78, 76, 73, 249, 8000, 8000, 'China'),
    (224, 'Wang',   'He',        'Q2',       34, 'partial_support', 78, 78, 74, 250, 8000, 8000, 'China'),
    (225, 'Liu',    'Hao',       'xiao8',    34, 'full_support',    76, 80, 78, 252, 8500, 8500, 'China'),

    # ── Natus Vincere (35) ────────────────────────────────────────────────
    (226, 'Valentin','Kovalenko','Solo2',    35, 'carry',           80, 76, 74, 252, 8500, 8500, 'Russia'),
    (227, 'Nikita', 'Lepko',     'Depressed',35, 'mid',             80, 78, 74, 252, 8500, 8500, 'Russia'),
    (228, 'Gleb',   'Kalinin',   'Funn1k',   35, 'offlane',         78, 76, 74, 250, 8000, 8000, 'Russia'),
    (229, 'Dmitry', 'Palchevskyi','Crystallis',35,'partial_support',80,78,76,252, 8500, 8500, 'Ukraine'),
    (230, 'Roman',  'Korneev',   'Resolut',  35, 'full_support',    78, 78, 76, 250, 8000, 8000, 'Russia'),

    # ── Fnatic (36) ───────────────────────────────────────────────────────
    (231, 'Nuengnara','Teeramahanon','Nueng', 36, 'carry',          76, 74, 72, 244, 7000, 7000, 'Thailand'),
    (232, 'Djardel', 'Jicko',    'DJ2',      36, 'mid',             78, 76, 74, 248, 7500, 7500, 'Philippines'),
    (233, 'Anucha',  'Jirawong', 'Jabz2',    36, 'offlane',         76, 74, 72, 244, 7000, 7000, 'Thailand'),
    (234, 'Kenny',   'Deo',      'Kennyko',  36, 'partial_support', 74, 74, 72, 242, 6500, 6500, 'Philippines'),
    (235, 'Armel',   'Paul',     'Armel',    36, 'full_support',    76, 76, 74, 246, 7000, 7000, 'Philippines'),

    # ── T1 (37) ───────────────────────────────────────────────────────────
    (236, 'Carlo',   'Palad',    'Kuku2',    37, 'carry',           78, 74, 72, 246, 7500, 7500, 'Philippines'),
    (237, 'Kim',     'Daeil',    'QO',       37, 'mid',             80, 78, 74, 250, 8500, 8500, 'South Korea'),
    (238, 'Park',    'Sunghoon', 'March2',   37, 'offlane',         78, 76, 74, 248, 8000, 8000, 'South Korea'),
    (239, 'Lee',     'Sangdon',  'Gabbi',    37, 'partial_support', 78, 76, 74, 248, 8000, 8000, 'South Korea'),
    (240, 'Johnmar', 'Villaluna','YawaR2',   37, 'full_support',    76, 76, 74, 246, 7500, 7500, 'Philippines'),

    # ── Evil Geniuses (38) ────────────────────────────────────────────────
    (241, 'Syed',    'Hassan',   'Sumail2',  38, 'carry',           84, 78, 76, 258, 9500, 9500, 'Pakistan'),
    (242, 'Andreas', 'Franck',   'Cr1t4',    38, 'mid',             78, 78, 76, 250, 8500, 8500, 'Denmark'),
    (243, 'Matthew', 'Marquardt','Pakur',    38, 'offlane',         76, 74, 72, 244, 7000, 7000, 'USA'),
    (244, 'Danil',   'Sinyakov', 'Kinetic',  38, 'partial_support', 74, 74, 72, 242, 6500, 6500, 'Russia'),
    (245, 'Jonah',   'Mannion',  'Snakechuck',38,'full_support',    74, 74, 72, 242, 6500, 6500, 'USA'),

    # ── Thunder Awaken (39) ───────────────────────────────────────────────
    (246, 'Geordy',  'Guillen',  'Wisper',   39, 'carry',           74, 72, 70, 242, 6500, 6500, 'Peru'),
    (247, 'Hector',  'Levano',   'K1-',      39, 'mid',             72, 74, 70, 242, 6500, 6500, 'Peru'),
    (248, 'Adrian',  'Mendez',   'Sacred',   39, 'offlane',         72, 72, 70, 240, 6000, 6000, 'Peru'),
    (249, 'Benjamin','Cruz',     'Benjaz',   39, 'partial_support', 72, 72, 70, 240, 6000, 6000, 'Peru'),
    (250, 'Matias',  'Banegas',  'Scofield2',39, 'full_support',    70, 72, 70, 238, 5500, 5500, 'Bolivia'),

    # ── Blacklist International (40) ──────────────────────────────────────
    (251, 'Michael', 'Enriquez', 'ninjaboogie',40,'carry',          76, 74, 72, 244, 7000, 7000, 'Philippines'),
    (252, 'Karl',    'Jayme',    'Karl2',    40, 'mid',             76, 76, 74, 246, 7500, 7500, 'Philippines'),
    (253, 'Erin',    'Jaspe',    'Yopaj2',   40, 'offlane',         76, 74, 72, 244, 7000, 7000, 'Philippines'),
    (254, 'Orlando', 'Salvacion','Ori2',     40, 'partial_support', 74, 74, 72, 242, 6500, 6500, 'Philippines'),
    (255, 'Bryle',   'Alvizo',   'Bryle',    40, 'full_support',    74, 76, 72, 244, 7000, 7000, 'Philippines'),

    # ── RNG (42) ──────────────────────────────────────────────────────────
    (256, 'Zhou',    'Yang',     'fy2',      42, 'carry',           78, 76, 72, 248, 7500, 7500, 'China'),
    (257, 'Ye',      'Qian',     'Sd',       42, 'mid',             76, 76, 74, 248, 7500, 7500, 'China'),
    (258, 'Ding',    'Tengjiao', 'NothingToSay2',42,'offlane',      76, 74, 72, 246, 7000, 7000, 'China'),
    (259, 'Gao',     'Zhenxiong','Jiyuano',  42, 'partial_support', 74, 74, 72, 242, 6500, 6500, 'China'),
    (260, 'Chen',    'Wei',      'DD',       42, 'full_support',    74, 74, 72, 242, 6500, 6500, 'China'),

    # ── Yellow Submarine (43) ─────────────────────────────────────────────
    (261, 'Vadim',   'Karpov',   'SnY',      43, 'carry',           72, 70, 68, 238, 5500, 5500, 'Russia'),
    (262, 'Denis',   'Gutnik',   'TMT',      43, 'mid',             70, 70, 68, 238, 5500, 5500, 'Russia'),
    (263, 'Igor',    'Goroda',   'Funn2',    43, 'offlane',         70, 68, 68, 236, 5000, 5000, 'Russia'),
    (264, 'Arseny',  'Borzov',   'Save2',    43, 'partial_support', 68, 70, 68, 236, 5000, 5000, 'Russia'),
    (265, 'Mikhail', 'Anosov',   'Miposhka2',43, 'full_support',    70, 72, 70, 240, 5500, 5500, 'Russia'),

    # ── Parivision (44) ───────────────────────────────────────────────────
    (266, 'Giorgi',  'Zaridze',  'Resolut2', 44, 'carry',           74, 72, 70, 242, 6500, 6500, 'Georgia'),
    (267, 'Ruslan',  'Mindubaev','Biver',    44, 'mid',             72, 74, 72, 242, 6500, 6500, 'Kazakhstan'),
    (268, 'Andrei',  'Kadyk',    'Incident', 44, 'offlane',         70, 70, 68, 238, 5500, 5500, 'Russia'),
    (269, 'Alexandr','Duyun',    'Cooman',   44, 'partial_support', 70, 70, 68, 238, 5500, 5500, 'Russia'),
    (270, 'Alexei',  'Nagorski', 'GeneRaL2', 44, 'full_support',    72, 72, 70, 240, 5500, 5500, 'Russia'),

    # ── Hokori (45) ───────────────────────────────────────────────────────
    (271, 'Abner',   'Chua',     'Accel',    45, 'carry',           70, 68, 68, 236, 5000, 5000, 'Peru'),
    (272, 'Frosty',  'Aguilar',  'Frosty',   45, 'mid',             68, 70, 68, 236, 5000, 5000, 'Peru'),
    (273, 'Diego',   'Perez',    'DiegoPeru',45, 'offlane',         68, 68, 68, 235, 5000, 5000, 'Peru'),
    (274, 'Pablo',   'Guerrero', 'Pablo',    45, 'partial_support', 68, 68, 66, 234, 4500, 4500, 'Peru'),
    (275, 'Martin',  'Estrada',  'Seiba',    45, 'full_support',    68, 68, 68, 235, 4500, 4500, 'Peru'),

    # ── Azure SEA (46) ────────────────────────────────────────────────────
    (276, 'Sompong', 'Srisuk',   'Kuku3',    46, 'carry',           70, 68, 68, 236, 5000, 5000, 'Thailand'),
    (277, 'Itthiphat','Alapan',  'minn',     46, 'mid',             68, 70, 68, 236, 5000, 5000, 'Thailand'),
    (278, 'Ryo',     'Tanaka',   'Ryo',      46, 'offlane',         68, 68, 66, 234, 4500, 4500, 'Japan'),
    (279, 'Pakorn',  'Tachavirojkul','pekz', 46, 'partial_support', 68, 68, 68, 235, 4500, 4500, 'Thailand'),
    (280, 'Chris',   'Koh',      'Chris_Luck',46,'full_support',    68, 70, 68, 236, 5000, 5000, 'Singapore'),

    # ── NaVi Junior (47) ──────────────────────────────────────────────────
    (281, 'Aleksei', 'Kuznetsov','Antares2', 47, 'carry',           70, 68, 68, 236, 5000, 5000, 'Russia'),
    (282, 'Pavel',   'Pisarev',  'W_Zayac',  47, 'mid',             70, 70, 68, 236, 5000, 5000, 'Russia'),
    (283, 'Maxim',   'Ivanov',   '9DAY',     47, 'offlane',         68, 68, 66, 234, 4500, 4500, 'Russia'),
    (284, 'Yevhen',  'Zolotarev','RAMZES3',  47, 'partial_support', 68, 68, 68, 235, 4500, 4500, 'Ukraine'),
    (285, 'Dmitry',  'Rubanov',  'SEVER',    47, 'full_support',    68, 68, 68, 235, 4500, 4500, 'Russia'),

    # ── Team Tickles (48) ─────────────────────────────────────────────────
    (286, 'Tuomas',  'Gronqvist','Kaito',    48, 'carry',           68, 66, 66, 234, 4500, 4500, 'Finland'),
    (287, 'Henrik',  'Poulsen',  'hFnk',     48, 'mid',             68, 68, 66, 234, 4500, 4500, 'Denmark'),
    (288, 'Tobias',  'Limborg',  'Tobias',   48, 'offlane',         66, 66, 64, 232, 4000, 4000, 'Denmark'),
    (289, 'Enrico',  'Rysebak',  'Enrico',   48, 'partial_support', 66, 66, 64, 232, 4000, 4000, 'Denmark'),
    (290, 'Oscar',   'Lahdo',    'Bananaman',48, 'full_support',    66, 68, 66, 234, 4000, 4000, 'Sweden'),
]

# ── Additional free agents (team_id=0) ──────────────────────────────────────
FREE_AGENTS = [
    (291, 'Sébastien','Debs',   'fly',       0, 'partial_support', 80, 80, 82, 258, 0, 9500, 'France'),
    (292, 'Johan',   'Sundstein','N0tail2',   0, 'full_support',    76, 82, 85, 258, 0, 9000, 'Denmark'),
    (293, 'Amir',    'Al-Barkawi','Miracle2', 0, 'carry',           88, 80, 76, 262, 0,13000, 'Jordan'),
    (294, 'Danil',   'Ishutin', 'Dendi2',    0, 'mid',             78, 76, 82, 258, 0, 8500, 'Ukraine'),
    (295, 'Jonni',   'Akan',    'Taiga',     0, 'full_support',    80, 80, 80, 258, 0, 9000, 'Finland'),
    (296, 'Yazied',  'Jaradat', 'YapzOr2',   0, 'partial_support', 84, 82, 80, 262, 0,10500, 'Jordan'),
    (297, 'Lasse',   'Urpalainen','matu2',   0, 'carry',           82, 80, 78, 258, 0,10000, 'Finland'),
    (298, 'Ludwig',  'Wahlberg','Zai2',      0, 'offlane',         80, 80, 78, 256, 0, 9500, 'Sweden'),
    (299, 'Clement', 'Ivanov',  'puppey2',   0, 'full_support',    76, 88, 88, 266, 0,11000, 'Estonia'),
    (300, 'Kuro',    'Salehi',  'KuroKy2',   0, 'full_support',    78, 84, 85, 260, 0, 9500, 'Germany'),
    (301, 'Amer',    'Al-Barkawi','Miracle3', 0, 'carry',           86, 80, 76, 260, 0,12000, 'Jordan'),
    (302, 'Omar',    'Aliwi',   'w33_3',     0, 'mid',             82, 80, 78, 258, 0,10000, 'Iraq'),
    (303, 'Clinton', 'Loomis',  'Fear2',     0, 'carry',           76, 76, 78, 248, 0, 8000, 'USA'),
    (304, 'Ben',     'de la Cruz','Moo',     0, 'full_support',    74, 78, 78, 248, 0, 7500, 'USA'),
    (305, 'Kanishka','Sosale',  'BuLba2',    0, 'offlane',         72, 74, 74, 244, 0, 7000, 'USA'),
    (306, 'Sumail',  'Hassan',  'Sumail3',   0, 'carry',           90, 78, 74, 260, 0,13000, 'Pakistan'),
    (307, 'Rasmus',  'Blomdin', 'BlackHole', 0, 'offlane',         76, 74, 72, 246, 0, 7500, 'Sweden'),
    (308, 'Park',    'Taeyang', 'forev',     0, 'offlane',         78, 76, 74, 248, 0, 8000, 'South Korea'),
    (309, 'Chai',    'Yee Fung','mushi',     0, 'carry',           78, 76, 74, 248, 0, 8000, 'Malaysia'),
    (310, 'Ivan',    'Borislavov','MC2',     0, 'offlane',         80, 78, 76, 252, 0, 8500, 'Bulgaria'),
    (311, 'Abed',    'Yusop',   'Abed2',     0, 'mid',             88, 80, 74, 258, 0,12000, 'Philippines'),
    (312, 'Erin',    'Jaspe',   'Yopaj3',    0, 'offlane',         74, 72, 70, 242, 0, 7000, 'Philippines'),
    (313, 'Tommy',   'Le',      'Tommy',     0, 'carry',           76, 74, 72, 244, 0, 7500, 'USA'),
    (314, 'Roman',   'Kushaliev','biver2',   0, 'full_support',    72, 76, 74, 246, 0, 7000, 'Kazakhstan'),
    (315, 'Dmitriy', 'Fishman2','Fishman2',  0, 'partial_support', 74, 78, 74, 248, 0, 7500, 'Russia'),
    (316, 'Alexei',  'Oganov',  'Zayac',     0, 'full_support',    76, 76, 76, 250, 0, 8000, 'Russia'),
    (317, 'Maxim',   'Semenets','Limitless', 0, 'mid',             78, 76, 74, 248, 0, 8000, 'Russia'),
    (318, 'Danil',   'Kutovoy', 'gpk2',      0, 'mid',             88, 74, 70, 252, 0, 9500, 'Russia'),
    (319, 'Evgeniy', 'Panov',   'Chu',       0, 'carry',           74, 72, 70, 242, 0, 6500, 'Russia'),
    (320, 'Artem',   'Bragin',  'Alohadance', 0,'partial_support', 76, 76, 76, 250, 0, 8000, 'Russia'),
]

# ── Extra tournaments (2028-2030 extension) ─────────────────────────────────
EXTRA_TOURNAMENTS = [
    ("ESL One Bangkok 2028",      "2028-01-23", "2028-01-30",  500_000,   500),
    ("PGL Wallachia Season 6",    "2028-03-05", "2028-03-12", 1_000_000, 1000),
    ("DreamLeague Season 30",     "2028-04-23", "2028-04-30", 1_000_000, 1000),
    ("ESL One Birmingham 2028",   "2028-06-04", "2028-06-11",  500_000,   500),
    ("The International 2028",    "2028-08-05", "2028-08-17", 2_000_000, 1500),
    ("PGL Bucharest 2028",        "2028-09-18", "2028-09-25",  500_000,   500),
    ("ESL One Kuala Lumpur 2028", "2028-10-30", "2028-11-06",  500_000,   500),
    ("DreamLeague Season 31",     "2028-12-04", "2028-12-11", 1_000_000, 1000),
    ("ESL One Bangkok 2029",      "2029-01-22", "2029-01-29",  500_000,   500),
    ("PGL Wallachia Season 7",    "2029-03-04", "2029-03-11", 1_000_000, 1000),
    ("DreamLeague Season 32",     "2029-04-22", "2029-04-29", 1_000_000, 1000),
    ("ESL One Birmingham 2029",   "2029-06-03", "2029-06-10",  500_000,   500),
    ("The International 2029",    "2029-08-04", "2029-08-16", 2_000_000, 1500),
    ("PGL Bucharest 2029",        "2029-09-17", "2029-09-24",  500_000,   500),
    ("ESL One Kuala Lumpur 2029", "2029-10-29", "2029-11-05",  500_000,   500),
    ("DreamLeague Season 33",     "2029-12-03", "2029-12-10", 1_000_000, 1000),
    ("ESL One Bangkok 2030",      "2030-01-21", "2030-01-28",  500_000,   500),
    ("PGL Wallachia Season 8",    "2030-03-03", "2030-03-10", 1_000_000, 1000),
    ("DreamLeague Season 34",     "2030-04-21", "2030-04-28", 1_000_000, 1000),
    ("The International 2030",    "2030-08-03", "2030-08-15", 2_200_000, 1500),
]


def migrate(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    cur.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate2'")
    if cur.fetchone()[0]:
        conn.close()
        return

    # ── Update ratings / budgets for teams 1-16 ──────────────────────────
    for tid, name, rating, budget in TEAM_RATINGS:
        cur.execute(
            "UPDATE teams SET rating=?, budget=? WHERE id=? AND (rating IS NULL OR rating=0)",
            (rating, budget, tid),
        )

    # ── Insert new teams ──────────────────────────────────────────────────
    for tid, name, country, budget, rating in NEW_TEAMS:
        cur.execute(
            "INSERT OR IGNORE INTO teams (id, name, country, budget, rating, player) "
            "VALUES (?, ?, ?, ?, ?, 'no')",
            (tid, name, country, budget, rating),
        )

    # ── Insert players ────────────────────────────────────────────────────
    existing_ids = {r[0] for r in cur.execute("SELECT id FROM players").fetchall()}
    role_col = {
        'carry': 'carry', 'mid': 'mid', 'offlane': 'offlane',
        'partial_support': 'partial_support', 'full_support': 'full_support',
    }

    for p in NEW_PLAYERS + FREE_AGENTS:
        pid, name, surname, nick, team_id, role, micro, macro, soft, cap, wage, exp_wage, country = p
        if pid in existing_ids:
            continue
        cur.execute(
            """INSERT INTO players
               (id, name, surname, nickname, team_id, role,
                micro_skills, macro_skills, soft_skills, skill_cap,
                wage, expected_wage, country, fame, competence, morale, time_in_team)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, name, surname, nick, team_id, role,
             micro, macro, soft, cap, wage, exp_wage,
             country, 60, 7, 7, 1),
        )
        existing_ids.add(pid)

    # ── Wire team roster slots ────────────────────────────────────────────
    for p in NEW_PLAYERS:
        pid, name, surname, nick, team_id, role = p[0], p[1], p[2], p[3], p[4], p[5]
        col = role_col.get(role, role)
        cur.execute(
            f"UPDATE teams SET {col}=? WHERE id=? AND ({col} IS NULL OR {col}='' OR {col}=0)",
            (pid, team_id),
        )

    # ── Insert tournaments ────────────────────────────────────────────────
    existing_t = {r[0] for r in cur.execute("SELECT name FROM tournaments").fetchall()}
    for name, start, end, prize, rpool in EXTRA_TOURNAMENTS:
        if name not in existing_t:
            cur.execute(
                "INSERT INTO tournaments (name, start_date, end_date, prizepool, ratingpool) "
                "VALUES (?,?,?,?,?)",
                (name, start, end, prize, rpool),
            )

    # ── Deduplication fixes ───────────────────────────────────────────────
    # Free-agent clones of active players → delete; 293=Miracle2 (removed from roster)
    cur.execute("""DELETE FROM players WHERE id IN (
        291,292,293,296,297,298,299,300,301,302,303,306,307,310,183,190,192,312,33
    )""")

    # Sumail Hassan: put original free agent (72) on EG carry, delete clone (241)
    cur.execute("UPDATE teams  SET carry=72           WHERE id=38 AND (carry=241 OR carry IS NULL)")
    cur.execute("UPDATE players SET team_id=38, wage=13000 WHERE id=72 AND team_id=0")
    cur.execute("DELETE FROM players WHERE id=241")

    # Give OG Topson the real nickname now that the free-agent duplicate is gone
    cur.execute("UPDATE players SET nickname='Topson'  WHERE id=97  AND nickname='Topson2'")
    # Gaimin mid: Quinn2 → Quinn (free-agent clone deleted)
    cur.execute("UPDATE players SET nickname='Quinn'   WHERE id=101 AND nickname='Quinn2'")

    # Same-person-on-two-teams: rename one to avoid exact name+surname collision
    cur.execute("UPDATE players SET name='Anurak', nickname='Jabz2'    WHERE id=233")  # Fnatic
    cur.execute("UPDATE players SET name='Renato',  nickname='Kuku2'    WHERE id=236")  # T1
    cur.execute("UPDATE players SET name='Kyle', surname='Callahan', nickname='Quinn.GG' WHERE id=23")  # GG
    cur.execute("UPDATE players SET name='Ryan'                         WHERE id=253")  # Blacklist Yopaj2

    # Nuengnara: give Fnatic slot a different name (free agent ID 64 is the iconic one)
    cur.execute("UPDATE players SET name='Worawit', surname='Nueng', nickname='Nueng' WHERE id=231")

    # Syed Hassan name disambiguation
    cur.execute("UPDATE players SET name='Sumail'      WHERE id=241 AND name='Syed'")  # may already be deleted
    cur.execute("UPDATE players SET name='Syed Ahmer'  WHERE id=104 AND name='Syed'")

    # SilverEdge (BetBoom) was incorrectly mapped to Yaroslav Naidenov → new identity
    cur.execute("UPDATE players SET name='Alexei', surname='Naumenkov' WHERE id=109")

    # Nickname fixes
    cur.execute("UPDATE players SET nickname='Ceb'     WHERE id=291 AND nickname='fly'")  # if not deleted
    cur.execute("UPDATE players SET nickname='Nisha.M' WHERE id=18  AND nickname='Nisha'")
    cur.execute("UPDATE players SET nickname='Ace.RU'  WHERE id=102 AND nickname='Ace'")

    # Team Zero duplicate: rename empty team 41 → Team Empire
    cur.execute("UPDATE teams SET name='Team Empire', country='Russia' WHERE id=41 AND name='Team Zero'")

    # y` role correction: was inserted as mid (team 10), user moved to full_support FA
    cur.execute("UPDATE players SET role='full_support', team_id=0, wage=0 WHERE id=207 AND role='mid'")

    cur.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate2')")
    conn.commit()
    conn.close()
    print(f"✓ Migrated: {db_path}")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["start_database.db"]
    for path in targets:
        migrate(path)
