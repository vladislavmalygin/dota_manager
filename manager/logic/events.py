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
    ('no_event',             3),
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

    event = random.choices(_EVENT_NAMES, weights=_EVENT_WEIGHTS, k=1)[0]
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
