import sqlite3
import random

ROLES = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
_SKILL_MAX    = 100
_BASE_XP_PER_GAME = 0.5

_PER_SKILL_CAP = {
    'micro_skills': 'micro_cap',
    'macro_skills': 'macro_cap',
    'soft_skills':  'soft_cap',
}

_ROLE_LABELS = {
    'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Offlane',
    'partial_support': 'Support 4', 'full_support': 'Support 5',
}

# ── Regional definitions ──────────────────────────────────────────────────────

_CIS = {
    'Russia', 'Ukraine', 'Belarus', 'Kazakhstan', 'Moldova', 'Georgia',
    'Armenia', 'Azerbaijan', 'Uzbekistan', 'Kyrgyzstan', 'Tajikistan',
}
_EU = {
    'Sweden', 'Denmark', 'Norway', 'Finland', 'Germany', 'France',
    'Netherlands', 'Belgium', 'Poland', 'Czech Republic', 'Czechia',
    'Slovakia', 'Bulgaria', 'Romania', 'Austria', 'Spain', 'Italy',
    'Switzerland', 'United Kingdom', 'Estonia', 'Latvia', 'Lithuania',
    'Hungary', 'Iceland', 'Portugal', 'Greece', 'Croatia', 'Serbia',
}
_NA = {'USA', 'Canada'}
_CN = {'China'}
_SEA = {
    'Malaysia', 'Philippines', 'Indonesia', 'Thailand', 'Vietnam',
    'Singapore', 'Myanmar', 'Cambodia', 'South Korea', 'Laos',
}
_SA = {
    'Peru', 'Brazil', 'Argentina', 'Chile', 'Colombia', 'Bolivia',
    'Venezuela', 'Uruguay', 'Ecuador', 'Nicaragua', 'Paraguay',
}
# MENA → treated as EU per game design
_MENA = {
    'Jordan', 'Lebanon', 'Iraq', 'UAE', 'Saudi Arabia', 'Egypt',
    'Israel', 'Iran', 'Turkey', 'Kuwait', 'Qatar', 'Bahrain',
    'Morocco', 'Tunisia', 'Algeria', 'Pakistan',
}

# Which regions a team's dominant region is comfortable signing from
# Primary = same region, Secondary = listed others (lower preference)
_COMPAT = {
    'CIS':  ('CIS',  ('EU', 'NA')),
    'EU':   ('EU',   ('CIS', 'NA')),
    'NA':   ('NA',   ('EU', 'CIS')),
    'CN':   ('CN',   ('SEA',)),
    'SEA':  ('SEA',  ('CN',)),
    'SA':   ('SA',   ('NA',)),    # SA can occasionally sign NA players
    'OPEN': ('OPEN', ('CIS', 'EU', 'NA', 'CN', 'SEA', 'SA')),
}


def _region(country: str) -> str:
    if country in _CIS:  return 'CIS'
    if country in _CN:   return 'CN'
    if country in _SEA:  return 'SEA'
    if country in _SA:   return 'SA'
    if country in _MENA: return 'EU'   # MENA treated as EU
    if country in _EU:   return 'EU'
    if country in _NA:   return 'NA'
    return 'OPEN'


def _dominant_region(countries: list) -> str:
    """Return the dominant regional identity of a team's current roster."""
    if not countries:
        return 'OPEN'
    from collections import Counter
    counts = Counter(_region(c) for c in countries if c)
    if not counts:
        return 'OPEN'
    top_region, top_count = counts.most_common(1)[0]
    # Need at least 2 players from same region to call it dominant
    return top_region if top_count >= 2 else 'OPEN'


def _tier(micro: int, macro: int) -> int:
    """
    Skill tier as AI perceives a player's general quality.
    3 = green (pro level), 2 = yellow (semi-pro), 1 = red (amateur)
    AI doesn't see exact numbers — only rough tier.
    """
    avg = ((micro or 0) + (macro or 0)) / 2
    if avg >= 75: return 3
    if avg >= 55: return 2
    return 1


def _find_free_agent(cur, role, budget, dominant, min_tier=None, strict_region=True):
    """
    Find the best affordable free agent of the given role.

    Preference order:
      1. Same region as dominant
      2. Compatible secondary region (if strict_region=False)
      3. Any region as last resort for empty-slot filling (min_tier=None)

    Returns (player_id, nickname, wage) or None.
    """
    cur.execute("""
        SELECT id, nickname, micro_skills, macro_skills,
               COALESCE(expected_wage, 0) as wage, country
        FROM players
        WHERE team_id = 0
          AND role = ?
          AND COALESCE(expected_wage, 0) <= ?
        ORDER BY (COALESCE(micro_skills,0) + COALESCE(macro_skills,0)) DESC
    """, (role, budget))
    candidates = cur.fetchall()

    primary, secondaries = _COMPAT.get(dominant, ('OPEN', ()))

    def _pick_from(pool, min_t):
        for pid, nick, micro, macro, wage, country in pool:
            if min_t and _tier(micro or 0, macro or 0) < min_t:
                continue
            r = _region(country or '')
            if r == primary or dominant == 'OPEN':
                return pid, nick, wage
        return None

    def _pick_secondary(pool, min_t):
        for pid, nick, micro, macro, wage, country in pool:
            if min_t and _tier(micro or 0, macro or 0) < min_t:
                continue
            if _region(country or '') in secondaries:
                return pid, nick, wage
        return None

    # Try primary region first
    result = _pick_from(candidates, min_tier)
    if result:
        return result

    # Try secondary (compatible) regions
    if not strict_region:
        result = _pick_secondary(candidates, min_tier)
        if result:
            return result

    # Last resort: fill empty slot with anyone affordable (no min_tier applied)
    if min_tier is None:
        for pid, nick, micro, macro, wage, country in candidates:
            return pid, nick, wage

    return None


# ── transfer probability based on results ────────────────────────────────────

def _transfer_probs(placements, group_eliminated):
    """
    Returns {team_name: (prob, max_tier_to_replace)}
    prob      = probability of attempting a replacement this transfer window
    max_tier  = highest tier player they'll consider replacing
                (1 = only red, 2 = red+yellow, 3 = would replace anyone)
    """
    probs = {}

    if placements:
        for name, place in placements.items():
            if place <= 4:
                pass                              # satisfied — no changes
            elif place <= 6:
                probs[name] = (0.15, 1)          # small chance, only replace red
            elif place <= 8:
                probs[name] = (0.35, 2)          # decent chance, red+yellow
            else:
                probs[name] = (0.55, 2)          # unhappy, red+yellow

    if group_eliminated:
        for name, _ in group_eliminated:
            # Group exit → most frustrated
            probs[name] = (0.65, 2)

    return probs


# ── Main AI transfers function ─────────────────────────────────────────────────

def ai_transfers(db_name, placements=None, group_eliminated=None):
    """
    Region-aware, result-driven AI transfers.

    placements:       {team_name: place} from tournament (or None for monthly call)
    group_eliminated: [(team_name, pts)]  (or None)
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    transfer_probs = _transfer_probs(placements or {}, group_eliminated or [])

    c.execute(
        "SELECT id, name, COALESCE(budget,0), "
        "carry, mid, offlane, partial_support, full_support "
        "FROM teams WHERE player='no'"
    )
    ai_teams = c.fetchall()

    news = []

    for team_id, team_name, budget, *slots in ai_teams:

        # ── Gather current roster info ────────────────────────────────────────
        current = []   # [(pid, role, micro, macro, country)]
        for role, pid in zip(ROLES, slots):
            if not pid:
                continue
            c.execute(
                "SELECT micro_skills, macro_skills, country FROM players WHERE id=?",
                (pid,),
            )
            row = c.fetchone()
            if row:
                current.append((pid, role, row[0] or 0, row[1] or 0, row[2] or ''))

        dom = _dominant_region([p[4] for p in current])

        # ── Step 1: fill empty slots ──────────────────────────────────────────
        for role, pid in zip(ROLES, slots):
            if pid:
                # Verify player still exists (guards against deleted players)
                c.execute("SELECT id FROM players WHERE id=?", (pid,))
                if not c.fetchone():
                    c.execute(f"UPDATE teams SET {role}=NULL WHERE id=?", (team_id,))
                continue

            agent = _find_free_agent(c, role, budget, dom, min_tier=None, strict_region=False)
            if not agent:
                continue
            new_pid, new_nick, wage = agent
            c.execute(f"UPDATE teams SET {role}=? WHERE id=?", (new_pid, team_id))
            c.execute(
                "UPDATE players SET team_id=?, wage=? WHERE id=?",
                (team_id, wage, new_pid),
            )
            budget -= wage
            news.append(
                f"Трансфер: {team_name} подписал {new_nick} "
                f"({_ROLE_LABELS.get(role, role)})"
            )

        # ── Step 2: maybe replace underperformer after bad results ────────────
        prob_data = transfer_probs.get(team_name)
        if not prob_data:
            continue
        prob, max_tier = prob_data

        if random.random() > prob:
            continue   # team doesn't act this window

        # Find the worst player on the team
        if not current:
            continue
        worst = min(current, key=lambda p: _tier(p[2], p[3]))
        w_pid, w_role, w_micro, w_macro, w_country = worst
        w_tier = _tier(w_micro, w_macro)

        # Don't replace green players (tier 3), and respect max_tier cap
        if w_tier >= 3 or w_tier > max_tier:
            continue

        # Look for a better free agent: strictly higher tier, regional preference
        c.execute(
            "SELECT COALESCE(wage,0) FROM players WHERE id=?", (w_pid,)
        )
        cur_wage_row = c.fetchone()
        cur_wage = cur_wage_row[0] if cur_wage_row else 0

        agent = _find_free_agent(
            c, w_role,
            budget + cur_wage,
            dom,
            min_tier=w_tier + 1,
            strict_region=True,    # strict: must be compatible region
        )

        # If strict region found nothing, try secondary regions
        if not agent:
            agent = _find_free_agent(
                c, w_role,
                budget + cur_wage,
                dom,
                min_tier=w_tier + 1,
                strict_region=False,
            )

        if not agent:
            continue

        new_pid, new_nick, new_wage = agent

        # Release old player
        avg = (w_micro + w_macro) // 2
        exp_wage = max(avg * 180, int(cur_wage * 0.85))
        c.execute(
            "SELECT nickname FROM players WHERE id=?", (w_pid,)
        )
        old_nick_row = c.fetchone()
        old_nick = old_nick_row[0] if old_nick_row else '?'

        c.execute(
            "UPDATE players SET team_id=0, wage=0, expected_wage=? WHERE id=?",
            (exp_wage, w_pid),
        )
        c.execute(
            f"UPDATE teams SET {w_role}=NULL WHERE id=?", (team_id,)
        )
        # Cohesion penalty
        c.execute(
            "UPDATE teams SET cohesion=MAX(0, COALESCE(cohesion,0)-15) WHERE id=?",
            (team_id,),
        )
        # Sign new player
        c.execute(
            f"UPDATE teams SET {w_role}=? WHERE id=?", (new_pid, team_id)
        )
        c.execute(
            "UPDATE players SET team_id=?, wage=? WHERE id=?",
            (team_id, new_wage, new_pid),
        )
        budget = budget + cur_wage - new_wage

        tier_names = {1: 'слабый', 2: 'средний', 3: 'сильный'}
        news.append(
            f"Трансфер: {team_name} заменил {old_nick} "
            f"({tier_names[w_tier]}) → {new_nick} ({_ROLE_LABELS.get(w_role, w_role)})"
        )

    for msg in news:
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
            (msg, 'Трансферный рынок'),
        )

    conn.commit()
    conn.close()


# ── Training from games ───────────────────────────────────────────────────────

def apply_training_from_games(db_name, games_played, season=None, placements=None, champion_name=None):
    """Priority-based training after tournament matches. Also updates player_career_stats."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM teams WHERE player='yes'")
    row = cur.fetchone()
    player_team_id   = row[0] if row else None
    player_team_name = row[1].strip() if row else None

    # Determine season from DB if not provided
    if season is None:
        try:
            gd = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
            season = int(gd[0][:4]) if gd else 2024
        except Exception:
            season = 2024

    # Build win set: team_name → bool won (simplified: winner = champion)
    # Use placements dict {team_name: place} if provided
    winner_team = champion_name  # may be None

    for team_name, n_games in games_played.items():
        if not n_games:
            continue
        is_player_team = (team_name.strip() == player_team_name)

        cur.execute(
            "SELECT carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE name=?",
            (team_name,),
        )
        team_row = cur.fetchone()
        if not team_row:
            continue

        for pid in team_row:
            if not pid:
                continue
            cur.execute(
                "SELECT train_priority, COALESCE(train_xp, 0.0), "
                "micro_skills, macro_skills, soft_skills, "
                "COALESCE(skill_cap, 300), COALESCE(competence, 5), "
                "COALESCE(learning_rate, 5), "
                "COALESCE(micro_cap, 100), COALESCE(macro_cap, 100), COALESCE(soft_cap, 100) "
                "FROM players WHERE id=?",
                (pid,),
            )
            p = cur.fetchone()
            if not p:
                continue
            (priority, xp, micro, macro, soft,
             skill_cap, competence, learning_rate,
             micro_cap, macro_cap, soft_cap) = p
            micro = micro or 0; macro = macro or 0; soft = soft or 0

            if is_player_team:
                if not priority:
                    continue
            else:
                skills_map = {
                    'micro_skills': micro,
                    'macro_skills': macro,
                    'soft_skills':  soft,
                }
                priority = min(skills_map, key=skills_map.get)

            current = {'micro_skills': micro, 'macro_skills': macro,
                       'soft_skills': soft}[priority]
            per_cap = {'micro_skills': micro_cap,
                       'macro_skills': macro_cap,
                       'soft_skills':  soft_cap}[priority]
            total = micro + macro + soft

            if total >= skill_cap or current >= per_cap:
                continue

            lr_factor = learning_rate / 5.0
            xp_gain = (competence / 5.0) * _BASE_XP_PER_GAME * n_games * lr_factor
            new_xp = (xp or 0.0) + xp_gain

            gained = 0
            while (new_xp >= 1.0
                   and total + gained < skill_cap
                   and current + gained < per_cap):
                new_xp -= 1.0
                gained += 1

            cur.execute(
                f"UPDATE players SET {priority}={priority}+?, train_xp=? WHERE id=?",
                (gained, new_xp, pid),
            )

        # comp_exp: +1 per tournament game
        for pid in team_row:
            if pid:
                cur.execute(
                    "UPDATE players SET comp_exp=COALESCE(comp_exp,0)+? WHERE id=?",
                    (n_games, pid),
                )

        # career_stats: update games / wins
        place = (placements or {}).get(team_name, 99)
        won_match = (place == 1)  # "win" = tournament champion
        for pid in team_row:
            if pid:
                try:
                    cur.execute("""
                        INSERT INTO player_career_stats (player_id, season, games, wins, mvp_count)
                        VALUES (?, ?, ?, ?, 0)
                        ON CONFLICT(player_id, season) DO UPDATE SET
                            games = games + excluded.games,
                            wins  = wins  + excluded.wins
                    """, (pid, season, n_games, 1 if won_match else 0))
                except Exception:
                    pass

    conn.commit()
    conn.close()


def develop_free_agents(db_name):
    """Monthly: free agents slowly improve skills; expected_wage decays with time."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, COALESCE(micro_skills,0), COALESCE(macro_skills,0),
               COALESCE(soft_skills,0), COALESCE(skill_cap,300),
               COALESCE(micro_cap,100), COALESCE(macro_cap,100), COALESCE(soft_cap,100),
               COALESCE(expected_wage,5000)
        FROM players WHERE team_id=0 AND age IS NOT NULL
    """)
    for pid, mi, ma, so, cap, mc, xc, sc, exp_w in cur.fetchall():
        # Skill drift (small chance to gain one point in weakest stat)
        total = mi + ma + so
        if total < cap:
            options = [('micro_skills', mi, mc), ('macro_skills', ma, xc), ('soft_skills', so, sc)]
            random.shuffle(options)
            for col, val, per_cap in options:
                if val < per_cap and total + 1 <= cap and random.random() < 0.25:
                    cur.execute(f"UPDATE players SET {col}={col}+1 WHERE id=?", (pid,))
                    break

        # Wage expectation decay: -3% per month, floor = skill-based minimum
        skill_floor = max(2000, ((mi + ma) // 2) * 60)
        if exp_w > skill_floor:
            new_w = max(skill_floor, int(exp_w * 0.97))
            if new_w != exp_w:
                cur.execute("UPDATE players SET expected_wage=? WHERE id=?", (new_w, pid))

    conn.commit()
    conn.close()


# ── Morale helpers ────────────────────────────────────────────────────────────

def update_morale_after_tournament(db_name, placements, group_eliminated):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM teams")
    name_to_id = {row[1].strip(): row[0] for row in cur.fetchall()}

    place_map = dict(placements)
    for team_name, _ in group_eliminated:
        if team_name not in place_map:
            place_map[team_name] = 10

    for team_name, place in place_map.items():
        tid = name_to_id.get(team_name)
        if not tid:
            continue
        if place == 1:   delta = 3
        elif place <= 3: delta = 2
        elif place <= 8: delta = 1
        else:            delta = -1

        cur.execute(
            "SELECT carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE id=?",
            (tid,),
        )
        slots = cur.fetchone()
        if not slots:
            continue
        for pid in slots:
            if pid:
                cur.execute(
                    "UPDATE players "
                    "SET morale=MAX(1, MIN(10, COALESCE(morale, 5)+?)) "
                    "WHERE id=?",
                    (delta, pid),
                )

    conn.commit()
    conn.close()


def update_morale_monthly(db_name):
    conn = sqlite3.connect(db_name)
    # Underpaid players lose morale
    conn.execute("""
        UPDATE players
        SET morale = MAX(1, COALESCE(morale, 5) - 1)
        WHERE team_id != 0
          AND expected_wage IS NOT NULL
          AND expected_wage > 0
          AND COALESCE(wage, 0) < expected_wage * 0.8
    """)
    # Increment time_in_team for active roster
    conn.execute("""
        UPDATE players SET time_in_team = COALESCE(time_in_team, 0) + 1
        WHERE team_id != 0
    """)
    # Cohesion grows based on average time_in_team of the team's roster
    c = conn.cursor()
    c.execute(
        "SELECT id, carry, mid, offlane, partial_support, full_support FROM teams"
    )
    for row in c.fetchall():
        tid = row[0]
        pids = [p for p in row[1:] if p]
        if not pids:
            continue
        ph = ','.join('?' * len(pids))
        avg_time = c.execute(
            f"SELECT AVG(COALESCE(time_in_team,0)) FROM players WHERE id IN ({ph})",
            pids
        ).fetchone()[0] or 0
        # +3/month if avg tenure > 6 months, +2 if > 3, +1 otherwise; cap 100
        gain = 3 if avg_time >= 6 else (2 if avg_time >= 3 else 1)
        conn.execute(
            "UPDATE teams SET cohesion=MIN(100, COALESCE(cohesion,0)+?) WHERE id=?",
            (gain, tid)
        )
    conn.commit()
    conn.close()


def update_form_monthly(db_name):
    """Shift each player's hidden form (1-10) based on stability.
    High stability → small drift; low stability → big swings.
    Always pulls slightly toward 5-6 to mean-revert.
    """
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        "SELECT id, COALESCE(form, 5), COALESCE(stability, 5), COALESCE(morale, 5) "
        "FROM players"
    )
    updates = []
    for pid, form, stability, morale in c.fetchall():
        max_swing = max(1, (11 - stability) // 2)   # stab=10→0, stab=5→3, stab=1→5
        drift = random.randint(-max_swing, max_swing)
        # morale nudge: low morale pulls form down
        morale_pull = 1 if morale >= 7 else (-1 if morale <= 3 else 0)
        # mean-reversion toward 5
        revert = 1 if form < 5 else (-1 if form > 6 else 0)
        new_form = max(1, min(10, form + drift + morale_pull + revert))
        if new_form != form:
            updates.append((new_form, pid))
    for new_form, pid in updates:
        c.execute("UPDATE players SET form=? WHERE id=?", (new_form, pid))
    conn.commit()
    conn.close()


def update_form_after_tournament(db_name, placements, group_eliminated):
    """Adjust form based on tournament result: top finish → boost, early exit → drop."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    place_map = dict(placements)
    for team, _ in group_eliminated:
        place_map.setdefault(team, 10)

    for team_name, place in place_map.items():
        c.execute(
            "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE name=?",
            (team_name,)
        )
        row = c.fetchone()
        if not row:
            continue
        # form delta: 1st → +3, top4 → +2, top8 → +1, 9-12 → -1, 13+ → -2
        if place == 1:
            delta = 3
        elif place <= 4:
            delta = 2
        elif place <= 8:
            delta = 1
        elif place <= 12:
            delta = -1
        else:
            delta = -2
        for pid in row:
            if pid:
                c.execute(
                    "UPDATE players SET form=MAX(1,MIN(10,COALESCE(form,5)+?)) WHERE id=?",
                    (delta, pid)
                )
    conn.commit()
    conn.close()


def set_ai_train_priorities(db_name):
    """Monthly: AI teams assign train_priority based on player role and weakest stat."""
    _ROLE_PRIO = {
        'carry':           ['micro_skills', 'macro_skills', 'soft_skills'],
        'mid':             ['macro_skills', 'micro_skills', 'soft_skills'],
        'offlane':         ['macro_skills', 'soft_skills',  'micro_skills'],
        'partial_support': ['soft_skills',  'macro_skills', 'micro_skills'],
        'full_support':    ['soft_skills',  'macro_skills', 'micro_skills'],
    }
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        "SELECT id, role, COALESCE(micro_skills,0), COALESCE(macro_skills,0), "
        "COALESCE(soft_skills,0), COALESCE(micro_cap,100), COALESCE(macro_cap,100), "
        "COALESCE(soft_cap,100) "
        "FROM players WHERE team_id != 0"
    )
    for pid, role, mi, ma, so, mc, xc, sc in c.fetchall():
        prio_order = _ROLE_PRIO.get(role, ['micro_skills', 'macro_skills', 'soft_skills'])
        caps = {'micro_skills': mc, 'macro_skills': xc, 'soft_skills': sc}
        vals = {'micro_skills': mi, 'macro_skills': ma, 'soft_skills': so}
        # pick first stat in role-priority order that has room to grow
        chosen = next(
            (s for s in prio_order if vals[s] < caps[s]),
            min(prio_order, key=lambda s: vals[s])
        )
        c.execute("UPDATE players SET train_priority=? WHERE id=?", (chosen, pid))
    conn.commit()
    conn.close()


def apply_age_decline(db_name):
    """Seasonal skill decay for players 28+. Older = faster decline."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
        "SELECT id, COALESCE(age,22), "
        "COALESCE(micro_skills,0), COALESCE(macro_skills,0), COALESCE(soft_skills,0) "
        "FROM players WHERE COALESCE(age,22) >= 28"
    )
    for pid, age, micro, macro, soft in c.fetchall():
        # decay per skill: age 28→1, 30→2, 32→3, 34+→4
        rate = min(4, (age - 26) // 2)
        dm = random.randint(0, rate)
        dx = random.randint(0, rate)
        ds = random.randint(0, rate)
        c.execute(
            "UPDATE players SET "
            "micro_skills=MAX(1,micro_skills-?), "
            "macro_skills=MAX(1,macro_skills-?), "
            "soft_skills=MAX(1,soft_skills-?) "
            "WHERE id=?",
            (dm, dx, ds, pid),
        )
    conn.commit()
    conn.close()


def decay_ratings_season_end(db_name):
    conn = sqlite3.connect(db_name)
    conn.execute("UPDATE teams SET rating = ROUND(COALESCE(rating, 0) * 0.75)")
    conn.commit()
    conn.close()


def ai_poach_attempt(db_name, game_date_str):
    """AI teams try to poach player-team members with contracts expiring in ≤60 days."""
    from datetime import date, timedelta
    try:
        today = date.fromisoformat(game_date_str)
    except Exception:
        return

    deadline = str(today + timedelta(days=60))

    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, carry, mid, offlane, partial_support, full_support "
        "FROM teams WHERE player='yes'"
    )
    team = cur.fetchone()
    if not team:
        conn.close()
        return

    player_ids = [p for p in team[1:] if p]
    if not player_ids:
        conn.close()
        return

    cur.execute("SELECT id, name, COALESCE(budget,0) FROM teams WHERE player='no'")
    ai_teams = cur.fetchall()
    if not ai_teams:
        conn.close()
        return

    for pid in player_ids:
        cur.execute(
            "SELECT nickname, contract_end, COALESCE(morale,5), "
            "COALESCE(expected_wage,0), COALESCE(wage,0), role, "
            "COALESCE(poaching_team_id,0) "
            "FROM players WHERE id=?",
            (pid,),
        )
        p = cur.fetchone()
        if not p:
            continue
        nick, contract_end, morale, exp_wage, wage, role, already_poached = p

        if not contract_end or contract_end > deadline or already_poached:
            continue
        if not role:
            continue

        unhappy = morale < 6 or (exp_wage > 0 and wage < exp_wage * 0.8)
        prob = 0.55 if unhappy else 0.30
        if random.random() > prob:
            continue

        candidates = list(ai_teams)
        random.shuffle(candidates)
        for ai_tid, ai_name, ai_budget in candidates:
            cur.execute(f"SELECT {role} FROM teams WHERE id=?", (ai_tid,))
            slot = cur.fetchone()
            if slot and slot[0]:
                continue
            if ai_budget < max(exp_wage, wage, 1_000):
                continue

            cur.execute("UPDATE players SET poaching_team_id=? WHERE id=?", (ai_tid, pid))
            conn.execute(
                "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                (
                    f"{ai_name} заинтересована в {nick}. "
                    f"Контракт истекает {contract_end}. Рассмотрите продление.",
                    'Трансферный рынок',
                ),
            )
            break

    conn.commit()
    conn.close()


def ai_buy_offer(db_name):
    """Monthly: AI teams may send purchase offers for player's best players."""
    import random as _r
    conn = sqlite3.connect(db_name)
    cur  = conn.cursor()

    cur.execute("SELECT id, name FROM teams WHERE player='yes'")
    my = cur.fetchone()
    if not my:
        conn.close()
        return
    my_id, my_name = my

    cur.execute(
        "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE id=?",
        (my_id,),
    )
    slots = cur.fetchone()
    if not slots:
        conn.close()
        return
    player_ids = [p for p in slots if p]
    if not player_ids:
        conn.close()
        return

    if _r.random() > 0.30:   # 30% monthly chance any offer at all
        conn.close()
        return

    # Pick a random player that doesn't have an existing offer
    _r.shuffle(player_ids)
    for pid in player_ids:
        existing = cur.execute(
            "SELECT id FROM ai_offers WHERE player_id=?", (pid,)
        ).fetchone()
        if existing:
            continue
        p = cur.execute(
            "SELECT nickname, micro_skills, macro_skills, contract_end FROM players WHERE id=?",
            (pid,)
        ).fetchone()
        if not p:
            continue
        nick, micro, macro, cend = p
        micro = micro or 1; macro = macro or 1

        # Find an AI team that can afford
        gd = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
        gd_str = gd[0] if gd else '2024-01-01'
        from ingame_interface.transfers import _transfer_fee
        fee = _transfer_fee(micro, macro, cend or gd_str, gd_str)

        cur.execute("""
            SELECT id, name FROM teams
            WHERE player != 'yes' AND COALESCE(budget,0) >= ?
            ORDER BY RANDOM() LIMIT 1
        """, (fee,))
        buyer = cur.fetchone()
        if not buyer:
            continue
        buyer_id, buyer_name = buyer

        cur.execute(
            "INSERT OR REPLACE INTO ai_offers (player_id, team_id, fee, created) VALUES (?,?,?,?)",
            (pid, buyer_id, fee, gd_str),
        )
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
            (
                f"{buyer_name} предлагает ${fee:,} за {nick}. "
                f"Примите или отклоните в разделе Трансферы.",
                gd_str, 'Трансферный рынок',
            ),
        )
        break

    conn.commit()
    conn.close()


def ai_team_trades(db_name):
    """Monthly: AI teams occasionally swap players directly (no FA pool detour)."""
    import random as _r
    conn = sqlite3.connect(db_name)
    cur  = conn.cursor()

    # Find AI teams with full roster that have upgrade opportunities
    cur.execute("""
        SELECT t.id, t.name, t.carry, t.mid, t.offlane, t.partial_support, t.full_support,
               COALESCE(t.budget,0)
        FROM teams t
        WHERE t.player!='yes'
          AND t.carry IS NOT NULL AND t.mid IS NOT NULL AND t.offlane IS NOT NULL
        ORDER BY RANDOM() LIMIT 6
    """)
    sellers = cur.fetchall()

    roles = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']

    for stid, sname, *sids, sbudget in sellers:
        if _r.random() > 0.15:   # 15% chance per team per month
            continue
        # Pick a random player from seller
        pids = [p for p in sids if p]
        if not pids:
            continue
        pid = _r.choice(pids)
        role_col = roles[[i for i, p in enumerate(sids) if p == pid][0]]

        p = cur.execute(
            "SELECT nickname, micro_skills, macro_skills, COALESCE(expected_wage,5000) "
            "FROM players WHERE id=?", (pid,)
        ).fetchone()
        if not p:
            continue
        nick, micro, macro, exp_w = p
        skill = (micro or 0) + (macro or 0)

        # Find a buyer AI team that has empty slot and can pay
        cur.execute(f"""
            SELECT id, name, COALESCE(budget,0) FROM teams
            WHERE player!='yes' AND id!=?
              AND {role_col} IS NULL
              AND COALESCE(budget,0) >= ?
            ORDER BY RANDOM() LIMIT 1
        """, (stid, exp_w))
        buyer = cur.fetchone()
        if not buyer:
            continue
        btid, bname, bbudget = buyer

        # Check buyer has upgrade
        buyer_pid = cur.execute(
            f"SELECT {role_col} FROM teams WHERE id=?", (btid,)
        ).fetchone()
        if buyer_pid and buyer_pid[0]:
            continue   # slot taken (shouldn't happen but guard)

        fee = skill * 300
        cur.execute(f"UPDATE teams SET {role_col}=NULL WHERE id=?", (stid,))
        cur.execute(f"UPDATE teams SET {role_col}=? WHERE id=?", (pid, btid))
        cur.execute("UPDATE players SET team_id=? WHERE id=?", (btid, pid))
        cur.execute("UPDATE teams SET budget=budget+? WHERE id=?", (fee, stid))
        cur.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (fee, btid))
        break  # one trade per month

    conn.commit()
    conn.close()
