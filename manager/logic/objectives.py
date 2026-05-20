"""Tournament mini-objectives system."""
import sqlite3
import random

_DDL = """
CREATE TABLE IF NOT EXISTS tournament_objectives (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id   INTEGER NOT NULL,
    obj_type        TEXT NOT NULL,
    target          INTEGER DEFAULT 0,
    description     TEXT,
    reward_budget   INTEGER DEFAULT 0,
    reward_rep      INTEGER DEFAULT 0,
    completed       INTEGER DEFAULT 0,
    failed          INTEGER DEFAULT 0
);
"""

_OBJECTIVES = [
    # (type, target, description, reward_budget, reward_rep)
    ('top_place', 4,  'Занять топ-4',                 50_000,  5),
    ('top_place', 8,  'Войти в топ-8',                 30_000,  3),
    ('top_place', 1,  'Выиграть турнир',              150_000, 15),
    ('win_match',  1, 'Выиграть хотя бы 1 матч',       20_000,  2),
    ('win_match',  3, 'Выиграть 3+ матча',              40_000,  4),
    ('no_group_loss', 0, 'Не проиграть ни одного BO2 в группе', 35_000, 4),
    ('survive_groups', 0, 'Пройти групповую стадию',   25_000,  3),
]


def ensure_table(db_name):
    conn = sqlite3.connect(db_name)
    conn.execute(_DDL)
    conn.commit()
    conn.close()


def generate_objective(db_name, tournament_id):
    """Pick a random objective for this tournament. Returns objective dict."""
    ensure_table(db_name)
    conn = sqlite3.connect(db_name)
    # Don't duplicate
    existing = conn.execute(
        "SELECT id FROM tournament_objectives WHERE tournament_id=?",
        (tournament_id,)
    ).fetchone()
    if existing:
        conn.close()
        return None

    obj_type, target, desc, budget, rep = random.choice(_OBJECTIVES)
    conn.execute(
        "INSERT INTO tournament_objectives "
        "(tournament_id, obj_type, target, description, reward_budget, reward_rep) "
        "VALUES (?,?,?,?,?,?)",
        (tournament_id, obj_type, target, desc, budget, rep),
    )
    conn.commit()
    conn.close()
    return {'type': obj_type, 'target': target, 'description': desc,
            'reward_budget': budget, 'reward_rep': rep}


def get_active_objective(db_name, tournament_id):
    ensure_table(db_name)
    conn = sqlite3.connect(db_name)
    row = conn.execute(
        "SELECT id, obj_type, target, description, reward_budget, reward_rep, completed, failed "
        "FROM tournament_objectives WHERE tournament_id=? LIMIT 1",
        (tournament_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0], 'type': row[1], 'target': row[2],
        'description': row[3], 'reward_budget': row[4],
        'reward_rep': row[5], 'completed': row[6], 'failed': row[7],
    }


def resolve_objective(db_name, tournament_id, placements, group_elim, player_team_name):
    """Check if objective was met and award rewards."""
    ensure_table(db_name)
    obj = get_active_objective(db_name, tournament_id)
    if not obj or obj['completed'] or obj['failed']:
        return None

    place = placements.get(player_team_name, 99)
    if place == 99:
        for i, (t, _) in enumerate(sorted(group_elim, key=lambda x: x[1], reverse=True)):
            if t == player_team_name:
                place = 9 + i
                break

    otype = obj['type']
    target = obj['target']
    met = False

    if otype == 'top_place':
        met = (place <= target)
    elif otype == 'win_match':
        # Count bracket wins: each non-group stage match where player won
        # Approximate: if place <= 8 they won at least some bracket matches
        wins_approx = max(0, 16 - place)
        met = wins_approx >= target
    elif otype == 'no_group_loss':
        # Check group stage - no draws or losses (only 2-0 wins)
        # We approximate: if player finished top-2 in their group
        met = (place <= 8)
    elif otype == 'survive_groups':
        met = (place <= 8)

    conn = sqlite3.connect(db_name)
    if met:
        conn.execute(
            "UPDATE tournament_objectives SET completed=1 WHERE id=?", (obj['id'],)
        )
        if obj['reward_budget']:
            conn.execute(
                "UPDATE teams SET budget=budget+? WHERE player='yes'",
                (obj['reward_budget'],)
            )
        if obj['reward_rep']:
            conn.execute(
                "UPDATE characters SET reputation=COALESCE(reputation,0)+?",
                (obj['reward_rep'],)
            )
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
            (f'Цель турнира выполнена: «{obj["description"]}»! '
             f'+${obj["reward_budget"]:,} +{obj["reward_rep"]} репутации.',
             'now', 'Турнир'),
        )
        result = 'completed'
    else:
        conn.execute(
            "UPDATE tournament_objectives SET failed=1 WHERE id=?", (obj['id'],)
        )
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
            (f'Цель турнира провалена: «{obj["description"]}».',
             'now', 'Турнир'),
        )
        result = 'failed'

    conn.commit()
    conn.close()
    return result
