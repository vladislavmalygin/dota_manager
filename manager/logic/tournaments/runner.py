"""
Tournament event generator — pure Python, no Kivy.

Format:
  • 16 teams (8 direct invites + 8 regional qualifiers)
  • Group stage: 2 groups of 8, round-robin BO2
      – Top 4 per group → Upper Bracket (8 UB seeds)
      – Bottom 4 per group → Lower Bracket (8 LB seeds)
  • Main event: 16-team double elimination
      LB R1    → 4 matches BO1  → 4 survive,  4 out  (P13-16)
      UB R1    → 4 matches BO3  → 4 UB winners, 4 drop to LB
      LB R2    → 4 matches BO3  → 4 survive,  4 out  (P9-12)
      LB R3    → 2 matches BO3  → 2 survive,  2 out  (P7-8)
      UB SF    → 2 matches BO3  → 2 UB Final seeds, 2 drop to LB
      LB QF    → 2 matches BO3  → 2 LB SF seeds, 2 out  (P5-6)
      UB Final → 1 match  BO3  → UB champion, loser → LB SF (3-team)
      LB SF    → 1 match  BO3  (2 LB QF winners + UB Final loser, 1 bye)
      LB Final → 1 match  BO3
      Grand Final → BO5
  • Placements: 1/2 GF, 3-4 LB Final/SF losers, 5-6 LB QF losers,
                7-8 LB R3 losers, 9-12 LB R2 losers, 13-16 LB R1 losers
"""

import sqlite3
import random

from logic.dota.match_data import get_match_data, get_teams_with_player_yes
from logic.dota.game import dota_simulation_for_bots, dota_simulation_logged
from logic.tournaments.invites import invites, invites_with_events, get_non_qualified_teams
from logic.tournaments.prizepool import get_prizepool_worldcup_system
from logic.tournaments.rating import get_ratingpool_worldcup_system


# ── helpers ───────────────────────────────────────────────────────────────────

def get_lineup(team_name, db_name):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute(
        "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE name = ?",
        (team_name,),
    )
    role_ids = cur.fetchone()
    if not role_ids:
        conn.close()
        return []
    roles = ['Carry', 'Mid', 'Offlane', 'Support 4', 'Support 5']
    lineup = []
    for i, role in enumerate(roles):
        pid = role_ids[i]
        if pid:
            cur.execute(
                "SELECT name, surname, nickname, micro_skills, macro_skills FROM players WHERE id=?",
                (pid,),
            )
            p = cur.fetchone()
            if p:
                lineup.append({'role': role, 'name': (p[0] or '').strip(),
                                'surname': (p[1] or '').strip(),
                                'nick': (p[2] or '').strip(),
                                'micro': p[3] or 0, 'macro': p[4] or 0})
    conn.close()
    return lineup


def _play_one(t1, t2, db_name):
    skills = get_match_data(t1, t2, db_name)
    return dota_simulation_for_bots(t1, t2, skills) if skills else random.choice([t1, t2])


def _play_one_logged(t1, t2, db_name, hero_picks=None):
    skills = get_match_data(t1, t2, db_name, hero_picks=hero_picks)
    if not skills:
        return random.choice([t1, t2]), [], [], {}
    return dota_simulation_logged(t1, t2, skills)


def replay_match_with_heroes(t1, t2, db_name, hero_picks):
    """Re-run a logged match with hero picks applied. Returns (winner, lines, snaps, stats)."""
    return _play_one_logged(t1, t2, db_name, hero_picks=hero_picks)


def _play_bo(t1, t2, db_name, n):
    """Best-of-N with early termination when a team clinches."""
    needed = n // 2 + 1
    s = {t1: 0, t2: 0}
    for _ in range(n):
        s[_play_one(t1, t2, db_name)] += 1
        if s[t1] == needed or s[t2] == needed:
            break
    if s[t1] == s[t2]:
        w = random.choice([t1, t2])
    else:
        w = t1 if s[t1] > s[t2] else t2
    return w, s[t1], s[t2]


def _play_bo2(t1, t2, db_name):
    """Dota BO2: always 2 games. Returns (pts_t1, pts_t2, wins_t1, wins_t2)."""
    w1 = _play_one(t1, t2, db_name)
    w2 = _play_one(t1, t2, db_name)
    wins1 = (1 if w1 == t1 else 0) + (1 if w2 == t1 else 0)
    wins2 = 2 - wins1
    pts1 = 2 if wins1 == 2 else (1 if wins1 == 1 else 0)
    pts2 = 2 if wins2 == 2 else (1 if wins2 == 1 else 0)
    return pts1, pts2, wins1, wins2


def _play_bo2_logged(t1, t2, db_name):
    """Dota BO2 logged. Returns (pts_t1, pts_t2, wins_t1, wins_t2, lines, snaps)."""
    all_lines, all_snaps = [], []
    wins = {t1: 0, t2: 0}
    blank = {'phase': 'laning', 'minute': 0,
             'kills_t1': 0, 'kills_t2': 0, 'tokens_t1': 0, 'tokens_t2': 0}
    sep = '═' * 50

    for game_num in range(1, 3):
        header = f'  ИГРА {game_num}  ·  {t1} [{wins[t1]}] — [{wins[t2]}] {t2}'
        for line in [sep, header, sep]:
            all_lines.append(line)
            all_snaps.append(blank.copy())
        gw, lines, snaps, _stats = _play_one_logged(t1, t2, db_name)
        all_lines.extend(lines)
        all_snaps.extend(snaps)
        wins[gw] += 1

    w1, w2 = wins[t1], wins[t2]
    pts1 = 2 if w1 == 2 else (1 if w1 == 1 else 0)
    pts2 = 2 if w2 == 2 else (1 if w2 == 1 else 0)
    return pts1, pts2, w1, w2, all_lines, all_snaps


def _play_bo_logged(t1, t2, db_name, n):
    """Best-of-N for player matches with early termination.
    Returns (winner, score_t1, score_t2, all_lines, all_snaps).
    """
    needed = n // 2 + 1
    s = {t1: 0, t2: 0}
    all_lines, all_snaps = [], []

    for game_num in range(1, n + 1):
        blank = {'phase': 'laning', 'minute': 0,
                 'kills_t1': 0, 'kills_t2': 0, 'tokens_t1': 0, 'tokens_t2': 0,
                 'game_score_t1': s[t1], 'game_score_t2': s[t2], 'best_of': n}
        sep = '═' * 50
        header = f'  ИГРА {game_num}  ·  {t1} [{s[t1]}] — [{s[t2]}] {t2}'
        for line in [sep, header, sep]:
            all_lines.append(line)
            all_snaps.append(blank.copy())

        winner_game, lines, snaps, last_stats = _play_one_logged(t1, t2, db_name)
        for snp in snaps:
            snp['game_score_t1'] = s[t1]
            snp['game_score_t2'] = s[t2]
            snp['best_of'] = n
        all_lines.extend(lines)
        all_snaps.extend(snaps)
        s[winner_game] += 1
        if s[t1] == needed or s[t2] == needed:
            break

    if s[t1] == s[t2]:
        winner = random.choice([t1, t2])
    else:
        winner = t1 if s[t1] > s[t2] else t2
    return winner, s[t1], s[t2], all_lines, all_snaps, last_stats


# ── event builder helpers ─────────────────────────────────────────────────────

def _match_event(t1, t2, winner, loser, score_t1, score_t2, stage,
                 is_player, lines=None, snaps=None,
                 standings=None, group_idx=None):
    ev = {
        'type':            'match_result',
        'stage':           stage,
        'team1':           t1, 'team2': t2,
        'winner':          winner, 'loser': loser,
        'score_t1':        score_t1, 'score_t2': score_t2,
        'is_player_match': is_player,
    }
    if standings is not None:
        ev['standings'] = standings
        ev['group_idx'] = group_idx
    return ev


def _lineup_event(t1, t2, stage, lines, snaps, winner, score_t1, score_t2, db_name, n,
                  stats=None):
    return {
        'type':        'match_lineup',
        'stage':       stage,
        'team1':       t1, 'team2': t2,
        't1_lineup':   get_lineup(t1, db_name),
        't2_lineup':   get_lineup(t2, db_name),
        'match_log':   lines,
        'match_snaps': snaps,
        'winner':      winner,
        'score_t1':    score_t1, 'score_t2': score_t2,
        'best_of':     n,
        'match_stats': stats or {},
    }


# ── Minor tournament helpers ──────────────────────────────────────────────────

def _swiss_pairs(teams, wins):
    """Swiss pairing: pair teams by closest win count."""
    sorted_t = sorted(teams, key=lambda t: (-wins.get(t, 0), random.random()))
    pairs, used = [], set()
    for i, t1 in enumerate(sorted_t):
        if t1 in used:
            continue
        for t2 in sorted_t[i+1:]:
            if t2 not in used:
                pairs.append((t1, t2))
                used.add(t1); used.add(t2)
                break
    return pairs


def _generate_minor(minor_teams, db_name, player_teams, gp_fn):
    """Swiss BO1 group + top-4 BO3 playoff. Returns (events, placements)."""
    if len(minor_teams) < 4:
        return [], {}

    events  = []
    teams   = list(minor_teams)
    wins    = {t: 0 for t in teams}

    events.append({
        'type': 'minor_header',
        'teams': teams,
        'player_teams': list(player_teams),
    })

    num_rounds = min(4, max(3, len(teams) - 1))

    for rnd in range(1, num_rounds + 1):
        pairs = _swiss_pairs(teams, wins)
        stage = f'Малый Т. — Швейцарка Р{rnd} (BO1)'
        events.append({'type': 'stage_header', 'stage': stage, 'pairs': pairs})

        for t1, t2 in pairs:
            is_p = t1 in player_teams or t2 in player_teams
            if is_p:
                winner, lines, snaps, mstats = _play_one_logged(t1, t2, db_name)
                s1, s2 = (1, 0) if winner == t1 else (0, 1)
                events.append(_lineup_event(t1, t2, stage, lines, snaps,
                                            winner, s1, s2, db_name, 1, mstats))
            else:
                winner = _play_one(t1, t2, db_name)
                s1, s2 = (1, 0) if winner == t1 else (0, 1)
            loser = t2 if winner == t1 else t1
            wins[winner] += 1
            gp_fn(t1, t2, 1)
            events.append(_match_event(t1, t2, winner, loser, s1, s2, stage, is_p))

        ranked = sorted(teams, key=lambda t: (-wins[t], t))
        events.append({
            'type': 'minor_standings',
            'round': rnd,
            'standings': [(t, wins[t]) for t in ranked],
            'player_teams': list(player_teams),
        })

    # ── Playoff ────────────────────────────────────────────────────
    ranked = sorted(teams, key=lambda t: (-wins[t], t))
    top4   = ranked[:4]
    events.append({
        'type': 'stage_header',
        'stage': 'Малый Т. — Плей-офф (BO3)',
        'pairs': [(top4[0], top4[3]), (top4[1], top4[2])],
    })

    sf_winners, sf_losers = [], []
    for t1, t2 in [(top4[0], top4[3]), (top4[1], top4[2])]:
        is_p = t1 in player_teams or t2 in player_teams
        if is_p:
            w, s1, s2, lines, snaps, mstats = _play_bo_logged(t1, t2, db_name, 3)
            events.append(_lineup_event(t1, t2, 'Малый Т. Полуфинал',
                                        lines, snaps, w, s1, s2, db_name, 3, mstats))
        else:
            w, s1, s2 = _play_bo(t1, t2, db_name, 3)
        l = t2 if w == t1 else t1
        sf_winners.append(w); sf_losers.append(l)
        gp_fn(t1, t2, s1 + s2)
        events.append(_match_event(t1, t2, w, l, s1, s2, 'Малый Т. Полуфинал', is_p))

    t1, t2 = sf_winners
    is_p = t1 in player_teams or t2 in player_teams
    if is_p:
        wf, s1, s2, lines, snaps, mstats = _play_bo_logged(t1, t2, db_name, 3)
        events.append(_lineup_event(t1, t2, 'Малый Т. Финал',
                                    lines, snaps, wf, s1, s2, db_name, 3, mstats))
    else:
        wf, s1, s2 = _play_bo(t1, t2, db_name, 3)
    lf = t2 if wf == t1 else t1
    gp_fn(t1, t2, s1 + s2)
    events.append(_match_event(t1, t2, wf, lf, s1, s2, 'Малый Т. Финал', is_p))

    minor_places = {wf: 1, lf: 2}
    for i, l in enumerate(sf_losers): minor_places[l] = 3 + i
    for i, t in enumerate(ranked[4:]): minor_places[t] = 5 + i

    events.append({
        'type':       'minor_results',
        'champion':    wf,
        'placements':  minor_places,
        'wins':        dict(wins),
        'player_teams': list(player_teams),
    })

    return events, minor_places


# ── main generator ────────────────────────────────────────────────────────────

_DPC_REGION_MAP = {
    'EEU': 'EEU',
    'WEU': 'WEU',
    'SEA': 'SEA',
    'CN':  'China',
    'NA':  'NA',
    'SA':  'SA',
}


def _dpc_region_filter(tournament_name):
    """Return DB region string if tournament is a DPC regional league, else None."""
    import re
    m = re.search(r'\bDPC\s+(EEU|WEU|SEA|CN|NA|SA)\b', tournament_name or '')
    if m:
        return _DPC_REGION_MAP.get(m.group(1))
    return None


def generate_tournament_events(db_name, tournament_id):
    conn_t = sqlite3.connect(db_name)
    t_row = conn_t.execute(
        "SELECT name FROM tournaments WHERE id=?", (tournament_id,)
    ).fetchone()
    conn_t.close()
    tournament_name = t_row[0] if t_row else ''
    region_filter = _dpc_region_filter(tournament_name)

    player_teams = get_teams_with_player_yes(db_name)
    qualified_16, qualifier_events, player_qualified = invites_with_events(
        db_name, region_filter=region_filter
    )
    qualified_16 = qualified_16[:16]
    direct_8     = qualified_16[:8]
    qualifier_8  = qualified_16[8:]
    minor_teams  = get_non_qualified_teams(db_name, qualified_16)

    # Seed groups by rating: snake-draft so top teams split across groups
    conn_r = sqlite3.connect(db_name)
    _ratings = {r[0].strip(): r[1] for r in conn_r.execute(
        "SELECT name, COALESCE(rating,0) FROM teams"
    ).fetchall()}
    conn_r.close()
    seeded = sorted(qualified_16, key=lambda t: _ratings.get(t, 0), reverse=True)
    # snake: picks alternate groups, shuffled within each pair to add variance
    group_a, group_b = [], []
    for i, t in enumerate(seeded):
        (group_a if i % 2 == 0 else group_b).append(t)
    random.shuffle(group_a)
    random.shuffle(group_b)
    groups = [group_a, group_b]
    group_standings = [{t: 0 for t in g} for g in groups]

    events = []
    placements = {}
    group_eliminated = []
    games_played = {}

    def _gp(t1, t2, n):
        games_played[t1] = games_played.get(t1, 0) + n
        games_played[t2] = games_played.get(t2, 0) + n

    # ── Qualifier events (player's matches, if any) ───────────────
    if qualifier_events:
        events.append({
            'type':         'qualifier_header',
            'player_teams': list(player_teams),
            'player_qualified': player_qualified,
        })
        events.extend(qualifier_events)
        events.append({
            'type':         'qualifier_done',
            'qualified_8':  list(qualifier_8),
            'player_qualified': player_qualified,
            'player_teams': list(player_teams),
        })

    # ── Qualifier summary ──────────────────────────────────────────
    events.append({
        'type':             'qualifier_summary',
        'direct':            list(direct_8),
        'qualified':         list(qualifier_8),
        'minor':             list(minor_teams),
        'player_teams':      list(player_teams),
        'player_qualified':  player_qualified,
    })

    # ── Draw ──────────────────────────────────────────────────────
    events.append({
        'type': 'draw',
        'groups': [list(g) for g in groups],
        'player_teams': list(player_teams),
    })

    # ── Group stage: round-robin BO2 ──────────────────────────────
    def _rr_rounds(gi, group):
        """Standard round-robin: fix team[0], rotate the rest.
        Returns list of rounds; each round is a list of (gi, t1, t2) pairs."""
        teams = list(group)
        if len(teams) % 2:
            teams.append(None)          # dummy bye slot
        n = len(teams)
        fixed    = teams[0]
        rotating = teams[1:]
        rounds   = []
        for _ in range(n - 1):
            round_pairs = []
            a, b = fixed, rotating[0]
            if a is not None and b is not None:
                round_pairs.append((gi, a, b))
            for k in range(1, n // 2):
                a, b = rotating[k], rotating[n - 1 - k]
                if a is not None and b is not None:
                    round_pairs.append((gi, a, b))
            rounds.append(round_pairs)
            rotating = [rotating[-1]] + rotating[:-1]   # rotate right
        return rounds

    schedules   = [_rr_rounds(gi, group) for gi, group in enumerate(groups)]
    num_rounds  = max(len(s) for s in schedules)
    ordered     = []
    for rnd in range(num_rounds):
        for gi, schedule in enumerate(schedules):
            if rnd < len(schedule):
                ordered.extend(schedule[rnd])

    for gi, t1, t2 in ordered:
        is_player = t1 in player_teams or t2 in player_teams
        if is_player:
            pts1, pts2, s1, s2, lines, snaps = _play_bo2_logged(t1, t2, db_name)
        else:
            pts1, pts2, s1, s2 = _play_bo2(t1, t2, db_name)
            lines, snaps = [], []

        _gp(t1, t2, 2)
        group_standings[gi][t1] += pts1
        group_standings[gi][t2] += pts2

        winner = t1 if s1 > s2 else (t2 if s2 > s1 else '')
        loser  = t2 if winner == t1 else (t1 if winner == t2 else '')

        if is_player:
            events.append(_lineup_event(t1, t2, f'Группа {gi + 1} (BO2)',
                                        lines, snaps, winner or t1, s1, s2, db_name, 2))
        events.append(_match_event(t1, t2, winner, loser, s1, s2,
                                   f'Группа {gi + 1} (BO2)', is_player,
                                   standings=dict(group_standings[gi]),
                                   group_idx=gi))

    # ── Groups complete: top 4 → UB, bottom 4 → LB ───────────────
    ub_seeds = []
    lb_seeds = []
    final_standings = []
    for gi, standings in enumerate(group_standings):
        sorted_s = sorted(standings.items(), key=lambda x: x[1], reverse=True)
        final_standings.append(sorted_s)
        for rank, (team, pts) in enumerate(sorted_s):
            if rank < 4:
                ub_seeds.append(team)
            else:
                lb_seeds.append(team)

    events.append({
        'type':            'groups_complete',
        'group_standings':  final_standings,
        'top_teams':        ub_seeds,
        'groups':           [list(g) for g in groups],
    })

    # ─── MAIN EVENT: 16-team double elimination ───────────────────
    random.shuffle(ub_seeds)
    random.shuffle(lb_seeds)

    def _run_stage(label, pairs_flat, bo, events, player_teams, db_name):
        """Simulate one bracket round. Returns (winners, losers)."""
        winners, losers = [], []
        for i in range(0, len(pairs_flat), 2):
            t1, t2 = pairs_flat[i], pairs_flat[i + 1]
            is_player = t1 in player_teams or t2 in player_teams
            if is_player:
                w, s1, s2, lines, snaps, mstats = _play_bo_logged(t1, t2, db_name, bo)
            else:
                w, s1, s2 = _play_bo(t1, t2, db_name, bo)
                lines, snaps, mstats = [], [], {}
            l = t2 if w == t1 else t1
            _gp(t1, t2, s1 + s2)
            winners.append(w)
            losers.append(l)
            if is_player:
                events.append(_lineup_event(t1, t2, label, lines, snaps,
                                            w, s1, s2, db_name, bo, mstats))
            events.append(_match_event(t1, t2, w, l, s1, s2, label, is_player))
        return winners, losers

    def _stage_header(label, pairs):
        events.append({'type': 'stage_header', 'stage': label, 'pairs': pairs})

    # LB R1 (BO1): 4 matches — 4 out (P13-16)
    _stage_header('LB — Раунд 1 (BO1)', [(lb_seeds[i], lb_seeds[i+1]) for i in range(0, 8, 2)])
    lb_r2_seeds, lb_r1_elim = _run_stage(
        'LB — Раунд 1 (BO1)', lb_seeds, 1, events, player_teams, db_name)
    for t in lb_r1_elim:
        placements[t] = 13

    # UB R1 (BO3): 4 matches — 4 UB winners, 4 drop to LB
    _stage_header('UB — Раунд 1 (BO3)', [(ub_seeds[i], ub_seeds[i+1]) for i in range(0, 8, 2)])
    ub_sf_seeds, ub_r1_drops = _run_stage(
        'UB — Раунд 1 (BO3)', ub_seeds, 3, events, player_teams, db_name)

    # LB R2 (BO3): LB R1 survivors vs UB R1 drops (crossed) — 4 out (P9-12)
    lb_r2_all = [lb_r2_seeds[i // 2] if i % 2 == 0 else ub_r1_drops[i // 2]
                 for i in range(8)]
    _stage_header('LB — Раунд 2 (BO3)', [(lb_r2_all[i], lb_r2_all[i+1]) for i in range(0, 8, 2)])
    lb_r3_seeds, lb_r2_elim = _run_stage(
        'LB — Раунд 2 (BO3)', lb_r2_all, 3, events, player_teams, db_name)
    for t in lb_r2_elim:
        placements[t] = 9

    # LB R3 (BO3): 2 matches — 2 out (P7-8)
    random.shuffle(lb_r3_seeds)
    _stage_header('LB — Раунд 3 (BO3)', [(lb_r3_seeds[i], lb_r3_seeds[i+1]) for i in range(0, 4, 2)])
    lb_qf_seeds, lb_r3_elim = _run_stage(
        'LB — Раунд 3 (BO3)', lb_r3_seeds, 3, events, player_teams, db_name)
    for t in lb_r3_elim:
        placements[t] = 7

    # UB SF (BO3): 2 matches — 2 UB Final seeds, 2 drop to LB
    _stage_header('UB — Полуфиналы (BO3)', [(ub_sf_seeds[i], ub_sf_seeds[i+1]) for i in range(0, 4, 2)])
    ub_final_seeds, ub_sf_drops = _run_stage(
        'UB — Полуфиналы (BO3)', ub_sf_seeds, 3, events, player_teams, db_name)

    # LB QF (BO3): 2 LB R3 survivors + 2 UB SF drops — 2 out (P5-6)
    lb_qf_all = [lb_qf_seeds[0], ub_sf_drops[1],
                 lb_qf_seeds[1], ub_sf_drops[0]]
    _stage_header('LB — Четвертьфиналы (BO3)',
                  [(lb_qf_all[0], lb_qf_all[1]), (lb_qf_all[2], lb_qf_all[3])])
    lb_sf_seeds, lb_qf_elim = _run_stage(
        'LB — Четвертьфиналы (BO3)', lb_qf_all, 3, events, player_teams, db_name)
    for t in lb_qf_elim:
        placements[t] = 5

    # UB Final (BO3)
    _stage_header('UB — Финал (BO3)', [(ub_final_seeds[0], ub_final_seeds[1])])
    ub_champ_list, ub_final_losers = _run_stage(
        'UB — Финал (BO3)', ub_final_seeds, 3, events, player_teams, db_name)
    ub_champion    = ub_champ_list[0]
    ub_final_loser = ub_final_losers[0]

    # LB SF (BO3) — 3 teams: 2 LB QF winners + UB Final loser, 1 bye
    lb_sf_all = lb_sf_seeds + [ub_final_loser]
    random.shuffle(lb_sf_all)
    sf_pair      = (lb_sf_all[0], lb_sf_all[1])
    lb_final_bye = lb_sf_all[2]
    _stage_header('LB — Полуфинал (BO3)', [sf_pair])
    lb_sf_winner_list, lb_sf_losers = _run_stage(
        'LB — Полуфинал (BO3)', list(sf_pair), 3, events, player_teams, db_name)
    lb_sf_winner = lb_sf_winner_list[0]
    for t in lb_sf_losers:
        placements[t] = 3

    # LB Final (BO3)
    _stage_header('LB — Финал (BO3)', [(lb_sf_winner, lb_final_bye)])
    lb_champ_list, lb_final_losers = _run_stage(
        'LB — Финал (BO3)', [lb_sf_winner, lb_final_bye], 3, events, player_teams, db_name)
    lb_champion = lb_champ_list[0]
    placements[lb_final_losers[0]] = 3

    # Grand Final (BO5)
    _stage_header('Гранд-финал (BO5)', [(ub_champion, lb_champion)])
    t1, t2 = ub_champion, lb_champion
    is_player = t1 in player_teams or t2 in player_teams
    if is_player:
        gf_w, gs1, gs2, gf_lines, gf_snaps, gf_stats = _play_bo_logged(t1, t2, db_name, 5)
        events.append(_lineup_event(t1, t2, 'Гранд-финал (BO5)',
                                    gf_lines, gf_snaps, gf_w, gs1, gs2, db_name, 5, gf_stats))
    else:
        gf_w, gs1, gs2 = _play_bo(t1, t2, db_name, 5)
    _gp(t1, t2, gs1 + gs2)
    gf_loser = t2 if gf_w == t1 else t1
    events.append(_match_event(t1, t2, gf_w, gf_loser, gs1, gs2,
                               'Гранд-финал (BO5)', is_player))
    placements[gf_w]     = 1
    placements[gf_loser] = 2

    # ── Tournament results ────────────────────────────────────────
    events.append({
        'type':            'tournament_results',
        'champion':         gf_w,
        'placements':       placements,
        'group_eliminated': group_eliminated,
        'tournament_id':    tournament_id,
        'games_played':     games_played,
    })

    # ── Minor tournament (parallel) ───────────────────────────────
    if minor_teams:
        minor_events, _ = _generate_minor(minor_teams, db_name, player_teams, _gp)
        events.extend(minor_events)

    return events, placements, group_eliminated


# ── DB helpers ────────────────────────────────────────────────────────────────

def save_tournament_results(tournament_id, placements, group_eliminated, db_name):
    prizes   = get_prizepool_worldcup_system(tournament_id, db_name)
    ratings  = get_ratingpool_worldcup_system(tournament_id, db_name)

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    group_sorted = sorted(group_eliminated, key=lambda x: x[1], reverse=True)
    final_standings = [None] * 16
    for team, place in placements.items():
        if 1 <= place <= 16:
            final_standings[place - 1] = team
    for i, (team, _) in enumerate(group_sorted):
        idx = 8 + i
        if idx < 16 and not final_standings[idx]:
            final_standings[idx] = team

    cur.execute("SELECT id, name FROM teams")
    id_map = {row[1].strip(): row[0] for row in cur.fetchall()}

    place_cols = {
        f"place{i + 1}": id_map.get(final_standings[i])
        for i in range(16)
        if final_standings[i] and id_map.get(final_standings[i])
    }
    if place_cols:
        set_clause = ", ".join(f"{c} = ?" for c in place_cols)
        cur.execute(
            f"UPDATE tournaments SET {set_clause} WHERE id = ?",
            list(place_cols.values()) + [tournament_id],
        )

    for i, team_name in enumerate(final_standings):
        if not team_name:
            continue
        tid = id_map.get(team_name)
        if not tid:
            continue
        prize      = prizes[i]  if prizes  and i < len(prizes)   else 0
        rating_pts = ratings[i] if ratings and i < len(ratings)   else 0
        if prize:
            cur.execute("UPDATE teams SET budget = budget + ? WHERE id = ?", (prize, tid))
        if rating_pts:
            cur.execute(
                "UPDATE teams SET rating = COALESCE(rating, 0) + ? WHERE id = ?",
                (rating_pts, tid),
            )

    # Cohesion +5 for all 16 participating teams
    all_participants = list(placements.keys()) + [t for t, _ in group_eliminated]
    for team_name in all_participants:
        tid = id_map.get(team_name.strip())
        if tid:
            cur.execute(
                "UPDATE teams SET cohesion = MIN(100, COALESCE(cohesion, 0) + 10) WHERE id=?",
                (tid,),
            )

    # H2H records (Feature 5)
    try:
        player_id_row = cur.execute("SELECT id FROM teams WHERE player='yes'").fetchone()
        if player_id_row:
            ptid = player_id_row[0]
            player_name = cur.execute("SELECT name FROM teams WHERE id=?", (ptid,)).fetchone()
            pname_str = player_name[0].strip() if player_name else ''
            p_place = placements.get(pname_str, 99)
            if p_place < 99:
                for opp_name, opp_place in placements.items():
                    if opp_name == pname_str:
                        continue
                    opp_row = cur.execute(
                        "SELECT id FROM teams WHERE name=?", (opp_name,)
                    ).fetchone()
                    if not opp_row:
                        continue
                    opp_id = opp_row[0]
                    cur.execute(
                        "INSERT OR IGNORE INTO h2h_records (opponent_team_id) VALUES (?)",
                        (opp_id,)
                    )
                    if p_place < opp_place:
                        cur.execute(
                            "UPDATE h2h_records SET wins=wins+1, last_tournament=? "
                            "WHERE opponent_team_id=?",
                            (str(tournament_id), opp_id)
                        )
                    elif opp_place < p_place:
                        cur.execute(
                            "UPDATE h2h_records SET losses=losses+1, last_tournament=? "
                            "WHERE opponent_team_id=?",
                            (str(tournament_id), opp_id)
                        )
    except Exception:
        pass

    # Rival tracking (Feature 3)
    try:
        player_row = cur.execute(
            "SELECT id, rival_team_id FROM teams WHERE player='yes'"
        ).fetchone()
        if player_row:
            ptid, rival_id = player_row
            if rival_id:
                rival_name_row = cur.execute("SELECT name FROM teams WHERE id=?", (rival_id,)).fetchone()
                rival_name_str = rival_name_row[0].strip() if rival_name_row else ''
                player_place = placements.get(
                    cur.execute("SELECT name FROM teams WHERE id=?", (ptid,)).fetchone()[0].strip()
                    if ptid else '', 99)
                rival_place = placements.get(rival_name_str, 99)
                if rival_place < 99 and player_place < 99:
                    if player_place < rival_place:
                        cur.execute(
                            "UPDATE teams SET rival_wins=COALESCE(rival_wins,0)+1 WHERE id=?",
                            (ptid,)
                        )
                    elif rival_place < player_place:
                        cur.execute(
                            "UPDATE teams SET rival_losses=COALESCE(rival_losses,0)+1 WHERE id=?",
                            (ptid,)
                        )
    except Exception:
        pass

    # Org reputation boost based on placement (Feature 4)
    rep_by_place = {1: 15, 2: 10, 3: 7, 4: 5, 5: 3, 6: 3, 7: 2, 8: 2}
    for i, team_name in enumerate(final_standings):
        if not team_name:
            continue
        tid = id_map.get(team_name)
        if not tid:
            continue
        place = i + 1
        rep_gain = rep_by_place.get(place, 1)
        try:
            cur.execute(
                "UPDATE teams SET org_reputation=MIN(100, COALESCE(org_reputation,20)+?) WHERE id=?",
                (rep_gain, tid),
            )
        except Exception:
            pass

    conn.commit()
    conn.close()


def increment_player_fatigue(db_name, team_name, amount=8):
    """Increase fatigue for all active players of a team after matches."""
    conn = sqlite3.connect(db_name)
    try:
        row = conn.execute(
            "SELECT carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE name=?", (team_name,)
        ).fetchone()
        if row:
            pids = [p for p in row if p]
            if pids:
                ph = ','.join('?' * len(pids))
                conn.execute(
                    f"UPDATE players SET fatigue=MIN(100, COALESCE(fatigue,0)+?) WHERE id IN ({ph})",
                    [amount] + list(pids)
                )
                conn.commit()
    except Exception:
        pass
    conn.close()


# ── Season schedule ───────────────────────────────────────────────────────────

SEASON_TOURNAMENTS = [
    ("ESL One Bangkok 2024",       "2024-11-10", "2024-11-17",  500_000,   2858),
    ("DreamLeague Season 25",      "2025-01-12", "2025-01-19", 1_000_000, 5715),
    ("ESL One Birmingham 2025",    "2025-03-09", "2025-03-16",  500_000,   2858),
    ("PGL Wallachia Season 3",     "2025-04-27", "2025-05-04", 1_000_000, 5715),
    ("The International 2025",     "2025-08-02", "2025-08-14", 1_600_000, 8572),
    ("PGL Bucharest 2025",         "2025-09-21", "2025-09-28",  500_000,   2858),
    ("ESL One Kuala Lumpur 2025",  "2025-11-02", "2025-11-09",  500_000,   2858),
    ("DreamLeague Season 26",      "2025-12-07", "2025-12-14", 1_000_000, 5715),
    ("ESL One Bangkok 2026",       "2026-01-25", "2026-02-01",  500_000,   2858),
    ("PGL Wallachia Season 4",     "2026-03-08", "2026-03-15", 1_000_000, 5715),
    ("DreamLeague Season 27",      "2026-04-26", "2026-05-03", 1_000_000, 5715),
    ("ESL One Birmingham 2026",    "2026-06-07", "2026-06-14",  500_000,   2858),
    ("The International 2026",     "2026-08-01", "2026-08-13", 1_600_000, 8572),
    ("PGL Bucharest 2026",         "2026-09-20", "2026-09-27",  500_000,   2858),
    ("ESL One Kuala Lumpur 2026",  "2026-11-01", "2026-11-08",  500_000,   2858),
    ("DreamLeague Season 28",      "2026-12-06", "2026-12-13", 1_000_000, 5715),
    ("ESL One Bangkok 2027",       "2027-01-24", "2027-01-31",  500_000,   2858),
    ("PGL Wallachia Season 5",     "2027-03-07", "2027-03-14", 1_000_000, 5715),
    ("DreamLeague Season 29",      "2027-04-25", "2027-05-02", 1_000_000, 5715),
    ("ESL One Birmingham 2027",    "2027-06-06", "2027-06-13",  500_000,   2858),
    ("The International 2027",     "2027-08-07", "2027-08-19", 1_800_000, 8572),
    ("PGL Bucharest 2027",         "2027-09-19", "2027-09-26",  500_000,   2858),
    ("ESL One Kuala Lumpur 2027",  "2027-10-31", "2027-11-07",  500_000,   2858),
    ("DreamLeague Season 30",      "2027-12-05", "2027-12-12", 1_000_000, 5715),
    ("ESL One Bangkok 2028",       "2028-01-23", "2028-01-30",  500_000,   2858),
    ("PGL Wallachia Season 6",     "2028-03-05", "2028-03-12", 1_000_000, 5715),
    ("DreamLeague Season 31",      "2028-04-23", "2028-04-30", 1_000_000, 5715),
    ("ESL One Birmingham 2028",    "2028-06-04", "2028-06-11",  500_000,   2858),
    ("The International 2028",     "2028-08-05", "2028-08-17", 2_000_000, 8572),
    ("PGL Bucharest 2028",         "2028-09-18", "2028-09-25",  500_000,   2858),
    ("ESL One Kuala Lumpur 2028",  "2028-10-30", "2028-11-06",  500_000,   2858),
    ("DreamLeague Season 32",      "2028-12-04", "2028-12-11", 1_000_000, 5715),
    ("ESL One Bangkok 2029",       "2029-01-22", "2029-01-29",  500_000,   2858),
    ("PGL Wallachia Season 7",     "2029-03-04", "2029-03-11", 1_000_000, 5715),
    ("DreamLeague Season 33",      "2029-04-22", "2029-04-29", 1_000_000, 5715),
    ("ESL One Birmingham 2029",    "2029-06-03", "2029-06-10",  500_000,   2858),
    ("The International 2029",     "2029-08-04", "2029-08-16", 2_000_000, 8572),
    ("PGL Bucharest 2029",         "2029-09-17", "2029-09-24",  500_000,   2858),
    ("ESL One Kuala Lumpur 2029",  "2029-10-29", "2029-11-05",  500_000,   2858),
    ("DreamLeague Season 34",      "2029-12-03", "2029-12-10", 1_000_000, 5715),
    ("ESL One Bangkok 2030",       "2030-01-21", "2030-01-28",  500_000,   2858),
    ("PGL Wallachia Season 8",     "2030-03-03", "2030-03-10", 1_000_000, 5715),
    ("DreamLeague Season 35",      "2030-04-21", "2030-04-28", 1_000_000, 5715),
    ("The International 2030",     "2030-08-03", "2030-08-15", 2_200_000, 8572),
]


def _regional_league_templates(year):
    """Return 4 regional DPC league events for a given year."""
    return [
        (f"DPC EEU Division I {year} S1",   f"{year}-02-10", f"{year}-02-17", 200_000, 1429),
        (f"DPC WEU Division I {year} S1",   f"{year}-02-12", f"{year}-02-19", 200_000, 1429),
        (f"DPC SEA Division I {year} S1",   f"{year}-07-08", f"{year}-07-13", 200_000, 1429),
        (f"DPC CN Division I {year} S1",    f"{year}-07-10", f"{year}-07-15", 200_000, 1429),
    ]


def ensure_season_tournaments(db_name):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("SELECT name FROM tournaments")
    existing = {row[0] for row in cur.fetchall()}
    for name, start, end, prize, rating in SEASON_TOURNAMENTS:
        if name not in existing:
            cur.execute(
                "INSERT INTO tournaments (name, start_date, end_date, prizepool, ratingpool) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, start, end, prize, rating),
            )
        else:
            cur.execute(
                "UPDATE tournaments SET ratingpool = ? WHERE name = ?",
                (rating, name),
            )
    # Add regional leagues for known years
    for year in range(2024, 2031):
        for name, start, end, prize, rating in _regional_league_templates(year):
            if name not in existing:
                cur.execute(
                    "INSERT INTO tournaments (name, start_date, end_date, prizepool, ratingpool) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (name, start, end, prize, rating),
                )
                existing.add(name)
            else:
                cur.execute(
                    "UPDATE tournaments SET ratingpool = ? WHERE name = ?",
                    (rating, name),
                )
    conn.commit()
    conn.close()


def ensure_next_year_tournaments(db_name, year):
    """Generate a standard 8-tournament year if no tournaments for that year exist."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tournaments WHERE start_date LIKE ?", (f'{year}%',))
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    sn = year - 2022   # approximate series number
    templates = [
        (f"ESL One Bangkok {year}",          f"{year}-01-21", f"{year}-02-01",   500_000,   500),
        (f"PGL Wallachia Season {sn}",       f"{year}-03-10", f"{year}-03-17", 1_000_000, 1000),
        (f"DreamLeague Season {sn*2}",       f"{year}-04-28", f"{year}-05-05", 1_000_000, 1000),
        (f"ESL One Birmingham {year}",       f"{year}-06-08", f"{year}-06-15",   500_000,   500),
        (f"The International {year}",        f"{year}-08-03", f"{year}-08-15", 2_200_000, 1500),
        (f"PGL Bucharest {year}",            f"{year}-09-20", f"{year}-09-27",   500_000,   500),
        (f"ESL One Kuala Lumpur {year}",     f"{year}-10-29", f"{year}-11-05",   500_000,   500),
        (f"DreamLeague Season {sn*2+1}",     f"{year}-12-07", f"{year}-12-14", 1_000_000, 1000),
    ]
    cur.execute("SELECT name FROM tournaments")
    existing = {r[0] for r in cur.fetchall()}
    for name, start, end, prize, rating in templates:
        if name not in existing:
            cur.execute(
                "INSERT INTO tournaments (name, start_date, end_date, prizepool, ratingpool) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, start, end, prize, rating),
            )
    for name, start, end, prize, rating in _regional_league_templates(year):
        if name not in existing:
            cur.execute(
                "INSERT INTO tournaments (name, start_date, end_date, prizepool, ratingpool) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, start, end, prize, rating),
            )
    conn.commit()
    conn.close()
