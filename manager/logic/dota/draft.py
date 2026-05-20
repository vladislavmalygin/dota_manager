"""
AI draft: composition archetypes, meta-aware picks, history-based bans.
"""
import json
import random
import sqlite3

from logic.heroes import HEROES, ROLE_ORDER, random_picks

_DDL_DRAFT_HISTORY = """
CREATE TABLE IF NOT EXISTS draft_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_date      TEXT,
    tournament_name TEXT,
    team1           TEXT,
    team2           TEXT,
    winner          TEXT,
    patch_name      TEXT,
    t1_picks        TEXT,
    t2_picks        TEXT,
    t1_bans         TEXT,
    t2_bans         TEXT,
    t1_pick_roles   TEXT,
    t2_pick_roles   TEXT
)
"""

# Draft archetypes: style → preferred hero tags per role
_ARCHETYPES = {
    'teamfight': {
        'carry':           ['teamfight', 'chrono', 'illusion tank', 'bkb teamfight'],
        'mid':             ['global nuke', 'burst nuke', 'nuke', 'x mark'],
        'offlane':         ['teamfight ult', 'RP combo', 'black hole', 'arena lock'],
        'partial_support': ['initiation', 'kinetic field', 'AoE'],
        'full_support':    ['aura freeze', 'chain golem', 'chain frost', 'heal ward'],
    },
    'push': {
        'carry':           ['rat', 'aura push', 'bear push', 'fast farm', 'illusion siege'],
        'mid':             ['rat nuke', 'split push', 'push', 'rat push'],
        'offlane':         ['aura push', 'slow push', 'vision push'],
        'partial_support': ['lane slow', 'chakra push', 'ward slow'],
        'full_support':    ['creep push', 'global push', 'roots overgrowth'],
    },
    'pick-off': {
        'carry':           ['pick-off', 'gank carry', 'gank assassin', 'gank invisible'],
        'mid':             ['roam', 'blink aggro', 'lane dom', 'evasion'],
        'offlane':         ['pick-off', 'night gank', 'bash initiate'],
        'partial_support': ['roam pick-off', 'gank roam', 'snowball', 'track gank'],
        'full_support':    ['save purify', 'save heal', 'save mist'],
    },
    'deathball': {
        'carry':           ['sustain', 'brawl', 'tank brawl', 'reincarnate'],
        'mid':             ['tanky push', 'tower push', 'push', 'lane bully'],
        'offlane':         ['initiation', 'sustain tank', 'tank initiate', 'dive heal'],
        'partial_support': ['initiation', 'disable', 'charge roam', 'snowball'],
        'full_support':    ['repel save', 'save heal', 'multicast', 'save mist'],
    },
    'poke': {
        'carry':           ['poke siege', 'aura push', 'global', 'flash farm'],
        'mid':             ['global nuke', 'poke gank', 'arsenal', 'burst nuke'],
        'offlane':         ['sustain', 'sustain tank', 'BKB AoE'],
        'partial_support': ['silence nuke', 'lane slow', 'cold embrace', 'kinetic field'],
        'full_support':    ['aura freeze', 'anti-heal', 'chain frost', 'teamfight ult'],
    },
}


def _get_archetype(db_name, team_id):
    """Choose a draft archetype for a team based on their tactic setting."""
    try:
        conn = sqlite3.connect(db_name)
        row = conn.execute(
            "SELECT COALESCE(tactic,'balanced') FROM teams WHERE id=?", (team_id,)
        ).fetchone()
        conn.close()
        tactic = row[0] if row else 'balanced'
    except Exception:
        tactic = 'balanced'

    _TACTIC_ARCH = {
        'aggressive':  ['teamfight', 'pick-off', 'deathball'],
        'defensive':   ['poke', 'push', 'teamfight'],
        'balanced':    list(_ARCHETYPES.keys()),
        'split_push':  ['push', 'poke', 'pick-off'],
        'teamfight':   ['teamfight', 'deathball'],
    }
    pool = _TACTIC_ARCH.get(tactic, list(_ARCHETYPES.keys()))
    return random.choice(pool)


def _hero_archetype_score(hero, role, archetype):
    """Bonus score for hero matching the draft archetype."""
    if archetype not in _ARCHETYPES:
        return 0
    preferred_tags = _ARCHETYPES[archetype].get(role, [])
    tag = hero[4] if len(hero) > 4 else ''
    return 3.0 if any(t in tag for t in preferred_tags) else 0.0


def _get_high_winrate_heroes(db_name, patch_name=None, min_picks=3, top_n=20):
    """Return set of hero names with high win rate from draft history."""
    try:
        ensure_draft_history(db_name)
        conn = sqlite3.connect(db_name)
        if patch_name:
            rows = conn.execute(
                "SELECT t1_pick_roles, t2_pick_roles, winner, team1, team2 "
                "FROM draft_history WHERE patch_name=?", (patch_name,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT t1_pick_roles, t2_pick_roles, winner, team1, team2 "
                "FROM draft_history ORDER BY id DESC LIMIT 200"
            ).fetchall()
        conn.close()

        stats = {}
        for t1_json, t2_json, winner, team1, team2 in rows:
            try:
                t1r = json.loads(t1_json or '{}')
                t2r = json.loads(t2_json or '{}')
            except Exception:
                continue
            for hname in t1r.values():
                if hname:
                    stats.setdefault(hname, [0, 0])
                    stats[hname][0] += 1
                    if winner == team1:
                        stats[hname][1] += 1
            for hname in t2r.values():
                if hname:
                    stats.setdefault(hname, [0, 0])
                    stats[hname][0] += 1
                    if winner == team2:
                        stats[hname][1] += 1

        high_wr = set()
        for hname, (picks, wins) in stats.items():
            if picks >= min_picks and wins / picks >= 0.55:
                high_wr.add(hname)
        return high_wr
    except Exception:
        return set()


def ensure_draft_history(db_name):
    conn = sqlite3.connect(db_name)
    conn.execute(_DDL_DRAFT_HISTORY)
    conn.commit()
    conn.close()


def record_draft(db_name, match_date, tournament_name,
                 team1, team2, winner,
                 t1_picks, t2_picks,
                 t1_bans=None, t2_bans=None):
    try:
        ensure_draft_history(db_name)

        def _normalise(picks):
            if not picks:
                return {}
            return {role: (h[0] if isinstance(h, tuple) else h)
                    for role, h in picks.items()}

        n1 = _normalise(t1_picks)
        n2 = _normalise(t2_picks)

        patch = '?'
        try:
            from logic.meta import get_active_patch
            p = get_active_patch(db_name)
            if p:
                patch = p[0]
        except Exception:
            pass

        conn = sqlite3.connect(db_name)
        conn.execute("""
            INSERT INTO draft_history
              (match_date, tournament_name, team1, team2, winner, patch_name,
               t1_picks, t2_picks, t1_bans, t2_bans, t1_pick_roles, t2_pick_roles)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            match_date, tournament_name, team1, team2, winner, patch,
            json.dumps(list(n1.values())),
            json.dumps(list(n2.values())),
            json.dumps(t1_bans or []),
            json.dumps(t2_bans or []),
            json.dumps(n1),
            json.dumps(n2),
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_hero_stats(db_name, patch_name=None, role=None, limit=20):
    try:
        ensure_draft_history(db_name)

        if patch_name is None:
            from logic.meta import get_active_patch
            p = get_active_patch(db_name)
            patch_name = p[0] if p else None

        conn = sqlite3.connect(db_name)
        rows = conn.execute(
            "SELECT t1_pick_roles, t2_pick_roles, winner, team1, team2 "
            "FROM draft_history" +
            (" WHERE patch_name=?" if patch_name else ""),
            (patch_name,) if patch_name else ()
        ).fetchall()
        conn.close()

        hero_role = {}
        for r in ROLE_ORDER:
            for h in HEROES[r]:
                hero_role[h[0]] = r

        stats = {}
        for t1_json, t2_json, winner, team1, team2 in rows:
            try:
                t1_roles = json.loads(t1_json or '{}')
                t2_roles = json.loads(t2_json or '{}')
            except Exception:
                continue
            for r, hname in t1_roles.items():
                if not hname:
                    continue
                if role and hero_role.get(hname) != role:
                    continue
                stats.setdefault(hname, [0, 0])
                stats[hname][0] += 1
                if winner == team1:
                    stats[hname][1] += 1
            for r, hname in t2_roles.items():
                if not hname:
                    continue
                if role and hero_role.get(hname) != role:
                    continue
                stats.setdefault(hname, [0, 0])
                stats[hname][0] += 1
                if winner == team2:
                    stats[hname][1] += 1

        result = []
        for hname, (picks, wins) in stats.items():
            wr = round(wins / picks * 100) if picks else 0
            result.append((hname, hero_role.get(hname, '?'), picks, wins, wr))

        result.sort(key=lambda x: x[2], reverse=True)
        return result[:limit]
    except Exception:
        return []


def _find_hero(role, name):
    for h in HEROES.get(role, []):
        if h[0] == name:
            return h
    return None


def _pick_for_player(conn, player_id, role, taken, patch_buffed=None,
                     archetype=None, high_wr_heroes=None):
    """Hero selection: archetype + meta + signature + skill, with high variety."""
    patch_buffed   = patch_buffed or set()
    high_wr_heroes = high_wr_heroes or set()

    pool = [h for h in HEROES.get(role, []) if h[0] not in taken]
    if not pool:
        pool = HEROES.get(role, [])

    if player_id:
        row = conn.execute(
            "SELECT signature_heroes, COALESCE(micro_skills,50), "
            "COALESCE(macro_skills,50), COALESCE(soft_skills,50) FROM players WHERE id=?",
            (player_id,)
        ).fetchone()
        if row:
            sig_json, micro, macro, soft = row

            # 40% chance to use signature hero (reduced from 100% to add variety)
            if sig_json and random.random() < 0.40:
                sig = json.loads(sig_json)
                # Prefer buffed + high-wr signature heroes
                for hero_name in sig:
                    if hero_name not in taken and hero_name in patch_buffed:
                        h = _find_hero(role, hero_name)
                        if h:
                            return h
                random.shuffle(sig)
                for hero_name in sig:
                    if hero_name not in taken:
                        h = _find_hero(role, hero_name)
                        if h:
                            return h

            # Score-based pick from full pool
            def _score(h):
                base = h[1] * micro + h[2] * macro + h[3] * soft
                meta  = 8.0 if h[0] in patch_buffed else 0.0
                hist  = 5.0 if h[0] in high_wr_heroes else 0.0
                arch  = _hero_archetype_score(h, role, archetype) if archetype else 0.0
                noise = random.uniform(0, 4)   # large noise for variety
                return base + meta + hist + arch + noise

            pool_scored = sorted(pool, key=_score, reverse=True)
            # Pick from top-8 for much more variety
            return random.choice(pool_scored[:8])

    # No player data: archetype + meta scoring
    def _fallback_score(h):
        meta = 6.0 if h[0] in patch_buffed else 0.0
        arch = _hero_archetype_score(h, role, archetype) if archetype else 0.0
        return h[1]+h[2]+h[3] + meta + arch + random.uniform(0, 3)

    pool_scored = sorted(pool, key=_fallback_score, reverse=True)
    return random.choice(pool_scored[:6])


def _smart_bans(available, n, opponent_picks, patch_buffed, high_wr_heroes,
                archetype=None):
    """Ban high win-rate, meta, and archetype-threatening heroes."""
    opp_picked = {h[0] if isinstance(h, tuple) else h
                  for h in opponent_picks.values()}

    candidates = []
    for role in ROLE_ORDER:
        for hero in HEROES[role]:
            name = hero[0]
            if name not in available or name in opp_picked:
                continue
            score = 0.0
            score += 8.0 if name in high_wr_heroes else 0.0
            score += 6.0 if name in patch_buffed else 0.0
            # Bonus for heroes that counter our archetype
            score += hero[1] + hero[2] + hero[3]
            score += random.uniform(0, 2)
            candidates.append((score, name))

    candidates.sort(reverse=True)
    # Mix top targets with some randomness: take top-20, shuffle, pick n
    top = [name for _, name in candidates[:20]]
    random.shuffle(top)
    return top[:n]


def get_ai_picks(db_name, team_id, exclude=None):
    """Return {role: hero_tuple} for a team with archetype + meta awareness."""
    exclude = set(exclude or [])

    conn = sqlite3.connect(db_name)
    row = conn.execute(
        "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE id=?",
        (team_id,)
    ).fetchone()
    if not row:
        conn.close()
        return random_picks(exclude=exclude)

    patch_buffed = set()
    patch_name   = None
    try:
        from logic.meta import get_patch_hero_lists, get_active_patch
        buffed, _, _ = get_patch_hero_lists(db_name)
        patch_buffed = set(buffed)
        p = get_active_patch(db_name)
        if p:
            patch_name = p[0]
    except Exception:
        pass

    high_wr = _get_high_winrate_heroes(db_name, patch_name)
    archetype = _get_archetype(db_name, team_id)

    picks = {}
    taken = set(exclude)
    for role, pid in zip(ROLE_ORDER, row):
        h = _pick_for_player(conn, pid, role, taken,
                             patch_buffed=patch_buffed,
                             archetype=archetype,
                             high_wr_heroes=high_wr)
        picks[role] = h
        taken.add(h[0])
    conn.close()
    return picks


def get_ai_draft(db_name, team1_name, team2_name):
    """Full CM-style draft for AI vs AI: bans then picks with strategic variety."""
    conn = sqlite3.connect(db_name)
    r1 = conn.execute("SELECT id FROM teams WHERE name=?", (team1_name,)).fetchone()
    r2 = conn.execute("SELECT id FROM teams WHERE name=?", (team2_name,)).fetchone()
    conn.close()

    tid1 = r1[0] if r1 else None
    tid2 = r2[0] if r2 else None

    patch_buffed = set()
    patch_name   = None
    try:
        from logic.meta import get_patch_hero_lists, get_active_patch
        buffed, nerfed, _ = get_patch_hero_lists(db_name)
        patch_buffed = set(buffed)
        p = get_active_patch(db_name)
        if p:
            patch_name = p[0]
    except Exception:
        pass

    high_wr = _get_high_winrate_heroes(db_name, patch_name)

    # Choose archetypes for each team
    arch1 = _get_archetype(db_name, tid1) if tid1 else random.choice(list(_ARCHETYPES))
    arch2 = _get_archetype(db_name, tid2) if tid2 else random.choice(list(_ARCHETYPES))

    all_names = {h[0] for role in ROLE_ORDER for h in HEROES[role]}
    banned = set()

    # 3 bans per team before picks (simplified CM: 3+3 bans)
    n_bans = 3
    t1_bans = _smart_bans(all_names - banned, n_bans, {}, patch_buffed, high_wr, arch1)
    banned.update(t1_bans)
    t2_bans = _smart_bans(all_names - banned, n_bans, {}, patch_buffed, high_wr, arch2)
    banned.update(t2_bans)

    # Picks with bans in effect
    t1_picks = get_ai_picks(db_name, tid1, exclude=banned) if tid1 \
               else random_picks(exclude=banned)
    taken = banned | {h[0] for h in t1_picks.values()}

    t2_picks = get_ai_picks(db_name, tid2, exclude=taken) if tid2 \
               else random_picks(exclude=taken)

    return {
        'team1':    t1_picks,
        'team2':    t2_picks,
        't1_bans':  t1_bans,
        't2_bans':  t2_bans,
    }


def ai_draft_bans(available_names, count, opponent_picks=None):
    """Legacy function kept for compatibility with CM draft UI."""
    opponent_picks = opponent_picks or {}
    picked = {h[0] if isinstance(h, tuple) else h for h in opponent_picks.values()}
    targets = list(picked & set(available_names))
    random.shuffle(targets)
    if len(targets) < count:
        rest = [h for h in available_names if h not in picked]
        random.shuffle(rest)
        targets += rest
    return targets[:count]
