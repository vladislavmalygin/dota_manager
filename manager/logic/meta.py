"""Meta patch system — which role is OP this patch."""
import sqlite3
import random

_ROLES = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']

_ROLE_RU = {
    'carry':           'Carry',
    'mid':             'Mid',
    'offlane':         'Offlane',
    'partial_support': 'Support 4',
    'full_support':    'Support 5',
}


def get_active_patch(db_name):
    """Return (patch_name, favored_role, bonus_pct) or None."""
    try:
        conn = sqlite3.connect(db_name)
        row = conn.execute(
            "SELECT patch_name, favored_role, bonus_pct FROM meta_patches "
            "WHERE active=1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row
    except Exception:
        return None


def rotate_patch(db_name, game_date_str):
    """Generate next patch. Call every 2 months. Returns (patch_name, favored_role)."""
    try:
        conn = sqlite3.connect(db_name)

        last = conn.execute(
            "SELECT patch_name, favored_role FROM meta_patches ORDER BY id DESC LIMIT 1"
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
            last_role = last[1]
        else:
            new_name  = '7.36'
            last_role = None

        # Pick a different role from last patch
        pool = [r for r in _ROLES if r != last_role]
        new_role = random.choice(pool)
        bonus    = random.choice([10, 12, 15])

        try:
            year = int(game_date_str[:4])
        except Exception:
            year = 2024

        conn.execute("UPDATE meta_patches SET active=0")
        conn.execute(
            "INSERT INTO meta_patches (season, patch_name, favored_role, bonus_pct, start_date, active) "
            "VALUES (?,?,?,?,?,1)",
            (year, new_name, new_role, bonus, game_date_str)
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
    p = get_active_patch(db_name)
    if not p:
        return 'Патч: нет данных'
    name, role, pct = p
    return f'Патч {name}: {_ROLE_RU.get(role, role)} +{pct}%'
