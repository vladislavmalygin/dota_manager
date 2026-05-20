"""
AI draft: picks heroes from signature_heroes in DB, falls back to skill-based selection.
Also records draft history and provides hero statistics.
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
    t1_picks        TEXT,   -- JSON: [hero_name, ...]
    t2_picks        TEXT,
    t1_bans         TEXT,
    t2_bans         TEXT,
    t1_pick_roles   TEXT,   -- JSON: {role: hero_name}
    t2_pick_roles   TEXT
)
"""


def ensure_draft_history(db_name):
    conn = sqlite3.connect(db_name)
    conn.execute(_DDL_DRAFT_HISTORY)
    conn.commit()
    conn.close()


def record_draft(db_name, match_date, tournament_name,
                 team1, team2, winner,
                 t1_picks, t2_picks,
                 t1_bans=None, t2_bans=None):
    """
    Record a draft to history.
    t1_picks / t2_picks: {role: hero_name} or {role: (name,...)}
    t1_bans / t2_bans: [hero_name, ...]
    """
    try:
        ensure_draft_history(db_name)

        # Normalise picks to {role: hero_name}
        def _normalise(picks):
            if not picks:
                return {}
            return {
                role: (h[0] if isinstance(h, tuple) else h)
                for role, h in picks.items()
            }

        n1 = _normalise(t1_picks)
        n2 = _normalise(t2_picks)

        # Current patch
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
    """
    Return list of (hero_name, role, picks, wins, win_rate) sorted by picks desc.
    If patch_name is None, use current active patch.
    """
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

        # Build role lookup
        hero_role = {}
        for r in ROLE_ORDER:
            for h in HEROES[r]:
                hero_role[h[0]] = r

        stats = {}   # hero_name → [picks, wins]
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


def _pick_for_player(conn, player_id, role, taken, patch_buffed=None):
    """Best hero for player from signature list, or skill-matched fallback.
    patch_buffed: set of hero names buffed in current patch (prioritise these).
    """
    patch_buffed = patch_buffed or set()
    if player_id:
        row = conn.execute(
            "SELECT signature_heroes, COALESCE(micro_skills,50), "
            "COALESCE(macro_skills,50), COALESCE(soft_skills,50) FROM players WHERE id=?",
            (player_id,)
        ).fetchone()
        if row:
            sig_json, micro, macro, soft = row
            if sig_json:
                sig = json.loads(sig_json)
                # Prefer buffed signature heroes
                for hero_name in sig:
                    if hero_name not in taken and hero_name in patch_buffed:
                        h = _find_hero(role, hero_name)
                        if h:
                            return h
                for hero_name in sig:
                    if hero_name not in taken:
                        h = _find_hero(role, hero_name)
                        if h:
                            return h
            pool = [h for h in HEROES.get(role, []) if h[0] not in taken]
            if pool:
                # Prioritise buffed heroes
                buffed_pool = [h for h in pool if h[0] in patch_buffed]
                if buffed_pool and random.random() < 0.50:
                    return random.choice(buffed_pool)
                pool_s = sorted(pool, key=lambda h: h[1]*micro + h[2]*macro + h[3]*soft, reverse=True)
                return random.choice(pool_s[:5])
    pool = [h for h in HEROES.get(role, []) if h[0] not in taken]
    return random.choice(pool) if pool else HEROES[role][0]


def get_ai_picks(db_name, team_id, exclude=None):
    """Return {role: hero_tuple} for team using signature heroes from DB."""
    exclude = set(exclude or [])
    conn = sqlite3.connect(db_name)
    row = conn.execute(
        "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE id=?",
        (team_id,)
    ).fetchone()
    if not row:
        conn.close()
        return random_picks(exclude=exclude)

    # Get patch buffed heroes
    patch_buffed = set()
    try:
        from logic.meta import get_patch_hero_lists
        buffed, _, _ = get_patch_hero_lists(db_name)
        patch_buffed = set(buffed)
    except Exception:
        pass

    picks = {}
    taken = set(exclude)
    for role, pid in zip(ROLE_ORDER, row):
        h = _pick_for_player(conn, pid, role, taken, patch_buffed)
        picks[role] = h
        taken.add(h[0])
    conn.close()
    return picks


def ai_draft_bans(available_names, count, opponent_picks=None):
    """AI bans: target opponent's best/meta heroes first."""
    opponent_picks = opponent_picks or {}
    # Priority: ban picked heroes if we know opponent's picks
    picked = {h[0] if isinstance(h, tuple) else h for h in opponent_picks.values()}
    targets = list(picked & set(available_names))
    random.shuffle(targets)
    if len(targets) < count:
        rest = [h for h in available_names if h not in picked]
        random.shuffle(rest)
        targets += rest
    return targets[:count]


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
