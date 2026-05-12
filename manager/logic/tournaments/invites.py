import sqlite3
import random
import math

from logic.dota.match_data import get_match_data
from logic.dota.game import dota_simulation_for_bots, dota_simulation_logged

REGIONS = ['NA', 'SA', 'WEU', 'EEU', 'China', 'SEA']


def _play_q(t1, t2, db_name):
    skills = get_match_data(t1, t2, db_name)
    return dota_simulation_for_bots(t1, t2, skills) if skills else random.choice([t1, t2])


def _play_q_logged(t1, t2, db_name):
    skills = get_match_data(t1, t2, db_name)
    if not skills:
        w = random.choice([t1, t2])
        return w, [], [], {}
    return dota_simulation_logged(t1, t2, skills)


def _single_elim(teams_rated, db_name):
    """Single elimination, highest-rated teams get byes. Returns winner name."""
    if not teams_rated:
        return None
    if len(teams_rated) == 1:
        return teams_rated[0][0]

    n = len(teams_rated)
    bracket_size = 1 << math.ceil(math.log2(max(n, 2)))
    byes = bracket_size - n

    # Top `byes` teams advance without playing
    advanced = [t[0] for t in teams_rated[:byes]]
    playing  = list(teams_rated[byes:])

    # Pair: highest seed vs lowest seed
    r1_winners = list(advanced)
    lo = len(playing) - 1
    hi = 0
    while hi < lo:
        r1_winners.append(_play_q(playing[hi][0], playing[lo][0], db_name))
        hi += 1
        lo -= 1
    if hi == lo:
        r1_winners.append(playing[hi][0])  # odd team gets bye

    # Continue rounds until 1 remains
    current = r1_winners
    while len(current) > 1:
        random.shuffle(current)
        nxt = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                nxt.append(_play_q(current[i], current[i + 1], db_name))
            else:
                nxt.append(current[i])
        current = nxt

    return current[0] if current else teams_rated[0][0]


def _single_elim_with_events(teams_rated, player_teams, db_name, stage='Квалификация (BO1)'):
    """Single elimination that logs matches involving player_teams.
    Returns (winner, events_list).
    """
    if not teams_rated:
        return None, []
    if len(teams_rated) == 1:
        return teams_rated[0][0], []

    events = []
    n = len(teams_rated)
    bracket_size = 1 << math.ceil(math.log2(max(n, 2)))
    byes = bracket_size - n
    advanced = [t[0] for t in teams_rated[:byes]]
    playing  = list(teams_rated[byes:])

    r1_winners = list(advanced)
    lo, hi = len(playing) - 1, 0
    while hi < lo:
        t1, t2 = playing[hi][0], playing[lo][0]
        is_p = t1 in player_teams or t2 in player_teams
        if is_p:
            winner, lines, snaps, stats = _play_q_logged(t1, t2, db_name)
            s1, s2 = (1, 0) if winner == t1 else (0, 1)
            events.append({
                'type': 'match_lineup',
                'stage': stage, 'team1': t1, 'team2': t2,
                'best_of': 1, 'match_log': lines, 'match_snaps': snaps,
                'winner': winner, 'score_t1': s1, 'score_t2': s2,
                'match_stats': stats, 'is_player_match': True,
            })
        else:
            winner = _play_q(t1, t2, db_name)
            s1, s2 = (1, 0) if winner == t1 else (0, 1)
        loser = t2 if winner == t1 else t1
        events.append({
            'type': 'match_result', 'stage': stage,
            'team1': t1, 'team2': t2, 'winner': winner, 'loser': loser,
            'score_t1': s1, 'score_t2': s2, 'is_player_match': is_p,
        })
        r1_winners.append(winner)
        hi += 1; lo -= 1
    if hi == lo:
        r1_winners.append(playing[hi][0])

    current = r1_winners
    while len(current) > 1:
        random.shuffle(current)
        nxt = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                t1, t2 = current[i], current[i + 1]
                is_p = t1 in player_teams or t2 in player_teams
                if is_p:
                    winner, lines, snaps, stats = _play_q_logged(t1, t2, db_name)
                    s1, s2 = (1, 0) if winner == t1 else (0, 1)
                    events.append({
                        'type': 'match_lineup',
                        'stage': stage, 'team1': t1, 'team2': t2,
                        'best_of': 1, 'match_log': lines, 'match_snaps': snaps,
                        'winner': winner, 'score_t1': s1, 'score_t2': s2,
                        'match_stats': stats, 'is_player_match': True,
                    })
                else:
                    winner = _play_q(t1, t2, db_name)
                    s1, s2 = (1, 0) if winner == t1 else (0, 1)
                loser = t2 if winner == t1 else t1
                events.append({
                    'type': 'match_result', 'stage': stage,
                    'team1': t1, 'team2': t2, 'winner': winner, 'loser': loser,
                    'score_t1': s1, 'score_t2': s2, 'is_player_match': is_p,
                })
                nxt.append(winner)
            else:
                nxt.append(current[i])
        current = nxt

    return (current[0] if current else teams_rated[0][0]), events


def _run_regional_qualifiers(regional, n_spots, db_name):
    """
    For each region with teams, run single-elimination qualifier.
    Spots are distributed proportionally; each active region gets ≥1.
    Returns list of qualified team names.
    """
    active = [(r, regional[r]) for r in REGIONS if regional.get(r)]
    if not active:
        return []

    total = sum(len(t) for _, t in active)
    spots = {r: 1 for r, _ in active}
    remaining = n_spots - len(active)

    # Extra spots proportionally to region team count (biggest first)
    for region, teams in sorted(active, key=lambda x: -len(x[1])):
        if remaining <= 0:
            break
        extra = max(0, round(len(teams) / total * n_spots) - spots[region])
        extra = min(extra, remaining, len(teams) - spots[region])
        if extra > 0:
            spots[region] += extra
            remaining -= extra

    # Leftover to largest regions
    for region, teams in sorted(active, key=lambda x: -len(x[1])):
        if remaining <= 0:
            break
        if spots[region] < len(teams):
            spots[region] += 1
            remaining -= 1

    qualifiers = []
    for region, teams in active:
        n = spots.get(region, 0)
        if n <= 0:
            continue
        sorted_t = sorted(teams, key=lambda t: t[1], reverse=True)
        if len(sorted_t) <= n:
            qualifiers.extend(t[0] for t in sorted_t)
            continue
        # Run n separate brackets (winner removed each time)
        remaining_t = list(sorted_t)
        for _ in range(n):
            if not remaining_t:
                break
            winner = _single_elim(remaining_t, db_name)
            qualifiers.append(winner)
            remaining_t = [t for t in remaining_t if t[0] != winner]

    return qualifiers


def get_non_qualified_teams(db_name, qualified_16):
    """Teams with 3+ filled slots that are NOT in the main tournament."""
    conn = sqlite3.connect(db_name)
    cur  = conn.cursor()
    cur.execute("""
        SELECT name FROM teams
        WHERE (CASE WHEN carry           IS NOT NULL THEN 1 ELSE 0 END +
               CASE WHEN mid             IS NOT NULL THEN 1 ELSE 0 END +
               CASE WHEN offlane         IS NOT NULL THEN 1 ELSE 0 END +
               CASE WHEN partial_support IS NOT NULL THEN 1 ELSE 0 END +
               CASE WHEN full_support    IS NOT NULL THEN 1 ELSE 0 END) >= 3
    """)
    eligible = {r[0].strip() for r in cur.fetchall()}
    conn.close()
    q_set = {t.strip() for t in qualified_16}
    return sorted(t for t in eligible if t not in q_set)


def _pad_to_16(result, db_name):
    """Fill result up to 16 with highest-rated remaining teams."""
    in_set = set(result)
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    if in_set:
        cur.execute(
            "SELECT name FROM teams WHERE name NOT IN ({}) "
            "ORDER BY COALESCE(rating,0) DESC".format(','.join('?' * len(in_set))),
            list(in_set),
        )
    else:
        cur.execute("SELECT name FROM teams ORDER BY COALESCE(rating,0) DESC")
    for row in cur.fetchall():
        name = row[0].strip()
        if name not in in_set:
            result.append(name)
            in_set.add(name)
            if len(result) >= 16:
                break
    conn.close()


def _build_teams_and_pool(db_name, region_filter=None):
    """Shared setup for both invites() and invites_with_events()."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("SELECT name FROM teams WHERE player='yes'")
    row = cur.fetchone()
    player_team = row[0].strip() if row else None
    cur.execute("""
        SELECT name, COALESCE(rating, 0), COALESCE(region, 'WEU')
        FROM teams
        WHERE player = 'yes'
           OR (carry IS NOT NULL AND mid IS NOT NULL AND offlane IS NOT NULL
               AND partial_support IS NOT NULL AND full_support IS NOT NULL)
        ORDER BY COALESCE(rating, 0) DESC, id ASC
    """)
    all_teams = [(r[0].strip(), r[1], r[2] or 'WEU') for r in cur.fetchall()]
    conn.close()
    if region_filter:
        all_teams = [t for t in all_teams if t[2] == region_filter]
    return player_team, all_teams


def invites(db_name, region_filter=None):
    """
    16 teams for a tournament:
      - Top 8 by rating → direct invites
      - 8 spots via regional qualifiers
    Player's team competes fairly — no guarantee.
    """
    player_team, all_teams = _build_teams_and_pool(db_name, region_filter)

    if len(all_teams) <= 16:
        result = [t[0] for t in all_teams]
        if len(result) < 16:
            _pad_to_16(result, db_name)
        return result[:16]

    direct = all_teams[:8]
    direct_names = {t[0] for t in direct}
    qualifier_pool = [t for t in all_teams[8:] if t[0] not in direct_names]
    regional = {}
    for name, rating, region in qualifier_pool:
        regional.setdefault(region, []).append((name, rating))

    qualifiers = _run_regional_qualifiers(regional, 8, db_name)
    qualifiers = list(dict.fromkeys(qualifiers))[:8]

    if len(qualifiers) < 8:
        pool_names = [t[0] for t in qualifier_pool if t[0] not in qualifiers]
        qualifiers.extend(pool_names[:8 - len(qualifiers)])

    result = [t[0] for t in direct] + qualifiers

    if len(result) < 16:
        _pad_to_16(result, db_name)

    return result[:16]


def invites_with_events(db_name, region_filter=None):
    """Like invites() but also generates qualifier match events if player is in qualifier pool.
    Returns (qualified_16, qualifier_events, player_qualified_bool).
    """
    player_team, all_teams = _build_teams_and_pool(db_name, region_filter)
    player_teams = {player_team} if player_team else set()

    if len(all_teams) <= 16:
        result = [t[0] for t in all_teams]
        if len(result) < 16:
            _pad_to_16(result, db_name)
        return result[:16], [], player_team in result if player_team else False

    direct = all_teams[:8]
    direct_names = {t[0] for t in direct}
    qualifier_pool = [t for t in all_teams[8:] if t[0] not in direct_names]

    # Check if player is in qualifier pool
    player_in_qual = player_team and player_team not in direct_names and \
                     any(t[0] == player_team for t in qualifier_pool)

    # Regional grouping
    regional = {}
    for name, rating, region in qualifier_pool:
        regional.setdefault(region, []).append((name, rating))

    qualifier_events = []
    qualifiers = []

    active = [(r, regional[r]) for r in REGIONS if regional.get(r)]
    total = sum(len(t) for _, t in active)
    spots = {r: 1 for r, _ in active}
    remaining = 8 - len(active)
    for region, teams in sorted(active, key=lambda x: -len(x[1])):
        if remaining <= 0:
            break
        extra = max(0, round(len(teams) / total * 8) - spots[region])
        extra = min(extra, remaining, len(teams) - spots[region])
        if extra > 0:
            spots[region] += extra
            remaining -= extra
    for region, teams in sorted(active, key=lambda x: -len(x[1])):
        if remaining <= 0:
            break
        if spots[region] < len(teams):
            spots[region] += 1
            remaining -= 1

    for region, teams in active:
        n = spots.get(region, 0)
        if n <= 0:
            continue
        sorted_t = sorted(teams, key=lambda t: t[1], reverse=True)
        if len(sorted_t) <= n:
            qualifiers.extend(t[0] for t in sorted_t)
            continue
        remaining_t = list(sorted_t)
        player_in_region = any(t[0] == player_team for t in sorted_t) if player_in_qual else False
        for _ in range(n):
            if not remaining_t:
                break
            if player_in_region:
                winner, evs = _single_elim_with_events(remaining_t, player_teams, db_name)
                qualifier_events.extend(evs)
                player_in_region = False  # only log once
            else:
                winner = _single_elim(remaining_t, db_name)
            qualifiers.append(winner)
            remaining_t = [t for t in remaining_t if t[0] != winner]

    qualifiers = list(dict.fromkeys(qualifiers))[:8]
    if len(qualifiers) < 8:
        pool_names = [t[0] for t in qualifier_pool if t[0] not in qualifiers]
        qualifiers.extend(pool_names[:8 - len(qualifiers)])

    result = [t[0] for t in direct] + qualifiers
    if len(result) < 16:
        _pad_to_16(result, db_name)
    result = result[:16]

    player_qualified = (player_team in result) if player_team else True
    return result, qualifier_events, player_qualified
