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

# Dota 2 CDN slug mapping: hero display name → internal slug
# URL: https://cdn.cloudflare.steamstatic.com/apps/dota2/images/heroes/{slug}_full.png
HERO_SLUG_MAP = {
    # Carry
    'Anti-Mage':        'antimage',
    'Phantom Assassin': 'phantom_assassin',
    'Juggernaut':       'juggernaut',
    'Terrorblade':      'terrorblade',
    'Medusa':           'medusa',
    'Slark':            'slark',
    'Gyrocopter':       'gyrocopter',
    'Faceless Void':    'faceless_void',
    'Naga Siren':       'naga_siren',
    'Lifestealer':      'life_stealer',
    'Morphling':        'morphling',
    'Drow Ranger':      'drow_ranger',
    'Lone Druid':       'lone_druid',
    'Alchemist':        'alchemist',
    'Spectre':          'spectre',
    'Luna':             'luna',
    'Chaos Knight':     'chaos_knight',
    'Ursa':             'ursa',
    'Troll Warlord':    'troll_warlord',
    'Bloodseeker':      'bloodseeker',
    # Mid
    'Lina':             'lina',
    'Invoker':          'invoker',
    'Storm Spirit':     'storm_spirit',
    'Queen of Pain':    'queenofpain',
    'Templar Assassin': 'templar_assassin',
    'Puck':             'puck',
    'Dragon Knight':    'dragon_knight',
    'Tinker':           'tinker',
    'Ember Spirit':     'ember_spirit',
    'Shadow Fiend':     'nevermore',
    'Viper':            'viper',
    'Death Prophet':    'death_prophet',
    'Batrider':         'batrider',
    'Huskar':           'huskar',
    'Void Spirit':      'void_spirit',
    'Kunkka':           'kunkka',
    'Arc Warden':       'arc_warden',
    'Broodmother':      'broodmother',
    'Zeus':             'zuus',
    'Silencer':         'silencer',
    # Offlane
    'Tidehunter':           'tidehunter',
    'Mars':                 'mars',
    'Centaur Warrunner':    'centaur',
    'Bristleback':          'bristleback',
    'Underlord':            'abyssal_underlord',
    'Pangolier':            'pangolier',
    'Monkey King':          'monkey_king',
    'Dark Seer':            'dark_seer',
    'Axe':                  'axe',
    'Sand King':            'sand_king',
    'Brewmaster':           'brewmaster',
    'Beastmaster':          'beastmaster',
    'Timbersaw':            'shredder',
    'Slardar':              'slardar',
    'Doom':                 'doom_bringer',
    'Legion Commander':     'legion_commander',
    'Magnus':               'magnataur',
    'Wraith King':          'skeleton_king',
    'Night Stalker':        'night_stalker',
    'Elder Titan':          'elder_titan',
    # Partial support
    'Earth Spirit':     'earth_spirit',
    'Rubick':           'rubick',
    'Earthshaker':      'earthshaker',
    'Nyx Assassin':     'nyx_assassin',
    'Clockwerk':        'rattletrap',
    'Tusk':             'tusk',
    'Grimstroke':       'grimstroke',
    'Bounty Hunter':    'bounty_hunter',
    'Shadow Demon':     'shadow_demon',
    'Disruptor':        'disruptor',
    'Bane':             'bane',
    'Mirana':           'mirana',
    'Undying':          'undying',
    'Spirit Breaker':   'spirit_breaker',
    'Jakiro':           'jakiro',
    'IO':               'wisp',
    'Keeper of Light':  'keeper_of_the_light',
    'Winter Wyvern':    'winter_wyvern',
    'Skywrath Mage':    'skywrath_mage',
    'Pudge':            'pudge',
    # Full support
    'Crystal Maiden':   'crystal_maiden',
    'Dazzle':           'dazzle',
    'Oracle':           'oracle',
    'Ancient Apparition':'ancient_apparition',
    'Witch Doctor':     'witch_doctor',
    'Lion':             'lion',
    'Warlock':          'warlock',
    'Vengeful Spirit':  'vengefulspirit',
    'Chen':             'chen',
    'Shadow Shaman':    'shadow_shaman',
    'Treant Protector': 'treant',
    'Ogre Magi':        'ogre_magi',
    'Lich':             'lich',
    'Abaddon':          'abaddon',
    'Omniknight':       'omniknight',
    'Leshrac':          'leshrac',
    'Pugna':            'pugna',
    'Enchantress':      'enchantress',
    'Snapfire':         'snapfire',
    'Hoodwink':         'hoodwink',
}

_HERO_IMAGE_DIR = None


def get_hero_image_path(hero_name):
    """Return local path to hero portrait image, or None if not downloaded."""
    import os
    global _HERO_IMAGE_DIR
    if _HERO_IMAGE_DIR is None:
        _HERO_IMAGE_DIR = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'hero_images'
        )
    slug = HERO_SLUG_MAP.get(hero_name)
    if not slug:
        return None
    path = os.path.join(_HERO_IMAGE_DIR, f'{slug}_full.png')
    return path if os.path.exists(path) else None

# Simple counter relationships: hero → [heroes that counter it]
COUNTERS = {
    'Anti-Mage':        ['Lina', 'Storm Spirit', 'Silencer'],
    'Phantom Assassin': ['Zeus', 'Slardar', 'Bloodseeker'],
    'Terrorblade':      ['Legion Commander', 'Chaos Knight', 'Axe'],
    'Medusa':           ['Axe', 'Legion Commander', 'Magnus'],
    'Faceless Void':    ['Bane', 'Doom', 'Axe'],
    'Lina':             ['Anti-Mage', 'Puck', 'Storm Spirit'],
    'Invoker':          ['Silencer', 'Anti-Mage', 'Templar Assassin'],
    'Storm Spirit':     ['Silencer', 'Lion', 'Bloodseeker'],
    'Tinker':           ['Anti-Mage', 'Nyx Assassin', 'Lifestealer'],
    'Shadow Fiend':     ['Nyx Assassin', 'Batrider', 'Doom'],
    'Axe':              ['Phantom Assassin', 'Slardar', 'Silencer'],
    'Enigma':           ['Faceless Void', 'Bane', 'Doom'],
    'Earthshaker':      ['Zeus', 'Lina', 'Anti-Mage'],
    'Magnus':           ['Silencer', 'Doom', 'Nyx Assassin'],
    'Naga Siren':       ['Silencer', 'Doom', 'Anti-Mage'],
    'Broodmother':      ['Dragon Knight', 'Batrider', 'Doom'],
    'Pudge':            ['Anti-Mage', 'Ursa', 'Slark'],
    'Bane':             ['Silencer', 'Anti-Mage', 'Lifestealer'],
}


def get_counters(hero_name):
    """Return list of hero names that counter the given hero."""
    return COUNTERS.get(hero_name, [])


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


def pick_signature_heroes(role, micro, macro, soft, n=3, favored_role=None):
    """Return n hero names from role pool suited to player's skill profile."""
    import random
    pool = HEROES.get(role, [])
    if not pool:
        return []
    # Score by how well hero multipliers match player's strengths
    def score(h):
        base = h[1] * micro + h[2] * macro + h[3] * soft
        # Bonus if this role is meta-favored (slightly biases toward OP heroes)
        meta_bonus = 5 if favored_role == role else 0
        return base + meta_bonus + random.uniform(0, 2)  # small noise for variety
    ranked = sorted(pool, key=score, reverse=True)
    # Pick from top 8 to allow variety
    candidates = ranked[:8]
    chosen = random.sample(candidates, min(n, len(candidates)))
    return [h[0] for h in chosen]


def assign_signature_heroes(db_name, player_ids=None):
    """Assign or refresh signature heroes for players. If player_ids=None → all NULL players."""
    import sqlite3, json
    from logic.meta import get_active_patch

    patch = get_active_patch(db_name)
    favored_role = patch[1] if patch else None

    conn = sqlite3.connect(db_name)
    if player_ids:
        ph = ','.join('?' * len(player_ids))
        rows = conn.execute(
            f"SELECT id, role, COALESCE(micro_skills,50), COALESCE(macro_skills,50), "
            f"COALESCE(soft_skills,50) FROM players WHERE id IN ({ph})",
            list(player_ids)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, role, COALESCE(micro_skills,50), COALESCE(macro_skills,50), "
            "COALESCE(soft_skills,50) FROM players WHERE signature_heroes IS NULL"
        ).fetchall()

    for pid, role, mi, ma, so in rows:
        if not role:
            continue
        heroes = pick_signature_heroes(role, mi, ma, so, n=3, favored_role=favored_role)
        if heroes:
            conn.execute(
                "UPDATE players SET signature_heroes=? WHERE id=?",
                (json.dumps(heroes), pid)
            )
    conn.commit()
    conn.close()


def update_signature_heroes_for_patch(db_name, new_favored_role):
    """On patch rotation: refresh 1 hero for some players to reflect meta shift."""
    import sqlite3, json, random

    conn = sqlite3.connect(db_name)
    rows = conn.execute(
        "SELECT id, role, COALESCE(micro_skills,50), COALESCE(macro_skills,50), "
        "COALESCE(soft_skills,50), signature_heroes FROM players WHERE team_id != 0"
    ).fetchall()

    for pid, role, mi, ma, so, sig_json in rows:
        if not role:
            continue
        # Players of the newly OP role: 70% chance to update 1 hero
        # Others: 25% chance
        chance = 0.70 if role == new_favored_role else 0.25
        if random.random() > chance:
            continue
        current = json.loads(sig_json) if sig_json else []
        pool = HEROES.get(role, [])
        if not pool:
            continue
        # Pick a new hero not already in signature
        candidates = [h[0] for h in pool if h[0] not in current]
        if not candidates:
            continue
        new_hero = random.choice(candidates)
        # Replace one random signature hero
        if current:
            idx = random.randrange(len(current))
            current[idx] = new_hero
        else:
            current = pick_signature_heroes(role, mi, ma, so, n=3, favored_role=new_favored_role)
        conn.execute(
            "UPDATE players SET signature_heroes=? WHERE id=?",
            (json.dumps(current[:3]), pid)
        )
    conn.commit()
    conn.close()
