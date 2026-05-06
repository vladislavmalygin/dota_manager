"""
Hero pool for match simulation.
Each hero: (name, micro_mult, macro_mult, soft_mult, style_tag)
style_tag shown in match log.
"""

HEROES = {
    'carry': [
        ('Anti-Mage',       1.00, 1.12, 0.88, 'late-game split'),
        ('Phantom Assassin', 1.10, 0.95, 0.95, 'burst/snowball'),
        ('Juggernaut',       1.06, 1.06, 0.88, 'sustain fight'),
        ('Terrorblade',      0.92, 1.15, 0.93, 'rat/split'),
        ('Medusa',           0.88, 1.18, 0.94, 'ultra late'),
        ('Slark',            1.12, 0.94, 0.94, 'pick-off'),
        ('Gyrocopter',       1.00, 1.10, 0.90, 'teamfight AoE'),
        ('Faceless Void',    1.08, 1.04, 0.88, 'Chronosphere'),
        ('Naga Siren',       0.90, 1.14, 0.96, 'illusion push'),
        ('Lifestealer',      1.10, 0.98, 0.92, 'tanky brawl'),
    ],
    'mid': [
        ('Lina',             0.96, 1.10, 0.94, 'burst nuke'),
        ('Invoker',          0.90, 1.16, 0.94, 'spell arsenal'),
        ('Storm Spirit',     1.08, 1.02, 0.90, 'pick-off roam'),
        ('Queen of Pain',    1.06, 1.06, 0.88, 'blink aggro'),
        ('Templar Assassin', 1.12, 1.00, 0.88, 'lane dominance'),
        ('Puck',             0.94, 1.08, 0.98, 'spell combo'),
        ('Dragon Knight',    1.04, 1.06, 0.90, 'tanky push'),
        ('Tinker',           0.88, 1.18, 0.94, 'rat/nuke'),
        ('Ember Spirit',     1.10, 1.00, 0.90, 'mobility/chain'),
        ('Shadow Fiend',     1.02, 1.10, 0.88, 'laning/nuke'),
    ],
    'offlane': [
        ('Tidehunter',       0.94, 1.00, 1.06, 'teamfight ult'),
        ('Mars',             1.06, 0.98, 0.96, 'arena lock'),
        ('Centaur Warrunner',1.04, 0.96, 1.00, 'initiation'),
        ('Bristleback',      1.00, 0.94, 1.06, 'sustain tank'),
        ('Underlord',        0.92, 1.04, 1.04, 'aura/push'),
        ('Pangolier',        1.08, 0.96, 0.96, 'roll chaos'),
        ('Monkey King',      1.10, 0.94, 0.96, 'pick-off/split'),
        ('Dark Seer',        0.88, 1.08, 1.04, 'vacuum combo'),
        ('Axe',              1.08, 0.94, 0.98, 'call/initiation'),
        ('Sand King',        0.94, 1.02, 1.04, 'BKB AoE'),
    ],
    'partial_support': [
        ('Earth Spirit',     1.06, 0.96, 0.98, 'roam/pick-off'),
        ('Rubick',           0.94, 1.00, 1.06, 'spell steal'),
        ('Earthshaker',      0.96, 0.98, 1.06, 'initiation'),
        ('Nyx Assassin',     1.06, 0.92, 1.02, 'gank roam'),
        ('Clockwerk',        1.04, 0.94, 1.02, 'initiation'),
        ('Tusk',             1.06, 0.92, 1.02, 'snowball gank'),
        ('Grimstroke',       0.92, 1.04, 1.04, 'lock/soul bind'),
        ('Ember Spirit',     1.06, 0.96, 0.98, 'roam carry'),
        ('Bounty Hunter',    1.08, 0.90, 1.02, 'track gank'),
        ('Shadow Demon',     0.90, 1.06, 1.04, 'disruption'),
    ],
    'full_support': [
        ('Crystal Maiden',   0.90, 0.98, 1.12, 'aura/freeze'),
        ('Dazzle',           0.88, 0.96, 1.16, 'save/heal'),
        ('Oracle',           0.86, 1.00, 1.14, 'save/purify'),
        ('Skywrath Mage',    0.92, 1.04, 1.04, 'silence nuke'),
        ('Ancient Apparition',0.90, 1.02, 1.08,'teamfight ult'),
        ('Witch Doctor',     0.88, 0.98, 1.14, 'heal/death ward'),
        ('Lion',             0.90, 1.02, 1.08, 'hex/drain'),
        ('Warlock',          0.86, 1.00, 1.14, 'chain/golem'),
        ('Vengeful Spirit',  0.92, 1.00, 1.08, 'swap/aura'),
        ('Chen',             0.86, 1.04, 1.10, 'creep push'),
    ],
}

ROLE_ORDER = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']


def random_picks(exclude=None):
    """Pick one random hero per role, optionally excluding already-taken names."""
    import random
    exclude = set(exclude or [])
    picks = {}
    for role in ROLE_ORDER:
        pool = [h for h in HEROES[role] if h[0] not in exclude]
        if not pool:
            pool = HEROES[role]
        h = random.choice(pool)
        picks[role] = h
        exclude.add(h[0])
    return picks


def apply_hero_bonuses(skills, picks):
    """
    skills: {role: {'micro':v,'macro':v,'soft':v,...}}
    picks:  {role: (name, mi_mult, ma_mult, so_mult, tag)}
    Returns modified copy.
    """
    result = {}
    for role, base in skills.items():
        hero = picks.get(role)
        if not hero:
            result[role] = dict(base)
            continue
        _, mi_m, ma_m, so_m, _ = hero
        result[role] = dict(base)
        result[role]['micro']  = base.get('micro', 0)  * mi_m
        result[role]['macro']  = base.get('macro', 0)  * ma_m
        result[role]['soft']   = base.get('soft', 0)   * so_m
    return result
