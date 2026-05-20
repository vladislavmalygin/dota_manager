"""Meta patch system — which heroes are OP / weak this patch."""
import json
import random
import sqlite3

from logic.heroes import HEROES, ROLE_ORDER

# Flat list of all hero names for random buffing
_ALL_HEROES = [(role, h[0]) for role in ROLE_ORDER for h in HEROES[role]]


def _hero_names_flat():
    return [h[0] for role in ROLE_ORDER for h in HEROES[role]]


_DDL_ALTER = [
    "ALTER TABLE meta_patches ADD COLUMN buffed_heroes TEXT DEFAULT '[]'",
    "ALTER TABLE meta_patches ADD COLUMN nerfed_heroes TEXT DEFAULT '[]'",
    "ALTER TABLE meta_patches ADD COLUMN hero_buff_pct INTEGER DEFAULT 15",
    "ALTER TABLE meta_patches ADD COLUMN hero_nerf_pct INTEGER DEFAULT 10",
    # Keep favored_role for backwards compat UI display
]


def _ensure_hero_columns(conn):
    for ddl in _DDL_ALTER:
        try:
            conn.execute(ddl)
        except Exception:
            pass


def get_active_patch(db_name):
    """Return (patch_name, favored_role, bonus_pct) or None — backwards compat."""
    try:
        conn = sqlite3.connect(db_name)
        _ensure_hero_columns(conn)
        row = conn.execute(
            "SELECT patch_name, favored_role, bonus_pct FROM meta_patches "
            "WHERE active=1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row
    except Exception:
        return None


def get_active_hero_mods(db_name):
    """Return dict: hero_name → multiplier (>1 = buff, <1 = nerf)."""
    try:
        conn = sqlite3.connect(db_name)
        _ensure_hero_columns(conn)
        row = conn.execute(
            "SELECT buffed_heroes, nerfed_heroes, hero_buff_pct, hero_nerf_pct "
            "FROM meta_patches WHERE active=1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if not row:
            return {}
        buffed_json, nerfed_json, buff_pct, nerf_pct = row
        mods = {}
        try:
            for h in json.loads(buffed_json or '[]'):
                mods[h] = 1.0 + (buff_pct or 15) / 100.0
        except Exception:
            pass
        try:
            for h in json.loads(nerfed_json or '[]'):
                mods[h] = 1.0 - (nerf_pct or 10) / 100.0
        except Exception:
            pass
        return mods
    except Exception:
        return {}


def get_patch_hero_lists(db_name):
    """Return (buffed_heroes, nerfed_heroes, patch_name) for current patch."""
    try:
        conn = sqlite3.connect(db_name)
        _ensure_hero_columns(conn)
        row = conn.execute(
            "SELECT patch_name, buffed_heroes, nerfed_heroes, hero_buff_pct, hero_nerf_pct "
            "FROM meta_patches WHERE active=1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if not row:
            return [], [], '?'
        patch, buf_j, nerf_j, buf_pct, nerf_pct = row
        buffed = json.loads(buf_j or '[]')
        nerfed = json.loads(nerf_j or '[]')
        return buffed, nerfed, patch
    except Exception:
        return [], [], '?'


def rotate_patch(db_name, game_date_str):
    """Generate next patch: buff 3-4 heroes, nerf 2-3. Returns (patch_name, favored_role)."""
    try:
        conn = sqlite3.connect(db_name)
        _ensure_hero_columns(conn)

        last = conn.execute(
            "SELECT patch_name, favored_role, buffed_heroes, nerfed_heroes "
            "FROM meta_patches ORDER BY id DESC LIMIT 1"
        ).fetchone()

        # Increment patch name
        if last:
            try:
                name = last[0]
                parts = name.split('.')
                major = int(parts[0])
                rest  = parts[1] if len(parts) > 1 else '36'
                digits = ''.join(c for c in rest if c.isdigit())
                suffix = ''.join(c for c in rest if not c.isdigit())
                minor  = int(digits) if digits else 36
                if suffix == '':
                    new_name = f'{major}.{minor}b'
                elif suffix == 'b':
                    new_name = f'{major}.{minor}c'
                elif suffix == 'c':
                    new_name = f'{major}.{minor}d'
                else:
                    new_name = f'{major}.{minor + 1}'
            except Exception:
                new_name = '7.37'
            last_buffed = json.loads(last[2] or '[]') if last[2] else []
            last_nerfed = json.loads(last[3] or '[]') if last[3] else []
        else:
            new_name  = '7.36'
            last_buffed = []
            last_nerfed = []

        all_heroes = _hero_names_flat()

        # Avoid buffing same heroes twice in a row; some nerfed last time get buffed now
        avoid_buff  = set(last_buffed)
        prefer_buff = set(last_nerfed)  # previously nerfed heroes get a second chance

        # 3-4 heroes buffed this patch
        buff_count = random.randint(3, 4)
        buff_pool  = [h for h in all_heroes if h not in avoid_buff]
        # Prioritise previously-nerfed heroes
        priority = [h for h in buff_pool if h in prefer_buff]
        rest     = [h for h in buff_pool if h not in prefer_buff]
        random.shuffle(priority); random.shuffle(rest)
        buffed = (priority + rest)[:buff_count]

        # 2-3 heroes nerfed (avoid just-buffed)
        nerf_count = random.randint(2, 3)
        nerf_pool  = [h for h in all_heroes if h not in buffed]
        nerfed     = random.sample(nerf_pool, min(nerf_count, len(nerf_pool)))

        buff_pct = random.choice([12, 15, 18, 20])
        nerf_pct = random.choice([8, 10, 12])

        # favored_role: role with most buffed heroes
        from collections import Counter
        role_of = {}
        for role in ROLE_ORDER:
            for h in HEROES[role]:
                role_of[h[0]] = role
        role_counts = Counter(role_of.get(h) for h in buffed if role_of.get(h))
        new_role = role_counts.most_common(1)[0][0] if role_counts else random.choice(ROLE_ORDER)
        year = int(game_date_str[:4]) if game_date_str else 2024

        conn.execute("UPDATE meta_patches SET active=0")
        conn.execute(
            "INSERT INTO meta_patches "
            "(season, patch_name, favored_role, bonus_pct, start_date, active, "
            " buffed_heroes, nerfed_heroes, hero_buff_pct, hero_nerf_pct) "
            "VALUES (?,?,?,?,?,1,?,?,?,?)",
            (year, new_name, new_role, buff_pct, game_date_str,
             json.dumps(buffed), json.dumps(nerfed), buff_pct, nerf_pct)
        )
        conn.commit()
        conn.close()

        try:
            from logic.heroes import update_signature_heroes_for_patch
            update_signature_heroes_for_patch(db_name, new_role)
        except Exception:
            pass

        return new_name, new_role
    except Exception:
        return '7.36', 'carry'


def patch_description(db_name):
    """Human-readable patch description for UI."""
    try:
        buffed, nerfed, patch = get_patch_hero_lists(db_name)
        if not patch or patch == '?':
            return 'Патч: нет данных'
        buf_str  = ', '.join(buffed[:3]) if buffed else '—'
        nerf_str = ', '.join(nerfed[:2]) if nerfed else '—'
        return f'Патч {patch}: [BUFF] {buf_str}  [NERF] {nerf_str}'
    except Exception:
        return 'Патч: нет данных'
