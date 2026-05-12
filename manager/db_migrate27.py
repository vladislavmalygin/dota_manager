import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate27'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    try:
        conn.execute("ALTER TABLE players ADD COLUMN psychotype TEXT DEFAULT 'team_player'")
    except Exception:
        pass

    # Assign psychotypes based on existing stats
    conn.execute("""
        UPDATE players SET psychotype='solo_carry'
        WHERE (micro_skills > COALESCE(macro_skills,0)+10
               OR micro_skills > COALESCE(soft_skills,0)+15)
          AND role IN ('carry','mid','offlane')
          AND (psychotype IS NULL OR psychotype='team_player')
    """)
    conn.execute("""
        UPDATE players SET psychotype='leader'
        WHERE COALESCE(soft_skills,0) >= 60
          AND COALESCE(comp_exp,0) >= 5
          AND (psychotype IS NULL OR psychotype='team_player')
    """)
    conn.execute("""
        UPDATE players SET psychotype='wildcard'
        WHERE ABS(COALESCE(micro_skills,0)-COALESCE(soft_skills,0)) < 5
          AND COALESCE(stability,5) <= 4
          AND (psychotype IS NULL OR psychotype='team_player')
          AND RANDOM()%5 = 0
    """)
    conn.execute(
        "UPDATE players SET psychotype='team_player' WHERE psychotype IS NULL"
    )

    conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate27')")
    conn.commit()
    conn.close()
