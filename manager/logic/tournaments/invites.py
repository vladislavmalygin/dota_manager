import sqlite3
import random
import math

from logic.dota.match_data import get_match_data
from logic.dota.game import dota_simulation_for_bots

REGIONS = ['NA', 'SA', 'WEU', 'EEU', 'China', 'SEA']


def _play_q(t1, t2, db_name):
    skills = get_match_data(t1, t2, db_name)
    return dota_simulation_for_bots(t1, t2, skills) if skills else random.choice([t1, t2])


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


def invites(db_name):
    """
    16 teams for a tournament:
      - Top 8 by rating → direct invites
      - 8 spots via regional qualifiers (single-elimination per region)
    Player's team is always included.
    """
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute("SELECT name FROM teams WHERE player='yes'")
    row = cur.fetchone()
    player_team = row[0].strip() if row else None

    cur.execute("""
        SELECT name, COALESCE(rating, 0), COALESCE(region, 'WEU')
        FROM teams
        ORDER BY COALESCE(rating, 0) DESC, id ASC
    """)
    all_teams = [(r[0].strip(), r[1], r[2] or 'WEU') for r in cur.fetchall()]
    conn.close()

    if len(all_teams) <= 16:
        return [t[0] for t in all_teams]

    # Direct invites: top 8
    direct = all_teams[:8]
    direct_names = {t[0] for t in direct}

    # Qualifier pool
    qualifier_pool = [t for t in all_teams[8:] if t[0] not in direct_names]

    # Group by region
    regional = {}
    for name, rating, region in qualifier_pool:
        regional.setdefault(region, []).append((name, rating))

    # Run qualifiers
    qualifiers = _run_regional_qualifiers(regional, 8, db_name)
    qualifiers = list(dict.fromkeys(qualifiers))[:8]   # deduplicate, cap at 8

    # Pad if regions didn't produce enough
    if len(qualifiers) < 8:
        pool_names = [t[0] for t in qualifier_pool if t[0] not in qualifiers]
        qualifiers.extend(pool_names[:8 - len(qualifiers)])

    result = [t[0] for t in direct] + qualifiers

    # Guarantee player team is in
    if player_team and player_team not in result:
        result[-1] = player_team

    return result[:16]
