"""
Team chemistry score (1-10) based on regional cohesion, tactic alignment,
time together, and morale. Applied as ±5% skill multiplier in match sim.
"""
import sqlite3
from collections import Counter


def chemistry_score(db_name, team_id):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    row = c.execute(
        "SELECT carry,mid,offlane,partial_support,full_support,"
        "COALESCE(tactic,'balanced') FROM teams WHERE id=?", (team_id,)
    ).fetchone()
    if not row or not any(row[:5]):
        conn.close()
        return 5.0

    pids   = [p for p in row[:5] if p]
    tactic = row[5]

    players = []
    for pid in pids:
        p = c.execute(
            "SELECT country, COALESCE(micro_skills,0), COALESCE(macro_skills,0),"
            "COALESCE(soft_skills,0), COALESCE(time_in_team,0), COALESCE(morale,5),"
            "COALESCE(psychotype,'team_player')"
            " FROM players WHERE id=?", (pid,)
        ).fetchone()
        if p:
            players.append(p)
    conn.close()

    if not players:
        return 5.0

    score = 5.0

    # Regional cohesion — same region = players comfortable communicating
    from logic.ai import _region
    regions = [_region(p[0] or '') for p in players]
    dominant = Counter(regions).most_common(1)[0][1] if regions else 0
    if   dominant >= 4: score += 1.5
    elif dominant >= 3: score += 0.8

    # Tactic fits team skill strengths
    micro_avg = sum(p[1] for p in players) / len(players)
    macro_avg = sum(p[2] for p in players) / len(players)
    soft_avg  = sum(p[3] for p in players) / len(players)
    best = max(micro_avg, macro_avg, soft_avg)
    if ((tactic == 'aggressive' and micro_avg == best) or
        (tactic == 'farming'    and macro_avg == best) or
        (tactic == 'teamplay'   and soft_avg  == best)):
        score += 0.8

    # Time together — veterans know each other's playstyle
    avg_time = sum(p[4] for p in players) / len(players)
    if   avg_time >= 3: score += 1.0
    elif avg_time >= 1: score += 0.5

    # Pair bonds — carry/mid/offlane veterans together ≥ 2 seasons
    core_times = [p[4] for p in players[:3]]  # carry, mid, offlane time_in_team
    bonded_pairs = sum(1 for t in core_times if t >= 2)
    if   bonded_pairs == 3: score += 1.2
    elif bonded_pairs == 2: score += 0.6

    # Psychotype effects
    psychotypes = [p[6] for p in players]
    leaders     = psychotypes.count('leader')
    team_players = psychotypes.count('team_player')
    if leaders >= 2:   score -= 1.5  # two alphas clash
    elif leaders == 1: score += 0.3  # one leader = good
    if team_players >= 3: score += 0.5

    # Morale
    avg_morale = sum(p[5] for p in players) / len(players)
    if   avg_morale >= 8: score += 0.5
    elif avg_morale <= 3: score -= 0.5

    return min(10.0, max(1.0, round(score * 10) / 10))


def pair_bond_description(db_name, team_id):
    """Return short text about strongest player pairs for UI."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    row = c.execute(
        "SELECT carry,mid,offlane,partial_support,full_support FROM teams WHERE id=?",
        (team_id,)
    ).fetchone()
    if not row:
        conn.close()
        return ''
    roles = ['carry', 'mid', 'offlane', 'sup4', 'sup5']
    pairs = []
    for i, pid in enumerate(row):
        if not pid:
            continue
        p = c.execute(
            "SELECT nickname, COALESCE(time_in_team,0) FROM players WHERE id=?", (pid,)
        ).fetchone()
        if p and p[1] >= 2:
            pairs.append((p[0], roles[i], p[1]))
    conn.close()
    if len(pairs) >= 2:
        names = ' + '.join(f'{n}({r})' for n, r, _ in pairs[:2])
        return f'Связка: {names}'
    return ''


def chemistry_mult(score):
    """Skill multiplier: score 5 → 1.0, score 10 → 1.05, score 1 → 0.96."""
    return 1.0 + (score - 5) * 0.01
