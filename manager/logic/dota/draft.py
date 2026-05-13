"""
AI draft: picks heroes from signature_heroes in DB, falls back to skill-based selection.
"""
import json
import random
import sqlite3

from logic.heroes import HEROES, ROLE_ORDER, random_picks


def _find_hero(role, name):
    for h in HEROES.get(role, []):
        if h[0] == name:
            return h
    return None


def _pick_for_player(conn, player_id, role, taken):
    """Best hero for player from signature list, or skill-matched fallback."""
    if player_id:
        row = conn.execute(
            "SELECT signature_heroes, COALESCE(micro_skills,50), "
            "COALESCE(macro_skills,50), COALESCE(soft_skills,50) FROM players WHERE id=?",
            (player_id,)
        ).fetchone()
        if row:
            sig_json, micro, macro, soft = row
            if sig_json:
                for hero_name in json.loads(sig_json):
                    if hero_name not in taken:
                        h = _find_hero(role, hero_name)
                        if h:
                            return h
            pool = [h for h in HEROES.get(role, []) if h[0] not in taken]
            if pool:
                pool_s = sorted(pool, key=lambda h: h[1]*micro + h[2]*macro + h[3]*soft, reverse=True)
                return random.choice(pool_s[:5])
    pool = [h for h in HEROES.get(role, []) if h[0] not in taken]
    return random.choice(pool) if pool else HEROES[role][0]


def get_ai_picks(db_name, team_id, exclude=None):
    """Return {role: hero_tuple} for team using signature heroes from DB.

    exclude: set of hero names already taken by the opponent.
    """
    exclude = set(exclude or [])
    conn = sqlite3.connect(db_name)
    row = conn.execute(
        "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE id=?",
        (team_id,)
    ).fetchone()
    if not row:
        conn.close()
        return random_picks(exclude=exclude)
    picks = {}
    taken = set(exclude)
    for role, pid in zip(ROLE_ORDER, row):
        h = _pick_for_player(conn, pid, role, taken)
        picks[role] = h
        taken.add(h[0])
    conn.close()
    return picks


def get_ai_draft(db_name, team1_name, team2_name):
    """Return {'team1': {role: hero_tuple}, 'team2': {role: hero_tuple}}."""
    conn = sqlite3.connect(db_name)
    r1 = conn.execute("SELECT id FROM teams WHERE name=?", (team1_name,)).fetchone()
    r2 = conn.execute("SELECT id FROM teams WHERE name=?", (team2_name,)).fetchone()
    conn.close()
    t1_picks = get_ai_picks(db_name, r1[0]) if r1 else random_picks()
    taken = {h[0] for h in t1_picks.values()}
    t2_picks = get_ai_picks(db_name, r2[0], exclude=taken) if r2 else random_picks(exclude=taken)
    return {'team1': t1_picks, 'team2': t2_picks}
