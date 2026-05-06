import sqlite3
import random

_ROLE_RU = {
    'carry': 'carry', 'mid': 'mid', 'offlane': 'offlane',
    'partial_support': 'support 4', 'full_support': 'support 5',
}

_CRISIS_STORIES = [
    '{team} переживает кризис: состав выставлен на продажу',
    'Источники: в {team} конфликт между игроками и руководством',
    '{team} отказалась от участия в предстоящем турнире',
    'Инсайд: {team} готовится к полной перестройке состава',
    '{team} задержала выплату зарплат — игроки на грани ухода',
]
_DOMINANT_STORIES = [
    '{team} — безоговорочный фаворит сезона по версии аналитиков',
    '{team} выиграла {n} матчей подряд и выглядит непобедимо',
    'Эксперты: бюджет {team} позволяет им удержать состав на годы вперёд',
    '{team} отказала нескольким командам, желавшим выкупить их игроков',
]
_RIVALRY_STORIES = [
    '{t1} и {t2} снова встретятся — эта дуэль стала главной интригой сезона',
    'Аналитики называют противостояние {t1} vs {t2} матчем года',
]
_SIGNING_STORIES = [
    '{team} усиливается: подписан {nick} (скилл {sk})',
    'Трансфер: {nick} переходит в {team}',
    '{team} закрыла позицию {role}: добро пожаловать, {nick}',
    '{nick} выбрал {team} несмотря на интерес нескольких клубов',
]
_FA_STORIES = [
    'Свободный агент {nick} (скилл {sk}) пока без предложений',
    '{nick} (FA, скилл {sk}) ожидает оферов после расторжения контракта',
    'Инсайд: {nick} ищет команду с серьёзными амбициями',
]


def generate_monthly_news(db_name):
    """Returns list of news strings for this month. 0-3 items."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT name FROM teams WHERE player='yes' LIMIT 1")
    my_row = c.fetchone()
    my_team = my_row[0].strip() if my_row else ''

    news = []

    # Recent AI transfer
    if random.random() < 0.45:
        c.execute("""
            SELECT p.nickname, p.micro_skills+p.macro_skills, t.name, p.role
            FROM players p JOIN teams t ON p.team_id=t.id
            WHERE t.player!='yes' AND COALESCE(p.time_in_team,0)<=1
              AND p.micro_skills+p.macro_skills >= 110
            ORDER BY RANDOM() LIMIT 1
        """)
        row = c.fetchone()
        if row:
            nick, sk, team, role = row
            role_ru = _ROLE_RU.get(role, role or '?')
            news.append(random.choice(_SIGNING_STORIES).format(
                nick=nick, sk=sk, team=team, role=role_ru))

    # AI team in crisis (low budget or low rating)
    if random.random() < 0.30:
        c.execute("""
            SELECT name FROM teams
            WHERE player!='yes'
              AND (COALESCE(budget,0) < 30000 OR COALESCE(rating,0) < 100)
            ORDER BY RANDOM() LIMIT 1
        """)
        row = c.fetchone()
        if row:
            news.append(random.choice(_CRISIS_STORIES).format(team=row[0]))

    # Dominant top team
    if random.random() < 0.28:
        c.execute("""
            SELECT name, COALESCE(rating,0) FROM teams
            WHERE player!='yes' AND COALESCE(rating,0) >= 500
            ORDER BY rating DESC LIMIT 3
        """)
        rows = c.fetchall()
        if rows:
            team, _ = random.choice(rows)
            n = random.randint(3, 8)
            news.append(random.choice(_DOMINANT_STORIES).format(team=team, n=n))

    # Rivalry story (two high-rated AI teams)
    if random.random() < 0.22:
        c.execute("""
            SELECT name FROM teams WHERE player!='yes'
            ORDER BY COALESCE(rating,0) DESC LIMIT 6
        """)
        top = [r[0] for r in c.fetchall()]
        if len(top) >= 2:
            t1, t2 = random.sample(top[:6], 2)
            news.append(random.choice(_RIVALRY_STORIES).format(t1=t1, t2=t2))

    # Notable free agent
    if random.random() < 0.25:
        c.execute("""
            SELECT nickname, micro_skills+macro_skills FROM players
            WHERE team_id=0 AND micro_skills+macro_skills >= 130
            ORDER BY RANDOM() LIMIT 1
        """)
        row = c.fetchone()
        if row:
            nick, sk = row
            news.append(random.choice(_FA_STORIES).format(nick=nick, sk=sk))

    # Cohesion / chemistry story
    if random.random() < 0.18:
        c.execute("""
            SELECT name, cohesion FROM teams
            WHERE player!='yes' AND cohesion>=70
            ORDER BY cohesion DESC LIMIT 1
        """)
        row = c.fetchone()
        if row:
            news.append(
                f'{row[0]} — одна из самых сыгранных команд мира '
                f'(сыгранность {row[1]}/100)')

    conn.close()
    random.shuffle(news)
    return news[:3]
