import sqlite3
import random
from datetime import date, timedelta

_EVENTS = [
    ('sponsor_bonus',       12),
    ('player_inspired',     12),
    ('player_vacation',     12),
    ('team_morale_boost',   12),
    ('team_morale_drop',    10),
    ('equipment_upgrade',    7),
    ('fine',                12),
    ('internal_conflict',    8),
    ('player_breakthrough',  7),
    ('media_buzz',           6),
    ('bootcamp',             6),
    ('scout_tip',            5),
    ('team_wants_kick',      4),
    ('player_wants_leave',   4),
    ('performance_slump',    6),
    ('rival_interest',       5),
    ('comeback_veteran',     4),
    # Feature 7: Media/scandals
    ('social_media_drama',   5),
    ('viral_clip',           5),
    ('controversy',          3),
    # Feature 8: Investors
    ('investor_offer',       3),
    # Sponsor acquisition
    ('sponsor_offer',        5),
    # Feature 9: Injuries
    ('player_injury',        5),
    # Feature 10: Force-majeure
    ('visa_problem',         3),
    ('tv_deal',              3),
    ('sponsor_viral_moment', 4),
    ('equipment_theft',      2),
    ('no_event',             3),
    # Psychotype-driven events
    ('leader_demands',       4),
    ('wildcard_incident',    3),
    ('solo_carry_demands',   3),
]
_EVENT_NAMES, _EVENT_WEIGHTS = zip(*_EVENTS)


def random_event_monthly(db_name, game_date_str=None):
    """Apply a random monthly event. Returns (title, text) or None."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, carry, mid, offlane, partial_support, full_support "
        "FROM teams WHERE player='yes'"
    )
    team = cur.fetchone()
    if not team:
        conn.close()
        return None

    team_id = team[0]
    player_ids = [p for p in team[1:] if p]
    if not player_ids:
        conn.close()
        return None

    try:
        today = date.fromisoformat(game_date_str) if game_date_str else date.today()
    except Exception:
        today = date.today()

    # Scale vacation weight by average team fatigue
    weights = list(_EVENT_WEIGHTS)
    vac_idx = _EVENT_NAMES.index('player_vacation')
    try:
        ph = ','.join('?' * len(player_ids))
        avg_fatigue = cur.execute(
            f"SELECT AVG(COALESCE(fatigue,0)) FROM players WHERE id IN ({ph})",
            player_ids,
        ).fetchone()[0] or 0
        if avg_fatigue >= 70:
            weights[vac_idx] = 40
        elif avg_fatigue >= 50:
            weights[vac_idx] = 25
        elif avg_fatigue >= 30:
            weights[vac_idx] = 16
    except Exception:
        pass

    event = random.choices(_EVENT_NAMES, weights=weights, k=1)[0]
    result = _apply(cur, event, team_id, player_ids, today)

    conn.commit()
    conn.close()
    return result


def _apply(cur, event, team_id, player_ids, today=None):
    if event == 'no_event':
        return None

    if event == 'sponsor_bonus':
        bonus = random.choice([15_000, 20_000, 25_000, 35_000, 50_000])
        cur.execute("UPDATE teams SET budget=budget+? WHERE id=?", (bonus, team_id))
        return ('Партнёрский бонус', f'Партнёр перечислил дополнительные средства: +${bonus:,}')

    if event == 'player_inspired':
        pid = random.choice(player_ids)
        cur.execute(
            "SELECT nickname, micro_skills, macro_skills, soft_skills, "
            "COALESCE(skill_cap,300) FROM players WHERE id=?", (pid,)
        )
        p = cur.fetchone()
        if not p:
            return None
        nick, micro, macro, soft, cap = p
        micro, macro, soft = micro or 0, macro or 0, soft or 0
        skills = {'micro_skills': micro, 'macro_skills': macro, 'soft_skills': soft}
        weakest_col = min(skills, key=skills.get)
        if micro + macro + soft >= cap or skills[weakest_col] >= 100:
            return None
        gain = random.randint(3, 6)
        cur.execute(
            f"UPDATE players SET {weakest_col}=MIN(100,{weakest_col}+?) WHERE id=?",
            (gain, pid)
        )
        names = {'micro_skills': 'Micro', 'macro_skills': 'Macro', 'soft_skills': 'Soft'}
        return ('Вдохновение', f'{nick} провёл самостоятельную тренировку: +{gain} {names[weakest_col]}')

    if event == 'player_vacation':
        # Vacation can't happen during The International month
        base = today or date.today()
        cur.execute(
            "SELECT COUNT(*) FROM tournaments "
            "WHERE name LIKE '%The International%' "
            "AND strftime('%Y-%m', start_date) = ?",
            (base.strftime('%Y-%m'),),
        )
        if (cur.fetchone() or (0,))[0] > 0:
            return None
        pid = random.choice(player_ids)
        cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
        p = cur.fetchone()
        if not p:
            return None
        nick = p[0]
        days = random.randint(14, 45)
        until = str(base + timedelta(days=days))
        cur.execute("UPDATE players SET injured_until=? WHERE id=?", (until, pid))
        reasons = ['болезнь', 'личные обстоятельства', 'отпуск по семейным причинам']
        reason = random.choice(reasons)
        return ('Отпуск', f'{nick} недоступен до {until} ({days} дней, {reason}). Нужна замена!', 'popup')

    if event == 'team_morale_boost':
        delta = random.randint(1, 2)
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET morale=MIN(10,COALESCE(morale,5)+?) WHERE id IN ({phs})",
            [delta] + list(player_ids)
        )
        return ('Командный дух', f'Отличная атмосфера в команде: +{delta} мораль всем')

    if event == 'team_morale_drop':
        delta = random.randint(1, 2)
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET morale=MAX(1,COALESCE(morale,5)-?) WHERE id IN ({phs})",
            [delta] + list(player_ids)
        )
        return ('Напряжение', f'Напряжённая обстановка: −{delta} мораль')

    if event == 'equipment_upgrade':
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET soft_skills=MIN(100,COALESCE(soft_skills,0)+2) WHERE id IN ({phs})",
            list(player_ids)
        )
        return ('Новое оборудование', 'Команда получила новую периферию: +2 Soft всем')

    if event == 'fine':
        fine = random.choice([10_000, 15_000, 20_000, 30_000])
        cur.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (fine, team_id))
        return ('Штраф', f'Административный штраф от лиги: −${fine:,}')

    if event == 'internal_conflict':
        if len(player_ids) < 2:
            return None
        p1, p2 = random.sample(player_ids, 2)
        cur.execute("SELECT nickname FROM players WHERE id=?", (p1,))
        n1 = (cur.fetchone() or ('?',))[0]
        cur.execute("SELECT nickname FROM players WHERE id=?", (p2,))
        n2 = (cur.fetchone() or ('?',))[0]
        cur.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-1) WHERE id IN (?,?)",
                    (p1, p2))
        return ('Конфликт', f'{n1} и {n2} поссорились на тренировке: −1 мораль обоим')

    if event == 'player_breakthrough':
        cur.execute(
            "SELECT id, nickname, micro_skills, macro_skills, soft_skills, "
            "COALESCE(skill_cap,300), COALESCE(age,25) "
            "FROM players WHERE id IN ({})".format(','.join('?' * len(player_ids))),
            list(player_ids)
        )
        young = [(r[0], r[1], r[2] or 0, r[3] or 0, r[4] or 0, r[5], r[6])
                 for r in cur.fetchall() if r[6] <= 24]
        if not young:
            return None
        pid, nick, micro, macro, soft, cap, age = random.choice(young)
        total = micro + macro + soft
        if total >= cap:
            return None
        gain = random.randint(2, 5)
        weakest = min([('micro_skills', micro), ('macro_skills', macro), ('soft_skills', soft)],
                      key=lambda x: x[1])[0]
        cur.execute(f"UPDATE players SET {weakest}=MIN(100,{weakest}+?) WHERE id=?", (gain, pid))
        return ('Прорыв', f'{nick} ({age} лет) резко прогрессирует: +{gain} {weakest.split("_")[0].capitalize()}')

    if event == 'media_buzz':
        bonus = random.choice([8_000, 12_000, 15_000])
        cur.execute("UPDATE teams SET budget=budget+? WHERE id=?", (bonus, team_id))
        stories = [
            'Команда попала в топ-10 самых перспективных коллективов',
            'Интервью игрока стало вирусным',
            'Медиапубликация о стиле игры команды собрала миллион просмотров',
        ]
        return ('Медиа-хайп', f'{random.choice(stories)}. Спонсоры прислали бонус: +${bonus:,}')

    if event == 'bootcamp':
        cost = 15_000
        cur.execute("SELECT budget FROM teams WHERE id=?", (team_id,))
        row = cur.fetchone()
        if not row or (row[0] or 0) < cost:
            return None
        cur.execute("UPDATE teams SET budget=budget-? WHERE id=?", (cost, team_id))
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET morale=MIN(10,COALESCE(morale,5)+1) WHERE id IN ({phs})",
            list(player_ids)
        )
        return ('Буткемп', f'Команда прошла выездной буткемп (−${cost:,}): +1 мораль всем')

    if event == 'scout_tip':
        cur.execute(
            "SELECT id, nickname, micro_skills, macro_skills, COALESCE(age,22) "
            "FROM players WHERE team_id=0 ORDER BY RANDOM() LIMIT 5"
        )
        candidates = cur.fetchall()
        if not candidates:
            return None
        pid, nick, micro, macro, age = random.choice(candidates)
        avg = ((micro or 0) + (macro or 0)) // 2
        return ('Совет скаута',
                f'Скаут рекомендует: {nick} (FA, возраст {age}, скилл {avg}) — '
                f'стоит рассмотреть на трансферном рынке')

    if event == 'team_wants_kick':
        if len(player_ids) < 3:
            return None
        # Pick 1–2 targets; rest "vote them out"
        n_targets = random.choice([1, 1, 2])
        targets = random.sample(player_ids, min(n_targets, len(player_ids)))
        target_names = []
        for pid in targets:
            cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
            row = cur.fetchone()
            target_names.append((row[0] if row else '?'))
        # Set cohesion to 0 and lock via conflict_targets
        cur.execute(
            "UPDATE teams SET cohesion=0, conflict_targets=? WHERE id=?",
            (','.join(str(p) for p in targets), team_id)
        )
        names_str = ' и '.join(target_names)
        return (
            'Раскол в команде',
            f'Игроки требуют отчислить: {names_str}. Сыгранность упала до 0 '
            f'и не будет расти, пока {names_str} {"остаётся" if len(targets)==1 else "остаются"} в команде.',
            'popup',
        )

    if event == 'player_wants_leave':
        pid = random.choice(player_ids)
        cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
        row = cur.fetchone()
        if not row:
            return None
        nick = row[0]
        # Set wants_to_leave + morale to 1
        cur.execute(
            "UPDATE players SET wants_to_leave=1, morale=1 WHERE id=?", (pid,)
        )
        return (
            'Игрок хочет уйти',
            f'{nick} заявил о желании покинуть команду. Мораль упала до 1 '
            f'и не восстановится, пока он остаётся. Рассмотрите трансфер.',
            'popup',
        )

    if event == 'performance_slump':
        pid = random.choice(player_ids)
        cur.execute("SELECT nickname, micro_skills, macro_skills FROM players WHERE id=?", (pid,))
        row = cur.fetchone()
        if not row:
            return None
        nick, micro, macro = row
        col = 'micro_skills' if (micro or 0) >= (macro or 0) else 'macro_skills'
        cur.execute(
            f"UPDATE players SET {col}=MAX(1,{col}-2), morale=MAX(1,COALESCE(morale,5)-1) "
            "WHERE id=?", (pid,)
        )
        return ('Спад формы', f'{nick} в плохой форме: −2 {col.split("_")[0].capitalize()}, −1 мораль')

    if event == 'rival_interest':
        pid = random.choice(player_ids)
        cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
        row = cur.fetchone()
        if not row:
            return None
        nick = row[0]
        cur.execute(
            "SELECT name FROM teams WHERE player!='yes' ORDER BY rating DESC LIMIT 10"
        )
        top_teams = [r[0] for r in cur.fetchall()]
        rival = random.choice(top_teams) if top_teams else 'конкурирующая команда'
        return ('Интерес соперников',
                f'{rival} интересуется {nick}. Продлите контракт, чтобы не потерять игрока.')

    # ── Feature 7: Social media ──────────────────────────────────────────────
    if event == 'social_media_drama':
        pid = random.choice(player_ids)
        cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
        row = cur.fetchone()
        if not row:
            return None
        nick = row[0]
        fine = random.choice([8_000, 12_000, 15_000])
        cur.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-1) WHERE id=?", (pid,))
        cur.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (fine, team_id))
        try:
            cur.execute("UPDATE teams SET org_reputation=MAX(0,org_reputation-3) WHERE id=?", (team_id,))
        except Exception:
            pass
        dramas = [
            f'{nick} написал провокационный пост — скандал в соцсетях.',
            f'{nick} поругался с фанатами в твиттере.',
            f'{nick} опубликовал критику организации в интернете.',
        ]
        return ('Скандал в соцсетях',
                f'{random.choice(dramas)} −${fine:,} штраф спонсоров, −1 мораль.', 'popup')

    if event == 'viral_clip':
        bonus = random.choice([6_000, 8_000, 12_000])
        cur.execute("UPDATE teams SET budget=budget+? WHERE id=?", (bonus, team_id))
        try:
            cur.execute("UPDATE teams SET org_reputation=MIN(100,org_reputation+5) WHERE id=?", (team_id,))
        except Exception:
            pass
        stories = [
            'Клип с невероятным мувом игрока набрал миллион просмотров.',
            'Хайлайт матча разлетелся по соцсетям — хайп зашкаливает.',
            'Контент команды стал вирусным — спонсоры довольны.',
        ]
        return ('Вирусный клип',
                f'{random.choice(stories)} Репутация +5, бюджет +${bonus:,}.')

    if event == 'controversy':
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET morale=MAX(1,COALESCE(morale,5)-1) WHERE id IN ({phs})",
            list(player_ids)
        )
        cur.execute("UPDATE teams SET cohesion=MAX(0,COALESCE(cohesion,0)-10) WHERE id=?", (team_id,))
        try:
            cur.execute("UPDATE teams SET org_reputation=MAX(0,org_reputation-5) WHERE id=?", (team_id,))
        except Exception:
            pass
        return ('Скандал',
                'Внутренний конфликт утёк в прессу. −1 мораль всем, −10 сыгранность, −5 репутации.',
                'popup')

    # ── Feature 8: Investors ─────────────────────────────────────────────────
    if event == 'investor_offer':
        # Check if investor already active
        try:
            cur.execute("SELECT COALESCE(investor_name,'') FROM teams WHERE id=?", (team_id,))
            row = cur.fetchone()
            if row and row[0]:
                return None  # already has investor
        except Exception:
            return None

        companies = ['Red Bull Esports Fund', 'GameBoost Capital', 'Nexus Ventures',
                     'ProPlay Investments', 'ESports Capital Group']
        company = random.choice(companies)
        amount  = random.choice([100_000, 150_000, 200_000])
        cut     = random.choice([10, 15, 20])
        seasons = 2
        return (
            'Предложение инвестора',
            f'{company} предлагает ${amount:,} инвестиций в обмен на {cut}% доходов '
            f'от стриминга на {seasons} сезона. Принять в разделе Организация.',
            'investor_pending',
            {'company': company, 'amount': amount, 'cut': cut, 'team_id': team_id,
             'game_date': str(today)},
        )

    # ── Sponsor acquisition ──────────────────────────────────────────────────
    if event == 'sponsor_offer':
        try:
            cur.execute(
                "SELECT COUNT(*) FROM sponsors WHERE is_active=1"
            )
            if (cur.fetchone() or (0,))[0] > 0:
                return None  # already has sponsor
            cur.execute(
                "SELECT id, name, monthly_income FROM sponsors "
                "WHERE is_active=0 ORDER BY RANDOM() LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                return None
            sid, sname, sincome = row
        except Exception:
            return None
        return (
            'Интерес спонсора',
            f'{sname} хочет стать партнёром команды (${sincome:,}/мес). '
            f'Рассмотрите предложение в разделе Спонсоры.',
            'popup',
        )

    # ── Feature 9: Injuries ──────────────────────────────────────────────────
    if event == 'player_injury':
        if not today:
            today = date.today()
        # Pick player not already injured
        eligible = []
        for pid in player_ids:
            cur.execute(
                "SELECT nickname, COALESCE(age,22), COALESCE(fatigue,0), injured_until "
                "FROM players WHERE id=?", (pid,)
            )
            row = cur.fetchone()
            if row:
                nick, age, fatigue, inj_until = row
                if inj_until:
                    try:
                        if date.fromisoformat(inj_until) >= today:
                            continue  # already injured
                    except Exception:
                        pass
                eligible.append((pid, nick, age, fatigue))
        if not eligible:
            return None
        pid, nick, age, fatigue = random.choice(eligible)
        base_days = random.randint(14, 45)
        # Older or fatigued players stay out longer
        if age >= 30:
            base_days = int(base_days * 1.4)
        if fatigue >= 60:
            base_days = int(base_days * 1.2)
        until = str(today + timedelta(days=base_days))
        cur.execute("UPDATE players SET injured_until=?, morale=MAX(1,COALESCE(morale,5)-1) WHERE id=?",
                    (until, pid))
        injury_types = ['растяжение', 'микротравма запястья', 'боль в спине', 'усталостная травма']
        return ('Травма',
                f'{nick} получил {random.choice(injury_types)} — недоступен до {until} '
                f'({base_days} дн.).', 'popup')

    # ── Feature 10: Force-majeure ────────────────────────────────────────────
    if event == 'visa_problem':
        if not today:
            today = date.today()
        pid = random.choice(player_ids)
        cur.execute("SELECT nickname, injured_until FROM players WHERE id=?", (pid,))
        row = cur.fetchone()
        if not row:
            return None
        nick, inj = row
        if inj:
            try:
                if date.fromisoformat(inj) >= today:
                    return None
            except Exception:
                pass
        days = random.randint(14, 45)
        until = str(today + timedelta(days=days))
        cur.execute("UPDATE players SET injured_until=? WHERE id=?", (until, pid))
        reasons = [
            'проблемы с визой для выездного турнира',
            'таможенные задержки, не успел на рейс',
            'бюрократические проволочки в консульстве',
        ]
        return ('Форс-мажор: виза',
                f'{nick} пропустит {days} дней из-за {random.choice(reasons)}.', 'popup')

    if event == 'tv_deal':
        bonus = random.choice([20_000, 30_000, 40_000])
        cur.execute("UPDATE teams SET budget=budget+? WHERE id=?", (bonus, team_id))
        try:
            cur.execute(
                "UPDATE teams SET org_reputation=MIN(100,org_reputation+8) WHERE id=?",
                (team_id,)
            )
        except Exception:
            pass
        channels = ['ESPN Esports', 'Twitch Prime', 'YouTube Gaming', 'local esports channel']
        return ('ТВ-сделка',
                f'{random.choice(channels)} хочет снять документальный фильм о команде. '
                f'Аванс: +${bonus:,}. Репутация +8.')

    if event == 'sponsor_viral_moment':
        bonus = random.choice([10_000, 15_000, 20_000])
        pid = random.choice(player_ids)
        cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
        row = cur.fetchone()
        nick = row[0] if row else '?'
        cur.execute("UPDATE teams SET budget=budget+? WHERE id=?", (bonus, team_id))
        try:
            cur.execute(
                "UPDATE teams SET org_reputation=MIN(100,org_reputation+5) WHERE id=?",
                (team_id,)
            )
        except Exception:
            pass
        moments = [
            f'невероятный мув {nick} собрал 2M просмотров за сутки',
            f'мем с {nick} стал вирусным в Dota-комьюнити',
            f'интервью {nick} разлетелось по соцсетям',
        ]
        return ('Вирусный момент',
                f'Спонсор в восторге — {random.choice(moments)}. Бонус: +${bonus:,}.')

    # ── Psychotype events ─────────────────────────────────────────────────────
    if event == 'leader_demands':
        # Leader psychotype demands recognition — either morale boost (accept) or conflict
        cur.execute(
            "SELECT id, nickname FROM players "
            "WHERE id IN ({}) AND COALESCE(psychotype,'team_player')='leader'".format(
                ','.join('?' * len(player_ids))),
            list(player_ids)
        )
        leaders = cur.fetchall()
        if not leaders:
            return None
        pid, nick = random.choice(leaders)
        accept = random.random() < 0.60
        if accept:
            cur.execute("UPDATE players SET morale=MIN(10,COALESCE(morale,5)+2) WHERE id=?", (pid,))
            cur.execute("UPDATE teams SET cohesion=MIN(100,COALESCE(cohesion,0)+5) WHERE id=?", (team_id,))
            return ('Лидер команды',
                    f'{nick} получил признание капитана. +2 мораль, +5 сыгранность.')
        else:
            cur.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-1) WHERE id=?", (pid,))
            cur.execute("UPDATE teams SET cohesion=MAX(0,COALESCE(cohesion,0)-10) WHERE id=?", (team_id,))
            return ('Требование лидера',
                    f'{nick} недоволен своим статусом в команде. −1 мораль, −10 сыгранность.',
                    'popup')

    if event == 'wildcard_incident':
        cur.execute(
            "SELECT id, nickname FROM players "
            "WHERE id IN ({}) AND COALESCE(psychotype,'team_player')='wildcard'".format(
                ','.join('?' * len(player_ids))),
            list(player_ids)
        )
        wildcards = cur.fetchall()
        if not wildcards:
            return None
        pid, nick = random.choice(wildcards)
        outcomes = [
            ('positive', f'{nick} удивил всех нестандартным решением — вирусный момент! +5 репутации.'),
            ('negative', f'{nick} устроил скандал в соцсетях — репутация −3, штраф.'),
            ('neutral',  f'{nick} отказался от стандартной тренировки — конфликт с тренером.'),
        ]
        outcome, msg = random.choice(outcomes)
        fine = random.choice([5_000, 10_000])
        if outcome == 'positive':
            try:
                cur.execute("UPDATE teams SET org_reputation=MIN(100,org_reputation+5) WHERE id=?", (team_id,))
            except Exception:
                pass
        elif outcome == 'negative':
            cur.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (fine, team_id))
            try:
                cur.execute("UPDATE teams SET org_reputation=MAX(0,org_reputation-3) WHERE id=?", (team_id,))
            except Exception:
                pass
        else:
            cur.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-1) WHERE id=?", (pid,))
        return ('Wildcard выходка', msg, 'popup')

    if event == 'solo_carry_demands':
        cur.execute(
            "SELECT id, nickname FROM players "
            "WHERE id IN ({}) AND COALESCE(psychotype,'team_player')='solo_carry'".format(
                ','.join('?' * len(player_ids))),
            list(player_ids)
        )
        solos = cur.fetchall()
        if not solos:
            return None
        pid, nick = random.choice(solos)
        # Solo carry demands more resources — accept = cohesion loss but morale up; decline = morale down
        accept = random.random() < 0.50
        if accept:
            cur.execute("UPDATE players SET morale=MIN(10,COALESCE(morale,5)+1) WHERE id=?", (pid,))
            cur.execute("UPDATE teams SET cohesion=MAX(0,COALESCE(cohesion,0)-8) WHERE id=?", (team_id,))
            return ('Ресурсы для керри',
                    f'{nick} получил больше фарма — мораль +1, но сыгранность −8 (команда недовольна).')
        else:
            cur.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-2) WHERE id=?", (pid,))
            return ('Конфликт с керри',
                    f'{nick} требовал приоритет фарма — отказ. Мораль −2.', 'popup')

    if event == 'equipment_theft':
        loss = random.choice([15_000, 20_000, 25_000])
        cur.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (loss, team_id))
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET morale=MAX(1,COALESCE(morale,5)-1) WHERE id IN ({phs})",
            list(player_ids)
        )
        incidents = [
            'ограбление на буткемпе — украдены ноутбуки и периферия',
            'пожар в офисе уничтожил оборудование',
            'кража компьютеров на выездном турнире',
        ]
        return ('Форс-мажор: оборудование',
                f'{random.choice(incidents)}. Потери: −${loss:,}, −1 мораль.', 'popup')

    if event == 'comeback_veteran':
        cur.execute(
            "SELECT id, nickname, micro_skills, macro_skills, soft_skills, "
            "COALESCE(skill_cap,300), COALESCE(age,25) "
            "FROM players WHERE id IN ({})".format(','.join('?' * len(player_ids))),
            list(player_ids)
        )
        vets = [(r[0], r[1], r[2] or 0, r[3] or 0, r[4] or 0, r[5], r[6])
                for r in cur.fetchall() if r[6] >= 28]
        if not vets:
            return None
        pid, nick, micro, macro, soft, cap, age = random.choice(vets)
        total = micro + macro + soft
        if total >= cap:
            return None
        gain = random.randint(3, 6)
        best = max([('micro_skills', micro), ('macro_skills', macro), ('soft_skills', soft)],
                   key=lambda x: x[1])[0]
        cur.execute(f"UPDATE players SET {best}=MIN(100,{best}+?) WHERE id=?", (gain, pid))
        cur.execute("UPDATE players SET morale=MIN(10,COALESCE(morale,5)+1) WHERE id=?", (pid,))
        return ('Второе дыхание',
                f'{nick} ({age} лет) нашёл мотивацию: +{gain} {best.split("_")[0].capitalize()}, +1 мораль')

    return None
