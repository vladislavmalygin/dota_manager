import sqlite3
import random

_EVENTS = [
    ('sponsor_bonus',     15),
    ('player_inspired',   15),
    ('player_injury',     15),
    ('team_morale_boost', 15),
    ('team_morale_drop',  12),
    ('equipment_upgrade',  8),
    ('fine',              15),
    ('no_event',           5),
]
_EVENT_NAMES, _EVENT_WEIGHTS = zip(*_EVENTS)


def random_event_monthly(db_name):
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

    event = random.choices(_EVENT_NAMES, weights=_EVENT_WEIGHTS, k=1)[0]
    result = _apply(cur, event, team_id, player_ids)

    conn.commit()
    conn.close()
    return result


def _apply(cur, event, team_id, player_ids):
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
        names = {
            'micro_skills': 'микроскилл',
            'macro_skills': 'макроскилл',
            'soft_skills':  'мягкие навыки',
        }
        return ('Вдохновение', f'{nick} провёл самостоятельную тренировку: +{gain} {names[weakest_col]}')

    if event == 'player_injury':
        pid = random.choice(player_ids)
        cur.execute("SELECT nickname, micro_skills, macro_skills FROM players WHERE id=?", (pid,))
        p = cur.fetchone()
        if not p:
            return None
        nick, micro, macro = p
        micro, macro = micro or 0, macro or 0
        loss = random.randint(3, 7)
        if micro >= macro:
            cur.execute("UPDATE players SET micro_skills=MAX(1,micro_skills-?) WHERE id=?", (loss, pid))
            return ('Травма', f'{nick} получил травму руки: −{loss} микроскилл')
        else:
            cur.execute("UPDATE players SET macro_skills=MAX(1,macro_skills-?) WHERE id=?", (loss, pid))
            return ('Травма', f'{nick} получил травму: −{loss} макроскилл')

    if event == 'team_morale_boost':
        delta = random.randint(1, 2)
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET morale=MIN(10,COALESCE(morale,5)+?) WHERE id IN ({phs})",
            [delta] + list(player_ids)
        )
        return ('Командный дух', f'Отличная атмосфера в команде: +{delta} мораль всем игрокам')

    if event == 'team_morale_drop':
        delta = random.randint(1, 2)
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET morale=MAX(1,COALESCE(morale,5)-?) WHERE id IN ({phs})",
            [delta] + list(player_ids)
        )
        return ('Напряжение', f'Напряжённая обстановка в коллективе: −{delta} мораль')

    if event == 'equipment_upgrade':
        phs = ','.join('?' * len(player_ids))
        cur.execute(
            f"UPDATE players SET soft_skills=MIN(100,COALESCE(soft_skills,0)+2) WHERE id IN ({phs})",
            list(player_ids)
        )
        return ('Новое оборудование', 'Команда получила новую периферию: +2 мягкие навыки всем')

    if event == 'fine':
        fine = random.choice([10_000, 15_000, 20_000, 30_000])
        cur.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (fine, team_id))
        return ('Штраф', f'Административный штраф от лиги: −${fine:,}')

    return None
