import sqlite3


def get_match_data(team1, team2, db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT carry, mid, offlane, partial_support, full_support, "
        "COALESCE(cohesion, 0) FROM teams WHERE name=?",
        (team1,),
    )
    team1_data = cursor.fetchone()
    if not team1_data:
        conn.close()
        return None

    cursor.execute(
        "SELECT carry, mid, offlane, partial_support, full_support, "
        "COALESCE(cohesion, 0) FROM teams WHERE name=?",
        (team2,),
    )
    team2_data = cursor.fetchone()
    if not team2_data:
        conn.close()
        return None

    cohesion1 = team1_data[5] // 10   # 0–10 integer bonus
    cohesion2 = team2_data[5] // 10

    player_ids = {
        'team1_carry':           team1_data[0],
        'team1_mid':             team1_data[1],
        'team1_offlane':         team1_data[2],
        'team1_partial_support': team1_data[3],
        'team1_full_support':    team1_data[4],
        'team2_carry':           team2_data[0],
        'team2_mid':             team2_data[1],
        'team2_offlane':         team2_data[2],
        'team2_partial_support': team2_data[3],
        'team2_full_support':    team2_data[4],
    }

    skills = {'team1': {}, 'team2': {}}

    for role, player_id in player_ids.items():
        team_key = 'team1' if role.startswith('team1') else 'team2'
        cohesion_b = cohesion1 if team_key == 'team1' else cohesion2

        if player_id:
            cursor.execute(
                "SELECT micro_skills, macro_skills, soft_skills, COALESCE(morale, 5) "
                "FROM players WHERE id=?",
                (player_id,),
            )
            row = cursor.fetchone()
        else:
            row = None

        if row:
            micro, macro, soft, morale = row
            bonus = (morale - 5) * 2 + cohesion_b
            skills[team_key][role] = {
                'micro_skills': max(1, (micro or 1) + bonus),
                'macro_skills': max(1, (macro or 1) + bonus),
                'soft_skills':  max(1, (soft  or 1) + bonus),
            }
        else:
            skills[team_key][role] = {
                'micro_skills': 1,
                'macro_skills': 1,
                'soft_skills':  1,
            }

    conn.close()
    return skills


def get_teams_with_player_yes(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM teams WHERE player='yes'")
    teams = cursor.fetchall()
    conn.close()
    return [team[0].strip() for team in teams]
