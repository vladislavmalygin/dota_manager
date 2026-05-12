import sqlite3
import random

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

from logic.ai import decay_ratings_season_end, apply_age_decline
from logic.tournaments.runner import ensure_next_year_tournaments
from logic.sponsors import check_and_pay_season_bonus


_YOUTH_FIRST   = ['Alex', 'Ivan', 'Max', 'Leon', 'Kai', 'Ryan', 'Lucas', 'Erik', 'Omar', 'Jun',
                  'Artem', 'Sven', 'Noel', 'Nico', 'Jae', 'Ryu', 'Luca', 'Felix', 'Dante', 'Hugo']
_YOUTH_LAST    = ['Chen', 'Park', 'Kim', 'Silva', 'Petrov', 'Müller', 'Garcia', 'Lee',
                  'Kozlov', 'Tanaka', 'Nguyen', 'Santos', 'Ivanov', 'Bauer', 'Rossi']
_YOUTH_NATIONS = ['Russia', 'China', 'South Korea', 'Brazil', 'Germany',
                  'USA', 'Philippines', 'Ukraine', 'Poland', 'Japan', 'Vietnam']
_YOUTH_ROLES   = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']

_NICK_NOUNS = [
    'Phantom', 'Shadow', 'Storm', 'Blade', 'Ember', 'Frost', 'Venom', 'Gale',
    'Spike', 'Blaze', 'Cinder', 'Drift', 'Flint', 'Gloom', 'Haze', 'Jinx',
    'Talon', 'Umbra', 'Wisp', 'Onyx', 'Pyre', 'Rift', 'Sable', 'Void',
    'Torch', 'Rune', 'Comet', 'Dusk', 'Flare', 'Bolt', 'Crest', 'Edge',
    'Forge', 'Grave', 'Howl', 'Iron', 'Knave', 'Lance', 'Mist', 'Nox',
    'Orbit', 'Plague', 'Quake', 'Relic', 'Smite', 'Thorn', 'Valor', 'Wraith',
    'Apex', 'Bane', 'Chaos', 'Dread', 'Echo', 'Fate', 'Grit', 'Husk',
]

# ── Nick generation ───────────────────────────────────────────────────────────

_CIS_NATIONS   = frozenset({'Russia', 'Ukraine', 'Poland', 'Belarus', 'Kazakhstan', 'Romania'})
_ASIAN_NATIONS = frozenset({'China', 'South Korea', 'Japan', 'Vietnam',
                             'Philippines', 'Taiwan', 'Malaysia', 'Singapore'})

_WORDS_SHORT = [
    'bolt', 'void', 'apex', 'flux', 'grim', 'nova', 'raze', 'haze',
    'jinx', 'rift', 'gale', 'dusk', 'fang', 'kite', 'pike', 'sage',
    'vex',  'arch', 'bane', 'colt', 'hunt', 'lash', 'mist', 'nox',
    'rune', 'sly',  'ward', 'zeal', 'edge', 'tide', 'soul', 'warp',
    'link', 'monk', 'pyre', 'quil', 'ruin', 'smit', 'vane', 'weld',
]

_LEET_MAP = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5'}


def _leet(word):
    return ''.join(_LEET_MAP.get(c, c) for c in word)


def _gen_nick_cis():
    w = random.choice(_WORDS_SHORT)
    p = random.randint(0, 5)
    if p == 0:   return _leet(w)                              # n0va, g4le
    if p == 1:   return f"x{w.capitalize()}"                  # xNova
    if p == 2:                                                  # m1ke, kuz4
        c = random.choice('mnkrbvdzsl')
        return f"{c}{_leet(w[1:])}"
    if p == 3:   return f"{w}{random.randint(1, 99)}"         # nova47
    if p == 4:   return f"{_leet(w)}{random.randint(1, 9)}"   # n0va3
    return f"{w}_{random.randint(1, 9)}"                       # nova_7


def _gen_nick_asian():
    p = random.randint(0, 3)
    if p == 0:   return random.choice(_NICK_NOUNS)             # Phantom
    if p == 1:                                                  # Bol7
        w = random.choice(_WORDS_SHORT)
        return f"{w.capitalize()}{random.randint(1, 9)}"
    if p == 2:                                                  # boLT (MiDas style)
        w = random.choice(_WORDS_SHORT)
        mid = max(1, len(w) // 2)
        return w[:mid].lower() + w[mid:].upper()
    return random.choice(_WORDS_SHORT).upper()                 # BOLT


def _gen_nick_western():
    p = random.randint(0, 3)
    if p == 0:   return random.choice(_WORDS_SHORT).capitalize()   # Crisp
    if p == 1:                                                       # CrispBolt
        w1 = random.choice(_WORDS_SHORT)
        w2 = random.choice(_WORDS_SHORT)
        return f"{w1.capitalize()}{w2.capitalize()}"
    if p == 2:   return f"{random.choice(_NICK_NOUNS)}{random.randint(1, 99)}"  # Phantom42
    return f"{random.choice(_WORDS_SHORT)}{random.randint(1, 999)}"              # bolt247


def generate_nick(country, existing_nicks):
    """Generate unique nickname based on player nationality."""
    nation = country or ''
    for _ in range(30):
        if nation in _CIS_NATIONS:
            nick = _gen_nick_cis()
        elif nation in _ASIAN_NATIONS:
            nick = _gen_nick_asian()
        else:
            nick = _gen_nick_western()
        if nick not in existing_nicks:
            existing_nicks.add(nick)
            return nick
    fallback = f"{random.choice(_NICK_NOUNS)}{random.randint(100, 999)}"
    existing_nicks.add(fallback)
    return fallback


def _snapshot_skills(db_name, year):
    """Save current skill levels for all players as season snapshot."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute("SELECT id, COALESCE(micro_skills,0), COALESCE(macro_skills,0), "
              "COALESCE(soft_skills,0) FROM players WHERE team_id != 0")
    for pid, mi, ma, so in c.fetchall():
        try:
            c.execute("""
                INSERT INTO player_skill_snapshot (player_id, season, micro, macro, soft)
                VALUES (?,?,?,?,?)
                ON CONFLICT(player_id, season) DO UPDATE SET
                    micro=excluded.micro, macro=excluded.macro, soft=excluded.soft
            """, (pid, year, mi, ma, so))
        except Exception:
            pass
    conn.commit()
    conn.close()


def _age_players(db_name, year, skip=False, max_retire=7):
    """Age all players +1. Apply degradation. Retire up to max_retire players.
    Returns list of (nick, team_id) for retired players on player's team."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Snapshot skills before aging
    _snapshot_skills(db_name, year - 1)

    c.execute("SELECT id FROM teams WHERE player='yes'")
    pt = (c.execute("SELECT id FROM teams WHERE player='yes'").fetchone() or (None,))[0]

    c.execute("SELECT id, age, micro_skills, macro_skills, soft_skills, team_id, nickname, "
              "COALESCE(retirement_age, 30) "
              "FROM players WHERE age IS NOT NULL")
    players = c.fetchall()

    retire_candidates = []
    retired_msgs = []
    player_team_retirements = []
    for pid, age, micro, macro, soft, team_id, nick, retirement_age in players:
        if age is None:
            continue
        age += 1
        c.execute("UPDATE players SET age=? WHERE id=?", (age, pid))

        micro = micro or 1; macro = macro or 1; soft = soft or 1

        def _lose_weakest():
            col = min([('micro_skills', micro), ('macro_skills', macro), ('soft_skills', soft)],
                      key=lambda x: x[1])[0]
            c.execute(f"UPDATE players SET {col}=MAX(1,{col}-1) WHERE id=?", (pid,))

        years_left = retirement_age - age
        if years_left <= 0:
            _lose_weakest()
            if random.random() < 0.40:
                _lose_weakest()
        elif years_left == 1:
            _lose_weakest()
        elif years_left == 2 and random.random() < 0.55:
            _lose_weakest()
        elif years_left == 3 and random.random() < 0.25:
            _lose_weakest()

        if age >= retirement_age:
            retire_candidates.append((pid, nick, team_id))

    # First season: skip retirements entirely
    if not skip:
        random.shuffle(retire_candidates)
        for pid, nick, team_id in retire_candidates[:max_retire]:
            if team_id and team_id != 0:
                c.execute("""UPDATE teams SET
                    carry           = CASE WHEN carry=?           THEN NULL ELSE carry           END,
                    mid             = CASE WHEN mid=?             THEN NULL ELSE mid             END,
                    offlane         = CASE WHEN offlane=?         THEN NULL ELSE offlane         END,
                    partial_support = CASE WHEN partial_support=? THEN NULL ELSE partial_support END,
                    full_support    = CASE WHEN full_support=?    THEN NULL ELSE full_support    END
                """, (pid, pid, pid, pid, pid))
                if team_id == pt:
                    player_team_retirements.append(nick)
            c.execute("DELETE FROM players WHERE id=?", (pid,))
            retired_msgs.append(nick)

    if retired_msgs:
        text = "Завершили карьеру: " + ", ".join(retired_msgs)
        c.execute("INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                  (text, f"{year}-01-01", "Новости"))

    conn.commit()
    conn.close()
    return player_team_retirements


def _generate_youth(db_name, year, count=3):
    """Add count young FA players to the pool and send inbox notice."""
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    if count == 0:
        conn.close()
        return

    existing_nicks = set(r[0] for r in c.execute("SELECT nickname FROM players").fetchall())

    roles = [random.choice(_YOUTH_ROLES) for _ in range(count)]
    nicks = []
    for role in roles:
        name    = random.choice(_YOUTH_FIRST)
        surname = random.choice(_YOUTH_LAST)
        country = random.choice(_YOUTH_NATIONS)
        age     = random.randint(17, 19)
        micro   = random.randint(52, 74)
        macro   = random.randint(52, 74)
        soft    = random.randint(46, 66)
        cap     = random.randint(210, 320)
        comp    = random.randint(3, 5)
        exp_w   = 2500 + comp * 500
        nick    = generate_nick(country, existing_nicks)
        ret_age   = random.randint(max(24, age + 1), 31)
        stab      = random.randint(3, 7)   # youth: moderate stability
        lr        = random.randint(6, 10)  # youth: fast learners
        form      = random.randint(4, 7)
        mc        = random.randint(70, 96)
        xc        = random.randint(70, 96)
        sc        = random.randint(62, 90)
        c.execute("""
            INSERT INTO players
              (nickname, name, surname, country, role, team_id,
               micro_skills, macro_skills, soft_skills, skill_cap,
               competence, morale, wage, expected_wage, age, retirement_age,
               stability, learning_rate, fame, character,
               form, micro_cap, macro_cap, soft_cap, is_youth)
            VALUES (?,?,?,?,?,0, ?,?,?,?, ?,7,0,?,?,?,?,?,30,'balanced', ?,?,?,?,1)
        """, (nick, name, surname, country, role,
              micro, macro, soft, cap, comp, exp_w, age, ret_age, stab, lr,
              form, mc, xc, sc))
        nicks.append(nick)

    if nicks:
        c.execute("INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                  (f"Академия: новые таланты на рынке — {', '.join(nicks)}",
                   f"{year}-01-01", "Скаутинг"))
    conn.commit()
    conn.close()

_GOLD   = (1.00, 0.85, 0.25, 1)
_SILVER = (0.85, 0.85, 0.85, 1)
_BRONZE = (0.80, 0.55, 0.30, 1)
_ACCENT = (0.35, 0.85, 1.00, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_DIM    = (0.55, 0.55, 0.55, 1)


def _lbl(text, height=32, color=_WHITE, bold=False, halign='center'):
    t = f'[b]{text}[/b]' if bold else text
    lbl = Label(
        text=t, markup=True,
        size_hint_y=None, height=height,
        color=color, halign=halign, valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


class SeasonEndPopup(Popup):
    def __init__(self, db_name, year, on_confirmed=None, **kwargs):
        super().__init__(**kwargs)
        self.title = f'Сезон {year} завершён'
        self.size_hint = (0.70, 0.88)
        self.auto_dismiss = False
        self.db_name = db_name
        self.year = year
        self._on_confirmed = on_confirmed
        self._build()

    def _build(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        # Top 10 teams by rating
        cur.execute(
            "SELECT name, COALESCE(rating, 0) FROM teams ORDER BY rating DESC LIMIT 10"
        )
        top_teams = cur.fetchall()

        # TI winner of this year + player placement
        cur.execute(
            """SELECT t.place1, t.place2, t.place3, t.place4,
                      t.place5, t.place6, t.place7, t.place8
               FROM tournaments t
               WHERE t.name LIKE ? AND t.place1 IS NOT NULL
               LIMIT 1""",
            (f'%International {self.year}%',),
        )
        ti_top8_row = cur.fetchone()

        ti_winner = None
        self._player_ti_place = None

        cur.execute("SELECT name, COALESCE(rating, 0) FROM teams WHERE player='yes'")
        player_row = cur.fetchone()
        player_name = player_row[0].strip() if player_row else None
        player_rating = player_row[1] if player_row else 0

        if ti_top8_row:
            # Resolve team IDs to names
            top8_names = []
            for tid in ti_top8_row:
                if tid:
                    cur.execute("SELECT name FROM teams WHERE id=?", (tid,))
                    r = cur.fetchone()
                    top8_names.append(r[0].strip() if r else None)
                else:
                    top8_names.append(None)
            ti_winner = top8_names[0]
            if player_name:
                for i, tname in enumerate(top8_names):
                    if tname and tname == player_name:
                        self._player_ti_place = i + 1
                        break

        conn.close()

        grid = GridLayout(cols=1, spacing=6, padding=(14, 10))

        # Banner
        if ti_winner:
            grid.add_widget(_lbl(
                f'Чемпион The International {self.year}: {ti_winner}',
                height=50, color=_GOLD, bold=True,
            ))
        else:
            grid.add_widget(_lbl(f'Сезон {self.year}', height=44, color=_ACCENT, bold=True))

        grid.add_widget(_lbl('Итоговый рейтинг сезона', height=34, color=_ACCENT, bold=True))

        for i, (name, rating) in enumerate(top_teams):
            is_player = player_name and name.strip() == player_name
            if i == 0:
                color = _GOLD
            elif i == 1:
                color = _SILVER
            elif i == 2:
                color = _BRONZE
            elif is_player:
                color = _GREEN
            else:
                color = _WHITE
            grid.add_widget(_lbl(
                f'{i+1}.  {name}  —  {int(rating)} pts',
                height=30, color=color,
            ))

        if player_name:
            # find player's actual rank
            cur2 = sqlite3.connect(self.db_name)
            c2 = cur2.cursor()
            c2.execute(
                "SELECT COUNT(*) FROM teams WHERE COALESCE(rating,0) > ?",
                (player_rating,),
            )
            rank = c2.fetchone()[0] + 1
            cur2.close()
            if rank > 10:
                grid.add_widget(_lbl(f'Ваша команда: {rank}-е место  —  {int(player_rating)} pts',
                                     height=32, color=_GREEN))

        grid.add_widget(_lbl('', height=8))
        grid.add_widget(_lbl(
            'Рейтинг сохранится на 30% — начинаем новый сезон.',
            height=34, color=(1.0, 0.65, 0.25, 1), bold=True,
        ))

        confirm_btn = Button(
            text=f'Начать сезон {self.year + 1}',
            size_hint_y=None, height=54,
            background_color=(0.15, 0.65, 0.25, 1), background_normal='',
        )
        confirm_btn.bind(on_press=self._confirm)
        grid.add_widget(confirm_btn)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)

        layout = BoxLayout(orientation='vertical', padding=4)
        layout.add_widget(scroll)
        self.content = layout

    def _confirm(self, _):
        sponsor_result = check_and_pay_season_bonus(
            self.db_name, self.year, getattr(self, '_player_ti_place', None)
        )
        if sponsor_result:
            sname, smsg, samount = sponsor_result
            conn = sqlite3.connect(self.db_name)
            conn.execute(
                "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                (f'Спонсор {sname}: {smsg}', 'Организация'),
            )
            conn.commit()
            conn.close()

        decay_ratings_season_end(self.db_name)
        apply_age_decline(self.db_name)
        ensure_next_year_tournaments(self.db_name, self.year + 1)

        # Reset youth camp counter for new season
        _sc = sqlite3.connect(self.db_name)
        _sc.execute("UPDATE teams SET youth_camp_count=0")
        _sc.commit()
        _sc.close()

        # Первый сезон = год первого завершённого турнира
        import sqlite3 as _sq
        _c = _sq.connect(self.db_name)
        _row = _c.execute(
            "SELECT MIN(CAST(SUBSTR(start_date,1,4) AS INTEGER)) "
            "FROM tournaments WHERE place1 IS NOT NULL"
        ).fetchone()
        _c.close()
        first_season = bool(_row and _row[0] and self.year <= _row[0])

        retirees = _age_players(
            self.db_name, self.year + 1, skip=first_season, max_retire=7
        )
        _generate_youth(self.db_name, self.year + 1, count=7)
        # Generate goals for next season
        from logic.goals import generate_season_goals
        generate_season_goals(self.db_name, self.year + 1)
        self.dismiss()
        if retirees:
            _show_retirement_popup(retirees, self._on_confirmed)
        elif self._on_confirmed:
            self._on_confirmed()


_FAREWELL_QUOTES = [
    "Это был незабываемый путь.",
    "Прощай, арена. Я дал всё, что мог.",
    "Уходить тяжело, но время пришло.",
    "Карьера завершена. Спасибо команде.",
    "Последний матч сыгран. Легенда уходит.",
]


def _show_retirement_popup(nicks, on_confirmed=None):
    import random as _r
    names_str = ', '.join(nicks)
    root = BoxLayout(orientation='vertical', padding=14, spacing=10)
    title_lbl = Label(
        text=f'[b]Прощание с командой[/b]', markup=True,
        color=(1.0, 0.85, 0.25, 1), size_hint_y=None, height=36,
        halign='center', valign='middle',
    )
    title_lbl.bind(size=title_lbl.setter('text_size'))
    root.add_widget(title_lbl)

    for nick in nicks:
        quote = _r.choice(_FAREWELL_QUOTES)
        nl = Label(
            text=f'[b]{nick}[/b] завершает карьеру.\n"{quote}"',
            markup=True, color=(0.92, 0.92, 0.92, 1),
            size_hint_y=None, height=54,
            halign='center', valign='middle',
        )
        nl.bind(size=nl.setter('text_size'))
        root.add_widget(nl)

    popup = Popup(
        title='', content=root,
        size_hint=(0.55, min(0.85, 0.22 + len(nicks) * 0.14)),
        auto_dismiss=False,
    )
    ok = Button(
        text='Проститься', size_hint_y=None, height=44,
        background_color=(0.22, 0.50, 0.22, 1), background_normal='',
    )
    root.add_widget(ok)

    def _close(_):
        popup.dismiss()
        if on_confirmed:
            on_confirmed()

    ok.bind(on_press=_close)
    popup.open()
