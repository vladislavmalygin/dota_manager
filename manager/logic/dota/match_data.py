import sqlite3
import random
from datetime import date


def get_match_data(team1, team2, db_name, hero_picks=None):
    """hero_picks = {'team1': {role_key: (name,mi_m,ma_m,so_m,tag)}, 'team2': {...}}"""
    try:
        from logic.meta import get_active_patch, get_active_hero_mods
        _meta_patch  = get_active_patch(db_name)
        _hero_mods   = get_active_hero_mods(db_name)  # {hero_name: multiplier}
    except Exception:
        _meta_patch = None
        _hero_mods  = {}

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        _gd = cursor.execute("SELECT date FROM save WHERE id=1").fetchone()
        _game_date = date.fromisoformat(_gd[0]) if _gd else date.today()
    except Exception:
        _game_date = date.today()

    cursor.execute(
        "SELECT carry, mid, offlane, partial_support, full_support, "
        "COALESCE(cohesion, 0), COALESCE(tactic, 'balanced'), "
        "COALESCE(strat_early,'safe_farm'), COALESCE(strat_mid,'map_control'), "
        "COALESCE(strat_late,'teamfight') FROM teams WHERE name=?",
        (team1,),
    )
    team1_data = cursor.fetchone()
    if not team1_data:
        conn.close()
        return None

    cursor.execute(
        "SELECT carry, mid, offlane, partial_support, full_support, "
        "COALESCE(cohesion, 0), COALESCE(tactic, 'balanced'), "
        "COALESCE(strat_early,'safe_farm'), COALESCE(strat_mid,'map_control'), "
        "COALESCE(strat_late,'teamfight') FROM teams WHERE name=?",
        (team2,),
    )
    team2_data = cursor.fetchone()
    if not team2_data:
        conn.close()
        return None

    cohesion1 = team1_data[5] // 10
    cohesion2 = team2_data[5] // 10
    tactic1   = team1_data[6]
    tactic2   = team2_data[6]

    # tactic → which skill gets +10%
    _TACTIC_SKILL = {
        'aggressive': 'micro_skills',
        'farming':    'macro_skills',
        'teamplay':   'soft_skills',
    }

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

        tactic_key = tactic1 if team_key == 'team1' else tactic2
        boosted_skill = _TACTIC_SKILL.get(tactic_key)

        if player_id:
            cursor.execute(
                "SELECT micro_skills, macro_skills, soft_skills, COALESCE(morale, 5), "
                "COALESCE(nickname, ''), COALESCE(stability, 5), COALESCE(form, 5), "
                "injured_until, COALESCE(fatigue, 0), "
                "COALESCE(role,''), COALESCE(secondary_role,''), "
                "COALESCE(secondary_comp, 5) "
                "FROM players WHERE id=?",
                (player_id,),
            )
            row = cursor.fetchone()
        else:
            row = None

        if row:
            (micro, macro, soft, morale, nick, stability, form,
             injured_until, fatigue, primary_role, sec_role, sec_comp) = row
            # Injured player plays at 40% effectiveness
            if injured_until:
                try:
                    if date.fromisoformat(injured_until) >= _game_date:
                        micro = max(1, int((micro or 1) * 0.40))
                        macro = max(1, int((macro or 1) * 0.40))
                        soft  = max(1, int((soft  or 1) * 0.40))
                        nick  = f'[отпуск]{nick}'
                except Exception:
                    pass
            # Secondary / out-of-role penalty before other modifiers
            slot_role = role.replace(f'{team_key}_', '')  # e.g. 'carry', 'mid'
            if primary_role and slot_role != primary_role:
                if slot_role == sec_role and sec_role:
                    # Playing secondary role: comp=1→×0.80, comp=5→×1.00, comp=10→×1.25
                    comp_mult = 0.80 + 0.04 * sec_comp
                    micro = max(1, int((micro or 1) * comp_mult))
                    macro = max(1, int((macro or 1) * comp_mult))
                    soft  = max(1, int((soft  or 1) * comp_mult))
                else:
                    # Completely out of role: −35%
                    micro = max(1, int((micro or 1) * 0.65))
                    macro = max(1, int((macro or 1) * 0.65))
                    soft  = max(1, int((soft  or 1) * 0.65))
            bonus = (morale - 5) * 2 + cohesion_b
            micro = max(1, (micro or 1) + bonus)
            macro = max(1, (macro or 1) + bonus)
            soft  = max(1, (soft  or 1) + bonus)
            if boosted_skill == 'micro_skills': micro = int(micro * 1.10)
            elif boosted_skill == 'macro_skills': macro = int(macro * 1.10)
            elif boosted_skill == 'soft_skills':  soft  = int(soft  * 1.10)
            # Persistent form multiplier: form=1→×0.68, form=5→×1.0, form=10→×1.32
            form_mult = max(0.68, min(1.32, 1.0 + (form - 5) * 0.064))
            micro = max(1, int(micro * form_mult))
            macro = max(1, int(macro * form_mult))
            soft  = max(1, int(soft  * form_mult))
            # Small per-game noise from stability (reduced from old ±27 max)
            max_var = max(0, 10 - stability)
            if max_var > 0:
                micro = max(1, micro + random.randint(-max_var, max_var))
                macro = max(1, macro + random.randint(-max_var, max_var))
                soft  = max(1, soft  + random.randint(-max_var, max_var))
            # Apply hero bonuses if picks provided
            if hero_picks:
                role_short = role.replace(f'{team_key}_', '')
                hero = (hero_picks.get(team_key) or {}).get(role_short)
                if hero:
                    _, mi_m, ma_m, so_m, _ = hero
                    micro = max(1, int(micro * mi_m))
                    macro = max(1, int(macro * ma_m))
                    soft  = max(1, int(soft  * so_m))
            # Meta patch hero mods: specific heroes buffed/nerfed this patch
            if _hero_mods and hero_picks:
                role_short = role.replace(f'{team_key}_', '')
                _picked_hero = (hero_picks.get(team_key) or {}).get(role_short)
                if _picked_hero:
                    _hero_name = _picked_hero[0] if isinstance(_picked_hero, tuple) else _picked_hero
                    _mod = _hero_mods.get(_hero_name, 1.0)
                    if _mod != 1.0:
                        micro = max(1, int(micro * _mod))
                        macro = max(1, int(macro * _mod))
                        soft  = max(1, int(soft  * _mod))
            skills[team_key][role] = {
                'micro_skills': micro,
                'macro_skills': macro,
                'soft_skills':  soft,
                'nickname':     nick or role,
            }
        else:
            skills[team_key][role] = {
                'micro_skills': 1,
                'macro_skills': 1,
                'soft_skills':  1,
            }

    skills['strat_t1'] = {
        'early': team1_data[7], 'mid': team1_data[8], 'late': team1_data[9],
    }
    skills['strat_t2'] = {
        'early': team2_data[7], 'mid': team2_data[8], 'late': team2_data[9],
    }

    # Chemistry multiplier
    try:
        from logic.chemistry import chemistry_score, chemistry_mult
        t1id = cursor.execute("SELECT id FROM teams WHERE name=?", (team1,)).fetchone()
        t2id = cursor.execute("SELECT id FROM teams WHERE name=?", (team2,)).fetchone()
        if t1id:
            m1 = chemistry_mult(chemistry_score(db_name, t1id[0]))
            for role_key in skills['team1']:
                for sk in ('micro_skills', 'macro_skills', 'soft_skills'):
                    if sk in skills['team1'][role_key]:
                        skills['team1'][role_key][sk] = max(1, int(skills['team1'][role_key][sk] * m1))
        if t2id:
            m2 = chemistry_mult(chemistry_score(db_name, t2id[0]))
            for role_key in skills['team2']:
                for sk in ('micro_skills', 'macro_skills', 'soft_skills'):
                    if sk in skills['team2'][role_key]:
                        skills['team2'][role_key][sk] = max(1, int(skills['team2'][role_key][sk] * m2))
    except Exception:
        pass

    conn.close()

    # Tactician skill: +5% per level to player team skills only
    try:
        from logic.manager_skills import get_skill_level as _gsl
        tac_lvl = _gsl(db_name, 'tactician')
        if tac_lvl > 0:
            import sqlite3 as _sq2
            _pt = _sq2.connect(db_name).execute("SELECT name FROM teams WHERE player='yes'").fetchone()
            if _pt:
                player_team_name = _pt[0].strip()
                tac_mult = 1.0 + tac_lvl * 0.05
                team_key = None
                if team1.strip() == player_team_name:
                    team_key = 'team1'
                elif team2.strip() == player_team_name:
                    team_key = 'team2'
                if team_key:
                    for rk in skills[team_key]:
                        for sk in ('micro_skills', 'macro_skills', 'soft_skills'):
                            if sk in skills[team_key][rk]:
                                skills[team_key][rk][sk] = max(1, int(skills[team_key][rk][sk] * tac_mult))
    except Exception:
        pass

    return skills


def get_teams_with_player_yes(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM teams WHERE player='yes'")
    teams = cursor.fetchall()
    conn.close()
    return [team[0].strip() for team in teams]
