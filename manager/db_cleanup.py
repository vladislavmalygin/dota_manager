"""
DB cleanup: remove duplicate/fictional teams and fictional players.
Idempotent (checks before acting).
"""
import sqlite3


# Teams to delete (id → reason)
TEAMS_DELETE = {
    9:  '1w Team — fictional Russian team',
    10: 'Team Zero — fictional Chinese team',
    11: 'G2 IG — fictional combination',
    12: 'Talon Esports — disbanded, empty',
    18: 'Gaimin Gladiators — disbanded, empty',
    19: 'BetBoom Team — duplicate of BB Team (id=8)',
    20: '9Pandas — disbanded, empty',
    22: 'Team Secret — on hiatus, empty',
    23: 'PSG.LGD — disbanded, empty',
    25: 'BOOM Esports — disbanded, empty',
    29: 'Shopify Rebellion — defunct org',
    30: 'TSM — no active Dota 2 team',
    41: 'Team Empire — empty',
    48: 'Team Tickles — fictional',
}

# Players to delete entirely (clearly fictional, no real-world equivalent)
PLAYERS_DELETE = [
    42,  # Munkushi     (1w Team)
    43,  # Chira_Junior (1w Team)
    45,  # swedenstrong (1w Team)
    46,  # respect      (1w Team)
    286, # Kaito        (Team Tickles)
    287, # hFnk         (Team Tickles)
    288, # Tobias       (Team Tickles)
    289, # Enrico       (Team Tickles)
    290, # Bananaman    (Team Tickles)
]

# Players to release to FA (real or semi-real players from deleted teams)
PLAYERS_RELEASE = [
    44,  # Cloud / Aleksandr Zakharov (1w Team → FA)
    206, 207, 208, 209, 210,  # Team Zero
    211, 212, 213, 214, 215,  # G2 IG
    157, 158, 159, 160,       # Shopify Rebellion
    161, 162, 163, 164, 165,  # TSM
]

# Teams whose slots need clearing (players already have team_id=0)
TEAMS_CLEAR_SLOTS = [6]  # Cloud9

# Special move: Davai Lama (id=77) joined Nigma Galaxy (id=21) as mid, March 2026
DAVAI_LAMA_ID = 77
NIGMA_ID = 21


def cleanup(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Idempotency: skip if already done
    c.execute("SELECT COUNT(*) FROM teams WHERE id=9")
    if c.fetchone()[0] == 0:
        print(f'[cleanup] Already applied to {db_name}, skipping.')
        conn.close()
        return

    # ── 1. Release players to FA ──────────────────────────────────────────────
    for pid in PLAYERS_RELEASE:
        c.execute("SELECT micro_skills, macro_skills, wage FROM players WHERE id=?", (pid,))
        row = c.fetchone()
        if not row:
            continue
        micro, macro, wage = (v or 0 for v in row)
        avg = (micro + macro) // 2
        exp = max(avg * 180, int(wage * 0.85))
        c.execute("UPDATE players SET team_id=0, wage=0, expected_wage=? WHERE id=?", (exp, pid))

    # ── 2. Delete fictional players ───────────────────────────────────────────
    for pid in PLAYERS_DELETE:
        c.execute("DELETE FROM players WHERE id=?", (pid,))

    # ── 3. Delete teams (and cascade-clear their player slots) ───────────────
    for tid in TEAMS_DELETE:
        # Any players still assigned to this team → release to FA
        c.execute(
            "SELECT carry,mid,offlane,partial_support,full_support FROM teams WHERE id=?", (tid,)
        )
        row = c.fetchone()
        if row:
            for slot_id in row:
                if slot_id:
                    c.execute("SELECT micro_skills,macro_skills,wage FROM players WHERE id=?", (slot_id,))
                    p = c.fetchone()
                    if p:
                        micro, macro, wage = (v or 0 for v in p)
                        avg = (micro + macro) // 2
                        exp = max(avg * 180, int(wage * 0.85))
                        c.execute(
                            "UPDATE players SET team_id=0, wage=0, expected_wage=? WHERE id=?",
                            (exp, slot_id),
                        )
        c.execute("DELETE FROM teams WHERE id=?", (tid,))

    # ── 4. Clear slots for teams with orphaned players ────────────────────────
    for tid in TEAMS_CLEAR_SLOTS:
        c.execute(
            "UPDATE teams SET carry=NULL,mid=NULL,offlane=NULL,"
            "partial_support=NULL,full_support=NULL WHERE id=?",
            (tid,),
        )

    # ── 5. Davai Lama → Nigma Galaxy mid ─────────────────────────────────────
    c.execute("SELECT id FROM players WHERE id=? AND team_id != ?", (DAVAI_LAMA_ID, NIGMA_ID))
    if c.fetchone():
        c.execute(
            "UPDATE players SET team_id=?, role='mid', wage=9000, "
            "expected_wage=9000, contract_end='2027-12-31' WHERE id=?",
            (NIGMA_ID, DAVAI_LAMA_ID),
        )
        c.execute("UPDATE teams SET mid=? WHERE id=?", (DAVAI_LAMA_ID, NIGMA_ID))
        print(f'[cleanup] Davai Lama → Nigma Galaxy mid')

    conn.commit()
    conn.close()

    # Summary
    remaining = sqlite3.connect(db_name).execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    fa_count  = sqlite3.connect(db_name).execute(
        "SELECT COUNT(*) FROM players WHERE team_id=0"
    ).fetchone()[0]
    print(f'[cleanup] Done: {remaining} teams, {fa_count} free agents — {db_name}')


if __name__ == '__main__':
    import sys
    dbs = sys.argv[1:] or ['start_database.db', 'saves/asd_asd.db']
    for db in dbs:
        try:
            cleanup(db)
        except Exception as e:
            print(f'[cleanup] Error on {db}: {e}')
