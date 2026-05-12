"""
Hero pool for match simulation.
Each hero: (name, micro_mult, macro_mult, soft_mult, style_tag)
20 heroes per role.
"""

HEROES = {
    'carry': [
        ('Anti-Mage',        1.00, 1.12, 0.88, 'split push'),
        ('Phantom Assassin', 1.10, 0.95, 0.95, 'burst'),
        ('Juggernaut',       1.06, 1.06, 0.88, 'sustain'),
        ('Terrorblade',      0.92, 1.15, 0.93, 'rat'),
        ('Medusa',           0.88, 1.18, 0.94, 'ultra late'),
        ('Slark',            1.12, 0.94, 0.94, 'pick-off'),
        ('Gyrocopter',       1.00, 1.10, 0.90, 'teamfight'),
        ('Faceless Void',    1.08, 1.04, 0.88, 'chrono'),
        ('Naga Siren',       0.90, 1.14, 0.96, 'illusions'),
        ('Lifestealer',      1.10, 0.98, 0.92, 'tank brawl'),
        ('Morphling',        1.14, 1.02, 0.84, 'hyper-carry'),
        ('Drow Ranger',      0.94, 1.12, 0.94, 'aura push'),
        ('Lone Druid',       0.90, 1.16, 0.94, 'bear push'),
        ('Alchemist',        0.86, 1.20, 0.94, 'fast farm'),
        ('Spectre',          0.96, 1.10, 0.94, 'global'),
        ('Luna',             0.94, 1.10, 0.96, 'flash farm'),
        ('Chaos Knight',     1.08, 0.98, 0.94, 'illusion tank'),
        ('Ursa',             1.12, 0.96, 0.92, 'roshan'),
        ('Troll Warlord',    1.10, 1.02, 0.88, 'brawl'),
        ('Bloodseeker',      1.08, 1.00, 0.92, 'gank carry'),
    ],
    'mid': [
        ('Lina',             0.96, 1.10, 0.94, 'burst nuke'),
        ('Invoker',          0.90, 1.16, 0.94, 'arsenal'),
        ('Storm Spirit',     1.12, 1.00, 0.88, 'roam'),
        ('Queen of Pain',    1.06, 1.06, 0.88, 'blink aggro'),
        ('Templar Assassin', 1.12, 1.00, 0.88, 'lane dom'),
        ('Puck',             0.94, 1.08, 0.98, 'spell combo'),
        ('Dragon Knight',    1.04, 1.06, 0.90, 'tanky push'),
        ('Tinker',           0.88, 1.18, 0.94, 'rat nuke'),
        ('Ember Spirit',     1.10, 1.00, 0.90, 'chain'),
        ('Shadow Fiend',     1.02, 1.10, 0.88, 'nuke'),
        ('Viper',            1.00, 1.08, 0.92, 'lane bully'),
        ('Death Prophet',    0.92, 1.12, 0.96, 'push'),
        ('Batrider',         1.04, 1.02, 0.94, 'initiation'),
        ('Huskar',           1.08, 0.96, 0.96, 'tower push'),
        ('Void Spirit',      1.14, 0.96, 0.90, 'evasion'),
        ('Kunkka',           1.02, 1.06, 0.92, 'x mark'),
        ('Arc Warden',       0.86, 1.20, 0.94, 'split push'),
        ('Broodmother',      1.06, 1.10, 0.84, 'split'),
        ('Zeus',             0.88, 1.10, 1.02, 'global nuke'),
        ('Silencer',         0.92, 1.06, 1.02, 'silence'),
    ],
    'offlane': [
        ('Tidehunter',       0.94, 1.00, 1.06, 'teamfight ult'),
        ('Mars',             1.06, 0.98, 0.96, 'arena lock'),
        ('Centaur Warrunner',1.04, 0.96, 1.00, 'initiation'),
        ('Bristleback',      1.00, 0.94, 1.06, 'sustain tank'),
        ('Underlord',        0.92, 1.04, 1.04, 'aura push'),
        ('Pangolier',        1.08, 0.96, 0.96, 'roll chaos'),
        ('Monkey King',      1.10, 0.94, 0.96, 'pick-off'),
        ('Dark Seer',        0.88, 1.08, 1.04, 'vacuum combo'),
        ('Axe',              1.08, 0.94, 0.98, 'call'),
        ('Sand King',        0.94, 1.02, 1.04, 'BKB AoE'),
        ('Brewmaster',       1.04, 0.98, 0.98, 'split'),
        ('Beastmaster',      1.00, 1.02, 0.98, 'vision push'),
        ('Timbersaw',        1.06, 0.96, 0.98, 'sustain'),
        ('Slardar',          1.08, 0.92, 1.00, 'bash initiate'),
        ('Doom',             1.02, 1.00, 0.98, 'doom silence'),
        ('Legion Commander', 1.10, 0.92, 0.98, 'duel'),
        ('Magnus',           1.00, 0.98, 1.02, 'RP combo'),
        ('Wraith King',      1.04, 0.98, 0.98, 'reincarnate'),
        ('Night Stalker',    1.08, 0.94, 0.98, 'night gank'),
        ('Elder Titan',      0.94, 1.00, 1.06, 'astral stomp'),
    ],
    'partial_support': [
        ('Earth Spirit',     1.06, 0.96, 0.98, 'roam pick-off'),
        ('Rubick',           0.94, 1.00, 1.06, 'spell steal'),
        ('Earthshaker',      0.96, 0.98, 1.06, 'initiation'),
        ('Nyx Assassin',     1.06, 0.92, 1.02, 'gank roam'),
        ('Clockwerk',        1.04, 0.94, 1.02, 'initiation'),
        ('Tusk',             1.06, 0.92, 1.02, 'snowball'),
        ('Grimstroke',       0.92, 1.04, 1.04, 'lock'),
        ('Bounty Hunter',    1.08, 0.90, 1.02, 'track gank'),
        ('Shadow Demon',     0.90, 1.06, 1.04, 'disruption'),
        ('Disruptor',        0.92, 1.00, 1.08, 'kinetic field'),
        ('Bane',             0.90, 0.98, 1.12, 'disable'),
        ('Mirana',           1.04, 0.96, 1.00, 'arrow gank'),
        ('Undying',          0.96, 0.96, 1.08, 'tombstone'),
        ('Spirit Breaker',   1.06, 0.92, 1.02, 'charge roam'),
        ('Jakiro',           0.88, 1.02, 1.10, 'lane slow'),
        ('IO',               0.86, 0.94, 1.20, 'relocate save'),
        ('Keeper of Light',  0.86, 1.04, 1.10, 'chakra push'),
        ('Winter Wyvern',    0.88, 0.98, 1.14, 'cold embrace'),
        ('Skywrath Mage',    0.92, 1.04, 1.04, 'silence nuke'),
        ('Pudge',            1.04, 0.92, 1.04, 'hook'),
    ],
    'full_support': [
        ('Crystal Maiden',   0.90, 0.98, 1.12, 'aura freeze'),
        ('Dazzle',           0.88, 0.96, 1.16, 'save heal'),
        ('Oracle',           0.86, 1.00, 1.14, 'save purify'),
        ('Ancient Apparition',0.90,1.02, 1.08, 'teamfight ult'),
        ('Witch Doctor',     0.88, 0.98, 1.14, 'heal ward'),
        ('Lion',             0.90, 1.02, 1.08, 'hex drain'),
        ('Warlock',          0.86, 1.00, 1.14, 'chain golem'),
        ('Vengeful Spirit',  0.92, 1.00, 1.08, 'swap aura'),
        ('Chen',             0.86, 1.04, 1.10, 'creep push'),
        ('Shadow Shaman',    0.90, 1.00, 1.10, 'hex shackle'),
        ('Treant Protector', 0.86, 0.98, 1.16, 'roots overgrowth'),
        ('Ogre Magi',        0.96, 0.94, 1.10, 'multicast'),
        ('Lich',             0.88, 1.00, 1.12, 'chain frost'),
        ('Abaddon',          0.90, 0.96, 1.14, 'save mist'),
        ('Omniknight',       0.88, 0.94, 1.18, 'repel save'),
        ('Leshrac',          0.88, 1.08, 1.04, 'push nuke'),
        ('Pugna',            0.86, 1.08, 1.06, 'decrepify'),
        ('Enchantress',      0.88, 1.02, 1.10, 'creep impetus'),
        ('Snapfire',         0.90, 0.96, 1.14, 'mortimer'),
        ('Hoodwink',         0.96, 0.96, 1.08, 'acorn gank'),
    ],
}


ROLE_ORDER = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']

# All hero names for quick lookup
ALL_HERO_NAMES = {h[0] for heroes in HEROES.values() for h in heroes}


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


def ai_draft_picks(banned_names, ai_roles_needed):
    """
    AI picks heroes for needed roles, avoiding banned names.
    Returns {role: hero_tuple}.
    Prefers high-value heroes (max multiplier sum).
    """
    import random
    banned = set(banned_names)
    result = {}
    taken = set()
    for role in ai_roles_needed:
        pool = [h for h in HEROES[role] if h[0] not in banned and h[0] not in taken]
        if not pool:
            pool = [h for h in HEROES[role] if h[0] not in taken] or HEROES[role]
        # Sort by combined multiplier descending, add some randomness
        pool_sorted = sorted(pool, key=lambda h: h[1]+h[2]+h[3], reverse=True)
        # Pick from top 5 randomly
        chosen = random.choice(pool_sorted[:5])
        result[role] = chosen
        taken.add(chosen[0])
    return result


def ai_draft_bans(available_names, n, player_picks_so_far):
    """
    AI selects n heroes to ban.
    Targets player's likely strong picks and high-value heroes.
    """
    import random
    # Ban high-value heroes not already picked by player
    already_picked = {h[0] for h in player_picks_so_far.values() if h}
    candidates = []
    for role in ROLE_ORDER:
        for hero in HEROES[role]:
            if hero[0] in available_names and hero[0] not in already_picked:
                # Score = sum of multipliers, prefer picks > 3.0
                score = hero[1] + hero[2] + hero[3]
                candidates.append((score, hero[0]))
    candidates.sort(reverse=True)
    top = [n for _, n in candidates[:15]]
    random.shuffle(top)
    return top[:n]
