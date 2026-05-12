"""Achievement system: unlock conditions + bonus queries."""
import sqlite3


def get_flags(db_name):
    """Return set of unlocked achievement_key strings for player team."""
    try:
        conn = sqlite3.connect(db_name)
        row = conn.execute(
            "SELECT COALESCE(achievement_flags,'') FROM teams WHERE player='yes'"
        ).fetchone()
        conn.close()
        if row and row[0]:
            return set(row[0].split(','))
    except Exception:
        pass
    return set()


def _unlock(db_name, key, game_date_str):
    """Unlock an achievement if not already unlocked. Returns (name, bonus_desc) or None."""
    conn = sqlite3.connect(db_name)
    try:
        row = conn.execute(
            "SELECT name, bonus_desc, unlocked_date FROM achievements WHERE achievement_key=?",
            (key,)
        ).fetchone()
        if not row or row[2]:   # already unlocked
            conn.close()
            return None
        name, bonus_desc = row[0], row[1]
        conn.execute(
            "UPDATE achievements SET unlocked_date=? WHERE achievement_key=?",
            (game_date_str, key)
        )
        # Append key to team flags
        flags_row = conn.execute(
            "SELECT COALESCE(achievement_flags,'') FROM teams WHERE player='yes'"
        ).fetchone()
        existing = flags_row[0] if flags_row else ''
        flags = set(existing.split(',')) if existing else set()
        flags.discard('')
        flags.add(key)
        conn.execute(
            "UPDATE teams SET achievement_flags=? WHERE player='yes'",
            (','.join(sorted(flags)),)
        )
        conn.commit()
        conn.close()
        return name, bonus_desc
    except Exception:
        conn.close()
        return None


def check_achievements(db_name, game_date_str, context=None):
    """
    Check all conditions and unlock eligible achievements.
    context: dict with optional hints like 'tournament_name', 'place', 'youth_count', 'fa_signed'
    Returns list of (name, bonus_desc) for newly unlocked achievements.
    """
    context = context or {}
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    unlocked = []

    try:
        # -- Basic data --
        player_row = c.execute(
            "SELECT id, COALESCE(rating,0), COALESCE(achievement_flags,''), "
            "COALESCE(rival_wins,0), carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE player='yes'"
        ).fetchone()
        if not player_row:
            conn.close()
            return []

        team_id = player_row[0]
        rating  = player_row[1]
        flags   = set(player_row[2].split(',')) if player_row[2] else set()
        rival_wins = player_row[3]
        slot_ids = [p for p in player_row[4:9] if p]

        all_teams_ranked = c.execute(
            "SELECT id FROM teams ORDER BY COALESCE(rating,0) DESC LIMIT 1"
        ).fetchone()
        is_number_one = all_teams_ranked and all_teams_ranked[0] == team_id

        # Count tournaments player team participated in
        tournament_count = c.execute(
            "SELECT COUNT(*) FROM tournaments WHERE "
            "(place1=? OR place2=? OR place3=? OR place4=? OR "
            " place5=? OR place6=? OR place7=? OR place8=? OR "
            " place9=? OR place10=? OR place11=? OR place12=? OR "
            " place13=? OR place14=? OR place15=? OR place16=?)",
            [team_id] * 16
        ).fetchone()[0]

        # Count tournament wins
        win_count = c.execute(
            "SELECT COUNT(*) FROM tournaments WHERE place1=?", (team_id,)
        ).fetchone()[0]

        # Count TI wins
        ti_wins = c.execute(
            "SELECT COUNT(*) FROM tournaments "
            "WHERE place1=? AND name LIKE '%International%'",
            (team_id,)
        ).fetchone()[0]

        # Count distinct Major wins
        major_wins = c.execute(
            "SELECT COUNT(DISTINCT name) FROM tournaments WHERE place1=?",
            (team_id,)
        ).fetchone()[0]

        # Count FA signings (approx: players who joined with time_in_team <= 1 and no youth)
        fa_signed = context.get('fa_signed_total', 0)

        # Iron squad: all players time_in_team >= 12
        iron = False
        if slot_ids:
            ph = ','.join('?' * len(slot_ids))
            min_time = c.execute(
                f"SELECT MIN(COALESCE(time_in_team,0)) FROM players WHERE id IN ({ph})",
                slot_ids
            ).fetchone()[0] or 0
            iron = (min_time >= 12)

        # Ace groups: count clean group stages (tracked in context or separate check)
        clean_groups = context.get('clean_group_stages', 0)

    except Exception:
        conn.close()
        return []
    finally:
        conn.close()

    def _try(key):
        r = _unlock(db_name, key, game_date_str)
        if r:
            unlocked.append(r)

    if tournament_count >= 1:
        _try('first_tournament')
    if win_count >= 1:
        _try('first_win')
    if is_number_one:
        _try('world_number_one')
    if rival_wins >= 10:
        _try('rival_dominator')
    if iron and len(slot_ids) >= 5:
        _try('iron_squad')
    if context.get('youth_win'):
        _try('youth_movement')
    if ti_wins >= 1:
        _try('the_international')
    if clean_groups >= 3:
        _try('ace_groups')
    if major_wins >= 3:
        _try('dynasty')
    if fa_signed >= 10:
        _try('headhunter')

    return unlocked


def apply_monthly_bonuses(db_name, base_streaming_income):
    """Apply achievement bonuses to monthly streaming income. Returns modified value."""
    flags = get_flags(db_name)
    income = base_streaming_income
    if 'first_win' in flags:
        income = int(income * 1.10)
    if 'dynasty' in flags:
        income += 15_000
    return income


def get_wage_discount(db_name):
    """Return wage discount multiplier from achievements (< 1.0 = cheaper)."""
    flags = get_flags(db_name)
    mult = 1.0
    if 'rival_dominator' in flags:
        mult *= 0.95
    if 'headhunter' in flags:
        mult *= 0.97
    return mult


def get_morale_bonus(db_name):
    """Extra morale at tournament start from achievements."""
    flags = get_flags(db_name)
    return 3 if 'ace_groups' in flags else 0


def get_rep_monthly_bonus(db_name):
    """Monthly org_reputation bonus from world_number_one achievement."""
    flags = get_flags(db_name)
    return 5 if 'world_number_one' in flags else 0
