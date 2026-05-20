"""Pure-Python manager skill helpers — no Kivy dependency."""
import sqlite3


def get_skill_level(db_name, skill_key):
    try:
        conn = sqlite3.connect(db_name)
        row = conn.execute(
            "SELECT COALESCE(level,0) FROM manager_skills WHERE skill_key=?",
            (skill_key,),
        ).fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception:
        return 0


def has_skill(db_name, skill_key, min_level=1):
    return get_skill_level(db_name, skill_key) >= min_level
