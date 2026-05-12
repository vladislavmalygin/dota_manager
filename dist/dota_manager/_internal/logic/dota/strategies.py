"""
Draft strategies per game phase.

Each strategy entry:
  name, pros, cons, best_skill
  mods: phase → {skill_key: multiplier}
  special: optional dict of special flags used in game.py
"""

EARLY_STRATEGIES = {
    'aggro_lane': {
        'name':       'Агрессия на лайне',
        'pros':       '+18% micro на лайне, ×1.8 шанс первой крови, давление на соперника',
        'cons':       '−12% macro на лайне, расходуем ресурсы',
        'best_skill': 'micro',
        'mods': {
            'laning':   {'micro': 1.18, 'macro': 0.88},
            'midgame':  {'micro': 1.05},
            'lategame': {},
        },
        'special': {'first_blood_mult': 1.8, 'early_tower_chance': 0.40},
    },
    'safe_farm': {
        'name':       'Безопасный фарм',
        'pros':       '+18% macro на лайне, стабильный ресурсный старт',
        'cons':       '−10% micro на лайне, теряем инициативу',
        'best_skill': 'macro',
        'mods': {
            'laning':   {'macro': 1.18, 'micro': 0.90},
            'midgame':  {'macro': 1.08},
            'lategame': {'macro': 1.06},
        },
        'special': {'early_tower_chance': 0.15},
    },
    'support_roam': {
        'name':       'Ротации саппортов',
        'pros':       '+28% mid micro, шанс ранней вышки ×1.6',
        'cons':       '−15% на боковых лайнах, беззащитные carry/offlane',
        'best_skill': 'soft',
        'mods': {
            'laning':   {'mid_micro': 1.28, 'side_micro': 0.85},
            'midgame':  {'soft': 1.10},
            'lategame': {},
        },
        'special': {'early_tower_chance': 0.48},
    },
}

MID_STRATEGIES = {
    'smoke_gank': {
        'name':       'Смок-ганки',
        'pros':       'Шанс смока ×2.2, +15% micro в мидгейме, непредсказуемость',
        'cons':       '−12% macro, слабее в открытых боях',
        'best_skill': 'micro',
        'mods': {
            'midgame':  {'micro': 1.15, 'macro': 0.88},
            'lategame': {'micro': 1.05},
        },
        'special': {'smoke_chance': 0.55, 'smoke_bonus_mult': 2.2},
    },
    'obj_push': {
        'name':       'Пуш объектов',
        'pros':       '+18% macro в мидгейме, ×1.9 шанс вышки',
        'cons':       '−10% micro, уязвимы к контратаке',
        'best_skill': 'macro',
        'mods': {
            'midgame':  {'macro': 1.18, 'micro': 0.90},
            'lategame': {'macro': 1.05},
        },
        'special': {'mid_tower_chance_mult': 1.9},
    },
    'map_control': {
        'name':       'Контроль карты',
        'pros':       '+20% soft в мидгейме, сильная транзиция в лейт',
        'cons':       'Медленнее, меньше burst-убийств',
        'best_skill': 'soft',
        'mods': {
            'midgame':  {'soft': 1.20},
            'lategame': {'soft': 1.12},
        },
        'special': {},
    },
}

LATE_STRATEGIES = {
    'teamfight': {
        'name':       '5v5 тимфайт',
        'pros':       '+25% soft в лейте, сильные командные бои',
        'cons':       'Рискованно при отставании, нужен высокий soft',
        'best_skill': 'soft',
        'mods': {
            'lategame': {'soft': 1.25, 'micro': 1.05},
        },
        'special': {},
    },
    'split_push': {
        'name':       'Сплит-пуш',
        'pros':       '+35% micro carry в лейте, сложно защищаться',
        'cons':       '−12% soft, слабее в прямых боях',
        'best_skill': 'micro',
        'mods': {
            'lategame': {'carry_micro': 1.35, 'soft': 0.88},
        },
        'special': {'split_push': True},
    },
    'siege': {
        'name':       'Осада хайграунда',
        'pros':       '+18% macro в лейте, низкий риск, стабильность',
        'cons':       'Медленно, даёт время соперника фармить',
        'best_skill': 'macro',
        'mods': {
            'lategame': {'macro': 1.18},
        },
        'special': {'dispersion_mult': 0.65},
    },
}

ALL_STRATEGIES = {
    'early': EARLY_STRATEGIES,
    'mid':   MID_STRATEGIES,
    'late':  LATE_STRATEGIES,
}

DEFAULT_EARLY = 'safe_farm'
DEFAULT_MID   = 'map_control'
DEFAULT_LATE  = 'teamfight'


def ai_pick_strategy(avg_micro, avg_macro, avg_soft):
    """Pick best strategy for each phase based on team skill profile."""
    # Early
    if avg_micro >= avg_macro and avg_micro >= avg_soft:
        early = 'aggro_lane'
    elif avg_soft >= avg_micro and avg_soft >= avg_macro:
        early = 'support_roam'
    else:
        early = 'safe_farm'

    # Mid
    if avg_micro >= avg_macro and avg_micro >= avg_soft:
        mid = 'smoke_gank'
    elif avg_macro >= avg_micro and avg_macro >= avg_soft:
        mid = 'obj_push'
    else:
        mid = 'map_control'

    # Late
    if avg_soft >= avg_micro and avg_soft >= avg_macro:
        late = 'teamfight'
    elif avg_micro >= avg_macro:
        late = 'split_push'
    else:
        late = 'siege'

    return early, mid, late


def get_phase_mods(strategy_key, phase, strategies_dict):
    """Return skill multiplier dict for a given phase."""
    s = strategies_dict.get(strategy_key)
    if not s:
        return {}
    return s.get('mods', {}).get(phase, {})


def get_specials(strategy_key, strategies_dict):
    return (strategies_dict.get(strategy_key) or {}).get('special', {})
