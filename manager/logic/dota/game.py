import random

from logic.dota.match_data import get_match_data

dispersion = 1000


def _early_game(team1, team2, skills, tokens):
    synergy = 1
    for tick in range(12):
        if tick % 2 == 0:
            if (random.randint(0, dispersion) + skills['team1']['team1_mid']['micro_skills'] >
                    random.randint(0, dispersion) + skills['team2']['team2_mid']['micro_skills']):
                tokens[team1] += 1
            else:
                tokens[team2] += 1

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_offlane']['micro_skills'] * synergy +
                    skills['team1']['team1_partial_support']['micro_skills'] >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_carry']['micro_skills'] * synergy +
                    skills['team2']['team2_full_support']['micro_skills'] * synergy):
                tokens[team1] += 2
            else:
                tokens[team2] += 2

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_carry']['micro_skills'] * synergy +
                    skills['team1']['team1_full_support']['micro_skills'] * synergy >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_offlane']['micro_skills'] * synergy +
                    skills['team2']['team2_partial_support']['micro_skills'] * synergy):
                tokens[team1] += 2
            else:
                tokens[team2] += 2


def _mid_game(team1, team2, skills, tokens):
    tick_params = [
        (['team1_mid', 'team1_partial_support', 'team1_full_support'],
         ['team2_mid', 'team2_partial_support', 'team2_full_support']),
        (['team1_mid', 'team1_partial_support', 'team1_offlane'],
         ['team2_mid', 'team2_partial_support', 'team2_offlane']),
        (['team1_mid', 'team1_carry', 'team1_offlane'],
         ['team2_mid', 'team2_carry', 'team2_offlane']),
    ]
    for t1_roles, t2_roles in tick_params:
        s1 = sum(skills['team1'][r][k] for r in t1_roles for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in t2_roles for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 4
        else:
            tokens[team2] += 4
        if abs(tokens[team1] - tokens[team2]) >= 24:
            return


def _late_game(team1, team2, skills, tokens):
    all_roles_t1 = ['team1_mid', 'team1_carry', 'team1_offlane', 'team1_partial_support', 'team1_full_support']
    all_roles_t2 = ['team2_mid', 'team2_carry', 'team2_offlane', 'team2_partial_support', 'team2_full_support']

    while abs(tokens[team1] - tokens[team2]) < 24:
        s1 = sum(skills['team1'][r][k] for r in all_roles_t1 for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in all_roles_t2 for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 8
        else:
            tokens[team2] += 8


def dota_simulation_for_bots(team1, team2, skills):
    tokens = {team1: 0, team2: 0}
    _early_game(team1, team2, skills, tokens)
    _mid_game(team1, team2, skills, tokens)
    _late_game(team1, team2, skills, tokens)
    return team1 if tokens[team1] > tokens[team2] else team2


_K  = '[color=ffd700]'   # kills / first blood
_T  = '[color=ff7722]'   # towers
_R  = '[color=cc88ff]'   # roshan / objectives
_W  = '[color=44ff88]'   # winner / positive
_H  = '[color=55ccff]'   # phase headers
_D  = '[color=555555]'   # dim separators
_X  = '[/color]'


def _nick(skills, team_key, role_suffix):
    return skills[team_key].get(f'{team_key}_{role_suffix}', {}).get('nickname', '?')


# ── Per-event map positions ───────────────────────────────────────────────────
# (nx, ny) in 0-1 normalised space; Radiant=team1 bottom-left, Dire=team2 top-right

# Base phase positions (fallback)
_BASE_POS = {
    'laning': {
        'team1_carry':           (0.44, 0.10), 'team1_mid':             (0.34, 0.30),
        'team1_offlane':         (0.10, 0.44), 'team1_partial_support': (0.14, 0.38),
        'team1_full_support':    (0.38, 0.14),
        'team2_carry':           (0.56, 0.90), 'team2_mid':             (0.66, 0.70),
        'team2_offlane':         (0.90, 0.56), 'team2_partial_support': (0.86, 0.62),
        'team2_full_support':    (0.62, 0.86),
    },
    'midgame': {
        'team1_carry':           (0.40, 0.32), 'team1_mid':             (0.44, 0.46),
        'team1_offlane':         (0.28, 0.52), 'team1_partial_support': (0.32, 0.44),
        'team1_full_support':    (0.38, 0.38),
        'team2_carry':           (0.60, 0.68), 'team2_mid':             (0.56, 0.54),
        'team2_offlane':         (0.72, 0.48), 'team2_partial_support': (0.68, 0.56),
        'team2_full_support':    (0.62, 0.62),
    },
    'lategame': {
        'team1_carry':           (0.46, 0.46), 'team1_mid':             (0.44, 0.50),
        'team1_offlane':         (0.40, 0.52), 'team1_partial_support': (0.38, 0.48),
        'team1_full_support':    (0.42, 0.44),
        'team2_carry':           (0.54, 0.54), 'team2_mid':             (0.56, 0.50),
        'team2_offlane':         (0.60, 0.48), 'team2_partial_support': (0.62, 0.52),
        'team2_full_support':    (0.58, 0.56),
    },
}

# Event-context overrides: positions when specific action occurs
_CTX_POSITIONS = {
    # Laning: mid fight
    'mid_t1': {   # t1 winning mid
        'team1_mid': (0.42, 0.42), 'team2_mid': (0.60, 0.60),
    },
    'mid_t2': {   # t2 winning mid
        'team1_mid': (0.38, 0.34), 'team2_mid': (0.58, 0.56),
    },
    # Laning: top fight (t1 offlane vs t2 carry)
    'top_t1': {
        'team1_offlane': (0.14, 0.58), 'team1_partial_support': (0.12, 0.50),
        'team2_carry': (0.20, 0.70), 'team2_full_support': (0.16, 0.76),
    },
    'top_t2': {
        'team2_carry': (0.10, 0.62), 'team2_full_support': (0.12, 0.68),
        'team1_offlane': (0.18, 0.50), 'team1_partial_support': (0.14, 0.44),
    },
    # Laning: bot fight (t1 carry vs t2 offlane)
    'bot_t1': {
        'team1_carry': (0.54, 0.12), 'team1_full_support': (0.48, 0.12),
        'team2_offlane': (0.66, 0.12), 'team2_partial_support': (0.70, 0.14),
    },
    'bot_t2': {
        'team2_offlane': (0.60, 0.14), 'team2_partial_support': (0.64, 0.10),
        'team1_carry': (0.48, 0.10), 'team1_full_support': (0.44, 0.12),
    },
    # Midgame: smoke gank t1
    'smoke_t1': {
        'team1_carry': (0.52, 0.48), 'team1_mid': (0.50, 0.52),
        'team1_offlane': (0.48, 0.50), 'team1_partial_support': (0.50, 0.46),
        'team1_full_support': (0.46, 0.50),
    },
    # Midgame: smoke gank t2
    'smoke_t2': {
        'team2_carry': (0.48, 0.52), 'team2_mid': (0.50, 0.48),
        'team2_offlane': (0.52, 0.50), 'team2_partial_support': (0.50, 0.54),
        'team2_full_support': (0.54, 0.50),
    },
    # Midgame: teamfight center
    'fight_t1': {
        'team1_carry': (0.44, 0.46), 'team1_mid': (0.46, 0.50),
        'team1_offlane': (0.42, 0.52), 'team1_partial_support': (0.44, 0.48),
        'team1_full_support': (0.40, 0.50),
        'team2_carry': (0.58, 0.56), 'team2_mid': (0.56, 0.52),
        'team2_offlane': (0.60, 0.50), 'team2_partial_support': (0.58, 0.54),
        'team2_full_support': (0.62, 0.52),
    },
    'fight_t2': {
        'team1_carry': (0.58, 0.54), 'team1_mid': (0.56, 0.50),
        'team1_offlane': (0.60, 0.48), 'team1_partial_support': (0.58, 0.52),
        'team1_full_support': (0.62, 0.50),
        'team2_carry': (0.44, 0.46), 'team2_mid': (0.46, 0.50),
        'team2_offlane': (0.42, 0.52), 'team2_partial_support': (0.44, 0.48),
        'team2_full_support': (0.40, 0.50),
    },
    # Roshan
    'roshan': {
        'team1_carry': (0.32, 0.58), 'team1_mid': (0.30, 0.60),
        'team1_offlane': (0.28, 0.56), 'team1_partial_support': (0.34, 0.58),
        'team1_full_support': (0.30, 0.54),
    },
    # Lategame: high-ground push t1
    'hg_push_t1': {
        'team1_carry': (0.72, 0.72), 'team1_mid': (0.68, 0.76),
        'team1_offlane': (0.64, 0.72), 'team1_partial_support': (0.70, 0.68),
        'team1_full_support': (0.66, 0.68),
        'team2_carry': (0.80, 0.80), 'team2_mid': (0.82, 0.76),
        'team2_offlane': (0.84, 0.80), 'team2_partial_support': (0.78, 0.82),
        'team2_full_support': (0.82, 0.82),
    },
    'hg_push_t2': {
        'team2_carry': (0.28, 0.28), 'team2_mid': (0.32, 0.24),
        'team2_offlane': (0.36, 0.28), 'team2_partial_support': (0.30, 0.32),
        'team2_full_support': (0.34, 0.32),
        'team1_carry': (0.20, 0.20), 'team1_mid': (0.18, 0.24),
        'team1_offlane': (0.16, 0.20), 'team1_partial_support': (0.22, 0.18),
        'team1_full_support': (0.18, 0.18),
    },
    # Split push
    'split_t1': {
        'team1_carry': (0.78, 0.10), 'team1_mid': (0.48, 0.50),
        'team1_offlane': (0.46, 0.50), 'team1_partial_support': (0.50, 0.48),
        'team1_full_support': (0.44, 0.52),
    },
    'split_t2': {
        'team2_carry': (0.22, 0.90), 'team2_mid': (0.52, 0.50),
        'team2_offlane': (0.54, 0.50), 'team2_partial_support': (0.50, 0.52),
        'team2_full_support': (0.56, 0.48),
    },
}


def _get_event_positions(phase, event_text, event_type, winning_team, team1, team2):
    """Return full positions dict for this event by merging base + context overrides."""
    import copy
    base = copy.deepcopy(_BASE_POS.get(phase, _BASE_POS['laning']))
    ctx  = {}

    txt = event_text.lower()
    is_t1_win = (winning_team == team1) if winning_team else None

    if phase == 'laning':
        if 'мид' in txt or 'mid' in txt:
            ctx = _CTX_POSITIONS['mid_t1' if is_t1_win else 'mid_t2']
        elif 'топ' in txt or 'top' in txt:
            ctx = _CTX_POSITIONS['top_t1' if is_t1_win else 'top_t2']
        elif 'бот' in txt or 'bot' in txt:
            ctx = _CTX_POSITIONS['bot_t1' if is_t1_win else 'bot_t2']
    elif phase == 'midgame':
        if 'рошан' in txt or 'roshan' in txt:
            ctx = _CTX_POSITIONS['roshan']
        elif 'smoke' in txt or 'смок' in txt or 'ганк' in txt:
            ctx = _CTX_POSITIONS['smoke_t1' if is_t1_win else 'smoke_t2']
        elif ('тимфайт' in txt or 'командный' in txt or 'teamfight' in txt
              or 'бой' in txt or 'убийств' in txt):
            ctx = _CTX_POSITIONS['fight_t1' if is_t1_win else 'fight_t2']
        elif 'сплит' in txt or 'split' in txt:
            ctx = _CTX_POSITIONS['split_t1' if is_t1_win else 'split_t2']
    elif phase == 'lategame':
        if 'хай' in txt or 'high' in txt or 'highground' in txt or 'хайграунд' in txt:
            ctx = _CTX_POSITIONS['hg_push_t1' if is_t1_win else 'hg_push_t2']
        elif 'тимфайт' in txt or 'teamfight' in txt or 'финальн' in txt:
            ctx = _CTX_POSITIONS['fight_t1' if is_t1_win else 'fight_t2']

    if event_type == 'kill':
        # For kills, merge fight positions
        kill_ctx = _CTX_POSITIONS['fight_t1' if is_t1_win else 'fight_t2']
        ctx = {**kill_ctx, **ctx}

    base.update(ctx)
    return base


def _fresh_towers():
    return {
        'top': [True, True, True],   # [T1, T2, T3]  T1=outermost
        'mid': [True, True, True],
        'bot': [True, True, True],
        'hg':  [True, True],
        'throne': True,
    }


def _tower_count(state):
    n = sum(state['top']) + sum(state['mid']) + sum(state['bot']) + sum(state['hg'])
    return n + (1 if state['throne'] else 0)


def _apply_strat_mods(skills, team_key, strat_key, phase, strategies_dict):
    """Return a copy of team's role skills with strategy multipliers for a phase."""
    from logic.dota.strategies import get_phase_mods
    mods = get_phase_mods(strat_key, phase, strategies_dict)
    if not mods:
        return skills[team_key]
    result = {}
    for role, rskills in skills[team_key].items():
        rs = dict(rskills)
        # global skill mods
        if 'micro' in mods:
            rs['micro_skills'] = max(1, int(rs.get('micro_skills', 1) * mods['micro']))
        if 'macro' in mods:
            rs['macro_skills'] = max(1, int(rs.get('macro_skills', 1) * mods['macro']))
        if 'soft' in mods:
            rs['soft_skills'] = max(1, int(rs.get('soft_skills', 1) * mods['soft']))
        # role-specific mods
        is_mid  = 'mid' in role
        is_side = 'carry' in role or 'offlane' in role
        if 'mid_micro' in mods and is_mid:
            rs['micro_skills'] = max(1, int(rs.get('micro_skills', 1) * mods['mid_micro']))
        if 'side_micro' in mods and is_side:
            rs['micro_skills'] = max(1, int(rs.get('micro_skills', 1) * mods['side_micro']))
        if 'carry_micro' in mods and 'carry' in role:
            rs['micro_skills'] = max(1, int(rs.get('micro_skills', 1) * mods['carry_micro']))
        result[role] = rs
    return result


def dota_simulation_logged(team1, team2, skills):
    """Returns (winner, log_lines, snapshots, stats)."""
    from logic.dota.strategies import EARLY_STRATEGIES, MID_STRATEGIES, LATE_STRATEGIES, get_specials
    tokens  = {team1: 0, team2: 0}
    kills   = {team1: 0, team2: 0}
    towers  = {team1: _fresh_towers(), team2: _fresh_towers()}
    lines   = []
    snaps   = []
    minute  = 0

    strat_t1 = skills.get('strat_t1', {})
    strat_t2 = skills.get('strat_t2', {})

    # special flags merged from both teams' strategies
    def _spec(strat_dict, phase_strats, key, default):
        s = get_specials(strat_dict.get(phase_strats, ''), {
            'early': EARLY_STRATEGIES, 'mid': MID_STRATEGIES, 'late': LATE_STRATEGIES
        }.get(phase_strats, {}))
        return s.get(key, default)

    # player nicknames
    t1 = {
        'carry': _nick(skills, 'team1', 'carry'),
        'mid':   _nick(skills, 'team1', 'mid'),
        'off':   _nick(skills, 'team1', 'offlane'),
        'ps':    _nick(skills, 'team1', 'partial_support'),
        'fs':    _nick(skills, 'team1', 'full_support'),
    }
    t2 = {
        'carry': _nick(skills, 'team2', 'carry'),
        'mid':   _nick(skills, 'team2', 'mid'),
        'off':   _nick(skills, 'team2', 'offlane'),
        'ps':    _nick(skills, 'team2', 'partial_support'),
        'fs':    _nick(skills, 'team2', 'full_support'),
    }

    # Hero names passed via skills (optional, set by pre-match picker)
    hero_names = skills.get('hero_names', {})  # role_key → hero_name

    def _snap(phase, event='', winner_team=None, event_line=''):
        import copy
        pos = _get_event_positions(phase, event_line or event, event, winner_team, team1, team2)
        return {
            'phase':           phase,
            'minute':          minute,
            'kills_t1':        kills[team1],
            'kills_t2':        kills[team2],
            'tokens_t1':       tokens[team1],
            'tokens_t2':       tokens[team2],
            'towers_t1':       _tower_count(towers[team1]),
            'towers_t2':       _tower_count(towers[team2]),
            'towers_state_t1': copy.deepcopy(towers[team1]),
            'towers_state_t2': copy.deepcopy(towers[team2]),
            'players_t1':      dict(t1),
            'players_t2':      dict(t2),
            'hero_names':      hero_names,
            'positions':       pos,
            '_event':          event,
        }

    _last_winner = [None]

    def _add(line, phase, event='', winner_team=None):
        if winner_team:
            _last_winner[0] = winner_team
        lines.append(line)
        snaps.append(_snap(phase, event, _last_winner[0], line))

    def _sep(phase):
        _add(f'{_D}{"─" * 44}{_X}', phase)

    def _tower_fall(winning_team, lane, phase):
        loser    = team2 if winning_team == team1 else team1
        attacker = t1[lane] if winning_team == team1 else t2[lane]
        # Map role-based lane name to tower dict key
        lane_key = {'carry': 'bot', 'off': 'top', 'mid': 'mid'}.get(lane, 'mid')
        lane_list = towers[loser].get(lane_key, [])
        # Cascade: destroy outermost alive tower (T1 before T2 before T3)
        fell = False
        for i, alive in enumerate(lane_list):
            if alive:
                towers[loser][lane_key][i] = False
                fell = True
                break
        if not fell:
            # Lane towers all gone — try HG
            for i, alive in enumerate(towers[loser]['hg']):
                if alive:
                    towers[loser]['hg'][i] = False
                    fell = True
                    break
        if fell:
            c1 = _tower_count(towers[team1])
            c2 = _tower_count(towers[team2])
            _add(f'  {_T}Башня на {_lane_name(lane)} рухнула! ({attacker})  '
                 f'[{c1}↑ — ↑{c2}]{_X}', phase, 'tower')

    def _lane_name(lane):
        return {'carry': 'боте', 'off': 'топе', 'mid': 'миде'}.get(lane, lane)

    # ── LANING ───────────────────────────────────────────────────────────────
    _sep('laning')
    # Apply early strategies
    early_key_t1 = strat_t1.get('early', 'safe_farm')
    early_key_t2 = strat_t2.get('early', 'safe_farm')
    es1 = _apply_strat_mods(skills, 'team1', early_key_t1, 'laning', EARLY_STRATEGIES)
    es2 = _apply_strat_mods(skills, 'team2', early_key_t2, 'laning', EARLY_STRATEGIES)
    fb_mult_t1 = get_specials(early_key_t1, EARLY_STRATEGIES).get('first_blood_mult', 1.0)
    fb_mult_t2 = get_specials(early_key_t2, EARLY_STRATEGIES).get('first_blood_mult', 1.0)
    et_chance_t1 = get_specials(early_key_t1, EARLY_STRATEGIES).get('early_tower_chance', 0.30)
    et_chance_t2 = get_specials(early_key_t2, EARLY_STRATEGIES).get('early_tower_chance', 0.30)
    early_strat_name_t1 = EARLY_STRATEGIES.get(early_key_t1, {}).get('name', '')
    early_strat_name_t2 = EARLY_STRATEGIES.get(early_key_t2, {}).get('name', '')
    _add(f'  {_H}ЛАЙНСТЕЙДЖ{_X}', 'laning')
    _add(f'  Стратегия {team1}: [b]{early_strat_name_t1}[/b]  |  '
         f'{team2}: [b]{early_strat_name_t2}[/b]', 'laning')
    _sep('laning')

    # Override local skill refs for laning phase
    def _es1(role, key): return es1.get(role, {}).get(key, 1)
    def _es2(role, key): return es2.get(role, {}).get(key, 1)

    first_blood = False
    synergy = 1

    for tick in range(12):
        minute = tick

        # mid lane
        if tick % 2 == 0:
            m1 = random.randint(0, dispersion) + _es1('team1_mid', 'micro_skills')
            m2 = random.randint(0, dispersion) + _es2('team2_mid', 'micro_skills')
            if m1 > m2:
                tokens[team1] += 1
                if not first_blood and random.random() < 0.6 * fb_mult_t1:
                    kills[team1] += 1
                    first_blood = True
                    _add(f'  {_K}ПЕРВАЯ КРОВЬ:  {t1["mid"]} убивает {t2["mid"]}  '
                         f'[{kills[team1]}:{kills[team2]}]{_X}', 'laning', 'kill', winner_team=team1)
                else:
                    kills[team1] += random.randint(0, 1)
                    _add(f'  Мид:  {t1["mid"]} доминирует  '
                         f'[{tokens[team1]}:{tokens[team2]}]', 'laning')
            else:
                tokens[team2] += 1
                if not first_blood and random.random() < 0.6 * fb_mult_t2:
                    kills[team2] += 1
                    first_blood = True
                    _add(f'  {_K}ПЕРВАЯ КРОВЬ:  {t2["mid"]} убивает {t1["mid"]}  '
                         f'[{kills[team1]}:{kills[team2]}]{_X}', 'laning', 'kill', winner_team=team2)
                else:
                    kills[team2] += random.randint(0, 1)
                    _add(f'  Мид:  {t2["mid"]} доминирует  '
                         f'[{tokens[team1]}:{tokens[team2]}]', 'laning')

        # top lane
        if tick % 3 == 0:
            s1 = (random.randint(0, dispersion)
                  + _es1('team1_offlane', 'micro_skills') * synergy
                  + _es1('team1_partial_support', 'micro_skills'))
            s2 = (random.randint(0, dispersion)
                  + _es2('team2_carry', 'micro_skills') * synergy
                  + _es2('team2_full_support', 'micro_skills'))
            if s1 > s2:
                tokens[team1] += 2
                kills[team1] += random.randint(1, 2)
                _add(f'  Топ:  {t1["off"]} + {t1["ps"]} выигрывают лайн  '
                     f'[{tokens[team1]}:{tokens[team2]}]', 'laning', winner_team=team1)
                if random.random() < et_chance_t1:
                    _tower_fall(team1, 'off', 'laning')
            else:
                tokens[team2] += 2
                kills[team2] += random.randint(1, 2)
                _add(f'  Топ:  {t2["carry"]} + {t2["fs"]} выигрывают лайн  '
                     f'[{tokens[team1]}:{tokens[team2]}]', 'laning', winner_team=team2)
                if random.random() < et_chance_t2:
                    _tower_fall(team2, 'off', 'laning')

        # bot lane
        if tick % 3 == 0:
            s1 = (random.randint(0, dispersion)
                  + _es1('team1_carry', 'micro_skills') * synergy
                  + _es1('team1_full_support', 'micro_skills'))
            s2 = (random.randint(0, dispersion)
                  + _es2('team2_offlane', 'micro_skills') * synergy
                  + _es2('team2_partial_support', 'micro_skills'))
            if s1 > s2:
                tokens[team1] += 2
                kills[team1] += random.randint(1, 2)
                _add(f'  Бот:  {t1["carry"]} (carry) уничтожает лайн  '
                     f'[{tokens[team1]}:{tokens[team2]}]', 'laning', winner_team=team1)
                if random.random() < et_chance_t1:
                    _tower_fall(team1, 'carry', 'laning')
            else:
                tokens[team2] += 2
                kills[team2] += random.randint(1, 2)
                _add(f'  Бот:  {t2["carry"]} (carry) уничтожает лайн  '
                     f'[{tokens[team1]}:{tokens[team2]}]', 'laning', winner_team=team2)
                if random.random() < et_chance_t2:
                    _tower_fall(team2, 'carry', 'laning')

    minute = 12
    _add(f'  Итог лайна:  {team1} {tokens[team1]}  —  {tokens[team2]} {team2}', 'laning')

    # ── MIDGAME ───────────────────────────────────────────────────────────────
    _sep('midgame')
    mid_key_t1 = strat_t1.get('mid', 'map_control')
    mid_key_t2 = strat_t2.get('mid', 'map_control')
    ms1 = _apply_strat_mods(skills, 'team1', mid_key_t1, 'midgame', MID_STRATEGIES)
    ms2 = _apply_strat_mods(skills, 'team2', mid_key_t2, 'midgame', MID_STRATEGIES)
    smoke_chance_t1 = get_specials(mid_key_t1, MID_STRATEGIES).get('smoke_chance', 0.25)
    smoke_chance_t2 = get_specials(mid_key_t2, MID_STRATEGIES).get('smoke_chance', 0.25)
    smoke_mult_t1   = get_specials(mid_key_t1, MID_STRATEGIES).get('smoke_bonus_mult', 1.0)
    smoke_mult_t2   = get_specials(mid_key_t2, MID_STRATEGIES).get('smoke_bonus_mult', 1.0)
    tower_mult_t1   = get_specials(mid_key_t1, MID_STRATEGIES).get('mid_tower_chance_mult', 1.0)
    tower_mult_t2   = get_specials(mid_key_t2, MID_STRATEGIES).get('mid_tower_chance_mult', 1.0)
    mid_strat_name_t1 = MID_STRATEGIES.get(mid_key_t1, {}).get('name', '')
    mid_strat_name_t2 = MID_STRATEGIES.get(mid_key_t2, {}).get('name', '')
    _add(f'  {_H}МИДГЕЙМ — КОМАНДНЫЕ БОИ{_X}', 'midgame')
    _add(f'  Стратегия {team1}: [b]{mid_strat_name_t1}[/b]  |  '
         f'{team2}: [b]{mid_strat_name_t2}[/b]', 'midgame')
    _sep('midgame')

    def _ms1(role, key): return ms1.get(role, {}).get(key, 1)
    def _ms2(role, key): return ms2.get(role, {}).get(key, 1)

    mid_combos = [
        (['team1_mid', 'team1_partial_support', 'team1_full_support'],
         ['team2_mid', 'team2_partial_support', 'team2_full_support'],
         'team1_mid', 'team2_mid'),
        (['team1_mid', 'team1_partial_support', 'team1_offlane'],
         ['team2_mid', 'team2_partial_support', 'team2_offlane'],
         'team1_offlane', 'team2_offlane'),
        (['team1_mid', 'team1_carry', 'team1_offlane'],
         ['team2_mid', 'team2_carry', 'team2_offlane'],
         'team1_carry', 'team2_carry'),
    ]
    _smoke_used = {team1: False, team2: False}

    for i, (r1, r2, hero1_key, hero2_key) in enumerate(mid_combos):
        minute = 15 + i * 5
        s1 = sum(_ms1(r, k) for r in r1 for k in ('macro_skills', 'micro_skills'))
        s2 = sum(_ms2(r, k) for r in r2 for k in ('macro_skills', 'micro_skills'))

        if not _smoke_used[team1] and random.random() < smoke_chance_t1:
            s1 += int(dispersion * smoke_mult_t1 / 4)
            _smoke_used[team1] = True
            _add(f'  {_R}Смок-ганг! {team1} выходит в лес...{_X}', 'midgame', 'smoke')

        if not _smoke_used[team2] and random.random() < smoke_chance_t2:
            s2 += int(dispersion * smoke_mult_t2 / 4)
            _smoke_used[team2] = True
            _add(f'  {_R}Смок-ганг! {team2} выходит в лес...{_X}', 'midgame', 'smoke')

        hero1 = ms1.get(hero1_key, {}).get('nickname', team1)
        hero2 = ms2.get(hero2_key, {}).get('nickname', team2)

        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 4
            ks = random.randint(2, 4)
            kills[team1] += ks
            _add(f'  {_K}Тимфайт: {hero1} ведёт {team1} к победе! +{ks} килов  '
                 f'[{kills[team1]}:{kills[team2]}]{_X}', 'midgame', 'kill', winner_team=team1)
            if random.random() < 0.50 * tower_mult_t1:
                _tower_fall(team1, 'mid', 'midgame')
        else:
            tokens[team2] += 4
            ks = random.randint(2, 4)
            kills[team2] += ks
            _add(f'  {_K}Тимфайт: {hero2} ведёт {team2} к победе! +{ks} килов  '
                 f'[{kills[team1]}:{kills[team2]}]{_X}', 'midgame', 'kill', winner_team=team2)
            if random.random() < 0.50 * tower_mult_t2:
                _tower_fall(team2, 'mid', 'midgame')

        if abs(tokens[team1] - tokens[team2]) >= 24:
            winner = team1 if tokens[team1] > tokens[team2] else team2
            _add(f'  {_W}Разгром на мидгейме: {winner}!{_X}', 'midgame')
            _sep('midgame')
            _add(f'  {_W}ПОБЕДИТЕЛЬ: {winner}{_X}', 'midgame')
            return winner, lines, snaps, _make_stats(winner, team1, team2,
                                                      kills, towers, minute, skills, t1, t2)

    # ── LATEGAME ─────────────────────────────────────────────────────────────
    _sep('lategame')
    late_key_t1 = strat_t1.get('late', 'teamfight')
    late_key_t2 = strat_t2.get('late', 'teamfight')
    ls1 = _apply_strat_mods(skills, 'team1', late_key_t1, 'lategame', LATE_STRATEGIES)
    ls2 = _apply_strat_mods(skills, 'team2', late_key_t2, 'lategame', LATE_STRATEGIES)
    disp_mult_t1 = get_specials(late_key_t1, LATE_STRATEGIES).get('dispersion_mult', 1.0)
    disp_mult_t2 = get_specials(late_key_t2, LATE_STRATEGIES).get('dispersion_mult', 1.0)
    late_strat_name_t1 = LATE_STRATEGIES.get(late_key_t1, {}).get('name', '')
    late_strat_name_t2 = LATE_STRATEGIES.get(late_key_t2, {}).get('name', '')
    _add(f'  {_H}ЛЕЙТГЕЙМ{_X}', 'lategame')
    _add(f'  Стратегия {team1}: [b]{late_strat_name_t1}[/b]  |  '
         f'{team2}: [b]{late_strat_name_t2}[/b]', 'lategame')
    _sep('lategame')

    def _ls1(role, key): return ls1.get(role, {}).get(key, 1)
    def _ls2(role, key): return ls2.get(role, {}).get(key, 1)

    minute = 30
    all_r1 = ['team1_mid', 'team1_carry', 'team1_offlane',
               'team1_partial_support', 'team1_full_support']
    all_r2 = ['team2_mid', 'team2_carry', 'team2_offlane',
               'team2_partial_support', 'team2_full_support']
    rosh_alive = True

    _late_obj = [
        ('аутпост', 'R'),
        ('бараки', 'T'),
        ('башню трона', 'T'),
    ]

    while abs(tokens[team1] - tokens[team2]) < 24:
        s1 = sum(_ls1(r, k) for r in all_r1 for k in ('macro_skills', 'micro_skills'))
        s2 = sum(_ls2(r, k) for r in all_r2 for k in ('macro_skills', 'micro_skills'))

        if rosh_alive and random.random() < 0.35:
            rosh_alive = False
            rosh_winner = team1 if s1 > s2 else team2
            carrier = t1['carry'] if rosh_winner == team1 else t2['carry']
            tokens[rosh_winner] += 4
            kills[rosh_winner] += random.randint(1, 3)
            _add(f'  {_R}{minute} мин: {carrier} забирает Рошана → Aegis!  '
                 f'[{kills[team1]}:{kills[team2]}]{_X}', 'lategame', 'забрала Рошана')
            minute += 2
            continue

        d1 = int(dispersion * disp_mult_t1)
        d2 = int(dispersion * disp_mult_t2)
        if random.randint(0, d1) + s1 > random.randint(0, d2) + s2:
            tokens[team1] += 8
            ks = random.randint(2, 5)
            kills[team1] += ks
            obj, otype = random.choice(_late_obj)
            hero = random.choice([t1['carry'], t1['mid'], t1['off']])
            if otype == 'T':
                _tower_fall(team1, 'carry', 'lategame')
            _add(f'  {_K}{minute} мин: {hero} — {team1} уничтожает {obj}! +{ks} килов{_X}',
                 'lategame', 'kill', winner_team=team1)
        else:
            tokens[team2] += 8
            ks = random.randint(2, 5)
            kills[team2] += ks
            obj, otype = random.choice(_late_obj)
            hero = random.choice([t2['carry'], t2['mid'], t2['off']])
            if otype == 'T':
                _tower_fall(team2, 'carry', 'lategame')
            _add(f'  {_K}{minute} мин: {hero} — {team2} уничтожает {obj}! +{ks} килов{_X}',
                 'lategame', 'kill', winner_team=team2)
        minute += 5

    winner = team1 if tokens[team1] > tokens[team2] else team2
    _sep('lategame')
    _add(f'  {_W}ПОБЕДИТЕЛЬ: {winner}{_X}', 'lategame')
    stats = _make_stats(winner, team1, team2, kills, towers, minute, skills, t1, t2)
    return winner, lines, snaps, stats


def _make_stats(winner, team1, team2, kills, towers, minute, skills, t1, t2):
    """Build match summary stats for UI display."""
    wt = 'team1' if winner == team1 else 'team2'
    wnicks = t1 if winner == team1 else t2
    roles  = ['carry', 'mid', 'off', 'ps', 'fs']
    role_keys = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
    best_nick, best_score, best_role = None, 0, 'carry'
    for r, rk in zip(roles, role_keys):
        s = skills[wt].get(f'{wt}_{rk}', {})
        sc = s.get('micro_skills', 0) + s.get('macro_skills', 0)
        nick = s.get('nickname')
        if nick and sc > best_score:
            best_score = sc; best_nick = nick; best_role = rk
    return {
        'kills_t1':  kills[team1],
        'kills_t2':  kills[team2],
        'towers_t1': _tower_count(towers[team1]),
        'towers_t2': _tower_count(towers[team2]),
        'duration':  minute,
        'mvp_nick':  best_nick or winner,
        'mvp_role':  best_role,
    }


def dota_simulation(team1, team2, skills):
    """Версия с выводом для матчей игрока (без задержек)."""
    tokens = {team1: 0, team2: 0}
    synergy = 1

    print(f"\n=== МАТЧ: {team1} vs {team2} ===")

    for tick in range(12):
        if tick % 2 == 0:
            if (random.randint(0, dispersion) + skills['team1']['team1_mid']['micro_skills'] >
                    random.randint(0, dispersion) + skills['team2']['team2_mid']['micro_skills']):
                tokens[team1] += 1
                print(f"  Мид: {team1} получает преимущество [{tokens[team1]}:{tokens[team2]}]")
            else:
                tokens[team2] += 1
                print(f"  Мид: {team2} получает преимущество [{tokens[team1]}:{tokens[team2]}]")

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_offlane']['micro_skills'] * synergy +
                    skills['team1']['team1_partial_support']['micro_skills'] >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_carry']['micro_skills'] * synergy +
                    skills['team2']['team2_full_support']['micro_skills'] * synergy):
                tokens[team1] += 2
                print(f"  Топ: {team1} выигрывает лайн [{tokens[team1]}:{tokens[team2]}]")
            else:
                tokens[team2] += 2
                print(f"  Топ: {team2} выигрывает лайн [{tokens[team1]}:{tokens[team2]}]")

        if tick % 3 == 0:
            if (random.randint(0, dispersion) +
                    skills['team1']['team1_carry']['micro_skills'] * synergy +
                    skills['team1']['team1_full_support']['micro_skills'] * synergy >
                    random.randint(0, dispersion) +
                    skills['team2']['team2_offlane']['micro_skills'] * synergy +
                    skills['team2']['team2_partial_support']['micro_skills'] * synergy):
                tokens[team1] += 2
                print(f"  Бот: {team1} выигрывает лайн [{tokens[team1]}:{tokens[team2]}]")
            else:
                tokens[team2] += 2
                print(f"  Бот: {team2} выигрывает лайн [{tokens[team1]}:{tokens[team2]}]")

    print(f"После лайнстейджа: {team1}={tokens[team1]}, {team2}={tokens[team2]}")

    tick_params = [
        (['team1_mid', 'team1_partial_support', 'team1_full_support'],
         ['team2_mid', 'team2_partial_support', 'team2_full_support']),
        (['team1_mid', 'team1_partial_support', 'team1_offlane'],
         ['team2_mid', 'team2_partial_support', 'team2_offlane']),
        (['team1_mid', 'team1_carry', 'team1_offlane'],
         ['team2_mid', 'team2_carry', 'team2_offlane']),
    ]
    for t1_roles, t2_roles in tick_params:
        s1 = sum(skills['team1'][r][k] for r in t1_roles for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in t2_roles for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 4
            print(f"  Тимфайт: {team1} выигрывает [{tokens[team1]}:{tokens[team2]}]")
        else:
            tokens[team2] += 4
            print(f"  Тимфайт: {team2} выигрывает [{tokens[team1]}:{tokens[team2]}]")
        if abs(tokens[team1] - tokens[team2]) >= 24:
            winner = team1 if tokens[team1] > tokens[team2] else team2
            print(f"  Ранняя победа: {winner}!")
            return winner

    all_roles_t1 = ['team1_mid', 'team1_carry', 'team1_offlane', 'team1_partial_support', 'team1_full_support']
    all_roles_t2 = ['team2_mid', 'team2_carry', 'team2_offlane', 'team2_partial_support', 'team2_full_support']
    events = ["забрала Рошана", "сломала бараки", "убила кора", "совершила смок-ганг"]
    minute = 30

    while abs(tokens[team1] - tokens[team2]) < 24:
        s1 = sum(skills['team1'][r][k] for r in all_roles_t1 for k in ('macro_skills', 'micro_skills'))
        s2 = sum(skills['team2'][r][k] for r in all_roles_t2 for k in ('macro_skills', 'micro_skills'))
        if random.randint(0, dispersion) + s1 > random.randint(0, dispersion) + s2:
            tokens[team1] += 8
            print(f"  {minute}мин: {team1} {random.choice(events)} [{tokens[team1]}:{tokens[team2]}]")
        else:
            tokens[team2] += 8
            print(f"  {minute}мин: {team2} {random.choice(events)} [{tokens[team1]}:{tokens[team2]}]")
        minute += 5

    winner = team1 if tokens[team1] > tokens[team2] else team2
    print(f"=== Победитель: {winner} ===\n")
    return winner
