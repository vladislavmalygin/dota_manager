"""
Monthly player dialogue events. Returns a dialogue dict or None.
Each dialogue has: title, text, player_nick, choices list of (label, callback_key).
The caller (UI) renders buttons and calls apply_dialogue_choice(db_name, dialogue, choice_key).
"""
import sqlite3
import random

_DIALOGUE_CHANCE = 0.35   # probability any dialogue fires this month


def get_player_dialogue(db_name):
    """Return dialogue dict or None. Does NOT modify the DB yet."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute(
        "SELECT id, carry, mid, offlane, partial_support, full_support "
        "FROM teams WHERE player='yes'"
    )
    team = c.fetchone()
    if not team:
        conn.close()
        return None
    team_id = team[0]
    pids = [p for p in team[1:] if p]
    if not pids:
        conn.close()
        return None

    if random.random() > _DIALOGUE_CHANCE:
        conn.close()
        return None

    pid = random.choice(pids)
    c.execute(
        "SELECT nickname, COALESCE(morale,5), COALESCE(wage,0), "
        "COALESCE(expected_wage,0), role, COALESCE(age,22), "
        "COALESCE(micro_skills,0)+COALESCE(macro_skills,0) "
        "FROM players WHERE id=?", (pid,)
    )
    p = c.fetchone()
    conn.close()
    if not p:
        return None

    nick, morale, wage, exp_wage, role, age, skill = p

    dialogues = []

    # Wage request — underpaid or high morale and skill
    if wage < exp_wage * 0.85 or (skill >= 140 and wage < exp_wage):
        new_wage = int(exp_wage * 1.10)
        dialogues.append({
            'type':    'wage_request',
            'pid':     pid,
            'nick':    nick,
            'title':   f'{nick} просит повышение',
            'text':    (f'{nick} подошёл поговорить: «Я считаю, что моя работа стоит '
                        f'больше. Хочу ${new_wage:,}/мес вместо ${wage:,}.»'),
            'new_wage': new_wage,
            'choices': [
                ('✓ Согласиться', 'accept'),
                ('✗ Отказать',    'decline'),
            ],
        })

    # Happy message — high morale, good conditions
    if morale >= 8:
        dialogues.append({
            'type':  'happy',
            'pid':   pid,
            'nick':  nick,
            'title': f'{nick} доволен',
            'text':  random.choice([
                f'{nick}: «Я рад быть частью этой команды. Продолжаем работать!»',
                f'{nick}: «Атмосфера в команде отличная, мне нравится здесь.»',
                f'{nick}: «Всё идёт как надо, буду стараться ещё больше.»',
            ]),
            'choices': [('OK', 'ok')],
        })

    # Transfer request — low morale or long underpaid
    if morale <= 3:
        dialogues.append({
            'type':    'transfer_request',
            'pid':     pid,
            'nick':    nick,
            'title':   f'{nick} хочет уйти',
            'text':    (f'{nick}: «Я не вижу своего будущего здесь. '
                        f'Рассматриваю предложения от других команд.»'),
            'choices': [
                ('Отпустить',          'release'),
                ('Убедить остаться',   'keep'),
            ],
        })

    # Role change request — player not happy with current role
    if age <= 23 and skill >= 120:
        _ROLE_RU = {
            'carry': 'carry', 'mid': 'mid', 'offlane': 'offlane',
            'partial_support': 'support 4', 'full_support': 'support 5',
        }
        dialogues.append({
            'type':    'role_request',
            'pid':     pid,
            'nick':    nick,
            'title':   f'{nick} хочет сменить роль',
            'text':    (f'{nick} ({_ROLE_RU.get(role,role)}): «Мне интересно попробовать '
                        f'другую роль. Дашь шанс?»'),
            'choices': [
                ('Разрешить тренировать другую роль', 'accept'),
                ('Нет, оставайся на своей',           'decline'),
            ],
        })

    # Team conflict: one player demands another be removed
    if len(pids) >= 2 and random.random() < 0.12:
        other_pid = random.choice([p for p in pids if p != pid])
        c.execute("SELECT nickname FROM players WHERE id=?", (other_pid,))
        other_row = c.fetchone()
        if other_row:
            other_nick = other_row[0]
            dialogues.append({
                'type':       'team_conflict',
                'pid':        pid,
                'pid2':       other_pid,
                'nick':       nick,
                'nick2':      other_nick,
                'team_id':    team_id,
                'title':      'Конфликт в команде',
                'text':       (f'{nick} требует убрать {other_nick} из состава: '
                               f'«Либо он, либо я». '
                               f'Пока конфликт не решён — сыгранность 0.'),
                'choices': [
                    (f'Уволить {other_nick}',  'fire'),
                    ('Примирить (−2 мораль обоим)', 'reconcile'),
                ],
            })

    # Player wants out immediately (stronger than transfer_request)
    if morale <= 2:
        dialogues.append({
            'type':    'player_wants_out',
            'pid':     pid,
            'nick':    nick,
            'title':   f'{nick} категорически хочет уйти',
            'text':    (f'{nick}: «Я остаюсь только силой. Моя мотивация нулевая '
                        f'пока меня не отпустят.»'),
            'choices': [
                ('Отпустить немедленно', 'release'),
                ('Удержать (мораль 0)',  'force_keep'),
            ],
        })

    # Contract negotiation — player demands before expiry
    try:
        _cn = sqlite3.connect(db_name)
        ce_row = _cn.execute("SELECT contract_end FROM players WHERE id=?", (pid,)).fetchone()
        gd_row = _cn.execute("SELECT date FROM save WHERE id=1").fetchone()
        _cn.close()
    except Exception:
        ce_row = None
        gd_row = None
    if ce_row and ce_row[0]:
        try:
            from datetime import date as _date, timedelta as _td
            ce_date = _date.fromisoformat(ce_row[0])
            game_date = _date.fromisoformat(gd_row[0]) if gd_row else _date.today()
            days_left = (ce_date - game_date).days
            if 0 < days_left <= 45 and skill >= 100:
                demand_wage = int(exp_wage * random.uniform(1.10, 1.35))
                demands = random.choices(
                    ['wage', 'promise_top5', 'both'],
                    weights=[50, 30, 20]
                )[0]
                if demands == 'wage':
                    demand_text = f'Хочу контракт ${demand_wage:,}/мес.'
                elif demands == 'promise_top5':
                    demand_text = 'Хочу гарантию — команда попадёт в топ-5 на следующем Major.'
                else:
                    demand_text = f'Хочу ${demand_wage:,}/мес и гарантию результата.'
                dialogues.append({
                    'type':        'contract_negotiation',
                    'pid':         pid,
                    'nick':        nick,
                    'demands':     demands,
                    'demand_wage': demand_wage,
                    'days_left':   days_left,
                    'title':       f'{nick}: переговоры о контракте',
                    'text':        (f'{nick} ({days_left} дн. до конца контракта): «{demand_text}»'),
                    'choices': [
                        ('Принять условия',      'accept'),
                        ('Предложить меньше (-10%)', 'counter'),
                        ('Отказать',             'decline'),
                    ],
                })
        except Exception:
            pass

    if not dialogues:
        return None
    return random.choice(dialogues)


def apply_dialogue_choice(db_name, dialogue, choice_key):
    """Apply the chosen response. Returns (title, result_text)."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    pid  = dialogue['pid']
    nick = dialogue['nick']
    dtype = dialogue['type']
    result_text = ''

    if dtype == 'wage_request':
        if choice_key == 'accept':
            new_wage = dialogue['new_wage']
            c.execute("UPDATE players SET wage=?, expected_wage=?, morale=MIN(10,COALESCE(morale,5)+1) WHERE id=?",
                      (new_wage, new_wage, pid))
            c.execute("UPDATE teams SET budget=budget-(? * 12) WHERE player='yes'",
                      (new_wage - dialogue.get('old_wage', new_wage - 1000),))
            result_text = f'{nick} доволен: +1 мораль. Новая зарплата: ${new_wage:,}/мес.'
        else:
            c.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-1) WHERE id=?", (pid,))
            result_text = f'{nick} расстроен отказом: −1 мораль.'

    elif dtype == 'happy':
        c.execute("UPDATE players SET morale=MIN(10,COALESCE(morale,5)+1) WHERE id=?", (pid,))
        result_text = f'{nick}: +1 мораль от позитивного разговора.'

    elif dtype == 'transfer_request':
        if choice_key == 'release':
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (pid,))
            c.execute(
                "UPDATE teams SET carry=NULL WHERE player='yes' AND carry=?", (pid,))
            c.execute(
                "UPDATE teams SET mid=NULL WHERE player='yes' AND mid=?", (pid,))
            c.execute(
                "UPDATE teams SET offlane=NULL WHERE player='yes' AND offlane=?", (pid,))
            c.execute(
                "UPDATE teams SET partial_support=NULL WHERE player='yes' AND partial_support=?", (pid,))
            c.execute(
                "UPDATE teams SET full_support=NULL WHERE player='yes' AND full_support=?", (pid,))
            result_text = f'{nick} освобождён и стал свободным агентом.'
        else:
            bonus = 5000
            c.execute("UPDATE players SET morale=MIN(10,COALESCE(morale,5)+2) WHERE id=?", (pid,))
            c.execute("UPDATE teams SET budget=budget-? WHERE player='yes'", (bonus,))
            result_text = f'Убедил {nick} остаться (+2 мораль, −${bonus:,} бонус).'

    elif dtype == 'role_request':
        if choice_key == 'accept':
            c.execute("UPDATE players SET morale=MIN(10,COALESCE(morale,5)+1), "
                      "train_xp=COALESCE(train_xp,0)+1.0 WHERE id=?", (pid,))
            result_text = f'{nick} мотивирован: +1 мораль, +1 XP.'
        else:
            c.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-1) WHERE id=?", (pid,))
            result_text = f'{nick} разочарован: −1 мораль.'

    elif dtype == 'team_conflict':
        pid2 = dialogue.get('pid2')
        nick2 = dialogue.get('nick2', '?')
        team_id = dialogue.get('team_id')
        if choice_key == 'fire' and pid2:
            # Release the targeted player
            for col in ('carry', 'mid', 'offlane', 'partial_support', 'full_support'):
                c.execute(f"UPDATE teams SET {col}=NULL WHERE player='yes' AND {col}=?", (pid2,))
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (pid2,))
            c.execute("UPDATE players SET morale=MIN(10,COALESCE(morale,5)+2) WHERE id=?", (pid,))
            result_text = f'{nick2} уволен. {nick} доволен (+2 мораль).'
        else:
            # Reconcile — zero cohesion, both lose morale
            if team_id:
                c.execute("UPDATE teams SET cohesion=0 WHERE id=?", (team_id,))
            for p in [pid, pid2]:
                if p:
                    c.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-2) WHERE id=?", (p,))
            result_text = f'Примирение: сыгранность 0, оба теряют −2 мораль.'

    elif dtype == 'player_wants_out':
        if choice_key == 'release':
            for col in ('carry', 'mid', 'offlane', 'partial_support', 'full_support'):
                c.execute(f"UPDATE teams SET {col}=NULL WHERE player='yes' AND {col}=?", (pid,))
            c.execute("UPDATE players SET team_id=0, wage=0 WHERE id=?", (pid,))
            result_text = f'{nick} отпущен. Нужна замена.'
        else:
            c.execute("UPDATE players SET morale=1 WHERE id=?", (pid,))
            result_text = f'{nick} удержан силой. Мораль упала до 1.'

    elif dtype == 'contract_negotiation':
        demand_wage = dialogue.get('demand_wage', 0)
        demands     = dialogue.get('demands', 'wage')
        from datetime import timedelta as _td, date as _d
        c.execute("SELECT date FROM save WHERE id=1")
        gd = c.fetchone()
        game_date = _d.fromisoformat(gd[0]) if gd else _d.today()
        new_end = str(game_date + _td(days=365 * 2))

        if choice_key == 'accept':
            c.execute(
                "UPDATE players SET wage=?, expected_wage=?, morale=MIN(10,COALESCE(morale,5)+2), "
                "contract_end=?, renewal_notified=0 WHERE id=?",
                (demand_wage, demand_wage, new_end, pid)
            )
            result_text = (f'{nick} доволен условиями. Контракт продлён на 2 года. '
                           f'Зарплата: ${demand_wage:,}/мес. +2 мораль.')
        elif choice_key == 'counter':
            counter_wage = int(demand_wage * 0.90)
            # 60% chance player accepts counter
            if random.random() < 0.60:
                c.execute(
                    "UPDATE players SET wage=?, expected_wage=?, "
                    "morale=MIN(10,COALESCE(morale,5)+1), "
                    "contract_end=?, renewal_notified=0 WHERE id=?",
                    (counter_wage, counter_wage, new_end, pid)
                )
                result_text = (f'{nick} принял встречное предложение ${counter_wage:,}/мес. '
                               f'Контракт на 2 года. +1 мораль.')
            else:
                c.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-2) WHERE id=?", (pid,))
                result_text = f'{nick} отверг встречное предложение: −2 мораль. Риск потерять игрока.'
        else:
            c.execute("UPDATE players SET morale=MAX(1,COALESCE(morale,5)-2), "
                      "wants_to_leave=1 WHERE id=?", (pid,))
            result_text = f'{nick} обиделся на отказ: −2 мораль, хочет уйти.'

    conn.commit()
    conn.close()
    return (dialogue['title'], result_text)
