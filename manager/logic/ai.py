import sqlite3
import random

ROLES = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
_SKILL_MAX = 100
_BASE_XP_PER_GAME = 0.3

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
            "UPDATE teams SET cohesion=MAX(0, COALESCE(cohesion,0)-30) WHERE id=?",
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

def apply_training_from_games(db_name, games_played):
    """Priority-based training after tournament matches."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute("SELECT name FROM teams WHERE player='yes'")
    row = cur.fetchone()
    player_team_name = row[0].strip() if row else None

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
                "COALESCE(skill_cap, 300), COALESCE(competence, 5) "
                "FROM players WHERE id=?",
                (pid,),
            )
            p = cur.fetchone()
            if not p:
                continue
            priority, xp, micro, macro, soft, skill_cap, competence = p
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
            total = micro + macro + soft

            if total >= skill_cap or current >= _SKILL_MAX:
                continue

            xp_gain = (competence / 5.0) * _BASE_XP_PER_GAME * n_games
            new_xp = (xp or 0.0) + xp_gain

            gained = 0
            while (new_xp >= 1.0
                   and total + gained < skill_cap
                   and current + gained < _SKILL_MAX):
                new_xp -= 1.0
                gained += 1

            cur.execute(
                f"UPDATE players SET {priority}={priority}+?, train_xp=? WHERE id=?",
                (gained, new_xp, pid),
            )

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
    conn.execute("""
        UPDATE players
        SET morale = MAX(1, COALESCE(morale, 5) - 1)
        WHERE team_id != 0
          AND expected_wage IS NOT NULL
          AND expected_wage > 0
          AND COALESCE(wage, 0) < expected_wage * 0.8
    """)
    conn.commit()
    conn.close()


def decay_ratings_season_end(db_name):
    conn = sqlite3.connect(db_name)
    conn.execute("UPDATE teams SET rating = ROUND(COALESCE(rating, 0) * 0.3)")
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
