"""
Migration 31:
  1. Normalize team regions: CIS→EEU, EU→WEU (so DPC filters work)
  2. Set contract_end for players on teams who have none (12-month contract)
  3. Fill empty AI team roster slots from free agents
"""
import sqlite3


def migrate(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM _migrations WHERE name='migrate31'")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    # 1. Normalize regions
    c.execute("UPDATE teams SET region='EEU' WHERE region='CIS'")
    c.execute("UPDATE teams SET region='WEU' WHERE region='EU'")

    # 2. Contract_end for players on teams without it — set to 1 year from game date
    try:
        gd_row = c.execute("SELECT date FROM save WHERE id=1").fetchone()
        game_date = gd_row[0] if gd_row else '2026-01-01'
    except Exception:
        game_date = '2026-01-01'

    # Parse year from game_date, add 1 year
    try:
        from datetime import date, timedelta
        d = date.fromisoformat(game_date)
        contract_end = str(d + timedelta(days=365))
    except Exception:
        contract_end = '2027-01-01'

    c.execute("""
        UPDATE players SET contract_end=?
        WHERE team_id != 0 AND (contract_end IS NULL OR contract_end = '')
    """, (contract_end,))

    # 3. Fill empty AI team roster slots from free agents
    _fill_empty_slots(c, conn)

    c.execute("INSERT OR IGNORE INTO _migrations (name) VALUES ('migrate31')")
    conn.commit()
    conn.close()


def _fill_empty_slots(c, conn):
    """Fill each empty roster slot with best affordable free agent."""
    roles = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']

    c.execute("""
        SELECT id, name, COALESCE(budget, 500000),
               carry, mid, offlane, partial_support, full_support,
               COALESCE(region, 'WEU')
        FROM teams WHERE player='no'
    """)
    teams = c.fetchall()

    for row in teams:
        team_id, team_name = row[0], row[1]
        budget = row[2]
        slots = list(row[3:8])
        region = row[8]

        for i, (role, pid) in enumerate(zip(roles, slots)):
            if pid:
                continue  # slot filled

            # Find best free agent by role, affordable, prefer same region countries
            c.execute("""
                SELECT p.id, p.nickname, COALESCE(p.expected_wage, p.wage, 5000)
                FROM players p
                WHERE p.team_id = 0 AND p.role = ?
                  AND COALESCE(p.expected_wage, p.wage, 5000) <= ?
                ORDER BY (COALESCE(p.micro_skills, 0) + COALESCE(p.macro_skills, 0)) DESC
                LIMIT 1
            """, (role, budget // 2))  # cap at half budget per player
            agent = c.fetchone()
            if not agent:
                # Last resort: any free agent of this role
                c.execute("""
                    SELECT p.id, p.nickname, COALESCE(p.expected_wage, p.wage, 3000)
                    FROM players p
                    WHERE p.team_id = 0 AND p.role = ?
                    ORDER BY (COALESCE(p.micro_skills, 0) + COALESCE(p.macro_skills, 0)) DESC
                    LIMIT 1
                """, (role,))
                agent = c.fetchone()

            if not agent:
                continue

            new_pid, new_nick, wage = agent
            c.execute(f"UPDATE teams SET {role}=? WHERE id=?", (new_pid, team_id))
            c.execute(
                "UPDATE players SET team_id=?, wage=? WHERE id=?",
                (team_id, wage, new_pid),
            )
            budget -= wage
            slots[i] = new_pid


if __name__ == '__main__':
    import sys
    for db in (sys.argv[1:] or ['start_database.db']):
        migrate(db)
        print(f'[migrate31] done: {db}')
