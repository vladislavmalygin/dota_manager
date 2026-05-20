import sqlite3
import random
from datetime import date, timedelta

_RENEWAL_DAYS = 60  # show renewal offer when contract ≤ this many days away

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


import ui_theme as T

_ACCENT = T.ACCENT
_DIM    = T.TEXT_DIM
_WHITE  = T.TEXT_MAIN
_GREEN  = T.POSITIVE
_YELLOW = T.WARNING
_RED    = T.NEGATIVE


def _show_window_popup():
    """Show info popup when player tries to sell outside transfer window."""
    content = BoxLayout(orientation='vertical', padding=12, spacing=8)
    lbl = Label(
        text='Трансферное окно закрыто.\n\nПродажи игроков доступны только в\n'
             '[b]январе[/b] и [b]августе[/b].\n\nОтпустить (без компенсации) можно всегда.',
        markup=True, halign='center', valign='middle',
        color=(0.92, 0.92, 0.92, 1),
    )
    lbl.bind(size=lbl.setter('text_size'))
    content.add_widget(lbl)
    p = Popup(title='Трансфер недоступен', content=content, size_hint=(0.50, 0.38))
    btn = Button(text='Понятно', size_hint_y=None, height=44,
                 background_color=(0.4, 0.4, 0.8, 1), background_normal='')
    btn.bind(on_press=p.dismiss)
    content.add_widget(btn)
    p.open()


class NegotiationPopup(Popup):
    """Wage negotiation before signing a free agent."""

    def __init__(self, db_name, pid, role, demanded_wage, years, on_accepted, **kwargs):
        super().__init__(**kwargs)
        self.db_name       = db_name
        self._pid          = pid
        self._role         = role
        self._demanded     = demanded_wage
        self._years        = years
        self._on_accepted  = on_accepted
        self.title         = ''
        self.size_hint     = (0.72, 0.72)
        self.auto_dismiss  = False
        self._build()

    def _build(self):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        cur.execute(
            "SELECT name, surname, nickname, micro_skills, macro_skills, soft_skills, "
            "COALESCE(morale, 5), COALESCE(age, 22), COALESCE(team_id, 0) FROM players WHERE id=?",
            (self._pid,),
        )
        p = cur.fetchone()
        rep_row = cur.execute(
            "SELECT COALESCE(reputation,0) FROM characters LIMIT 1"
        ).fetchone()
        reputation = rep_row[0] if rep_row else 0

        # Rating comparison: player's current team vs our team
        my_rating  = (cur.execute(
            "SELECT COALESCE(rating,0) FROM teams WHERE player='yes'"
        ).fetchone() or (0,))[0]
        player_team_id = p[8] if p else 0
        their_rating = 0
        if player_team_id:
            their_rating = (cur.execute(
                "SELECT COALESCE(rating,0) FROM teams WHERE id=?", (player_team_id,)
            ).fetchone() or (0,))[0]

        # Competing AI interest for T2+ players (skill >= 120)
        competitors = []
        skill_sum = ((p[3] or 0) + (p[4] or 0)) if p else 0
        if skill_sum >= 120:
            interest_chance = min(0.75, (skill_sum - 100) / 160)
            cur.execute(
                f"SELECT t.name FROM teams t "
                f"WHERE t.player != 'yes' "
                f"AND (t.{self._role} IS NULL OR t.{self._role} = 0) "
                f"AND COALESCE(t.budget, 0) >= ? "
                f"ORDER BY t.rating DESC LIMIT 8",
                (self._demanded * 8,)
            )
            candidate_teams = [r[0] for r in cur.fetchall()]
            if candidate_teams and random.random() < interest_chance:
                n_comp = random.randint(1, min(2, len(candidate_teams)))
                competitors = random.sample(candidate_teams, n_comp)

        conn.close()
        if not p:
            self.content = Label(text='Игрок не найден')
            return

        fname, lname, nick, micro, macro, soft, morale, age, _ = p
        avg = ((micro or 0) + (macro or 0)) // 2

        # Rating delta: positive = we're better rated → player wants to come
        rating_delta = my_rating - their_rating
        rating_factor = max(-0.20, min(0.20, rating_delta / 500))  # ±20% wage effect

        demanded = max(1000, int(self._demanded * (1.0 - rating_factor)))

        # Apply competing bid premium
        bid_premium = 0
        if competitors:
            bid_premium = random.randint(6, 16)
            demanded = int(demanded * (1 + bid_premium / 100))

        low_wage  = max(1000, int(demanded * 0.80))
        high_wage = int(demanded * 1.15)

        # Agent fee for star players (avg >= 75): 15% of first-year wages
        agent_fee = 0
        agent_pct = 0
        if avg >= 75:
            agent_pct = 15 if avg >= 90 else 10
            agent_fee = round(demanded * 12 * agent_pct / 100 / 5000) * 5000

        # acceptance chance: morale + reputation + rating bonus
        rep_bonus    = min(20, reputation // 5)
        rating_bonus = int(rating_factor * 30)   # better team → +up to 6% chance
        low_chance   = max(20, min(80, 50 + (5 - morale) * 5 + rep_bonus + rating_bonus))

        root = BoxLayout(orientation='vertical', padding=10, spacing=8)

        # ── player card ──────────────────────────────────────────
        card = BoxLayout(orientation='horizontal', size_hint_y=None, height=64,
                         spacing=10)
        def _lbl(t, color=_WHITE, bold=False, halign='left'):
            l = Label(text=f'[b]{t}[/b]' if bold else t, markup=True,
                      color=color, halign=halign, valign='middle')
            l.bind(size=l.setter('text_size'))
            return l

        card.add_widget(_lbl(f'[b]{nick}[/b]\n{fname} {lname}', _ACCENT))
        card.add_widget(_lbl(f'Скилл: {avg}\nВозраст: {age}', _WHITE))
        card.add_widget(_lbl(f'Мораль: {morale}/10\nЛет контракта: {self._years}', _WHITE))
        root.add_widget(card)

        # ── competing bid banner ──────────────────────────────────
        if competitors:
            comp_names = ' и '.join(competitors)
            comp_lbl = Label(
                text=f'[b][!] Конкуренция:[/b] {comp_names} тоже интересуются  (+{bid_premium}% к запросу)',
                markup=True, color=_YELLOW, halign='center', valign='middle',
                size_hint_y=None, height=30, font_size='12sp',
            )
            comp_lbl.bind(size=comp_lbl.setter('text_size'))
            root.add_widget(comp_lbl)

        # ── divider ──────────────────────────────────────────────
        root.add_widget(Label(text='─' * 44, color=_DIM,
                              size_hint_y=None, height=16, font_size='12sp'))
        # Rating effect hint
        if abs(rating_factor) >= 0.03:
            if rating_factor > 0:
                hint = f'+  Мы рейтингом выше — игрок снизил запрос на {int(rating_factor*100)}%'
                hint_c = _GREEN
            else:
                hint = f'-  Мы рейтингом ниже — игрок завысил запрос на {int(-rating_factor*100)}%'
                hint_c = _RED
            root.add_widget(_lbl(hint, hint_c, halign='center'))
        root.add_widget(_lbl(f'Запрошенная зарплата:  ${demanded:,}/мес',
                             _YELLOW, bold=True, halign='center'))
        if agent_fee:
            root.add_widget(_lbl(
                f'Агент игрока требует единовременно: ${agent_fee:,}  ({agent_pct}% от года)',
                (1.00, 0.55, 0.20, 1), halign='center'))

        # ── offer buttons ─────────────────────────────────────────
        offers = BoxLayout(orientation='vertical', spacing=6, size_hint_y=None, height=150)

        def _offer_row(label, wage, sub, btn_text, btn_color, on_press):
            row = BoxLayout(size_hint_y=None, height=44, spacing=6)
            info = Label(
                text=f'{label}\n[color=888888]{sub}[/color]',
                markup=True, color=_WHITE, halign='left', valign='middle',
                size_hint_x=0.65,
            )
            info.bind(size=info.setter('text_size'))
            row.add_widget(info)
            btn = Button(
                text=btn_text, size_hint_x=0.35,
                background_color=btn_color, background_normal='',
                font_size='14sp',
            )
            btn.bind(on_press=on_press)
            row.add_widget(btn)
            return row

        offers.add_widget(_offer_row(
            f'${low_wage:,}/мес  (−20%)',
            low_wage,
            f'Шанс принятия: {low_chance}%',
            'Предложить',
            (0.70, 0.45, 0.10, 1),
            lambda _: self._try_sign(low_wage, low_chance, bonus_morale=False),
        ))
        offers.add_widget(_offer_row(
            f'${demanded:,}/мес  (по запросу)',
            demanded,
            'Принимает всегда',
            'Подписать',
            (0.15, 0.55, 0.20, 1),
            lambda _: self._try_sign(demanded, 100, bonus_morale=False),
        ))
        offers.add_widget(_offer_row(
            f'${high_wage:,}/мес  (+15%)',
            high_wage,
            '+1 к морали при подписании',
            'Бонус',
            (0.20, 0.35, 0.75, 1),
            lambda _: self._try_sign(high_wage, 100, bonus_morale=True),
        ))
        root.add_widget(offers)

        # ── custom wage input ─────────────────────────────────────
        root.add_widget(Label(text='─' * 44, color=_DIM,
                              size_hint_y=None, height=14, font_size='12sp'))
        custom_row = BoxLayout(size_hint_y=None, height=44, spacing=6)
        wage_input = TextInput(
            text=str(demanded), multiline=False,
            input_filter='int', font_size='14sp',
            size_hint_x=0.45, background_color=(0.14, 0.14, 0.18, 1),
            foreground_color=_WHITE, cursor_color=_ACCENT,
        )
        custom_lbl = Label(text='$/мес', color=_DIM, size_hint_x=0.12,
                           halign='left', valign='middle')
        custom_lbl.bind(size=custom_lbl.setter('text_size'))

        self._chance_lbl = Label(
            text=f'Шанс: {low_chance}%', color=_YELLOW,
            size_hint_x=0.22, halign='center', valign='middle',
        )
        self._chance_lbl.bind(size=self._chance_lbl.setter('text_size'))
        self._demanded_for_custom = demanded
        self._low_chance_for_custom = low_chance

        def _update_chance(inst, val):
            try:
                offer = int(val or 0)
            except ValueError:
                return
            ratio = offer / max(1, self._demanded_for_custom)
            if ratio >= 1.0:
                ch = 100
            elif ratio >= 0.80:
                ch = int(self._low_chance_for_custom + (100 - self._low_chance_for_custom) * (ratio - 0.80) / 0.20)
            else:
                ch = max(5, int(self._low_chance_for_custom * ratio / 0.80))
            self._chance_lbl.text = f'Шанс: {ch}%'
            self._chance_lbl.color = _GREEN if ch >= 80 else (_YELLOW if ch >= 40 else _RED)

        wage_input.bind(text=_update_chance)

        send_btn = Button(
            text='Предложить', size_hint_x=0.21,
            background_color=(0.35, 0.35, 0.10, 1), background_normal='',
            font_size='14sp',
        )

        def _custom_offer(_):
            try:
                offer = max(500, int(wage_input.text or 0))
            except ValueError:
                return
            ratio = offer / max(1, self._demanded_for_custom)
            if ratio >= 1.0:
                ch = 100
            elif ratio >= 0.80:
                ch = int(self._low_chance_for_custom + (100 - self._low_chance_for_custom) * (ratio - 0.80) / 0.20)
            else:
                ch = max(5, int(self._low_chance_for_custom * ratio / 0.80))
            self._try_sign(offer, ch, bonus_morale=False)

        send_btn.bind(on_press=_custom_offer)
        custom_row.add_widget(wage_input)
        custom_row.add_widget(custom_lbl)
        custom_row.add_widget(self._chance_lbl)
        custom_row.add_widget(send_btn)
        root.add_widget(custom_row)

        cancel = Button(text='Отмена', size_hint_y=None, height=40,
                        background_color=(0.45, 0.10, 0.10, 1),
                        background_normal='')
        cancel.bind(on_press=self.dismiss)
        root.add_widget(cancel)
        self.content = root

    def _try_sign(self, wage, chance, bonus_morale):
        self.dismiss()
        accepted = (chance >= 100) or (random.randint(1, 100) <= chance)
        if accepted:
            self._do_sign(wage, bonus_morale)
        else:
            self._show_rejection()

    def _do_sign(self, wage, bonus_morale):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        cur.execute("SELECT id FROM teams WHERE player='yes'")
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        team_id = row[0]
        game_date = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
        game_date = game_date[0] if game_date else str(date.today())
        contract_end = str(date.fromisoformat(game_date) + timedelta(days=365 * self._years))

        cur.execute(
            f"UPDATE teams SET {self._role}=? WHERE id=?", (self._pid, team_id)
        )
        cur.execute(
            "UPDATE players SET team_id=?, wage=?, contract_end=?, "
            "time_in_team=1, poaching_team_id=NULL, renewal_notified=0 "
            "WHERE id=?",
            (team_id, wage, contract_end, self._pid),
        )
        if bonus_morale:
            cur.execute("UPDATE players SET morale=MIN(10, COALESCE(morale,5)+1) WHERE id=?",
                        (self._pid,))
        cur.execute("SELECT nickname, micro_skills, macro_skills FROM players WHERE id=?",
                    (self._pid,))
        p_row = cur.fetchone()
        nick   = (p_row[0] if p_row else None) or '?'
        sk_sum = ((p_row[1] or 0) + (p_row[2] or 0)) if p_row else 0
        gd_row = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
        gd_str = gd_row[0] if gd_row else '2024'

        # Deduct agent fee for star players (reduced by negotiator skill)
        if sk_sum // 2 >= 75:
            _agent_pct = 15 if sk_sum // 2 >= 90 else 10
            try:
                from logic.manager_skills import get_skill_level
                neg_lvl = get_skill_level(self.db_name, 'negotiator')
                _agent_pct = max(0, _agent_pct - neg_lvl * 5)
            except Exception:
                pass
            _agent_fee = round(wage * 12 * _agent_pct / 100 / 5000) * 5000
            if _agent_fee > 0:
                conn.execute(
                    "UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?",
                    (_agent_fee, team_id),
                )
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
            (f'Подписан {nick} на {self._years} г., ${wage:,}/мес.', 'Трансфер'),
        )
        conn.commit()
        conn.close()

        # Goals: sign_skill — after commit to avoid DB lock
        try:
            from logic.goals import update_goal, year_from_date
            update_goal(self.db_name, year_from_date(gd_str), 'sign_skill', sk_sum)
        except Exception:
            pass

        if self._on_accepted:
            self._on_accepted()

    def _show_rejection(self):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        cur.execute("SELECT nickname FROM players WHERE id=?", (self._pid,))
        nick = (cur.fetchone() or ('?',))[0]
        conn.close()
        p = Popup(
            title='',
            content=Label(
                text=f'[b]{nick}[/b] отверг предложение.',
                markup=True, halign='center',
            ),
            size_hint=(0.45, 0.25),
        )
        p.open()


ROLE_LABELS = {
    'carry':           'Carry (1)',
    'mid':             'Mid (2)',
    'offlane':         'Offlane (3)',
    'partial_support': 'Support (4)',
    'full_support':    'Support (5)',
}
ROLE_COLS = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']


def is_transfer_window(game_date_str):
    """Трансферные окна: январь и август."""
    try:
        return date.fromisoformat(game_date_str).month in (1, 8)
    except Exception:
        return False


def _transfer_fee(micro, macro, contract_end_str, game_date_str):
    """Transfer fee driven primarily by skill; contract length is a minor modifier.

    Base: avg_skill^1.8 * 400  (exponential — stars worth much more than average)
    Contract modifier: 0 months→×0.75, 12 months→×1.0, 24+ months→×1.15
    Floor: 15,000 (anyone costs something)
    """
    avg = max(1, ((micro or 1) + (macro or 1)) // 2)
    base = int((avg ** 1.8) * 400)

    try:
        days   = (date.fromisoformat(contract_end_str) -
                  date.fromisoformat(game_date_str)).days
        months = max(0, days / 30)
    except Exception:
        months = 12

    # Contract modifier: ranges 0.75 (expired) → 1.15 (≥24 months)
    contract_mult = 0.75 + min(0.40, months / 60)
    fee = int(base * contract_mult)

    return max(15_000, round(fee / 5_000) * 5_000)


def _add_message(db_name, text, author="Трансфер"):
    conn = sqlite3.connect(db_name)
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
        (text, author),
    )
    conn.commit()
    conn.close()


def _lbl(text, height=36, color=(1, 1, 1, 1), bold=False):
    if bold:
        text = f"[b]{text}[/b]"
    lbl = Label(
        text=text, markup=bold,
        size_hint_y=None, height=height,
        color=color, halign='left', valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _header(text, height=42):
    lbl = Label(
        text=f'[b]{text}[/b]', markup=True,
        size_hint_y=None, height=height,
        color=(0.4, 0.9, 1.0, 1), halign='center', valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


_ROLE_TABS = [
    ('все',             'Все'),
    ('carry',           'Carry'),
    ('mid',             'Mid'),
    ('offlane',         'Off'),
    ('partial_support', 'Sup 4'),
    ('full_support',    'Sup 5'),
]

_TAB_COLORS = {
    'все':             (0.30, 0.30, 0.45, 1),
    'carry':           (0.55, 0.20, 0.20, 1),
    'mid':             (0.20, 0.45, 0.20, 1),
    'offlane':         (0.45, 0.28, 0.10, 1),
    'partial_support': (0.18, 0.35, 0.60, 1),
    'full_support':    (0.38, 0.18, 0.55, 1),
}


class TransferPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.title = "Трансферный рынок"
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        self._fa_role      = 'все'
        self._fa_min_skill = 0     # min (micro+macro)/2 filter
        self._fa_max_wage  = 99999 # max expected_wage filter
        self._build()

    # ── build / rebuild ───────────────────────────────────────

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=4, padding=4)

        # ── Global player search bar ─────────────────────────────
        search_bar = BoxLayout(size_hint_y=None, height=36, spacing=6)
        from kivy.uix.label import Label as _Lbl2
        from kivy.uix.textinput import TextInput as _TI2
        search_bar.add_widget(_Lbl2(
            text='Поиск игрока:', size_hint_x=None, width=120,
            color=(0.7, 0.7, 0.7, 1), font_size='13sp',
            halign='right', valign='middle',
        ))
        self._search_inp = _TI2(
            hint_text='никнейм...', multiline=False,
            size_hint_x=0.30, font_size='14sp',
        )
        self._search_inp.bind(text=self._on_search)
        search_bar.add_widget(self._search_inp)
        self._search_results = BoxLayout(orientation='vertical',
                                         size_hint_x=0.55, spacing=2)
        search_bar.add_widget(self._search_results)
        root.add_widget(search_bar)

        body = BoxLayout(orientation='horizontal', spacing=6)
        body.add_widget(self._make_squad_panel())
        body.add_widget(self._make_free_agents_panel())
        root.add_widget(body)

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=50,
            background_color=(0.7, 0.2, 0.2, 1),
        )
        close_btn.bind(on_press=self.dismiss)
        root.add_widget(close_btn)

        self.content = root

    def _rebuild(self):
        from kivy.clock import Clock
        ev = getattr(self, '_rebuild_ev', None)
        if ev:
            ev.cancel()
        self._rebuild_ev = Clock.schedule_once(lambda dt: self._build(), 0.05)

    def _set_fa_role(self, role):
        self._fa_role = role
        self._rebuild()

    def _rent_temp(self, pid, role):
        role_col = {
            'carry': 'carry', 'mid': 'mid', 'offlane': 'offlane',
            'partial_support': 'partial_support', 'full_support': 'full_support',
        }.get(role)
        if not role_col:
            return
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        cur.execute("SELECT id FROM teams WHERE player='yes'")
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        team_id = row[0]
        # If slot is empty, put player there directly; otherwise add to bench (squad screen assigns)
        cur.execute(f"SELECT {role_col} FROM teams WHERE id=?", (team_id,))
        slot = cur.fetchone()
        if not (slot and slot[0]):
            cur.execute(f"UPDATE teams SET {role_col}=? WHERE id=?", (pid, team_id))
        cur.execute(
            "UPDATE players SET team_id=?, is_temp=1, time_in_team=1 WHERE id=?",
            (team_id, pid))
        conn.commit()
        conn.close()
        self._rebuild()

    def _open_loan_out(self, pid, col, role, nick, wage):
        """Popup to pick AI team and duration for outgoing loan."""
        conn = sqlite3.connect(self.db_name)
        gd = conn.execute("SELECT date FROM save WHERE id=1").fetchone()
        game_date_str = gd[0] if gd else str(date.today())
        # Find AI teams with empty slot for this role
        avail = conn.execute(
            f"SELECT id, name, COALESCE(budget,0) FROM teams "
            f"WHERE player!='yes' AND {col} IS NULL "
            f"ORDER BY COALESCE(rating,0) DESC LIMIT 20"
        ).fetchall()
        conn.close()

        p = Popup(title=f'Аренда: {nick}', size_hint=(0.55, 0.75))
        sv = ScrollView()
        gl = GridLayout(cols=1, size_hint_y=None, spacing=4, padding=6)
        gl.bind(minimum_height=gl.setter('height'))

        if not avail:
            gl.add_widget(Label(text='Нет команд с пустым слотом для этой роли.',
                                size_hint_y=None, height=40))
        else:
            gl.add_widget(Label(
                text=f'Выберите команду и срок аренды. Доход: {int(wage*1.5):,}₽ за 3 мес.',
                size_hint_y=None, height=40,
                color=(0.75, 0.75, 1.0, 1), markup=True,
            ))
            for ai_tid, ai_name, ai_budget in avail:
                row = BoxLayout(size_hint_y=None, height=40, spacing=4)
                row.add_widget(Label(text=ai_name.strip(), size_hint_x=0.5,
                                     color=(0.9, 0.9, 0.9, 1), font_size='13sp'))
                for months, label in [(3, '3 мес'), (6, '6 мес')]:
                    fee = int(wage * months * 1.5)
                    b = Button(
                        text=f'{label} (+${fee//1000}k)',
                        size_hint_x=None, width=120, height=36,
                        background_color=(0.15, 0.45, 0.25, 1), background_normal='',
                        font_size='12sp',
                    )
                    def _do_loan(_, _tid=ai_tid, _tname=ai_name, _months=months, _fee=fee):
                        self._exec_loan_out(pid, col, _tid, _tname, _months, _fee,
                                            game_date_str)
                        p.dismiss()
                    b.bind(on_press=_do_loan)
                    row.add_widget(b)
                gl.add_widget(row)

        cancel = Button(text='Отмена', size_hint_y=None, height=44,
                        background_color=(0.5, 0.15, 0.15, 1), background_normal='')
        cancel.bind(on_press=p.dismiss)
        gl.add_widget(cancel)
        sv.add_widget(gl)
        p.content = sv
        p.open()

    def _open_trade(self, pid, col, role, nick, micro, macro):
        """Popup to pick AI player of same role to trade."""
        conn = sqlite3.connect(self.db_name)
        gd = conn.execute("SELECT date FROM save WHERE id=1").fetchone()
        game_date_str = gd[0] if gd else str(date.today())
        my_avg = (micro + macro) // 2
        # Diplomat skill: widens acceptable skill gap for trades
        _dip_bonus = 0
        try:
            from logic.manager_skills import get_skill_level
            _dip_bonus = get_skill_level(self.db_name, 'diplomat') * 10
        except Exception:
            pass

        # Find AI players of same role with skill < player's (AI accepts upgrade)
        candidates = conn.execute(f"""
            SELECT p.id, p.nickname, p.micro_skills, p.macro_skills, t.id, t.name
            FROM players p JOIN teams t ON t.id=p.team_id
            WHERE p.role=? AND t.player!='yes'
              AND (p.micro_skills+p.macro_skills) < ?
            ORDER BY (p.micro_skills+p.macro_skills) DESC LIMIT 20
        """, (role, micro + macro + _dip_bonus)).fetchall()
        conn.close()

        p = Popup(title=f'Обмен: {nick} → ?', size_hint=(0.60, 0.75))
        sv = ScrollView()
        gl = GridLayout(cols=1, size_hint_y=None, spacing=4, padding=6)
        gl.bind(minimum_height=gl.setter('height'))

        if not candidates:
            gl.add_widget(Label(text='Нет AI игроков той же роли со скиллом ниже.',
                                size_hint_y=None, height=40))
        else:
            gl.add_widget(Label(
                text=f'Ваш игрок: {nick} (скилл {my_avg}). Выберите, кого получить:',
                size_hint_y=None, height=36, color=(0.8, 0.8, 1.0, 1),
            ))
            for ai_pid, ai_nick, ai_mi, ai_ma, ai_tid, ai_tname in candidates:
                ai_avg = (ai_mi + ai_ma) // 2
                row = BoxLayout(size_hint_y=None, height=40, spacing=4)
                row.add_widget(Label(
                    text=f'{ai_nick} ({ai_tname.strip()})  скилл {ai_avg}',
                    size_hint_x=0.65, color=(0.85, 0.85, 0.85, 1), font_size='13sp',
                ))
                b = Button(
                    text='Обменять', size_hint_x=None, width=100, height=36,
                    background_color=(0.20, 0.45, 0.18, 1), background_normal='',
                    font_size='13sp',
                )
                def _do_trade(_, _apid=ai_pid, _atid=ai_tid, _aname=ai_tname,
                              _anick=ai_nick):
                    self._exec_trade(pid, col, _apid, _atid, _aname.strip(),
                                     _anick, game_date_str)
                    p.dismiss()
                b.bind(on_press=_do_trade)
                row.add_widget(b)
                gl.add_widget(row)

        cancel = Button(text='Отмена', size_hint_y=None, height=44,
                        background_color=(0.5, 0.15, 0.15, 1), background_normal='')
        cancel.bind(on_press=p.dismiss)
        gl.add_widget(cancel)
        sv.add_widget(gl)
        p.content = sv
        p.open()

    def _exec_trade(self, my_pid, my_col, ai_pid, ai_tid, ai_tname, ai_nick,
                    game_date_str):
        """Swap my player for AI player. AI gets upgrade, we get their slot."""
        conn = sqlite3.connect(self.db_name)
        # Find which slot ai_pid occupies
        ai_col = None
        for col in ('carry', 'mid', 'offlane', 'partial_support', 'full_support'):
            row = conn.execute(f"SELECT {col} FROM teams WHERE id=?", (ai_tid,)).fetchone()
            if row and str(row[0]) == str(ai_pid):
                ai_col = col
                break
        if not ai_col:
            conn.close()
            return

        my_tid = conn.execute("SELECT id FROM teams WHERE player='yes'").fetchone()
        if not my_tid:
            conn.close()
            return
        my_tid = my_tid[0]

        # Swap slots
        conn.execute(f"UPDATE teams SET {my_col}=? WHERE player='yes'", (ai_pid,))
        conn.execute(f"UPDATE teams SET {ai_col}=? WHERE id=?", (my_pid, ai_tid))
        # Update team_id
        conn.execute("UPDATE players SET team_id=? WHERE id=?", (my_tid, ai_pid))
        conn.execute("UPDATE players SET team_id=? WHERE id=?", (ai_tid, my_pid))
        # Cohesion penalty for both teams
        conn.execute(
            "UPDATE teams SET cohesion=MAX(0,COALESCE(cohesion,0)-10) WHERE player='yes'"
        )
        conn.execute(
            "UPDATE teams SET cohesion=MAX(0,COALESCE(cohesion,0)-10) WHERE id=?", (ai_tid,)
        )
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
            (f'Обмен: ваш игрок → {ai_tname}, получен {ai_nick}.',
             game_date_str, 'Трансфер'),
        )
        conn.commit()
        conn.close()
        self._rebuild()

    def _exec_loan_out(self, pid, col, ai_tid, ai_name, months, fee,
                       game_date_str):
        """Send player on loan to AI team."""
        from datetime import timedelta
        conn = sqlite3.connect(self.db_name)
        try:
            gd = date.fromisoformat(game_date_str)
        except Exception:
            gd = date.today()
        loan_until = str(gd + timedelta(days=months * 30))

        # Clear player's slot on player team
        conn.execute(f"UPDATE teams SET {col}=NULL WHERE player='yes'")
        # Assign player to AI team's slot
        conn.execute(f"UPDATE teams SET {col}=? WHERE id=?", (pid, ai_tid))
        # Update player record
        conn.execute(
            "UPDATE players SET team_id=?, loan_team_id=?, loan_until=?, loan_fee=? WHERE id=?",
            (ai_tid, ai_tid, loan_until, fee // months, pid)
        )
        # Pay loan fee upfront
        conn.execute("UPDATE teams SET budget=budget+? WHERE player='yes'", (fee,))
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
            (f'Игрок отдан в аренду в {ai_name} до {loan_until}. Доход: +${fee:,}.',
             game_date_str, 'Трансфер'),
        )
        conn.commit()
        conn.close()
        self._rebuild()

    def _show_player_actions(self, pid, col, nick, fee, role, micro, macro, wage,
                             in_window, game_date_str):
        """Popup with all actions for a roster player — replaces row button clutter."""
        p = Popup(title=f'Действия: {nick}', size_hint=(0.45, 0.55))
        from kivy.uix.gridlayout import GridLayout as _GL
        gl = _GL(cols=1, spacing=6, padding=10, size_hint_y=None)
        gl.bind(minimum_height=gl.setter('height'))

        def _close_do(fn, *args):
            p.dismiss()
            fn(*args)

        def _confirm_then(action_name, bg, fn, *args):
            """Replace popup content with confirmation."""
            from kivy.uix.boxlayout import BoxLayout as _BL
            confirm = _BL(orientation='vertical', padding=8, spacing=6)
            lbl = Label(
                text=f'[b]Подтвердить:[/b] {action_name}?',
                markup=True, color=(0.95, 0.95, 0.95, 1),
                size_hint_y=None, height=50,
                halign='center', valign='middle',
            )
            lbl.bind(size=lbl.setter('text_size'))
            confirm.add_widget(lbl)
            btn_row = BoxLayout(size_hint_y=None, height=48, spacing=6)
            yes = Button(text='Да, подтвердить', background_color=bg, background_normal='')
            no  = Button(text='Отмена', background_color=(0.35, 0.35, 0.35, 1), background_normal='')
            yes.bind(on_press=lambda _: (p.dismiss(), fn(*args)))
            no.bind(on_press=lambda _: p.dismiss())
            btn_row.add_widget(yes)
            btn_row.add_widget(no)
            confirm.add_widget(btn_row)
            p.content = confirm

        # Release
        rel = Button(
            text=f'Отпустить {nick} (бесплатно)',
            size_hint_y=None, height=48,
            background_color=(0.75, 0.20, 0.10, 1), background_normal='',
        )
        rel.bind(on_press=lambda _: _confirm_then(
            f'Отпустить {nick}', (0.75, 0.20, 0.10, 1),
            self._release, pid, col
        ))
        gl.add_widget(rel)

        # Sell (transfer window only)
        sell_clr = (0.55, 0.38, 0.05, 1) if in_window else (0.30, 0.30, 0.30, 1)
        sell = Button(
            text=f'Продать за ${fee:,}' + ('' if in_window else '  [окно закрыто]'),
            size_hint_y=None, height=48,
            background_color=sell_clr, background_normal='',
            disabled=not in_window,
        )
        sell.bind(on_press=lambda _: _confirm_then(
            f'Продать {nick} за ${fee:,}', (0.55, 0.38, 0.05, 1),
            self._sell_player, pid, col, fee
        ))
        gl.add_widget(sell)

        # Loan out
        loan_clr = (0.18, 0.38, 0.62, 1) if in_window else (0.30, 0.30, 0.30, 1)
        loan = Button(
            text='Отдать в аренду' + ('' if in_window else '  [окно закрыто]'),
            size_hint_y=None, height=48,
            background_color=loan_clr, background_normal='',
            disabled=not in_window,
        )
        loan.bind(on_press=lambda _: (
            p.dismiss(),
            self._open_loan_out(pid, col, role, nick, wage)
        ))
        gl.add_widget(loan)

        # Trade
        trade_clr = (0.30, 0.18, 0.52, 1) if in_window else (0.30, 0.30, 0.30, 1)
        trade = Button(
            text='Обмен игрок↔игрок' + ('' if in_window else '  [окно закрыто]'),
            size_hint_y=None, height=48,
            background_color=trade_clr, background_normal='',
            disabled=not in_window,
        )
        trade.bind(on_press=lambda _: (
            p.dismiss(),
            self._open_trade(pid, col, role, nick, micro, macro)
        ))
        gl.add_widget(trade)

        cancel = Button(
            text='Закрыть', size_hint_y=None, height=44,
            background_color=(0.35, 0.35, 0.35, 1), background_normal='',
        )
        cancel.bind(on_press=p.dismiss)
        gl.add_widget(cancel)

        from kivy.uix.scrollview import ScrollView as _SV
        sv = _SV()
        sv.add_widget(gl)
        p.content = sv
        p.open()

    def _on_search(self, inp, text):
        self._search_results.clear_widgets()
        q = text.strip().lower()
        if len(q) < 2:
            return
        conn = sqlite3.connect(self.db_name)
        rows = conn.execute("""
            SELECT p.nickname, p.role, p.micro_skills+p.macro_skills,
                   COALESCE(p.age,22), t.name, p.contract_end,
                   COALESCE(p.wage,0), p.team_id
            FROM players p
            LEFT JOIN teams t ON t.id=p.team_id
            WHERE LOWER(p.nickname) LIKE ? AND p.nickname != ''
            ORDER BY (p.micro_skills+p.macro_skills) DESC LIMIT 6
        """, (f'%{q}%',)).fetchall()
        conn.close()

        _ROLE_S = {'carry': 'C', 'mid': 'M', 'offlane': 'O',
                   'partial_support': 'S4', 'full_support': 'S5'}
        for nick, role, sk, age, team, cend, wage, tid in rows:
            status = 'FA' if not tid else (team.strip()[:14] if team else '?')
            clr = (0.30, 1.00, 0.50, 1) if not tid else (0.85, 0.85, 0.85, 1)
            role_s = _ROLE_S.get(role, '?')
            cend_s = cend[2:7] if cend else '—'
            txt = f'{nick}  [{role_s}]  sk{sk}  {age}л  {status}  кнт:{cend_s}'
            from kivy.uix.label import Label as _SL
            lbl = _SL(text=txt, color=clr, size_hint_y=None, height=18,
                      halign='left', valign='middle', font_size='11sp')
            lbl.bind(size=lbl.setter('text_size'))
            self._search_results.add_widget(lbl)

    def _toggle_watchlist(self, pid):
        conn = sqlite3.connect(self.db_name)
        existing = conn.execute(
            "SELECT id FROM watchlist WHERE player_id=?", (pid,)
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM watchlist WHERE player_id=?", (pid,))
        else:
            conn.execute("INSERT OR IGNORE INTO watchlist (player_id) VALUES (?)", (pid,))
        conn.commit()
        conn.close()
        self._rebuild()

    def _scout_player(self, pid, cost):
        conn = sqlite3.connect(self.db_name)
        budget = conn.execute(
            "SELECT COALESCE(budget,0) FROM teams WHERE player='yes'"
        ).fetchone()
        if not budget or budget[0] < cost:
            conn.close()
            return
        conn.execute("UPDATE teams SET budget=budget-? WHERE player='yes'", (cost,))
        conn.execute("UPDATE players SET scouted=1 WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        self._rebuild()

    # ── left panel: current squad ─────────────────────────────

    def _make_squad_panel(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute(
            "SELECT id, name, budget, carry, mid, offlane, partial_support, full_support, "
            "COALESCE(cohesion, 0) FROM teams WHERE player='yes'"
        )
        team = cur.fetchone()

        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))

        if not team:
            grid.add_widget(_lbl("Команда не найдена."))
            conn.close()
            sv = ScrollView(size_hint=(0.38, 1))
            sv.add_widget(grid)
            return sv

        team_id, team_name, budget, *slot_and_cohesion = team
        cohesion = slot_and_cohesion[-1]
        slot_ids = slot_and_cohesion[:-1]
        budget = budget or 0

        grid.add_widget(_header(f"  {team_name}"))
        grid.add_widget(_lbl(f"  Бюджет: ${budget:,}", color=(0.9, 0.9, 0.4, 1)))

        cohesion_color = (
            (0.2, 0.95, 0.35, 1) if cohesion >= 75 else
            (0.5, 0.95, 0.3, 1)  if cohesion >= 50 else
            (1.0, 0.85, 0.25, 1) if cohesion >= 25 else
            (0.95, 0.35, 0.25, 1)
        )
        grid.add_widget(_lbl(
            f"  Сыгранность: {cohesion}/100  (трансфер: −15)",
            height=28, color=cohesion_color,
        ))

        cur.execute("SELECT COALESCE(SUM(wage),0) FROM players WHERE team_id=?", (team_id,))
        total_wage = cur.fetchone()[0] or 0
        grid.add_widget(_lbl(f"  Зарплатный фонд: ${total_wage:,}/мес", height=30,
                             color=(0.8, 0.8, 0.8, 1)))

        # AI buy offers section
        try:
            offers = cur.execute("""
                SELECT ao.player_id, ao.team_id, ao.fee, p.nickname, t.name
                FROM ai_offers ao
                JOIN players p ON p.id = ao.player_id
                JOIN teams   t ON t.id = ao.team_id
                WHERE p.team_id = ?
            """, (team_id,)).fetchall()
            if offers:
                grid.add_widget(_header("  [+] Входящие предложения", height=34))
                for o_pid, o_tid, o_fee, o_nick, o_buyer in offers:
                    orow = BoxLayout(size_hint_y=None, height=42, spacing=4)
                    orow.add_widget(_lbl(
                        f"  {o_buyer} хочет {o_nick} за ${o_fee:,}",
                        color=(1.0, 0.85, 0.25, 1), height=42,
                    ))
                    acc = Button(text='OK Принять', size_hint=(None, None),
                                 width=90, height=36,
                                 background_color=(0.15, 0.55, 0.20, 1),
                                 background_normal='')
                    dec = Button(text='X  Отказ', size_hint=(None, None),
                                 width=80, height=36,
                                 background_color=(0.55, 0.15, 0.15, 1),
                                 background_normal='')
                    acc.bind(on_press=lambda _, pid=o_pid, tid=o_tid, fee=o_fee,
                             nick=o_nick, buyer=o_buyer:
                             self._accept_ai_offer(pid, tid, fee, nick, buyer))
                    dec.bind(on_press=lambda _, pid=o_pid:
                             self._decline_ai_offer(pid))
                    orow.add_widget(acc)
                    orow.add_widget(dec)
                    grid.add_widget(orow)
        except Exception as _e:
            T.log_err('ai_offers_panel', _e)

        grid.add_widget(_header("  Текущий состав", height=36))

        cur.execute("SELECT date FROM save WHERE id=1")
        date_row = cur.fetchone()
        try:
            today = date.fromisoformat(date_row[0]) if date_row else date.today()
        except Exception:
            today = date.today()
        in_window = is_transfer_window(str(today))

        for col, sid in zip(ROLE_COLS, slot_ids):
            role_label = ROLE_LABELS[col]
            if sid:
                cur.execute(
                    "SELECT id, nickname, micro_skills, macro_skills, wage, "
                    "contract_end, COALESCE(expected_wage,0) "
                    "FROM players WHERE id=?", (int(sid),)
                )
                p = cur.fetchone()
                if p:
                    pid, nick, micro, macro, wage, contract_end, exp_wage = p
                    avg = (micro + macro) // 2

                    expiring = False
                    days_left = None
                    if contract_end:
                        try:
                            cdate = date.fromisoformat(contract_end)
                            days_left = (cdate - today).days
                            expiring = 0 <= days_left <= _RENEWAL_DAYS
                        except Exception:
                            pass

                    exp_txt = f"  до {contract_end}" if contract_end else ""
                    if expiring:
                        exp_txt += f" (осталось {days_left} дн.!)"

                    info_color = (1.0, 0.6, 0.2, 1) if expiring else (0.9, 1.0, 0.85, 1)
                    row = BoxLayout(size_hint_y=None, height=46, spacing=3)
                    info = _lbl(
                        f"  [{role_label}]  {nick}   скилл {avg}   ${wage:,}{exp_txt}",
                        height=46, color=info_color,
                    )

                    fee = _transfer_fee(micro, macro, contract_end or str(today), str(today))

                    # Single "Действия" button replaces 4 cramped buttons
                    act_btn = Button(
                        text='Действия', size_hint=(None, None), width=90, height=38,
                        background_color=(0.25, 0.35, 0.50, 1), background_normal='',
                        font_size='13sp',
                    )
                    def _open_actions(_, _pid=pid, _col=col, _nick=nick, _fee=fee,
                                      _role=col, _mi=micro, _ma=macro, _w=wage):
                        self._show_player_actions(
                            _pid, _col, _nick, _fee, _role, _mi, _ma, _w,
                            in_window, str(today)
                        )
                    act_btn.bind(on_press=_open_actions)

                    row.add_widget(info)
                    row.add_widget(act_btn)

                    if expiring:
                        demanded = max(int(wage * 1.20), exp_wage)
                        demanded = round(demanded / 500) * 500 or demanded
                        for years, label in [(1, '1г'), (2, '2г'), (3, '3г')]:
                            can = budget >= demanded
                            rb = Button(
                                text=label,
                                size_hint=(None, None), width=44, height=38,
                                background_color=(0.1, 0.60, 0.25, 1) if can else (0.3, 0.3, 0.3, 1),
                                background_normal='',
                                disabled=not can,
                                font_size='13sp',
                            )
                            rb.bind(
                                on_press=lambda _, pid=pid, col=col,
                                w=demanded, y=years: self._renew(pid, col, w, y)
                            )
                            row.add_widget(rb)
                        renew_lbl = _lbl(
                            f"  Требует ${demanded:,}/мес",
                            height=46, color=(1.0, 0.85, 0.3, 1),
                        )
                        grid.add_widget(row)
                        grid.add_widget(renew_lbl)
                    else:
                        grid.add_widget(row)
            else:
                grid.add_widget(_lbl(f"  [{role_label}]  — свободно —",
                                     color=(0.6, 0.6, 0.6, 1)))

        # ── Bench ────────────────────────────────────────────────
        active_ids = set(s for s in slot_ids if s)
        ph = ','.join('?' * len(active_ids)) if active_ids else '0'
        cur.execute(
            f"SELECT id, nickname, role, micro_skills, macro_skills, wage, contract_end "
            f"FROM players WHERE team_id=? AND id NOT IN ({ph}) ORDER BY role",
            [team_id] + list(active_ids),
        )
        bench_players = cur.fetchall()
        conn.close()

        conn.close()

        if bench_players:
            grid.add_widget(_header("  Скамейка", height=32))
            for bpid, bnick, brole, bmic, bmac, bwage, bcend in bench_players:
                bmic = bmic or 0; bmac = bmac or 0; bwage = bwage or 0
                bavg = (bmic + bmac) // 2
                bfee = _transfer_fee(bmic, bmac, bcend or str(today), str(today))
                role_lbl = ROLE_LABELS.get(brole, brole or '?')
                brow = BoxLayout(size_hint_y=None, height=46, spacing=3)
                brow.add_widget(_lbl(
                    f"  [{role_lbl}]  {bnick}   скилл {bavg}   ${bwage:,}/мес",
                    height=46, color=(0.85, 0.85, 0.55, 1),
                ))
                brel = Button(
                    text='Отпустить', size_hint=(None, None), width=84, height=38,
                    background_color=(0.8, 0.3, 0.1, 1), background_normal='',
                )
                brel.bind(on_press=lambda _, p=bpid: self._release(p, None))
                brow.add_widget(brel)
                bsell = Button(
                    text=f'Продать\n${bfee//1000}k', size_hint=(None, None),
                    width=80, height=38,
                    background_color=(0.55, 0.35, 0.05, 1) if in_window else (0.3, 0.3, 0.3, 1),
                    background_normal='', font_size='12sp',
                )
                if in_window:
                    bsell.bind(on_press=lambda _, p=bpid, f=bfee, r=brole:
                               self._sell_player(p, None, f, player_role=r))
                else:
                    bsell.bind(on_press=lambda _: _show_window_popup())
                brow.add_widget(bsell)
                grid.add_widget(brow)

        sv = ScrollView(size_hint=(0.38, 1))
        sv.add_widget(grid)
        return sv

    # ── right panel: free agents ──────────────────────────────

    def _make_free_agents_panel(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute(
            "SELECT id, budget, carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE player='yes'"
        )
        team = cur.fetchone()
        if team:
            team_id, budget, *slot_ids = team
            budget = budget or 0
            filled = {ROLE_COLS[i]: slot_ids[i] for i in range(5)}
        else:
            team_id, budget, filled = None, 0, {}

        # game date for window + pre-contract checks
        gd_row = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
        game_date_str = gd_row[0] if gd_row else str(date.today())
        in_window = is_transfer_window(game_date_str)

        rf = self._fa_role  # active role filter ('все' or specific)
        role_cond   = f"AND p.role='{rf}'" if rf != 'все' else ''
        role_cond_p = f"AND role='{rf}'"   if rf != 'все' else ''

        game_d = date.fromisoformat(game_date_str)
        cutoff = str(game_d + timedelta(days=180))
        cur.execute(f"""
            SELECT p.id, p.nickname, p.name, p.surname, p.role,
                   p.micro_skills, p.macro_skills, p.contract_end,
                   COALESCE(p.expected_wage, p.wage, 5000), COALESCE(p.age,22),
                   t.name
            FROM players p JOIN teams t ON p.team_id=t.id
            WHERE p.team_id!=0 AND t.player!='yes'
              AND p.contract_end IS NOT NULL AND p.contract_end<=?
              AND COALESCE(p.pre_contract_team_id,0)=0
              {role_cond}
            ORDER BY (p.micro_skills+p.macro_skills) DESC
            LIMIT 15
        """, (cutoff,))
        pre_candidates = cur.fetchall()

        buyout_candidates = []
        if in_window:
            cur.execute(f"""
                SELECT p.id, p.nickname, p.name, p.surname, p.role,
                       p.micro_skills, p.macro_skills, p.soft_skills,
                       p.contract_end, COALESCE(p.expected_wage, p.wage, 5000),
                       COALESCE(p.age,22), t.id, t.name
                FROM players p JOIN teams t ON p.team_id=t.id
                WHERE p.team_id!=0 AND t.player!='yes'
                  AND p.contract_end IS NOT NULL
                  AND COALESCE(p.pre_contract_team_id,0)=0
                  {role_cond}
                ORDER BY (p.micro_skills+p.macro_skills) DESC
                LIMIT 20
            """)
            buyout_candidates = cur.fetchall()

        min_skill = self._fa_min_skill
        max_wage  = self._fa_max_wage
        skill_cond = f"AND (micro_skills+macro_skills)/2 >= {min_skill}" if min_skill > 0 else ''
        wage_cond  = f"AND COALESCE(expected_wage,0) <= {max_wage}" if max_wage < 99999 else ''
        cur.execute(f"""
            SELECT id, name, surname, nickname, role, micro_skills, macro_skills,
                   expected_wage, COALESCE(age, 22), COALESCE(scouted, 0),
                   COALESCE(psychotype,'team_player')
            FROM players
            WHERE team_id=0 AND role IS NOT NULL AND nickname != ''
              {role_cond_p} {skill_cond} {wage_cond}
            ORDER BY (micro_skills+macro_skills) DESC
            LIMIT 40
        """)
        free_agents = cur.fetchall()
        wl_ids = {r[0] for r in cur.execute("SELECT player_id FROM watchlist").fetchall()}
        wl_rows = cur.execute("""
            SELECT w.player_id, p.nickname, p.role,
                   COALESCE(p.micro_skills,0), COALESCE(p.macro_skills,0),
                   COALESCE(p.expected_wage,0), p.team_id,
                   COALESCE(t.name, 'Свободный агент')
            FROM watchlist w
            JOIN players p ON p.id = w.player_id
            LEFT JOIN teams t ON t.id = p.team_id AND p.team_id != 0
            ORDER BY (p.micro_skills+p.macro_skills) DESC
        """).fetchall()
        conn.close()

        # ── outer: tab bar + scroll ────────────────────────────
        outer = BoxLayout(orientation='vertical', size_hint=(0.62, 1))
        tab_bar = BoxLayout(size_hint_y=None, height=34, spacing=2)
        for rk, rl in _ROLE_TABS:
            active = rk == self._fa_role
            bc = _TAB_COLORS.get(rk, (0.3, 0.3, 0.45, 1))
            btn = Button(
                text=rl, background_normal='', font_size='13sp',
                background_color=(
                    (min(1, bc[0]+0.2), min(1, bc[1]+0.2), min(1, bc[2]+0.2), 1)
                    if active else bc
                ),
                bold=active,
            )
            btn.bind(on_press=lambda _, r=rk: self._set_fa_role(r))
            tab_bar.add_widget(btn)
        outer.add_widget(tab_bar)

        # Skill / wage filter bar
        from kivy.uix.textinput import TextInput
        filter_bar = BoxLayout(size_hint_y=None, height=34, spacing=4)
        filter_bar.add_widget(Label(text='Мин.скилл:', size_hint_x=None, width=70,
                                    color=(0.7, 0.7, 0.7, 1), font_size='13sp'))
        skill_inp = TextInput(
            text='' if self._fa_min_skill == 0 else str(self._fa_min_skill),
            hint_text='0', multiline=False, size_hint_x=0.12,
            input_filter='int', font_size='14sp',
        )
        filter_bar.add_widget(skill_inp)
        filter_bar.add_widget(Label(text='Макс.зарп.:', size_hint_x=None, width=80,
                                    color=(0.7, 0.7, 0.7, 1), font_size='13sp'))
        wage_inp = TextInput(
            text='' if self._fa_max_wage == 99999 else str(self._fa_max_wage),
            hint_text='любая', multiline=False, size_hint_x=0.14,
            input_filter='int', font_size='14sp',
        )
        filter_bar.add_widget(wage_inp)
        apply_btn = Button(text='Применить', size_hint_x=0.16,
                           background_color=(0.22, 0.45, 0.22, 1), background_normal='',
                           font_size='13sp')
        reset_btn = Button(text='Сброс', size_hint_x=0.10,
                           background_color=(0.40, 0.20, 0.20, 1), background_normal='',
                           font_size='13sp')

        def _apply_filter(_):
            try:
                self._fa_min_skill = int(skill_inp.text) if skill_inp.text.strip() else 0
            except Exception:
                self._fa_min_skill = 0
            try:
                self._fa_max_wage = int(wage_inp.text) if wage_inp.text.strip() else 99999
            except Exception:
                self._fa_max_wage = 99999
            self._rebuild()

        def _reset_filter(_):
            self._fa_min_skill = 0
            self._fa_max_wage  = 99999
            self._rebuild()

        apply_btn.bind(on_press=_apply_filter)
        reset_btn.bind(on_press=_reset_filter)
        filter_bar.add_widget(apply_btn)
        filter_bar.add_widget(reset_btn)
        outer.add_widget(filter_bar)

        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))
        lbl_role = ROLE_LABELS.get(rf, rf) if rf != 'все' else 'все роли'
        grid.add_widget(_header(f"  Свободные агенты  [{lbl_role}]"))

        _PSYCHO_CHIP = {
            'leader':      ('[Лид]', (1.00, 0.85, 0.20, 1)),
            'solo_carry':  ('[СК]', (0.40, 0.80, 1.00, 1)),
            'team_player': ('[Кмд]', (0.30, 0.95, 0.45, 1)),
            'wildcard':    ('[WC]', (1.00, 0.55, 0.20, 1)),
        }
        if not free_agents:
            grid.add_widget(_lbl("  Нет свободных игроков.", color=(0.7, 0.7, 0.7, 1)))
        else:
            _FA_EVEN = (0.09, 0.11, 0.16, 1)
            _FA_ODD  = (0.07, 0.08, 0.12, 1)
            for _fa_idx, (pid, fname, lname, nick, role, micro, macro, exp_wage, age, scouted, psychotype) in enumerate(free_agents):
                exp_wage = exp_wage or 0
                avg = (micro + macro) // 2
                scout_cost = max(3000, min(25000, avg * 200))

                can_sign = (
                    team_id is not None
                    and not filled.get(role)
                    and budget >= int(exp_wage * 0.80)
                )
                color = (1, 1, 1, 1) if can_sign else (0.55, 0.55, 0.55, 1)

                # Scout skill: free reveal
                _scout_reveal = False
                try:
                    from logic.manager_skills import has_skill
                    if not scouted and has_skill(self.db_name, 'scout'):
                        _scout_reveal = True
                except Exception:
                    pass

                _fa_bg = _FA_EVEN if _fa_idx % 2 == 0 else _FA_ODD
                row = BoxLayout(size_hint_y=None, height=46, spacing=3)
                import sqlite3 as _sq3
                with row.canvas.before:
                    from kivy.graphics import Color as _GCfa, Rectangle as _GRfa
                    _GCfa(*_fa_bg)
                    _fa_r = _GRfa()
                _fa_r_ref = _fa_r
                row.bind(pos=lambda w, _, _r=_fa_r_ref: setattr(_r, 'pos', w.pos),
                         size=lambda w, _, _r=_fa_r_ref: setattr(_r, 'size', w.size))
                if scouted or _scout_reveal:
                    skill_txt = f"скилл {avg}" + (' (ск)' if _scout_reveal else '')
                    pchip, pclr = _PSYCHO_CHIP.get(psychotype, ('', None))
                else:
                    skill_txt = "скилл ??"
                    pchip, pclr = '', None
                info = _lbl(
                    f"  {nick} ({fname} {lname.strip()})  "
                    f"{skill_txt}  возр. {age}  от ${exp_wage:,}/мес"
                    + (f'  {pchip}' if pchip else ''),
                    height=46, color=color,
                )
                row.add_widget(info)

                # Watchlist toggle button (always visible)
                in_wl = pid in wl_ids
                wl_btn = Button(
                    text='Вотч+' if in_wl else 'Вотч',
                    size_hint=(None, None), width=40, height=40,
                    background_color=(0.10, 0.35, 0.55, 1) if in_wl else (0.22, 0.22, 0.30, 1),
                    background_normal='', font_size='14sp',
                )
                wl_btn.bind(on_press=lambda _, _pid=pid: self._toggle_watchlist(_pid))
                row.add_widget(wl_btn)

                if not scouted:
                    can_scout = budget >= scout_cost
                    sc_btn = Button(
                        text=f'${scout_cost//1000}k',
                        size_hint=(None, None), width=72, height=40,
                        background_color=(0.30, 0.20, 0.55, 1) if can_scout else (0.28, 0.28, 0.28, 1),
                        background_normal='', font_size='13sp',
                        disabled=not can_scout,
                    )
                    sc_btn.bind(on_press=lambda _, _pid=pid, _cost=scout_cost:
                                self._scout_player(_pid, _cost))
                    row.add_widget(sc_btn)
                else:
                    # Торговаться buttons
                    for years, label in [(1, '1г'), (2, '2г'), (3, '3г')]:
                        btn = Button(
                            text=label,
                            size_hint=(None, None), width=48, height=40,
                            background_color=(0.15, 0.50, 0.22, 1) if can_sign else (0.28, 0.28, 0.28, 1),
                            background_normal='',
                            disabled=not can_sign,
                            font_size='14sp',
                        )
                        btn.bind(
                            on_press=lambda _, pid=pid, role=role, w=exp_wage, y=years:
                                NegotiationPopup(
                                    db_name=self.db_name,
                                    pid=pid, role=role,
                                    demanded_wage=w, years=y,
                                    on_accepted=self._rebuild,
                                ).open()
                        )
                        row.add_widget(btn)

                grid.add_widget(row)

        # ── watchlist section ─────────────────────────────────
        if wl_rows:
            grid.add_widget(_header('  Список наблюдения'))
            for wpid, wnick, wrole, wmi, wma, wwage, wtid, wteam in wl_rows:
                wavg = (wmi + wma) // 2
                status = 'FA' if not wtid else wteam
                wrow = BoxLayout(size_hint_y=None, height=36, spacing=3)
                winfo = _lbl(
                    f'  {wnick}  ({ROLE_LABELS.get(wrole,wrole)})  '
                    f'скилл {wavg}  ${wwage:,}/мес  [{status}]',
                    height=36,
                    color=(0.75, 0.90, 1.00, 1) if not wtid else (0.70, 0.70, 0.70, 1),
                )
                wrow.add_widget(winfo)
                rm_btn = Button(
                    text='X', size_hint=(None, None), width=32, height=32,
                    background_color=(0.50, 0.15, 0.15, 1), background_normal='',
                    font_size='14sp',
                )
                rm_btn.bind(on_press=lambda _, _pid=wpid: self._toggle_watchlist(_pid))
                wrow.add_widget(rm_btn)
                grid.add_widget(wrow)

        # ── window banner ──────────────────────────────────────
        next_window = 'Август' if game_d.month < 8 else 'Январь'
        if in_window:
            banner_txt = f'ТРАНСФЕРНОЕ ОКНО ОТКРЫТО ({game_d.strftime("%B").capitalize()})'
            banner_color = _GREEN
        else:
            banner_txt = f'Трансферное окно закрыто  (следующее: {next_window})'
            banner_color = (0.7, 0.3, 0.2, 1)
        grid.add_widget(_lbl(banner_txt, height=28, color=banner_color, bold=True))

        # ── pre-contract section ────────────────────────────────
        grid.add_widget(_header("  Пре-контракт  (≤ 6 мес. до конца)"))
        if not pre_candidates:
            grid.add_widget(_lbl("  Нет кандидатов.", color=_DIM))
        else:
            for pid, nick, fname, lname, role, micro, macro, cend, exp_wage, age, ai_team in pre_candidates:
                days_left = max(0, (date.fromisoformat(cend) - game_d).days)
                avg = ((micro or 0) + (macro or 0)) // 2
                slot_free = not filled.get(role)
                can_pre   = team_id is not None  # always allow if team exists
                # color: white if slot free, yellow warning if slot occupied
                color = _WHITE if slot_free else _YELLOW
                row = BoxLayout(size_hint_y=None, height=44, spacing=4)
                slot_note = '' if slot_free else ' [!] слот занят'
                row.add_widget(_lbl(
                    f"  {nick}  [{ROLE_LABELS.get(role,role)}]  скилл {avg}"
                    f"  возр.{age}  {ai_team}  —  {days_left} дн.{slot_note}",
                    height=44, color=color,
                ))
                btn = Button(
                    text='Договориться', size_hint=(None, None), width=110, height=38,
                    background_color=(0.20, 0.40, 0.75, 1) if can_pre else (0.3, 0.3, 0.3, 1),
                    background_normal='', disabled=not can_pre, font_size='13sp',
                )
                btn.bind(on_press=lambda _, p=pid, n=nick: self._pre_contract(p, n))
                row.add_widget(btn)
                grid.add_widget(row)

        # ── buyout section (transfer window only) ──────────────
        grid.add_widget(_header(
            f"  {'Выкуп игроков (окно открыто)' if in_window else 'Выкуп — только в трансферное окно'}"
        ))
        if not in_window:
            grid.add_widget(_lbl(f"  Откроется в {next_window}.", color=_DIM))
        elif not buyout_candidates:
            grid.add_widget(_lbl("  Нет доступных игроков.", color=_DIM))
        else:
            for pid, nick, fname, lname, role, micro, macro, soft, cend, exp_wage, age, ai_tid, ai_team in buyout_candidates:
                fee = _transfer_fee(micro, macro, cend, game_date_str)
                avg = ((micro or 0) + (macro or 0)) // 2
                days_left = max(0, (date.fromisoformat(cend) - game_d).days)
                can_buy = (
                    team_id is not None
                    and not filled.get(role)
                    and budget >= fee + exp_wage
                )
                color = _WHITE if can_buy else _DIM
                row = BoxLayout(size_hint_y=None, height=44, spacing=4)
                row.add_widget(_lbl(
                    f"  {nick}  [{ROLE_LABELS.get(role,role)}]  скилл {avg}"
                    f"  возр.{age}  {ai_team}  контракт:{days_left}дн  зарп:${exp_wage:,}",
                    height=44, color=color,
                ))
                btn = Button(
                    text=f'${fee:,}', size_hint=(None, None), width=88, height=38,
                    background_color=(0.65, 0.35, 0.05, 1) if can_buy else (0.3, 0.3, 0.3, 1),
                    background_normal='', disabled=not can_buy, font_size='13sp',
                )
                btn.bind(on_press=lambda _, p=pid, r=role, f=fee, t=ai_tid, w=exp_wage:
                         self._buyout(p, r, f, t, w))
                row.add_widget(btn)
                grid.add_widget(row)

        # ── temp rental section ───────────────────────────────
        if team_id:
            grid.add_widget(_header('  Временная аренда  (1 турнир, бесплатно)'))
            cur2 = sqlite3.connect(self.db_name).cursor()
            cur2.execute(f"""
                SELECT id, nickname, role,
                       COALESCE(micro_skills,0), COALESCE(macro_skills,0),
                       COALESCE(age,22), COALESCE(scouted,0)
                FROM players
                WHERE team_id=0 AND role IS NOT NULL AND nickname != ''
                  {role_cond_p}
                ORDER BY micro_skills+macro_skills DESC LIMIT 15
            """)
            temps = cur2.fetchall()
            cur2.connection.close()

            for pid, nick, role, micro, macro, age, scouted in temps:
                already_temp = filled.get(role)
                avg = (micro + macro) // 2
                skill_txt = f'скилл {avg}' if scouted else 'скилл ??'
                row = BoxLayout(size_hint_y=None, height=40, spacing=3)
                info = _lbl(
                    f'  {nick}  ({ROLE_LABELS.get(role, role)})  '
                    f'{skill_txt}  возр. {age}',
                    height=40,
                    color=(0.55, 0.55, 0.55, 1) if already_temp else (1, 1, 1, 1),
                )
                row.add_widget(info)
                if not already_temp:
                    btn = Button(
                        text='Арендовать',
                        size_hint=(None, None), width=100, height=34,
                        background_color=(0.22, 0.45, 0.55, 1),
                        background_normal='', font_size='13sp',
                    )
                    btn.bind(on_press=lambda _, _pid=pid, _role=role:
                             self._rent_temp(_pid, _role))
                    row.add_widget(btn)
                grid.add_widget(row)

        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(grid)
        outer.add_widget(sv)
        return outer

    # ── actions ───────────────────────────────────────────────

    def _sell_player(self, pid, role_col, fee, player_role=None):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()

        cur.execute("SELECT nickname, micro_skills, macro_skills, role FROM players WHERE id=?", (pid,))
        p_row = cur.fetchone()
        nick = p_row[0] if p_row else '?'
        seller_skill = (p_row[1] or 0) + (p_row[2] or 0) if p_row else 0
        # For bench players role_col is None — use the player's own role for buyer search
        buy_role = role_col or player_role or (p_row[3] if p_row else None)

        if not buy_role:
            conn.close()
            Popup(
                content=Label(text='Роль игрока не определена.', halign='center'),
                size_hint=(0.45, 0.22),
            ).open()
            return

        # 1) Prefer buyer with empty slot
        cur.execute(f"""
            SELECT id, name, budget FROM teams
            WHERE player != 'yes'
              AND {buy_role} IS NULL
              AND COALESCE(budget, 0) >= ?
            ORDER BY RANDOM() LIMIT 1
        """, (fee,))
        buyer = cur.fetchone()
        displaced_pid = None  # player to release if slot is occupied

        if not buyer:
            # 2) Fallback: buyer with occupied slot but weaker player there
            cur.execute(f"""
                SELECT t.id, t.name, t.budget, t.{buy_role}
                FROM teams t
                JOIN players p ON p.id = t.{buy_role}
                WHERE t.player != 'yes'
                  AND COALESCE(t.budget, 0) >= ?
                  AND (COALESCE(p.micro_skills,0) + COALESCE(p.macro_skills,0)) < ?
                ORDER BY RANDOM() LIMIT 1
            """, (fee, seller_skill))
            row = cur.fetchone()
            if row:
                buyer = (row[0], row[1], row[2])
                displaced_pid = row[3]

        conn.close()

        if not buyer:
            Popup(
                content=Label(
                    text=f'Нет покупателей на {nick}\nза ${fee:,}.',
                    markup=True, halign='center',
                ),
                size_hint=(0.48, 0.26),
            ).open()
            return

        buyer_id, buyer_name, _ = buyer

        # Confirm popup
        def _do_sell(_):
            confirm_popup.dismiss()
            c = sqlite3.connect(self.db_name)
            cx = c.cursor()
            cx.execute("SELECT id FROM teams WHERE player='yes'")
            my = (cx.fetchone() or (None,))[0]
            if not my:
                c.close(); return
            # Move money
            cx.execute("UPDATE teams SET budget=budget+? WHERE id=?", (fee, my))
            cx.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (fee, buyer_id))
            # Clear our slot (bench players have no slot to clear)
            if role_col:
                cx.execute(f"UPDATE teams SET {role_col}=NULL WHERE id=?", (my,))
            # Release displaced AI player if slot was occupied
            if displaced_pid:
                exp_wage_row = cx.execute(
                    "SELECT COALESCE(expected_wage, COALESCE(wage,0)*1.1) FROM players WHERE id=?",
                    (displaced_pid,)
                ).fetchone()
                exp_w = int(exp_wage_row[0]) if exp_wage_row else 5000
                cx.execute(f"UPDATE teams SET {buy_role}=NULL WHERE id=?", (buyer_id,))
                cx.execute(
                    "UPDATE players SET team_id=0, wage=0, expected_wage=? WHERE id=?",
                    (exp_w, displaced_pid),
                )
            # Set buyer slot
            cx.execute(f"UPDATE teams SET {buy_role}=? WHERE id=?", (pid, buyer_id))
            # Update player
            gd = cx.execute("SELECT date FROM save WHERE id=1").fetchone()
            gd = gd[0] if gd else str(date.today())
            cend = str(date.fromisoformat(gd) + timedelta(days=365))
            cx.execute("SELECT COALESCE(expected_wage,wage,5000) FROM players WHERE id=?", (pid,))
            new_wage = (cx.fetchone() or (5000,))[0]
            cx.execute(
                "UPDATE players SET team_id=?, wage=?, contract_end=?, "
                "time_in_team=1, poaching_team_id=NULL, pre_contract_team_id=NULL, "
                "renewal_notified=0 WHERE id=?",
                (buyer_id, new_wage, cend, pid),
            )
            _is_youth = (cx.execute(
                "SELECT COALESCE(is_youth,0) FROM players WHERE id=?", (pid,)
            ).fetchone() or (0,))[0]
            if not _is_youth:
                cx.execute(
                    "UPDATE teams SET cohesion=MAX(0,COALESCE(cohesion,0)-15) WHERE id=?",
                    (my,),
                )
            # Clear conflict_targets if this player was a target
            ct_row = cx.execute(
                "SELECT conflict_targets FROM teams WHERE id=?", (my,)
            ).fetchone()
            if ct_row and ct_row[0]:
                remaining = [x for x in ct_row[0].split(',')
                             if x.strip().isdigit() and int(x) != pid]
                cx.execute(
                    "UPDATE teams SET conflict_targets=? WHERE id=?",
                    (','.join(remaining) if remaining else None, my),
                )
            c.execute(
                "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
                (f"{nick} продан в {buyer_name} за ${fee:,}.", 'Трансфер'),
            )
            c.commit(); c.close()
            self._rebuild()

        content = BoxLayout(orientation='vertical', padding=10, spacing=8)
        content.add_widget(Label(
            text=f'[b]{buyer_name}[/b] готов купить [b]{nick}[/b]\nза [b]${fee:,}[/b].',
            markup=True, halign='center',
        ))
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=6)
        yes = Button(text='Продать', background_color=(0.15, 0.55, 0.20, 1),
                     background_normal='')
        no  = Button(text='Отмена',  background_color=(0.55, 0.15, 0.15, 1),
                     background_normal='')
        btn_row.add_widget(yes)
        btn_row.add_widget(no)
        content.add_widget(btn_row)

        confirm_popup = Popup(content=content, title='', size_hint=(0.52, 0.32),
                              auto_dismiss=False)
        yes.bind(on_press=_do_sell)
        no.bind(on_press=confirm_popup.dismiss)
        confirm_popup.open()

    def _accept_ai_offer(self, pid, buyer_id, fee, nick, buyer_name):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        cur.execute("SELECT id FROM teams WHERE player='yes'")
        my = (cur.fetchone() or (None,))[0]
        if not my:
            conn.close(); return
        # Find which role slot this player occupies
        cur.execute(
            "SELECT carry,mid,offlane,partial_support,full_support FROM teams WHERE id=?", (my,)
        )
        slots = cur.fetchone() or ()
        role_col = None
        for col, sid in zip(('carry','mid','offlane','partial_support','full_support'), slots):
            if sid is not None and int(sid) == pid:
                role_col = col; break
        if not role_col:
            conn.close(); return
        # Execute transfer
        cur.execute("UPDATE teams SET budget=budget+? WHERE id=?", (fee, my))
        cur.execute("UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?", (fee, buyer_id))
        cur.execute(f"UPDATE teams SET {role_col}=NULL WHERE id=?", (my,))
        cur.execute(f"UPDATE teams SET {role_col}=? WHERE id=?", (pid, buyer_id))
        gd = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
        gd_str = gd[0] if gd else str(date.today())
        cend = str(date.fromisoformat(gd_str) + timedelta(days=365))
        new_wage = (cur.execute(
            "SELECT COALESCE(expected_wage,wage,5000) FROM players WHERE id=?",(pid,)
        ).fetchone() or (5000,))[0]
        cur.execute(
            "UPDATE players SET team_id=?, wage=?, contract_end=?, "
            "time_in_team=1, poaching_team_id=NULL, pre_contract_team_id=NULL, "
            "wants_to_leave=0, renewal_notified=0 WHERE id=?",
            (buyer_id, new_wage, cend, pid),
        )
        _is_youth = (cur.execute(
            "SELECT COALESCE(is_youth,0) FROM players WHERE id=?", (pid,)
        ).fetchone() or (0,))[0]
        if not _is_youth:
            cur.execute("UPDATE teams SET cohesion=MAX(0,COALESCE(cohesion,0)-15) WHERE id=?", (my,))
        cur.execute("DELETE FROM ai_offers WHERE player_id=?", (pid,))
        # Clear conflict_targets if this player was a target
        ct_row = cur.execute(
            "SELECT conflict_targets FROM teams WHERE id=?", (my,)
        ).fetchone()
        if ct_row and ct_row[0]:
            remaining = [x for x in ct_row[0].split(',')
                         if x.strip().isdigit() and int(x) != pid]
            cur.execute(
                "UPDATE teams SET conflict_targets=? WHERE id=?",
                (','.join(remaining) if remaining else None, my),
            )
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
            (f"{nick} продан в {buyer_name} за ${fee:,}.", 'Трансфер'),
        )
        conn.commit(); conn.close()
        self._rebuild()

    def _decline_ai_offer(self, pid):
        conn = sqlite3.connect(self.db_name)
        conn.execute("DELETE FROM ai_offers WHERE player_id=?", (pid,))
        conn.commit(); conn.close()
        self._rebuild()

    def _pre_contract(self, pid, nick):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        cur.execute("SELECT id FROM teams WHERE player='yes'")
        row = cur.fetchone()
        if not row:
            conn.close(); return
        my_id = row[0]
        cur.execute("UPDATE players SET pre_contract_team_id=? WHERE id=?", (my_id, pid))
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
            (f"Пре-контракт подписан с {nick}. Перейдёт по истечении контракта.", 'Трансфер'),
        )
        conn.commit()
        conn.close()
        self._rebuild()

    def _buyout(self, pid, role, fee, ai_team_id, demanded_wage):
        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        cur.execute("SELECT id, budget FROM teams WHERE player='yes'")
        my = cur.fetchone()
        if not my:
            conn.close(); return
        my_id, my_budget = my
        my_budget = my_budget or 0

        if my_budget < fee + demanded_wage:
            conn.close()
            Popup(content=Label(text='Недостаточно бюджета.', halign='center'),
                  size_hint=(0.4, 0.22)).open()
            return

        cur.execute(f"SELECT {role} FROM teams WHERE id=?", (my_id,))
        slot = cur.fetchone()
        if slot and slot[0]:
            conn.close()
            Popup(content=Label(text='Слот уже занят.', halign='center'),
                  size_hint=(0.4, 0.22)).open()
            return

        gd = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
        gd = gd[0] if gd else str(date.today())
        contract_end = str(date.fromisoformat(gd) + timedelta(days=365))

        cur.execute("UPDATE teams SET budget=budget-? WHERE id=?", (fee, my_id))
        cur.execute("UPDATE teams SET budget=budget+? WHERE id=?", (fee, ai_team_id))
        cur.execute("""UPDATE teams SET
            carry=CASE WHEN carry=? THEN NULL ELSE carry END,
            mid=CASE WHEN mid=? THEN NULL ELSE mid END,
            offlane=CASE WHEN offlane=? THEN NULL ELSE offlane END,
            partial_support=CASE WHEN partial_support=? THEN NULL ELSE partial_support END,
            full_support=CASE WHEN full_support=? THEN NULL ELSE full_support END
        """, (pid,)*5)
        cur.execute(f"UPDATE teams SET {role}=? WHERE id=?", (pid, my_id))
        cur.execute(
            "UPDATE players SET team_id=?, wage=?, contract_end=?, "
            "time_in_team=1, poaching_team_id=NULL, pre_contract_team_id=NULL, "
            "renewal_notified=0 WHERE id=?",
            (my_id, demanded_wage, contract_end, pid),
        )
        nick  = (cur.execute("SELECT nickname FROM players WHERE id=?", (pid,)).fetchone() or ('?',))[0]
        aname = (cur.execute("SELECT name FROM teams WHERE id=?", (ai_team_id,)).fetchone() or ('?',))[0]
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
            (f"Выкуплен {nick} из {aname} за ${fee:,}. Контракт: ${demanded_wage:,}/мес, 1 год.",
             'Трансфер'),
        )
        conn.commit()
        conn.close()
        self._rebuild()

    def _release(self, player_id, role_col):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute(
            "SELECT name, nickname, micro_skills, macro_skills, wage FROM players WHERE id=?",
            (player_id,),
        )
        p = cur.fetchone()
        nick = p[1] if p else str(player_id)

        cur.execute("SELECT id, name FROM teams WHERE player='yes'")
        team = cur.fetchone()
        if not team:
            conn.close()
            return
        team_id, team_name = team

        if p:
            _, _, micro, macro, last_wage = p
            avg = ((micro or 10) + (macro or 10)) // 2
            expected = max(avg * 180, int((last_wage or 0) * 0.85))
        else:
            expected = 0

        if role_col:
            cur.execute(f"UPDATE teams SET {role_col}=NULL WHERE id=?", (team_id,))
        cur.execute(
            "UPDATE players SET team_id=0, wage=0, expected_wage=?, wants_to_leave=0 WHERE id=?",
            (expected, player_id),
        )
        # Clear conflict_targets if this player was a target
        ct_row = cur.execute(
            "SELECT conflict_targets FROM teams WHERE id=?", (team_id,)
        ).fetchone()
        if ct_row and ct_row[0]:
            remaining = [x for x in ct_row[0].split(',')
                         if x.strip().isdigit() and int(x) != player_id]
            cur.execute(
                "UPDATE teams SET conflict_targets=? WHERE id=?",
                (','.join(remaining) if remaining else None, team_id),
            )
        # Cohesion penalty (skip if releasing a conflict target or youth player)
        is_conflict_target = ct_row and ct_row[0] and str(player_id) in ct_row[0].split(',')
        _is_youth = (cur.execute(
            "SELECT COALESCE(is_youth,0) FROM players WHERE id=?", (player_id,)
        ).fetchone() or (0,))[0]
        if not is_conflict_target and not _is_youth:
            cur.execute(
                "UPDATE teams SET cohesion=MAX(0, COALESCE(cohesion, 0)-15) WHERE id=?",
                (team_id,),
            )
        conn.commit()
        conn.close()

        _add_message(self.db_name, f"{nick} отпущен из {team_name}.")
        self._rebuild()

    def _renew(self, player_id, role_col, wage, duration_years=1):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute("SELECT id, name, budget FROM teams WHERE player='yes'")
        team = cur.fetchone()
        if not team:
            conn.close()
            return
        team_id, team_name, budget = team
        budget = budget or 0
        if budget < wage:
            conn.close()
            return

        cur.execute("SELECT date FROM save WHERE id=1")
        date_row = cur.fetchone()
        try:
            game_date = date.fromisoformat(date_row[0]) if date_row else date.today()
            contract_end = str(game_date + timedelta(days=365 * duration_years))
        except Exception:
            contract_end = None

        cur.execute(
            "UPDATE players SET wage=?, contract_end=?, poaching_team_id=NULL WHERE id=?",
            (wage, contract_end, player_id),
        )
        conn.commit()
        conn.close()

        yr_word = {1: 'год', 2: 'года', 3: 'года'}.get(duration_years, 'лет')
        nick_conn = sqlite3.connect(self.db_name)
        nc = nick_conn.cursor()
        nc.execute("SELECT nickname FROM players WHERE id=?", (player_id,))
        nr = nc.fetchone()
        nick = nr[0] if nr else str(player_id)
        nick_conn.close()

        _add_message(
            self.db_name,
            f"Контракт {nick} продлён на {duration_years} {yr_word} до {contract_end} "
            f"за ${wage:,}/мес.",
        )
        self._rebuild()

    def _sign(self, player_id, role, wage, duration_years=1):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute("SELECT id, name, budget FROM teams WHERE player='yes'")
        team = cur.fetchone()
        if not team:
            conn.close()
            return
        team_id, team_name, budget = team
        budget = budget or 0

        cur.execute(f"SELECT {role} FROM teams WHERE id=?", (team_id,))
        slot = cur.fetchone()[0]
        if slot or budget < wage:
            conn.close()
            return

        cur.execute("SELECT nickname FROM players WHERE id=?", (player_id,))
        p = cur.fetchone()
        nick = p[0] if p else str(player_id)

        # Contract end date
        cur.execute("SELECT date FROM save WHERE id=1")
        date_row = cur.fetchone()
        if date_row:
            try:
                game_date = date.fromisoformat(date_row[0])
                contract_end = str(game_date + timedelta(days=365 * duration_years))
            except Exception:
                contract_end = None
        else:
            contract_end = None

        cur.execute(f"UPDATE teams SET {role}=? WHERE id=?", (player_id, team_id))
        cur.execute(
            "UPDATE players SET team_id=?, wage=?, contract_end=? WHERE id=?",
            (team_id, wage, contract_end, player_id),
        )
        conn.commit()
        conn.close()

        yr_word = {1: 'год', 2: 'года', 3: 'года'}.get(duration_years, 'лет')
        exp = f" на {duration_years} {yr_word} (до {contract_end})" if contract_end else ""
        _add_message(self.db_name, f"{nick} подписан в {team_name} за ${wage:,}/мес.{exp}")
        self._rebuild()


def show_transfers_popup(db_name, on_dismiss=None):
    p = TransferPopup(db_name=db_name)
    if on_dismiss:
        p.bind(on_dismiss=lambda *_: on_dismiss())
    p.open()
