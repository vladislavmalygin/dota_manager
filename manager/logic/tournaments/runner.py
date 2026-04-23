"""
Tournament event generator — pure Python, no Kivy.

Generates a deterministic sequence of events that the UI can
step through one at a time.
"""

import sqlite3
import random

from logic.dota.match_data import get_match_data, get_teams_with_player_yes
from logic.dota.game import dota_simulation_for_bots
from logic.tournaments.invites import invites
from logic.tournaments.prizepool import get_prizepool_worldcup_system
from logic.tournaments.rating import get_ratingpool_worldcup_system


def get_lineup(team_name, db_name):
    """Returns list of player dicts for a team (5 roles)."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE name = ?",
        (team_name,)
    )
    role_ids = cursor.fetchone()
    if not role_ids:
        conn.close()
        return []

    roles = ['Carry', 'Mid', 'Offlane', 'Support 4', 'Support 5']
    lineup = []
    for i, role in enumerate(roles):
        pid = role_ids[i]
        if pid:
            cursor.execute(
                "SELECT name, surname, nickname, micro_skills, macro_skills FROM players WHERE id = ?",
                (pid,)
            )
            p = cursor.fetchone()
            if p:
                lineup.append({
                    'role': role,
                    'name': (p[0] or '').strip(),
                    'surname': (p[1] or '').strip(),
                    'nick': (p[2] or '').strip(),
                    'micro': p[3] or 0,
                    'macro': p[4] or 0,
                })
    conn.close()
    return lineup


def _play(t1, t2, db_name):
    skills = get_match_data(t1, t2, db_name)
    return dota_simulation_for_bots(t1, t2, skills) if skills else random.choice([t1, t2])


def generate_tournament_events(db_name, tournament_id):
    """
    Pre-generates all tournament events.

    Returns (events_list, placements_dict, group_eliminated_list).

    Event types:
      'draw'            – show group assignments
      'match_lineup'    – show player lineups (player team match only)
      'match_result'    – result of one match
      'groups_complete' – final group standings
      'stage_header'    – QF/SF/Final bracket header
      'tournament_results' – champion + full standings
    """
    player_teams = get_teams_with_player_yes(db_name)
    all_teams = invites(db_name)[:16]
    random.shuffle(all_teams)
    groups = [all_teams[i:i + 4] for i in range(0, 16, 4)]
    group_standings = [{t: 0 for t in g} for g in groups]

    events = []

    # ── Draw ──────────────────────────────────────────────
    events.append({
        'type': 'draw',
        'groups': [list(g) for g in groups],
        'player_teams': list(player_teams),
    })

    # ── Group stage – all 6 matches per group, interleaved ─
    # pairs_per_group[gi] = list of (gi, t1, t2)
    pairs_per_group = []
    for gi, group in enumerate(groups):
        pairs = [
            (gi, group[i], group[j])
            for i in range(len(group))
            for j in range(i + 1, len(group))
        ]
        pairs_per_group.append(pairs)

    max_per_group = max(len(p) for p in pairs_per_group)
    ordered_matches = [
        pairs_per_group[gi][mi]
        for mi in range(max_per_group)
        for gi in range(4)
        if mi < len(pairs_per_group[gi])
    ]

    for gi, t1, t2 in ordered_matches:
        is_player = t1 in player_teams or t2 in player_teams
        winner = _play(t1, t2, db_name)
        loser = t2 if winner == t1 else t1
        group_standings[gi][winner] += 3

        if is_player:
            events.append({
                'type': 'match_lineup',
                'stage': f'Группа {gi + 1}',
                'team1': t1, 'team2': t2,
                't1_lineup': get_lineup(t1, db_name),
                't2_lineup': get_lineup(t2, db_name),
            })

        events.append({
            'type': 'match_result',
            'stage': f'Группа {gi + 1}',
            'team1': t1, 'team2': t2,
            'winner': winner, 'loser': loser,
            'is_player_match': is_player,
            'standings': dict(group_standings[gi]),
            'group_idx': gi,
        })

    # ── Group stage complete ───────────────────────────────
    top_teams, group_eliminated, final_standings = [], [], []
    for gi, standings in enumerate(group_standings):
        sorted_s = sorted(standings.items(), key=lambda x: x[1], reverse=True)
        final_standings.append(sorted_s)
        top_teams.extend(t for t, _ in sorted_s[:2])
        group_eliminated.extend(sorted_s[2:])

    events.append({
        'type': 'groups_complete',
        'group_standings': final_standings,
        'top_teams': top_teams,
        'groups': [list(g) for g in groups],
    })

    # ── Playoff ───────────────────────────────────────────
    random.shuffle(top_teams)

    def _playoff_round(pairs, stage_label):
        winners, losers = [], []
        events.append({'type': 'stage_header', 'stage': stage_label,
                       'pairs': [(p[0], p[1]) for p in pairs]})
        for t1, t2 in pairs:
            is_player = t1 in player_teams or t2 in player_teams
            winner = _play(t1, t2, db_name)
            loser = t2 if winner == t1 else t1
            winners.append(winner)
            losers.append(loser)
            if is_player:
                events.append({
                    'type': 'match_lineup',
                    'stage': stage_label,
                    'team1': t1, 'team2': t2,
                    't1_lineup': get_lineup(t1, db_name),
                    't2_lineup': get_lineup(t2, db_name),
                })
            events.append({
                'type': 'match_result',
                'stage': stage_label,
                'team1': t1, 'team2': t2,
                'winner': winner, 'loser': loser,
                'is_player_match': is_player,
            })
        return winners, losers

    qf_pairs = [(top_teams[i], top_teams[i + 1]) for i in range(0, 8, 2)]
    qf_winners, qf_losers = _playoff_round(qf_pairs, 'Четвертьфиналы')

    random.shuffle(qf_winners)
    sf_pairs = [(qf_winners[i], qf_winners[i + 1]) for i in range(0, 4, 2)]
    sf_winners, sf_losers = _playoff_round(sf_pairs, 'Полуфиналы')

    final_pair = [(sf_winners[0], sf_winners[1])]
    final_winners, _ = _playoff_round(final_pair, 'Финал')
    champion = final_winners[0]
    runner_up = sf_winners[1] if champion == sf_winners[0] else sf_winners[0]

    # ── Placements ────────────────────────────────────────
    placements = {champion: 1, runner_up: 2}
    for i, t in enumerate(sf_losers):
        placements[t] = 3 + i
    for i, t in enumerate(qf_losers):
        placements[t] = 5 + i

    events.append({
        'type': 'tournament_results',
        'champion': champion,
        'placements': placements,
        'group_eliminated': group_eliminated,
        'tournament_id': tournament_id,
    })

    return events, placements, group_eliminated


def save_tournament_results(tournament_id, placements, group_eliminated, db_name):
    """Persists standings, prizes and rating to the database."""
    prizes = get_prizepool_worldcup_system(tournament_id, db_name)
    ratings = get_ratingpool_worldcup_system(tournament_id, db_name)

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Build 1-16 standings list
    group_sorted = sorted(group_eliminated, key=lambda x: x[1], reverse=True)
    final_standings = [None] * 16
    for team, place in placements.items():
        final_standings[place - 1] = team
    for i, (team, _) in enumerate(group_sorted):
        final_standings[8 + i] = team

    cursor.execute("SELECT id, name FROM teams")
    id_map = {row[1].strip(): row[0] for row in cursor.fetchall()}

    # Write place1..place16
    place_cols = {
        f"place{i + 1}": id_map.get(final_standings[i])
        for i in range(16)
        if final_standings[i] and id_map.get(final_standings[i])
    }
    if place_cols:
        set_clause = ", ".join(f"{c} = ?" for c in place_cols)
        cursor.execute(
            f"UPDATE tournaments SET {set_clause} WHERE id = ?",
            list(place_cols.values()) + [tournament_id]
        )

    # Distribute prizes and rating
    for i, team_name in enumerate(final_standings):
        if not team_name:
            continue
        tid = id_map.get(team_name)
        if not tid:
            continue
        prize = prizes[i] if prizes and i < len(prizes) else 0
        rating_pts = ratings[i] if ratings and i < len(ratings) else 0
        if prize:
            cursor.execute("UPDATE teams SET budget = budget + ? WHERE id = ?", (prize, tid))
        if rating_pts:
            cursor.execute(
                "UPDATE teams SET rating = COALESCE(rating, 0) + ? WHERE id = ?",
                (rating_pts, tid)
            )

    conn.commit()
    conn.close()


SEASON_TOURNAMENTS = [
    # (name, start_date, end_date, prizepool, ratingpool)
    ("ESL One Bangkok 2024",   "2024-11-10", "2024-11-17", 500_000,   500),
    ("DreamLeague Season 25",  "2025-01-12", "2025-01-19", 1_000_000, 1000),
    ("ESL One Birmingham 2025","2025-03-09", "2025-03-16", 500_000,   500),
    ("PGL Wallachia Season 3", "2025-04-27", "2025-05-04", 1_000_000, 1000),
    ("The International 2025", "2025-08-02", "2025-08-14", 1_600_000, 1500),
]


def ensure_season_tournaments(db_name):
    """Adds missing season tournaments to an existing save database."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM tournaments")
    existing = {row[0] for row in cursor.fetchall()}

    for name, start, end, prize, rating in SEASON_TOURNAMENTS:
        if name not in existing:
            cursor.execute(
                "INSERT INTO tournaments (name, start_date, end_date, prizepool, ratingpool) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, start, end, prize, rating)
            )

    conn.commit()
    conn.close()
