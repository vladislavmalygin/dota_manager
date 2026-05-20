import sqlite3
from datetime import date, timedelta

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock

import ui_theme as T

from settings import SettingsPopup
from ingame_interface.inbox import show_message
from ingame_interface.mixin import show_custom_popup
from ingame_interface.squad import show_squad_popup
from ingame_interface.tournaments import TournamentPopup, TournamentsViewPopup
from ingame_interface.organization import show_organization_popup
from ingame_interface.profile import show_profile_popup
from ingame_interface.transfers import show_transfers_popup, is_transfer_window as _is_transfer_window
from logic.tournaments.invites import invites
from logic.tournaments.runner import ensure_season_tournaments
from logic.ai import (update_morale_monthly, update_form_monthly, ai_poach_attempt,
                       develop_free_agents, ai_buy_offer, ai_team_trades,
                       set_ai_train_priorities)
from logic.events import random_event_monthly
from logic.sponsors import ensure_sponsors_table, pay_monthly_income
from db_migrate2 import migrate as _migrate2
import random as _random
from db_migrate3 import migrate as _migrate3
from db_migrate4 import migrate as _migrate4
from db_migrate5 import migrate as _migrate5
from db_migrate6 import migrate as _migrate6
from db_migrate7 import migrate as _migrate7
from db_migrate8 import migrate as _migrate8
from db_migrate9  import migrate as _migrate9
from db_migrate10 import migrate as _migrate10
from db_migrate11 import migrate as _migrate11
from db_migrate12 import migrate as _migrate12
from db_migrate13 import migrate as _migrate13
from db_migrate14 import migrate as _migrate14
from db_migrate15 import migrate as _migrate15
from db_migrate16 import migrate as _migrate16
from db_migrate17 import migrate as _migrate17
from db_migrate18 import migrate as _migrate18
from db_migrate18_fix import migrate as _migrate18_fix
from db_migrate19 import migrate as _migrate19
from db_migrate20 import migrate as _migrate20
from db_migrate21 import migrate as _migrate21
from db_migrate22 import migrate as _migrate22
from db_migrate23 import migrate as _migrate23
from db_migrate24 import migrate as _migrate24
from db_migrate25 import migrate as _migrate25
from db_migrate26 import migrate as _migrate26
from db_migrate27 import migrate as _migrate27
from db_migrate28 import migrate as _migrate28
from db_migrate29 import migrate as _migrate29
from db_migrate30 import migrate as _migrate30
from db_migrate31 import migrate as _migrate31
from db_migrate32 import migrate as _migrate32
from db_migrate33 import migrate as _migrate33
from db_migrate34 import migrate as _migrate34
from db_migrate35 import migrate as _migrate35
from db_fix_orphans import fix as _fix_orphans


_TEAM_REGIONS = {
    1:  'EEU',   # Team Spirit
    2:  'China', # Xtreme Gaming
    3:  'WEU',   # Team Falcons (Saudi Arabia = WEU per design)
    4:  'WEU',   # Team Liquid
    5:  'WEU',   # Gamin Gladiators (Saudi Arabia = WEU)
    7:  'WEU',   # Tundra Esports
    8:  'EEU',   # BB Team
    13: 'SEA',   # Aurora
    14: 'NA',    # nouns
    15: 'SA',    # Heroic (LatAm roster)
    16: 'SA',    # Beastcoast
    17: 'WEU',   # OG
    21: 'WEU',   # Nigma Galaxy (Qatar = WEU)
    24: 'EEU',   # Virtus.pro
    26: 'WEU',   # Entity
    27: 'WEU',   # Alliance
    32: 'SEA',   # Execration
    33: 'China', # Team Aster
    34: 'China', # Azure Ray
    35: 'EEU',   # Natus Vincere
    36: 'SEA',   # Fnatic
    37: 'SEA',   # T1
    38: 'NA',    # Evil Geniuses
    39: 'SA',    # Thunder Awaken
    40: 'SEA',   # Blacklist International
    41: 'EEU',   # Nemiga Gaming
    42: 'EEU',   # PARIVISION
    43: 'WEU',   # MOUZ
    44: 'WEU',   # Zero Tenacity
    45: 'EEU',   # 1w Team
    46: 'EEU',   # L1GA TEAM
    47: 'EEU',   # VP.Prodigy
    48: 'SEA',   # REKONIX
}


def _fix_team_regions(db_name):
    """Assign regions to all known teams; skip teams that already have a region."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    for team_id, region in _TEAM_REGIONS.items():
        cur.execute(
            "UPDATE teams SET region=? WHERE id=? AND (region IS NULL OR region='')",
            (region, team_id),
        )
    conn.commit()
    conn.close()


def _fix_contracts(db_name):
    """Fill missing expected_wage and contract_end for all players."""
    from datetime import date, timedelta
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    # Read game start date
    cur.execute("SELECT date FROM save WHERE id=1")
    row = cur.fetchone()
    try:
        game_date = date.fromisoformat(row[0]) if row else date.today()
    except Exception:
        game_date = date.today()

    # --- expected_wage ---
    # Players in teams: if wage > 0, use wage; else compute from skills
    cur.execute("""
        UPDATE players
        SET expected_wage = CASE
            WHEN wage > 0 THEN wage
            ELSE MAX(3000, ((COALESCE(micro_skills,0) + COALESCE(macro_skills,0)) / 2) * 180)
        END
        WHERE (expected_wage IS NULL OR expected_wage = 0)
    """)
    # Free agents: always compute from skills (wage is 0)
    cur.execute("""
        UPDATE players
        SET expected_wage = MAX(3000,
            ((COALESCE(micro_skills,0) + COALESCE(macro_skills,0)) / 2) * 180)
        WHERE team_id = 0
          AND (expected_wage IS NULL OR expected_wage = 0)
    """)

    # --- contract_end ---
    # Spread contracts: base 1 year, vary by ±0-5 months via player id
    # to avoid a mass-expiry cliff at game start
    cur.execute("""
        SELECT id FROM players
        WHERE team_id != 0
          AND (contract_end IS NULL OR contract_end = '')
    """)
    player_ids = [r[0] for r in cur.fetchall()]
    for pid in player_ids:
        offset_days = 365 + (pid % 6) * 30   # 365..515 days
        contract_end = str(game_date + timedelta(days=offset_days))
        cur.execute("UPDATE players SET contract_end=? WHERE id=?", (contract_end, pid))

    conn.commit()
    conn.close()


def _get_menu_badges(db_name):
    """Return dict of button_text → badge_suffix for menu buttons."""
    badges = {}
    try:
        conn = sqlite3.connect(db_name)
        # Входящие: unread messages
        unread = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE COALESCE(read,0)=0"
        ).fetchone()
        if unread and unread[0] > 0:
            badges['Входящие'] = f' ({unread[0]})'

        # AI offers pending
        offers = conn.execute("SELECT COUNT(*) FROM ai_offers").fetchone()
        if offers and offers[0] > 0:
            badges['Трансферы'] = f' [+]{offers[0]}'

        # Состав: active conflict or wants_to_leave
        team = conn.execute(
            "SELECT id, COALESCE(conflict_targets,'') FROM teams WHERE player='yes'"
        ).fetchone()
        if team:
            has_conflict = bool(team[1])
            if not has_conflict:
                leaving = conn.execute(
                    "SELECT COUNT(*) FROM players WHERE team_id=? AND COALESCE(wants_to_leave,0)=1",
                    (team[0],)
                ).fetchone()
                has_conflict = leaving and leaving[0] > 0
            if has_conflict:
                badges['Состав'] = ' [!]'

        conn.close()
    except Exception as _e:
        T.log_err('_get_menu_badges', _e)
    return badges


def _pay_streaming_income(db_name, game_date_str):
    """Monthly passive income from streaming/merch based on rating and reputation."""
    conn = sqlite3.connect(db_name)
    try:
        row = conn.execute(
            "SELECT t.id, COALESCE(t.rating,0), COALESCE(t.fans,0) FROM teams t WHERE t.player='yes'"
        ).fetchone()
        if not row:
            conn.close()
            return
        team_id, rating, fans = row
        rep_row = conn.execute(
            "SELECT COALESCE(reputation,0) FROM characters LIMIT 1"
        ).fetchone()
        reputation = rep_row[0] if rep_row else 0

        # Fans add passive income: 1k per 10k fans (fan merch / tickets)
        fans_income = (fans // 10_000) * 1_000
        income = max(1_000, int(rating * 50 + reputation * 180 + fans_income))
        income = round(income / 500) * 500
        try:
            from logic.achievements import apply_monthly_bonuses
            income = apply_monthly_bonuses(db_name, income)
        except Exception:
            pass

        conn.execute("UPDATE teams SET budget=budget+? WHERE id=?", (income, team_id))
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
            (f"Доход от стриминга и мерча: +${income:,} (рейтинг {int(rating)}, репутация {reputation})",
             game_date_str, "Организация"),
        )
        conn.commit()
    except Exception:
        pass
    conn.close()


def _enforce_conflict_states(db_name):
    """Keep morale=1 for wants_to_leave players; keep cohesion=0 while conflict_targets active."""
    conn = sqlite3.connect(db_name)
    # Enforce morale=1 for players who want to leave (and are still on a team)
    conn.execute(
        "UPDATE players SET morale=1 WHERE wants_to_leave=1 AND team_id != 0"
    )
    # Check if conflict_targets are still on the team; clear if all gone
    row = conn.execute(
        "SELECT id, conflict_targets FROM teams WHERE player='yes' "
        "AND conflict_targets IS NOT NULL AND conflict_targets != ''"
    ).fetchone()
    if row:
        team_id, ct = row
        targets = [int(x) for x in ct.split(',') if x.strip().isdigit()]
        still_on_team = []
        for pid in targets:
            p = conn.execute(
                "SELECT team_id FROM players WHERE id=?", (pid,)
            ).fetchone()
            if p and p[0] == team_id:
                still_on_team.append(pid)
        if not still_on_team:
            conn.execute(
                "UPDATE teams SET conflict_targets=NULL WHERE id=?", (team_id,)
            )
        else:
            conn.execute("UPDATE teams SET cohesion=0 WHERE id=?", (team_id,))
    conn.commit()
    conn.close()


_current_game_popup = None   # single-popup-at-a-time tracking


def _patch_popups():
    """Position sub-popups in the main area; one at a time; sidebar always accessible."""
    from kivy.uix.popup import Popup
    from kivy.uix.modalview import ModalView

    if hasattr(Popup, '_orig_open'):
        return

    Popup._orig_open = Popup.open

    def _game_open(self, *a, **kw):
        global _current_game_popup
        sw, sh = (self.size_hint or (0.8, 0.8))[:2]
        if float(sw) >= 0.99 and float(sh) >= 0.99:
            Popup._orig_open(self, *a, **kw)
            return

        # Close previous sub-popup before opening new one
        if _current_game_popup and _current_game_popup is not self:
            try:
                _current_game_popup.dismiss()
            except Exception:
                pass
        _current_game_popup = self

        # Position in free area, no dim overlay
        sw = min(float(sw), 0.78)
        sh = min(float(sh), 0.89)
        self.size_hint = (sw, sh)
        cx = 0.20 + (0.80 - sw) / 2
        cy = (0.90 - sh) / 2
        self.pos_hint  = {'x': max(0.20, cx), 'y': max(0.0, cy)}
        self.background_color   = (0, 0, 0, 0)
        self.background         = ''
        self.separator_color    = (0, 0, 0, 0)
        self.title_bar_height   = 0
        Popup._orig_open(self, *a, **kw)

        # Clear ref when this popup dismisses
        def _on_dismiss(_inst):
            global _current_game_popup
            if _current_game_popup is self:
                _current_game_popup = None
        self.bind(on_dismiss=_on_dismiss)

    Popup.open = _game_open

    # Pass sidebar (x<20%) and topbar (y>89%) touches through
    ModalView._orig_touch_down = ModalView.on_touch_down

    def _mv_touch(self, touch):
        if not self.collide_point(*touch.pos):
            from kivy.core.window import Window
            if Window.width > 0:
                rx = touch.x / Window.width
                ry = touch.y / Window.height
                if rx < 0.205 or ry > 0.89:
                    return False
            if self.auto_dismiss:
                self.dismiss()
            return True
        from kivy.uix.floatlayout import FloatLayout
        return FloatLayout.on_touch_down(self, touch)

    ModalView.on_touch_down = _mv_touch


def _unpatch_popups():
    from kivy.uix.popup import Popup
    from kivy.uix.modalview import ModalView
    if hasattr(Popup, '_orig_open'):
        Popup.open = Popup._orig_open
        del Popup._orig_open
    if hasattr(ModalView, '_orig_touch_down'):
        ModalView.on_touch_down = ModalView._orig_touch_down
        del ModalView._orig_touch_down


class MainWindow(BoxLayout):
    def __init__(self, db_name, popup, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.db_name = db_name
        self.popup = popup

        _patch_popups()
        ensure_season_tournaments(db_name)
        self._migrate_db(db_name)

        self.date_object = self.get_date_from_db(1)

        from kivy.uix.label import Label
        from kivy.animation import Animation

        # ── Background ────────────────────────────────────────────────────────
        with self.canvas.before:
            Color(1, 1, 1, 0.5)
            self.rect = Rectangle(source='images/core1.png', pos=self.pos, size=self.size)
        self.bind(size=self._update_rect, pos=self._update_rect)

        # ── Top bar ───────────────────────────────────────────────────────────
        team_name      = self.get_team_name()
        tournament_name = self.get_next_tournament()

        top_bar = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=T.TOPBAR_H,
            spacing=4, padding=(8, 4),
        )
        with top_bar.canvas.before:
            Color(*T.BG_TOPBAR)
            self._top_rect = Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(
            pos=lambda w, _: setattr(self._top_rect, 'pos', w.pos),
            size=lambda w, _: setattr(self._top_rect, 'size', w.size),
        )

        # Team name (left)
        team_lbl = Label(
            text=f'[b]{team_name}[/b]', markup=True,
            color=T.PLAYER_CLR, font_size='17sp',
            size_hint_x=0.20, halign='left', valign='middle',
        )
        team_lbl.bind(size=team_lbl.setter('text_size'))
        top_bar.add_widget(team_lbl)

        # Budget label
        budget_txt, budget_color = self._get_budget_display()
        self._budget_lbl = Label(
            text=budget_txt, markup=True,
            color=budget_color, font_size=T.FS_TITLE,
            size_hint_x=0.17, halign='center', valign='middle',
        )
        self._budget_lbl.bind(size=self._budget_lbl.setter('text_size'))
        top_bar.add_widget(self._budget_lbl)

        # Rating label
        self._rating_lbl = Label(
            text=self._get_rating_display(), markup=True,
            color=T.TEXT_MAIN, font_size=T.FS_TITLE,
            size_hint_x=0.13, halign='center', valign='middle',
        )
        self._rating_lbl.bind(size=self._rating_lbl.setter('text_size'))
        top_bar.add_widget(self._rating_lbl)

        # Tournament button (center)
        self.tournament_button = Button(
            text=tournament_name,
            background_color=(0.65, 0.15, 0.15, 1), background_normal='',
            font_size=T.FS_BODY, size_hint_x=0.26,
            on_press=self.on_tournament_btn,
        )
        top_bar.add_widget(self.tournament_button)

        # Inbox badge button (topbar shortcut)
        from kivy.uix.label import Label as _L
        self._inbox_badge_btn = Button(
            text='', background_color=(0.55, 0.12, 0.12, 1), background_normal='',
            font_size='12sp', size_hint_x=0.06, markup=True,
        )
        self._inbox_badge_btn.bind(on_press=self.on_incoming)
        top_bar.add_widget(self._inbox_badge_btn)

        # Date label
        self.today_date_button = Button(
            text=str(self.date_object),
            background_color=(0.22, 0.32, 0.18, 1), background_normal='',
            font_size=T.FS_BODY, size_hint_x=0.10,
            on_press=self.on_press,
        )
        top_bar.add_widget(self.today_date_button)

        # Далее button
        self._next_btn = Button(
            text='Далее  ▶',
            background_color=(0.75, 0.65, 0.05, 1), background_normal='',
            font_size=T.FS_TITLE, bold=True, size_hint_x=0.08,
            on_press=self.on_next,
        )
        top_bar.add_widget(self._next_btn)

        # Skip-to-next button
        self._skip_btn = Button(
            text='▶▶ Матч',
            background_color=(0.38, 0.28, 0.04, 1), background_normal='',
            font_size=T.FS_BODY, size_hint_x=0.08,
            on_press=self.on_skip_to_tournament,
        )
        top_bar.add_widget(self._skip_btn)
        self._auto_advance_event = None
        self.add_widget(top_bar)

        # ── Body (sidebar + main area) ────────────────────────────────────────
        main_layout = BoxLayout(orientation='horizontal')

        # ── Left sidebar ──────────────────────────────────────────────────────
        from kivy.uix.scrollview import ScrollView
        sidebar_scroll = ScrollView(size_hint=(0.185, 1), do_scroll_x=False)
        left_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=1)
        left_layout.bind(minimum_height=left_layout.setter('height'))

        with sidebar_scroll.canvas.before:
            Color(*T.BG_SIDEBAR)
            self._side_rect = Rectangle(pos=sidebar_scroll.pos, size=sidebar_scroll.size)
        sidebar_scroll.bind(
            pos=lambda w, _: setattr(self._side_rect, 'pos', w.pos),
            size=lambda w, _: setattr(self._side_rect, 'size', w.size),
        )

        _BTN_H = T.NAV_BTN_H
        _SEP_H = T.NAV_SEP_H
        self._active_nav_btn = None

        def _sep(text):
            lbl = Label(
                text=f'[b]{text}[/b]', markup=True,
                size_hint_y=None, height=_SEP_H,
                color=T.NAV_SEP_FG, font_size=T.FS_TINY,
                halign='center', valign='middle',
            )
            lbl.bind(size=lbl.setter('text_size'))
            with lbl.canvas.before:
                Color(*T.NAV_SEP_BG)
                _r = Rectangle()
            lbl.bind(pos=lambda w, _: setattr(_r, 'pos', w.pos),
                     size=lambda w, _: setattr(_r, 'size', w.size))
            return lbl

        def _menu_btn(text, action):
            btn = Button(
                text=text, size_hint_y=None, height=_BTN_H,
                background_color=T.NAV_IDLE, background_normal='',
                font_size=T.FS_BODY, halign='center',
            )
            btn._base_text = text
            btn._has_alert = False

            def _press(inst):
                prev = self._active_nav_btn
                if prev and prev is not btn:
                    prev.background_color = (
                        T.NAV_ALERT if getattr(prev, '_has_alert', False)
                        else T.NAV_IDLE
                    )
                self._active_nav_btn = btn
                btn.background_color = T.NAV_ACTIVE
                action(inst)

            btn.bind(on_press=_press)
            return btn

        # Groups — reorganized for clarity
        _GROUPS = [
            ('СОСТАВ', [
                ('Состав',      self.on_roster),
                ('Трансферы',   self.on_transfers),
                ('Академия',    self.on_academy),
                ('Кланвары',    self.on_scrimmage),
            ]),
            ('ОРГАНИЗАЦИЯ', [
                ('Финансы',     self.on_finances),
                ('Спонсоры',    self.on_sponsors),
                ('Организация', self.on_organization),
                ('Навыки',      self.on_manager_skills),
                ('Цели',        self.on_goals),
            ]),
            ('ТУРНИРЫ / МИР', [
                ('Турниры',     self.on_tournaments),
                ('Команды',     self.on_league),
                ('Лидерборд',   self.on_leaderboard),
            ]),
            ('ИСТОРИЯ', [
                ('История',     self.on_history),
                ('Трансф. лог', self.on_transfer_history),
                ('Статистика',  self.on_stats),
                ('Герои патча', self.on_hero_stats),
            ]),
            ('ПРОЧЕЕ', [
                ('Входящие',    self.on_incoming),
                ('Достижения',  self.on_achievements),
                ('Мой профиль', self.on_profile),
                ('Настройки',   self.on_settings),
                ('Сохранить',   self.on_manual_save),
                ('Главное меню',self.on_main_menu),
            ]),
        ]

        # ── Home button ───────────────────────────────────────────────────────
        _home_sidebar_btn = Button(
            text='Главная', size_hint_y=None, height=_BTN_H + 6,
            background_color=T.NAV_ACTIVE, background_normal='',
            font_size=T.FS_TITLE, bold=True,
        )
        def _press_home(inst):
            prev = self._active_nav_btn
            if prev:
                prev.background_color = T.NAV_ALERT if getattr(prev, '_has_alert', False) else T.NAV_IDLE
            self._active_nav_btn = None
            _home_sidebar_btn.background_color = T.NAV_ACTIVE
            self._show_dashboard()
        _home_sidebar_btn.bind(on_press=_press_home)
        self._home_btn = _home_sidebar_btn
        left_layout.add_widget(_home_sidebar_btn)

        self._menu_buttons = {}
        for group_name, items in _GROUPS:
            left_layout.add_widget(_sep(group_name))
            for btn_text, action in items:
                btn = _menu_btn(btn_text, action)
                left_layout.add_widget(btn)
                self._menu_buttons[btn_text] = btn

        sidebar_scroll.add_widget(left_layout)
        self._refresh_menu_badges()

        # ── Main area ─────────────────────────────────────────────────────────
        self.main_area = BoxLayout(size_hint=(1, 1))
        with self.main_area.canvas.before:
            Color(0.06, 0.08, 0.11, 0.82)
            self.rect_main_area = Rectangle(pos=self.main_area.pos, size=self.main_area.size)
        self.main_area.bind(size=self._update_main_area_rect)

        self._show_dashboard()

        main_layout.add_widget(sidebar_scroll)
        main_layout.add_widget(self.main_area)
        self.add_widget(main_layout)

        # ── News ticker ───────────────────────────────────────────────────────
        from kivy.uix.label import Label as _Lbl
        ticker_bar = BoxLayout(size_hint_y=None, height=22)
        with ticker_bar.canvas.before:
            Color(0.04, 0.06, 0.10, 1)
            _tbr = Rectangle()
        ticker_bar.bind(pos=lambda w, _: setattr(_tbr, 'pos', w.pos),
                        size=lambda w, _: setattr(_tbr, 'size', w.size))
        self._ticker_lbl = _Lbl(
            text='', markup=True,
            color=(0.55, 0.65, 0.80, 1), font_size='11sp',
            halign='left', valign='middle',
        )
        self._ticker_lbl.bind(size=self._ticker_lbl.setter('text_size'))
        ticker_bar.add_widget(self._ticker_lbl)
        self.add_widget(ticker_bar)
        self._ticker_offset = [0.0]
        self._ticker_items  = []
        Clock.schedule_once(lambda dt: self._load_ticker(), 1.0)
        Clock.schedule_interval(self._tick_news, 0.05)

        # ── Keyboard shortcuts ────────────────────────────────────────────────
        from kivy.core.window import Window as _Win
        _Win.bind(on_key_down=self._on_key_down)

    def _on_key_down(self, _win, key, _scancode, _codepoint, modifiers):
        # Space → next day (only if no modifier)
        if key == 32 and not modifiers:
            if hasattr(self, '_next_btn') and not self._next_btn.disabled:
                self.on_next(None)
            return True
        return False

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def _get_budget_display(self):
        try:
            conn = sqlite3.connect(self.db_name)
            row = conn.execute(
                "SELECT COALESCE(budget,0) FROM teams WHERE player='yes'"
            ).fetchone()
            conn.close()
            budget = row[0] if row else 0
            txt = f'[b]${budget:,}[/b]'
            color = ((0.25, 0.90, 0.40, 1) if budget > 200_000
                     else (1.0, 0.85, 0.20, 1) if budget > 50_000
                     else (1.0, 0.35, 0.25, 1))
            return txt, color
        except Exception:
            return '$—', (0.5, 0.5, 0.5, 1)

    def _get_rating_display(self):
        try:
            conn = sqlite3.connect(self.db_name)
            rows = conn.execute(
                "SELECT name, COALESCE(rating,0) FROM teams ORDER BY COALESCE(rating,0) DESC"
            ).fetchall()
            my_row = conn.execute(
                "SELECT name, id, COALESCE(rating,0) FROM teams WHERE player='yes'"
            ).fetchone()
            conn.close()
            if not my_row:
                return 'Рейтинг: —'
            my_name, my_id, my_rating = my_row[0].strip(), my_row[1], my_row[2]
            rank = next((i+1 for i, (n, r) in enumerate(rows) if n.strip() == my_name), '?')
            # Trend from snapshots (last 2)
            trend_txt = ''
            try:
                conn2 = sqlite3.connect(self.db_name)
                snaps = conn2.execute(
                    "SELECT rating FROM team_snapshots WHERE team_id=? "
                    "ORDER BY snap_date DESC LIMIT 2", (my_id,)
                ).fetchall()
                conn2.close()
                if len(snaps) >= 2:
                    delta = int(snaps[0][0]) - int(snaps[1][0])
                    if delta > 0:
                        trend_txt = f'  [color=44dd66]↑{delta}[/color]'
                    elif delta < 0:
                        trend_txt = f'  [color=dd4444]↓{abs(delta)}[/color]'
            except Exception:
                pass
            return f'[b]#{rank}[/b]  {int(my_rating)} pts{trend_txt}'
        except Exception:
            pass
        return 'Рейтинг: —'

    def _show_inline(self, popup_instance, title=''):
        """Show any Popup's content inline in main_area (no floating popup)."""
        from kivy.uix.label import Label
        if hasattr(self, '_home_btn'):
            self._home_btn.background_color = T.NAV_IDLE

        self.main_area.clear_widgets()

        # ── Breadcrumb bar ────────────────────────────────────────────────────
        hdr = BoxLayout(size_hint_y=None, height=44, spacing=8, padding=(14, 4))
        with hdr.canvas.before:
            Color(*T.BG_HEADER)
            _hr = Rectangle()
        hdr.bind(pos =lambda w, _: setattr(_hr, 'pos',  w.pos),
                 size=lambda w, _: setattr(_hr, 'size', w.size))

        title_lbl = Label(text=f'[b]{title}[/b]', markup=True,
                          color=T.ACCENT, font_size=T.FS_TITLE,
                          halign='left', valign='middle')
        title_lbl.bind(size=title_lbl.setter('text_size'))

        home_btn = Button(text='← Главная',
                          size_hint=(None, 1), width=130,
                          background_color=T.BTN_NEUTRAL, background_normal='',
                          font_size=T.FS_BODY)
        home_btn.bind(on_press=lambda _: self._show_dashboard())

        hdr.add_widget(title_lbl)
        hdr.add_widget(home_btn)

        # ── Content holder (auto-updates on popup._build / _rebuild) ─────────
        content_box = BoxLayout()

        def _detach_and_add(widget):
            if widget.parent:
                widget.parent.remove_widget(widget)
            content_box.add_widget(widget)

        def _update_content(inst, val):
            content_box.clear_widgets()
            if val:
                _detach_and_add(val)

        popup_instance.bind(content=_update_content)
        popup_instance.dismiss = lambda *_: self._show_dashboard()

        frame = BoxLayout(orientation='vertical')
        frame.add_widget(hdr)
        frame.add_widget(content_box)
        self.main_area.add_widget(frame)

        if popup_instance.content:
            _detach_and_add(popup_instance.content)

        self._active_inline_popup = popup_instance

    def _show_dashboard(self, *_):
        # Reset sidebar nav highlight → home becomes active
        prev = getattr(self, '_active_nav_btn', None)
        if prev:
            prev.background_color = (
                T.NAV_ALERT if getattr(prev, '_has_alert', False) else T.NAV_IDLE
            )
        self._active_nav_btn = None
        if hasattr(self, '_home_btn'):
            self._home_btn.background_color = T.NAV_ACTIVE
        self._active_inline_popup = None
        self._refresh_menu_badges()
        # Update skip button label based on tournament state
        if hasattr(self, '_skip_btn'):
            at = self._get_active_tournament()
            if at:
                self._skip_btn.text = '>> Матч'
            else:
                self._skip_btn.text = '>> Турнир'
        self._build_dashboard()

    def _build_dashboard(self):
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.gridlayout import GridLayout

        self.main_area.clear_widgets()

        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()

            team = c.execute(
                "SELECT name, COALESCE(budget,0), COALESCE(rating,0), COALESCE(cohesion,0), "
                "carry, mid, offlane, partial_support, full_support, "
                "COALESCE(org_reputation,20), COALESCE(fans,0) "
                "FROM teams WHERE player='yes'"
            ).fetchone()
            if not team:
                conn.close()
                return

            t_name, budget, rating, cohesion, *_rest = team
            fans         = _rest[-1]
            org_reputation = _rest[-2]
            slot_ids = [s for s in _rest[:-2] if s]

            # Avg morale + wages
            avg_morale, total_wage = 5, 0
            if slot_ids:
                ph = ','.join('?' * len(slot_ids))
                rows = c.execute(
                    f"SELECT COALESCE(morale,5), COALESCE(wage,0) FROM players WHERE id IN ({ph})",
                    slot_ids
                ).fetchall()
                if rows:
                    avg_morale = sum(r[0] for r in rows) // len(rows)
                    total_wage = sum(r[1] for r in rows)

            # Active or next tournament
            active_tourn = self._get_active_tournament()
            t_row = c.execute(
                "SELECT name, start_date FROM tournaments WHERE place1 IS NULL ORDER BY start_date LIMIT 1"
            ).fetchone()

            # Last 3 results
            results = []
            my_id = c.execute("SELECT id FROM teams WHERE player='yes'").fetchone()
            if my_id:
                tid = my_id[0]
                for row in c.execute(
                    "SELECT name, place1,place2,place3,place4,place5,place6,place7,place8 "
                    "FROM tournaments WHERE place1 IS NOT NULL ORDER BY start_date DESC LIMIT 5"
                ):
                    t_title = row[0]
                    for i, p in enumerate(row[1:], 1):
                        if p == tid:
                            results.append((t_title, i))
                            break

            # All-teams ranking
            all_teams = c.execute(
                "SELECT name, COALESCE(rating,0), player FROM teams ORDER BY COALESCE(rating,0) DESC"
            ).fetchall()
            my_rank = next((i+1 for i, (n, r, pl) in enumerate(all_teams) if pl == 'yes'), '?')

            sponsor_income = 0
            sp = c.execute("SELECT monthly_income FROM sponsors WHERE is_active=1 LIMIT 1").fetchone()
            if sp:
                sponsor_income = sp[0] or 0
            fans_income = (fans // 10_000) * 1_000
            streaming = max(1_000, int(rating * 50 + org_reputation * 180 + fans_income))
            monthly_in = sponsor_income + streaming
            balance = monthly_in - total_wage

            # Action items
            actions = []
            game_date_str = str(self.date_object)

            # Contracts expiring < 60 days
            if slot_ids:
                ph2 = ','.join('?' * len(slot_ids))
                exp_rows = c.execute(
                    f"SELECT nickname, contract_end FROM players "
                    f"WHERE id IN ({ph2}) AND contract_end IS NOT NULL "
                    f"AND contract_end <= date(?, '+60 days') "
                    f"ORDER BY contract_end",
                    list(slot_ids) + [game_date_str]
                ).fetchall()
                for enick, cend in exp_rows:
                    try:
                        days = (date.fromisoformat(cend) - self.date_object).days
                        actions.append(('danger', f'Контракт {enick} истекает через {days} дн.'))
                    except Exception:
                        pass

            # AI buy offers
            ai_cnt = (c.execute("SELECT COUNT(*) FROM ai_offers").fetchone() or (0,))[0]
            if ai_cnt:
                actions.append(('warn', f'{ai_cnt} входящих трансферных предложения'))

            # Wants to leave
            leave_rows = c.execute(
                "SELECT nickname FROM players WHERE team_id=? AND COALESCE(wants_to_leave,0)=1",
                (my_id[0],)
            ).fetchall() if my_id else []
            for (lnick,) in leave_rows:
                actions.append(('warn', f'{lnick} хочет покинуть команду'))

            # Conflict
            ct_row = c.execute(
                "SELECT COALESCE(conflict_targets,'') FROM teams WHERE player='yes'"
            ).fetchone()
            if ct_row and ct_row[0]:
                actions.append(('danger', 'Конфликт в команде — требует решения'))

            # Low cohesion
            if cohesion < 25:
                actions.append(('danger', f'Сыгранность критически низкая: {cohesion}/100'))
            elif cohesion < 50:
                # Check if bootcamp available
                lbd = c.execute(
                    "SELECT last_bootcamp_date FROM teams WHERE player='yes'"
                ).fetchone()
                bc_avail = True
                if lbd and lbd[0]:
                    try:
                        from datetime import timedelta as _td
                        days_since = (self.date_object - date.fromisoformat(lbd[0])).days
                        bc_avail = days_since >= 30
                    except Exception:
                        pass
                if bc_avail:
                    actions.append(('warn', f'Сыгранность низкая ({cohesion}/100) — доступен буткемп'))

            # Salary cap warning
            if total_wage > 200_000:
                actions.append(('danger', f'Зарплаты ${total_wage:,}/мес превышают лимит $200k — налог $30k/мес'))

            # Rating / budget trend (last 6 monthly snapshots)
            rating_trend = None
            budget_trend = None
            if my_id:
                snaps = c.execute(
                    "SELECT rating, budget FROM team_snapshots "
                    "WHERE team_id=? ORDER BY snap_date DESC LIMIT 6",
                    (my_id[0],)
                ).fetchall()
                if len(snaps) >= 2:
                    rating_trend = int(snaps[0][0]) - int(snaps[-1][0])
                    budget_trend = snaps[0][1] - snaps[-1][1]

            conn.close()
        except Exception as _e:
            T.log_err('_show_dashboard', _e)
            return

        # ── Build dashboard layout ────────────────────────────────────────────
        sv    = ScrollView(size_hint=(1, 1))
        outer = GridLayout(cols=1, size_hint_y=None, spacing=14, padding=(16, 14))
        outer.bind(minimum_height=outer.setter('height'))

        def _card(bg=T.BG_CARD):
            return T.make_card(bg=bg, radius=10, padding=T.CARD_PAD,
                               spacing=T.CARD_SPACING)

        def _row(left, right, lc=T.TEXT_LABEL, rc=T.TEXT_MAIN):
            r = BoxLayout(size_hint_y=None, height=T.ROW_H)
            ll = Label(text=left,  markup=True, color=lc, font_size=T.FS_BODY,
                       halign='left',  valign='middle', size_hint_x=0.55)
            rl = Label(text=right, markup=True, color=rc, font_size=T.FS_BODY,
                       halign='right', valign='middle', size_hint_x=0.45)
            ll.bind(size=ll.setter('text_size'))
            rl.bind(size=rl.setter('text_size'))
            r.add_widget(ll); r.add_widget(rl)
            return r

        def _title(text, color=T.ACCENT):
            lbl = Label(text=f'[b]{text}[/b]', markup=True, color=color,
                        font_size=T.FS_TITLE, size_hint_y=None, height=T.TITLE_H,
                        halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            return lbl

        def _mc(rgba):
            return T.markup_color(rgba)

        # ── Transfer window banner ───────────────────────────────────────────
        if _is_transfer_window(str(self.date_object)):
            tw = _card((0.08, 0.22, 0.10, 1))
            lbl_tw = Label(
                text='[b]ТРАНСФЕРНОЕ ОКНО ОТКРЫТО[/b]  —  январь и август',
                markup=True, color=T.POSITIVE,
                font_size=T.FS_BODY, size_hint_y=None, height=T.ROW_H,
                halign='center', valign='middle',
            )
            lbl_tw.bind(size=lbl_tw.setter('text_size'))
            tw.add_widget(lbl_tw)
            outer.add_widget(tw)

        # ── Action items card ────────────────────────────────────────────────
        if actions:
            ca = _card((0.13, 0.07, 0.07, 1))
            ca.add_widget(_title('Требует внимания', T.NEGATIVE))
            for kind, text in actions:
                color = T.NEGATIVE if kind == 'danger' else T.WARNING
                lbl = Label(
                    text=f'  • {text}', color=color,
                    font_size=T.FS_BODY, size_hint_y=None, height=T.ROW_H_SM,
                    halign='left', valign='middle',
                )
                lbl.bind(size=lbl.setter('text_size'))
                ca.add_widget(lbl)
            outer.add_widget(ca)

        # ── Row 1: team overview + next tournament side by side ───────────────
        row1 = BoxLayout(size_hint_y=None, spacing=10)
        row1.bind(minimum_height=row1.setter('height'))

        def _trend_suffix(delta, is_money=False):
            if delta is None or delta == 0:
                return ''
            arrow = '↑' if delta > 0 else '↓'
            col   = _mc(T.POSITIVE) if delta > 0 else _mc(T.NEGATIVE)
            val   = f'${abs(delta):,}' if is_money else str(abs(delta))
            return f'  [color={col}]{arrow}{val}[/color]'

        c1 = _card(T.BG_CARD)
        c1.add_widget(_title(t_name.strip()))
        bc = T.budget_color(budget)
        c1.add_widget(_row('Бюджет',
                           f'[color={_mc(bc)}][b]${budget:,}[/b][/color]'
                           + _trend_suffix(budget_trend, is_money=True)))
        c1.add_widget(_row('Место в рейтинге',
                           f'[b]#{my_rank}[/b]  ({int(rating)} pts)'
                           + _trend_suffix(rating_trend)))
        def _bar_row(label, value, max_val, color):
            """Row with inline mini progress bar."""
            from kivy.uix.widget import Widget
            from kivy.graphics import Color as _GC, Rectangle as _GR
            r = BoxLayout(size_hint_y=None, height=T.ROW_H, spacing=4)
            ll = Label(text=label, color=T.TEXT_LABEL, font_size=T.FS_BODY,
                       halign='left', valign='middle', size_hint_x=0.38)
            ll.bind(size=ll.setter('text_size'))
            # Mini bar
            bar_outer = BoxLayout(size_hint_x=0.40, size_hint_y=None,
                                  height=10, padding=(0, 0))
            pct = max(0.0, min(1.0, value / max_val))
            fill = Widget(size_hint=(pct, 1))
            with fill.canvas.before:
                _GC(*color)
                _rf = _GR()
            fill.bind(pos=lambda w, _: setattr(_rf, 'pos', w.pos),
                      size=lambda w, _: setattr(_rf, 'size', w.size))
            empty = Widget(size_hint=(1 - pct, 1))
            with empty.canvas.before:
                _GC(0.20, 0.20, 0.24, 1)
                _re = _GR()
            empty.bind(pos=lambda w, _: setattr(_re, 'pos', w.pos),
                       size=lambda w, _: setattr(_re, 'size', w.size))
            bar_outer.add_widget(fill)
            bar_outer.add_widget(empty)
            rl = Label(
                text=f'[color={_mc(color)}]{value}[/color]/{max_val}',
                markup=True, color=T.TEXT_MAIN, font_size=T.FS_BODY,
                halign='right', valign='middle', size_hint_x=0.22,
            )
            rl.bind(size=rl.setter('text_size'))
            r.add_widget(ll)
            r.add_widget(bar_outer)
            r.add_widget(rl)
            return r

        coh_c = T.cohesion_color(cohesion)
        c1.add_widget(_bar_row('Сыгранность', cohesion, 100, coh_c))
        try:
            from logic.chemistry import pair_bond_description
            _pb = pair_bond_description(self.db_name, my_id[0] if my_id else None)
            if _pb:
                c1.add_widget(_row('', _pb, rc=(0.70, 0.90, 0.70, 1)))
        except Exception:
            pass
        mor_c = T.morale_color(avg_morale)
        c1.add_widget(_bar_row('Мораль состава', avg_morale, 10, mor_c))
        rep_c = T.cohesion_color(org_reputation)
        c1.add_widget(_bar_row('Репутация орг.', org_reputation, 100, rep_c))
        fans_str = f'{fans:,}' if fans < 1_000_000 else f'{fans/1_000_000:.1f}M'
        c1.add_widget(_row('Фанаты', f'[color=ff88cc]{fans_str}[/color]'))
        try:
            from logic.meta import patch_description
            c1.add_widget(_row('Мета', patch_description(self.db_name),
                               rc=(0.80, 0.75, 1.00, 1)))
        except Exception:
            pass
        bal_c  = T.balance_color(balance)
        sign   = '+' if balance >= 0 else ''
        c1.add_widget(_row('Баланс/мес',
                           f'[color={_mc(bal_c)}]{sign}${balance:,}[/color]'))

        if active_tourn:
            at = active_tourn
            queue        = at['match_queue']
            idx          = at['match_idx']
            total        = len(queue)
            player_teams = at['player_teams']
            draw_ev      = at.get('draw_ev') or {}
            groups       = draw_ev.get('groups', [])
            standings    = at['standings']

            # Detect phase: if any played match has a playoff stage → playoff
            _PLAYOFF_KEYWORDS = ('UB', 'LB', 'Grand', 'Гранд', 'Финал (BO3)', 'Финал (BO5)')
            in_playoff = any(
                any(kw in (queue[i]['result_ev'].get('stage', '')) for kw in _PLAYOFF_KEYWORDS)
                for i in range(min(idx, len(queue)))
            )

            # Find next player match
            next_player   = None
            days_to_next  = 0
            for j in range(idx, len(queue)):
                ev = queue[j]['result_ev']
                if ev.get('is_player_match'):
                    next_player  = ev
                    days_to_next = j - idx
                    break

            def _next_match_row(card):
                if next_player:
                    opp  = next_player['team2'] if next_player['team1'] in player_teams \
                           else next_player['team1']
                    when = 'Сегодня' if days_to_next == 0 else f'Через {days_to_next} дн.'
                    card.add_widget(_row(
                        f'[b]{when}[/b]', f'vs {opp[:16]}',
                        rc=(1.00, 0.85, 0.30, 1),
                    ))
                elif idx >= total:
                    card.add_widget(_row('', 'Завершается...', rc=T.TEXT_DIM))

            if not in_playoff and len(groups) >= 2:
                # ── Two group tables side by side ─────────────────────────────
                c2 = _card(T.BG_CARD_TRN)
                c2.size_hint_x = 0.65
                c2.add_widget(_title(at['name'][:30], (0.80, 0.55, 1.00, 1)))
                c2.add_widget(_row('Матч', f'[b]{idx}/{total}[/b]',
                                   rc=(0.95, 0.85, 1.00, 1)))

                groups_row = BoxLayout(size_hint_y=None, height=26 * 9, spacing=8)
                for gi, grp in enumerate(groups[:2]):
                    gcol = GridLayout(cols=1, spacing=2)
                    label = 'Группа A' if gi == 0 else 'Группа B'
                    lbl = Label(
                        text=f'[b]{label}[/b]', markup=True,
                        color=T.ACCENT, size_hint_y=None, height=24,
                        halign='left', valign='middle', font_size=T.FS_SMALL,
                    )
                    lbl.bind(size=lbl.setter('text_size'))
                    gcol.add_widget(lbl)
                    grp_st = sorted(
                        [(t, standings.get(t, 0)) for t in grp],
                        key=lambda x: x[1], reverse=True
                    )
                    for rank, (team, pts) in enumerate(grp_st):
                        is_my = team in player_teams
                        tc = _mc(T.PLAYER_CLR) if is_my else (
                            _mc(T.GOLD) if rank == 0 else _mc(T.TEXT_MAIN)
                        )
                        row_w = BoxLayout(size_hint_y=None, height=22)
                        tl = Label(
                            text=f'[color={tc}]{rank+1}. {team[:14]}[/color]',
                            markup=True, color=T.TEXT_MAIN,
                            font_size='11sp', halign='left', valign='middle',
                        )
                        tl.bind(size=tl.setter('text_size'))
                        pr = Label(
                            text=f'[color={tc}]{pts}[/color]',
                            markup=True, color=T.TEXT_MAIN,
                            font_size='11sp', halign='right', valign='middle',
                            size_hint_x=None, width=36,
                        )
                        row_w.add_widget(tl)
                        row_w.add_widget(pr)
                        gcol.add_widget(row_w)
                    groups_row.add_widget(gcol)
                c2.add_widget(groups_row)
                _next_match_row(c2)
                row1.add_widget(c1)
                row1.add_widget(c2)

            elif not in_playoff and standings:
                # ── Single group table (DPC / round-robin) ────────────────────
                c2 = _card(T.BG_CARD_TRN)
                c2.add_widget(_title(at['name'][:30], (0.80, 0.55, 1.00, 1)))
                c2.add_widget(_row('Матч', f'[b]{idx}/{total}[/b]',
                                   rc=(0.95, 0.85, 1.00, 1)))
                sorted_st = sorted(standings.items(), key=lambda x: x[1], reverse=True)
                for i, (team, pts) in enumerate(sorted_st[:8]):
                    is_my = team in player_teams
                    tc = _mc(T.PLAYER_CLR) if is_my else (
                        _mc(T.GOLD) if i == 0 else _mc(T.TEXT_MAIN)
                    )
                    c2.add_widget(_row(
                        f'[color={tc}]{i+1}. {team[:18]}[/color]',
                        f'[color={tc}]{pts} pts[/color]',
                    ))
                _next_match_row(c2)
                row1.add_widget(c1)
                row1.add_widget(c2)

            else:
                # ── Playoff bracket ───────────────────────────────────────────
                c2 = _card(T.BG_CARD_TRN)
                c2.add_widget(_title(at['name'][:30], (0.80, 0.55, 1.00, 1)))
                c2.add_widget(_row('Плей-офф', f'[b]{idx}/{total}[/b]',
                                   rc=(0.95, 0.85, 1.00, 1)))

                # Collect played playoff matches grouped by stage
                from collections import OrderedDict
                bracket_stages = OrderedDict()
                for i in range(min(idx, len(queue))):
                    ev = queue[i]['result_ev']
                    stage = ev.get('stage', '')
                    if any(kw in stage for kw in _PLAYOFF_KEYWORDS):
                        bracket_stages.setdefault(stage, []).append(ev)

                for stage, matches in bracket_stages.items():
                    lbl = Label(
                        text=f'[b]{stage}[/b]', markup=True,
                        color=T.TEXT_DIM, font_size='10sp',
                        size_hint_y=None, height=18,
                        halign='left', valign='middle',
                    )
                    lbl.bind(size=lbl.setter('text_size'))
                    c2.add_widget(lbl)
                    for ev in matches:
                        w   = ev.get('winner', '')
                        t1  = ev['team1']
                        t2  = ev['team2']
                        s1  = ev.get('score_t1', 0)
                        s2  = ev.get('score_t2', 0)
                        t1c = _mc(T.PLAYER_CLR) if t1 in player_teams else (
                              _mc(T.POSITIVE) if t1 == w else _mc(T.TEXT_DIM))
                        t2c = _mc(T.PLAYER_CLR) if t2 in player_teams else (
                              _mc(T.POSITIVE) if t2 == w else _mc(T.TEXT_DIM))
                        c2.add_widget(_row(
                            f'[color={t1c}]{t1[:14]}[/color]',
                            f'[color={t1c}]{s1}[/color]:{s2}  '
                            f'[color={t2c}]{t2[:14]}[/color]',
                            lc=T.TEXT_MAIN, rc=T.TEXT_MAIN,
                        ))

                # Upcoming playoff matches (show next few)
                upcoming_stages = {}
                for j in range(idx, min(idx + 8, total)):
                    ev = queue[j]['result_ev']
                    st = ev.get('stage', '')
                    if any(kw in st for kw in _PLAYOFF_KEYWORDS):
                        upcoming_stages.setdefault(st, []).append(ev)
                for st, evs in list(upcoming_stages.items())[:2]:
                    sep = Label(text=f'[b]→ {st}[/b]', markup=True,
                                color=(1.0, 0.85, 0.30, 1), font_size='10sp',
                                size_hint_y=None, height=18, halign='left', valign='middle')
                    sep.bind(size=sep.setter('text_size'))
                    c2.add_widget(sep)
                    for ev in evs[:2]:
                        t1, t2 = ev['team1'], ev['team2']
                        t1c = _mc(T.PLAYER_CLR) if t1 in player_teams else _mc(T.TEXT_MAIN)
                        t2c = _mc(T.PLAYER_CLR) if t2 in player_teams else _mc(T.TEXT_MAIN)
                        c2.add_widget(_row(
                            f'[color={t1c}]{t1[:16]}[/color]',
                            f'vs [color={t2c}]{t2[:16]}[/color]',
                            lc=T.TEXT_MAIN, rc=T.TEXT_DIM,
                        ))

                _next_match_row(c2)
                row1.add_widget(c1)
                row1.add_widget(c2)

            # Tournament button: non-clickable during active tournament
            if hasattr(self, 'tournament_button'):
                self.tournament_button.disabled = True
                self.tournament_button.background_color = (0.55, 0.10, 0.10, 1)
        elif t_row:
            t_title_val, t_start = t_row
            try:
                days_left = (date.fromisoformat(t_start) - self.date_object).days
                days_txt  = f'через {days_left} дн.' if days_left >= 0 else 'идёт сейчас'
            except Exception:
                days_txt = ''
            c2 = _card(T.BG_CARD_TRN)
            c2.add_widget(_title('Следующий турнир', (0.80, 0.55, 1.00, 1)))
            c2.add_widget(_row(t_title_val[:28], f'[b]{days_txt}[/b]',
                               rc=(0.95, 0.85, 1.00, 1)))
            row1.add_widget(c1)
            row1.add_widget(c2)
            if hasattr(self, 'tournament_button'):
                self.tournament_button.disabled = False
                self.tournament_button.background_color = (0.65, 0.15, 0.15, 1)
        else:
            row1.add_widget(c1)
            if hasattr(self, 'tournament_button'):
                self.tournament_button.disabled = False
                self.tournament_button.background_color = (0.65, 0.15, 0.15, 1)

        outer.add_widget(row1)

        # ── Row 2: recent results + top-8 side by side ───────────────────────
        row2 = BoxLayout(size_hint_y=None, spacing=10)
        row2.bind(minimum_height=row2.setter('height'))

        if results:
            c3 = _card(T.BG_CARD_RES)
            c3.add_widget(_title('Последние турниры', T.POSITIVE))
            MEDALS = {1: 'Победа', 2: '2-е место', 3: '3-е место', 4: '4-е место'}
            for t_title_val, place in results[:5]:
                pc = T.place_color(place)
                c3.add_widget(_row(
                    t_title_val[:28],
                    f'[color={_mc(pc)}][b]{MEDALS.get(place, f"{place}-е место")}[/b][/color]',
                ))
            row2.add_widget(c3)

        c4 = _card(T.BG_CARD_B)
        c4.add_widget(_title('Топ рейтинга', T.ACCENT))
        for i, (n, r, pl) in enumerate(all_teams[:8], 1):
            is_my = (pl == 'yes')
            nc = f'[color={_mc(T.PLAYER_CLR)}]' if is_my else (
                f'[color={_mc(T.GOLD)}]' if i <= 3 else f'[color={_mc(T.TEXT_MAIN)}]'
            )
            lc = T.PLAYER_CLR if is_my else T.TEXT_LABEL
            c4.add_widget(_row(
                f'{nc}[b]#{i}[/b][/color]  {n.strip()[:20]}',
                f'{int(r)} pts', lc=lc,
            ))
        row2.add_widget(c4)

        outer.add_widget(row2)

        # ── Row 3: recent inbox messages ─────────────────────────────────────
        try:
            _conn2 = sqlite3.connect(self.db_name)
            _msgs = _conn2.execute(
                "SELECT subject, body, created_at, is_read FROM messages "
                "ORDER BY id DESC LIMIT 6"
            ).fetchall()
            _conn2.close()
            if _msgs:
                c5 = _card((0.08, 0.10, 0.14, 1))
                c5.add_widget(_title('Последние сообщения', (0.55, 0.75, 1.00, 1)))
                for subj, body, cdate, is_read in _msgs:
                    alpha = 1.0 if not is_read else 0.55
                    dm = Label(
                        text=f'  [b]{(subj or "—")[:32]}[/b]   '
                             f'[color=888888]{(cdate or "")[:10]}[/color]',
                        markup=True,
                        color=(0.90, 0.90, 0.95, alpha),
                        font_size=T.FS_SMALL, size_hint_y=None, height=T.ROW_H_SM,
                        halign='left', valign='middle',
                    )
                    dm.bind(size=dm.setter('text_size'))
                    c5.add_widget(dm)
                outer.add_widget(c5)
        except Exception:
            pass

        sv.add_widget(outer)
        self.main_area.add_widget(sv)

    def _migrate_db(self, db_name):
        """Add new columns to existing saves without breaking old data."""
        conn = sqlite3.connect(db_name)
        for ddl in [
            "ALTER TABLE players ADD COLUMN contract_end TEXT",
            "ALTER TABLE players ADD COLUMN train_priority TEXT",
            "ALTER TABLE players ADD COLUMN train_xp REAL DEFAULT 0",
            "ALTER TABLE teams ADD COLUMN cohesion INTEGER DEFAULT 0",
            "ALTER TABLE players ADD COLUMN poaching_team_id INTEGER",
            "ALTER TABLE players ADD COLUMN renewal_notified INTEGER DEFAULT 0",
            "ALTER TABLE teams ADD COLUMN region TEXT",
            "ALTER TABLE players ADD COLUMN age INTEGER DEFAULT 22",
            "ALTER TABLE teams ADD COLUMN tactic TEXT DEFAULT 'balanced'",
            "ALTER TABLE players ADD COLUMN pre_contract_team_id INTEGER",
            "ALTER TABLE characters ADD COLUMN reputation INTEGER DEFAULT 0",
            "ALTER TABLE players ADD COLUMN secondary_role TEXT",
            "ALTER TABLE players ADD COLUMN secondary_comp INTEGER DEFAULT 5",
            "ALTER TABLE teams ADD COLUMN last_bootcamp_date TEXT",
            "ALTER TABLE teams ADD COLUMN planned_bootcamp_date TEXT",
            "ALTER TABLE teams ADD COLUMN planned_bootcamp_cost INTEGER DEFAULT 0",
            "ALTER TABLE players ADD COLUMN achievement_flags TEXT DEFAULT ''",
            "ALTER TABLE player_career_stats ADD COLUMN earnings INTEGER DEFAULT 0",
        ]:
            try:
                conn.execute(ddl)
            except Exception:
                pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_snapshots (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id   INTEGER NOT NULL,
                snap_date TEXT NOT NULL,
                rating    REAL DEFAULT 0,
                budget    INTEGER DEFAULT 0,
                UNIQUE(team_id, snap_date)
            )
        """)
        conn.commit()
        conn.close()
        _migrate2(db_name)
        _migrate3(db_name)
        _migrate4(db_name)
        _migrate5(db_name)
        _migrate6(db_name)
        _migrate7(db_name)
        _migrate8(db_name)
        _migrate9(db_name)
        _migrate10(db_name)
        _migrate11(db_name)
        _migrate12(db_name)
        _migrate13(db_name)
        _migrate14(db_name)
        _migrate15(db_name)
        _migrate16(db_name)
        _migrate17(db_name)
        _migrate18(db_name)
        _migrate18_fix(db_name)
        _migrate19(db_name)
        _migrate20(db_name)
        _migrate21(db_name)
        _migrate22(db_name)
        _migrate23(db_name)
        _migrate24(db_name)
        _fix_orphans(db_name)
        _fix_team_regions(db_name)
        _fix_contracts(db_name)
        ensure_sponsors_table(db_name)
        _migrate25(db_name)
        _migrate26(db_name)
        _migrate27(db_name)
        _migrate28(db_name)
        _migrate29(db_name)
        _migrate30(db_name)
        _migrate31(db_name)
        _migrate32(db_name)
        _migrate33(db_name)
        _migrate34(db_name)
        _migrate35(db_name)
        # Assign signature heroes to any players that don't have them yet
        try:
            from logic.heroes import assign_signature_heroes
            assign_signature_heroes(db_name)
        except Exception as _e:
            T.log_err('assign_signature_heroes', _e)
        # Generate season goals for current year if none exist
        try:
            from logic.goals import generate_season_goals, ensure_table
            ensure_table(db_name)
            import sqlite3 as _sq
            _gc = _sq.connect(db_name)
            _yr = int(self.date_object.year)
            _cnt = _gc.execute(
                "SELECT COUNT(*) FROM season_goals WHERE year=?", (_yr,)
            ).fetchone()[0]
            _gc.close()
            if _cnt == 0:
                generate_season_goals(db_name, _yr)
        except Exception as _e:
            T.log_err('generate_season_goals', _e)

    def _return_loan_players(self, conn):
        """Return players from outgoing loans whose loan_until has passed."""
        cur = conn.cursor()
        today = str(self.date_object)
        cur.execute(
            """SELECT id, nickname, loan_team_id, role FROM players
               WHERE loan_team_id IS NOT NULL AND loan_until IS NOT NULL
                 AND loan_until <= ?""",
            (today,),
        )
        returning = cur.fetchall()
        for pid, nick, loan_tid, role in returning:
            if not role:
                continue
            # Find which slot the player occupies on loan team
            for col in ('carry', 'mid', 'offlane', 'partial_support', 'full_support'):
                cur.execute(f"SELECT {col} FROM teams WHERE id=?", (loan_tid,))
                slot = cur.fetchone()
                if slot and str(slot[0]) == str(pid):
                    cur.execute(f"UPDATE teams SET {col}=NULL WHERE id=?", (loan_tid,))
                    break
            # Find player's slot back on player team (same role)
            cur.execute(f"SELECT {role} FROM teams WHERE player='yes'")
            slot_back = cur.fetchone()
            if slot_back and not slot_back[0]:
                cur.execute(f"UPDATE teams SET {role}=? WHERE player='yes'", (pid,))
                pt = cur.execute("SELECT id FROM teams WHERE player='yes'").fetchone()
                cur.execute(
                    "UPDATE players SET team_id=?, loan_team_id=NULL, loan_until=NULL, loan_fee=0 WHERE id=?",
                    (pt[0] if pt else 0, pid),
                )
                conn.execute(
                    "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                    (f'{nick} вернулся из аренды.', today, 'Трансфер'),
                )
            else:
                # Slot taken — player becomes FA
                cur.execute(
                    "UPDATE players SET team_id=0, loan_team_id=NULL, loan_until=NULL, loan_fee=0 WHERE id=?",
                    (pid,),
                )
                conn.execute(
                    "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                    (f'{nick} вернулся из аренды (слот занят — стал СА).', today, 'Трансфер'),
                )

    def _expire_contracts(self, conn):
        """Release players whose contract_end has passed."""
        cur = conn.cursor()
        today = str(self.date_object)
        cur.execute(
            """SELECT id, nickname FROM players
               WHERE team_id != 0
                 AND contract_end IS NOT NULL
                 AND contract_end <= ?""",
            (today,),
        )
        expired = cur.fetchall()
        for pid, nick in expired:
            cur.execute(
                "SELECT micro_skills, macro_skills, wage, role, "
                "COALESCE(poaching_team_id,0), COALESCE(pre_contract_team_id,0), "
                "COALESCE(age,22), COALESCE(retirement_age,35), team_id "
                "FROM players WHERE id=?",
                (pid,),
            )
            pr = cur.fetchone()
            if pr:
                avg = ((pr[0] or 10) + (pr[1] or 10)) // 2
                expected = max(avg * 180, int((pr[2] or 0) * 0.85))
                role = pr[3]
                poaching_tid     = pr[4] or 0
                pre_contract_tid = pr[5] or 0
                player_age       = pr[6]
                retirement_age   = pr[7]
                player_team_id   = pr[8]

                # Retirement check: player on player's team hitting retirement age
                if player_age >= retirement_age and player_team_id:
                    try:
                        pt_check = cur.execute(
                            "SELECT player FROM teams WHERE id=?", (player_team_id,)
                        ).fetchone()
                        if pt_check and pt_check[0] == 'yes':
                            # Get career stats for ceremony
                            total_games = (cur.execute(
                                "SELECT COALESCE(SUM(games),0) FROM player_career_stats WHERE player_id=?",
                                (pid,)
                            ).fetchone() or (0,))[0]
                            total_earn = (cur.execute(
                                "SELECT COALESCE(SUM(earnings),0) FROM player_career_stats WHERE player_id=?",
                                (pid,)
                            ).fetchone() or (0,))[0]
                            from kivy.clock import Clock as _Clk
                            _Clk.schedule_once(
                                lambda dt, _n=nick, _a=player_age, _g=total_games, _e=total_earn:
                                    self._show_retirement_ceremony(_n, _a, _g, _e), 0.5
                            )
                    except Exception:
                        pass
            else:
                expected = 0
                role = None
                poaching_tid = 0
                pre_contract_tid = 0

            # Clear slot on current team
            cur.execute(
                """UPDATE teams SET
                     carry           = CASE WHEN carry=? THEN NULL ELSE carry END,
                     mid             = CASE WHEN mid=? THEN NULL ELSE mid END,
                     offlane         = CASE WHEN offlane=? THEN NULL ELSE offlane END,
                     partial_support = CASE WHEN partial_support=? THEN NULL ELSE partial_support END,
                     full_support    = CASE WHEN full_support=? THEN NULL ELSE full_support END""",
                (pid, pid, pid, pid, pid),
            )

            signed_to_poacher = False

            # Priority 1: pre-contract with player's own team
            if pre_contract_tid and role and not signed_to_poacher:
                cur.execute(f"SELECT {role} FROM teams WHERE id=?", (pre_contract_tid,))
                slot = cur.fetchone()
                if slot and not slot[0]:
                    cur.execute(f"UPDATE teams SET {role}=? WHERE id=?",
                                (pid, pre_contract_tid))
                    cur.execute(
                        "UPDATE players SET team_id=?, wage=?, expected_wage=?, "
                        "poaching_team_id=NULL, pre_contract_team_id=NULL, "
                        "renewal_notified=0 WHERE id=?",
                        (pre_contract_tid, expected, expected, pid),
                    )
                    cur.execute("SELECT name FROM teams WHERE id=?", (pre_contract_tid,))
                    dest = (cur.fetchone() or ('?',))[0]
                    conn.execute(
                        "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
                        (f"{nick} прибыл по пре-контракту в {dest}!",
                         'Трансфер'),
                    )
                    signed_to_poacher = True

            if poaching_tid and role:
                cur.execute(f"SELECT {role} FROM teams WHERE id=?", (poaching_tid,))
                slot_row = cur.fetchone()
                if slot_row and not slot_row[0]:
                    cur.execute(
                        f"UPDATE teams SET {role}=? WHERE id=?", (pid, poaching_tid)
                    )
                    cur.execute(
                        "UPDATE players SET team_id=?, wage=?, expected_wage=?, "
                        "poaching_team_id=NULL, renewal_notified=0 WHERE id=?",
                        (poaching_tid, expected, expected, pid),
                    )
                    cur.execute("SELECT name FROM teams WHERE id=?", (poaching_tid,))
                    ai_name_row = cur.fetchone()
                    ai_name = ai_name_row[0] if ai_name_row else '?'
                    conn.execute(
                        "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                        (f"Контракт {nick} истёк. Игрок перешёл в {ai_name}.",
                         'Спортивный директор'),
                    )
                    signed_to_poacher = True

            if not signed_to_poacher:
                cur.execute(
                    "UPDATE players SET team_id=0, wage=0, expected_wage=?, "
                    "poaching_team_id=NULL, renewal_notified=0 WHERE id=?",
                    (expected, pid),
                )
                conn.execute(
                    "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                    (f"Контракт {nick} истёк. Игрок стал свободным агентом.",
                     'Спортивный директор'),
                )

    def get_date_from_db(self, record_id):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT date FROM save WHERE id = ?", (record_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                # Предполагаем, что дата хранится в формате 'YYYY-MM-DD'
                return date.fromisoformat(result[0])
            else:
                raise ValueError("No record found with the given ID.")
        except Exception as e:
            print(f"Error retrieving date from database: {e}")
            return date.today()

    def _update_rect(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _update_main_area_rect(self, instance, value):
        self.rect_main_area.pos = self.main_area.pos
        self.rect_main_area.size = self.main_area.size

    def _load_ticker(self):
        try:
            conn = sqlite3.connect(self.db_name)
            rows = conn.execute(
                "SELECT subject, body FROM messages ORDER BY id DESC LIMIT 12"
            ).fetchall()
            conn.close()
            items = []
            for subj, body in rows:
                text = (subj or '').strip() or (body or '')[:60].strip()
                if text:
                    items.append(text)
            sep = '     •     '
            self._ticker_full = sep.join(items) + sep if items else ''
            self._ticker_offset[0] = 0.0
        except Exception:
            self._ticker_full = ''

    def _tick_news(self, dt):
        text = getattr(self, '_ticker_full', '')
        if not text:
            return
        spd = 60   # pixels per second
        self._ticker_offset[0] = (self._ticker_offset[0] + spd * dt) % max(1, len(text) * 8)
        char_off = int(self._ticker_offset[0] / 8)
        rotated = text[char_off:] + text[:char_off]
        self._ticker_lbl.text = rotated[:120]

    def get_next_tournament_date(self):
        # During active tournament, next "event" is tomorrow (next match day)
        at = self._get_active_tournament()
        if at:
            return str(self.date_object + timedelta(days=1))
        date_object = self.get_date_from_db(1)
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT start_date FROM tournaments "
            "WHERE start_date >= ? AND place1 IS NULL "
            "ORDER BY start_date ASC LIMIT 1",
            (date_object,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def _deduct_salaries(self, conn):
        """Monthly: deduct wages, run AI training, update morale, expire contracts."""
        cursor = conn.cursor()

        # Player team salaries
        cursor.execute(
            "SELECT id, carry, mid, offlane, partial_support, full_support "
            "FROM teams WHERE player='yes'"
        )
        team = cursor.fetchone()
        if team:
            team_id = team[0]
            player_ids = [pid for pid in team[1:] if pid]
            if player_ids:
                placeholders = ','.join('?' * len(player_ids))
                cursor.execute(
                    f"SELECT COALESCE(SUM(wage), 0) FROM players WHERE id IN ({placeholders})",
                    player_ids,
                )
                total_wage = cursor.fetchone()[0] or 0
                if total_wage > 0:
                    cursor.execute(
                        "UPDATE teams SET budget=MAX(0, budget-?) WHERE id=?",
                        (total_wage, team_id),
                    )

                # Soft salary cap: $200k/month. Excess → luxury tax $30k
                _SALARY_CAP = 200_000
                _LUXURY_TAX = 30_000
                if total_wage > _SALARY_CAP:
                    cursor.execute(
                        "UPDATE teams SET budget=MAX(0, budget-?) WHERE id=?",
                        (_LUXURY_TAX, team_id),
                    )
                    conn.execute(
                        "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                        (
                            f'Налог на роскошь: зарплатный фонд ${total_wage:,} превышает '
                            f'лимит ${_SALARY_CAP:,}. Штраф −${_LUXURY_TAX:,}.',
                            str(self.date_object), 'Финансы',
                        ),
                    )

        # AI team wage deductions
        cursor.execute(
            "SELECT t.id, SUM(COALESCE(p.wage, 0)) "
            "FROM teams t "
            "JOIN players p ON p.team_id = t.id "
            "WHERE t.player != 'yes' "
            "GROUP BY t.id"
        )
        for ai_tid, ai_wages in cursor.fetchall():
            if ai_wages and ai_wages > 0:
                cursor.execute(
                    "UPDATE teams SET budget=MAX(0, budget-?) WHERE id=?",
                    (ai_wages, ai_tid),
                )

        # AI operational expenses — scales with budget to prevent hoarding
        cursor.execute(
            "SELECT id, COALESCE(rating,0), COALESCE(budget,0) FROM teams WHERE player!='yes'"
        )
        for ai_tid, ai_rating, ai_budget in cursor.fetchall():
            # Base: rating-driven routine costs
            base = 15_000 + int(ai_rating * 20)
            # Prestige spending: richer teams burn proportionally more
            if ai_budget > 2_000_000:
                base += int(ai_budget * 0.06)   # 6% of excess wealth/month
            elif ai_budget > 1_000_000:
                base += int(ai_budget * 0.04)
            elif ai_budget > 500_000:
                base += int(ai_budget * 0.02)
            expenses = _random.randint(base, base + 20_000)
            # Hard floor 100k to keep AI from going broke
            cursor.execute(
                "UPDATE teams SET budget=MAX(100_000, budget-?) WHERE id=?",
                (expenses, ai_tid),
            )
            # Quarterly big expenditure (25% monthly chance = ~once per quarter)
            if _random.random() < 0.25 and ai_budget > 600_000:
                big_spend = _random.randint(80_000, min(300_000, int(ai_budget * 0.15)))
                cursor.execute(
                    "UPDATE teams SET budget=MAX(100_000, budget-?) WHERE id=?",
                    (big_spend, ai_tid),
                )

        # Monthly team snapshot for dashboard trend
        snap_row = cursor.execute(
            "SELECT id, COALESCE(rating,0), COALESCE(budget,0) FROM teams WHERE player='yes'"
        ).fetchone()
        if snap_row:
            cursor.execute(
                "INSERT OR IGNORE INTO team_snapshots (team_id, snap_date, rating, budget) "
                "VALUES (?, ?, ?, ?)",
                (snap_row[0], str(self.date_object), int(snap_row[1]), snap_row[2]),
            )

        self._return_loan_players(conn)
        self._expire_contracts(conn)
        self._notify_expiring_contracts(conn)
        self._repay_loan(conn)
        self._trim_messages(conn)
        conn.commit()

        update_morale_monthly(self.db_name)
        update_form_monthly(self.db_name)
        # Motivator skill: +1 morale to all roster players
        try:
            from logic.manager_skills import get_skill_level
            mot_lvl = get_skill_level(self.db_name, 'motivator')
            if mot_lvl > 0:
                _mc = sqlite3.connect(self.db_name)
                _mc.execute("""
                    UPDATE players SET morale=MIN(10,COALESCE(morale,5)+?)
                    WHERE team_id IN (SELECT id FROM teams WHERE player='yes')
                """, (mot_lvl,))
                _mc.commit(); _mc.close()
        except Exception:
            pass
        # Monthly XP flush: apply accumulated train_xp to player skills
        try:
            from ingame_interface.scrimmage import _flush_scrim_xp
            _conn_pt = sqlite3.connect(self.db_name)
            _pt = _conn_pt.execute("SELECT name FROM teams WHERE player='yes'").fetchone()
            _conn_pt.close()
            if _pt:
                _flush_scrim_xp(self.db_name, _pt[0].strip())
        except Exception as _e:
            T.log_err('monthly_xp_flush', _e)
        develop_free_agents(self.db_name)
        set_ai_train_priorities(self.db_name)
        _enforce_conflict_states(self.db_name)
        ai_poach_attempt(self.db_name, str(self.date_object))
        if _is_transfer_window(str(self.date_object)):
            ai_buy_offer(self.db_name)
        ai_team_trades(self.db_name)
        # Monthly AI roster maintenance: fill empty slots from free agents
        ai_transfers(self.db_name)

        # Streaming / merch income
        _pay_streaming_income(self.db_name, str(self.date_object))

        # Manager reputation: small monthly gain for staying active
        try:
            _rc = sqlite3.connect(self.db_name)
            _team_row = _rc.execute(
                "SELECT COALESCE(rating,0), COALESCE(cohesion,0) FROM teams WHERE player='yes'"
            ).fetchone()
            if _team_row:
                _rating, _cohesion = _team_row
                # +1 always for being active, +1 if cohesion high, +1 if top rating
                _rep_gain = 1
                if _cohesion >= 70:
                    _rep_gain += 1
                if _rating >= 500:
                    _rep_gain += 1
                _rc.execute(
                    "UPDATE characters SET reputation=COALESCE(reputation,0)+?",
                    (_rep_gain,)
                )
            _rc.commit(); _rc.close()
        except Exception:
            pass

        # Cohesion goal check
        from logic.goals import update_goal, year_from_date
        year = year_from_date(str(self.date_object))
        coh_row = conn.execute("SELECT COALESCE(cohesion,0) FROM teams WHERE player='yes'").fetchone()
        if coh_row:
            update_goal(self.db_name, year, 'cohesion_target', coh_row[0])

        # Player career milestones
        self._check_player_milestones()

        # Monthly news
        from logic.news import generate_monthly_news
        for news_text in generate_monthly_news(self.db_name):
            c = sqlite3.connect(self.db_name)
            c.execute("INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
                      (news_text, 'Новости'))
            c.commit(); c.close()

        # Sponsor monthly income
        sponsor_pay = pay_monthly_income(self.db_name)
        if sponsor_pay:
            sname, samount = sponsor_pay
            c = sqlite3.connect(self.db_name)
            c.execute(
                "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                (f'Спонсор {sname}: ежемесячный доход +${samount:,}', 'Организация'),
            )
            c.commit()
            c.close()

        # Monthly achievement check + rep bonus
        try:
            from logic.achievements import check_achievements, get_rep_monthly_bonus
            _new_ach = check_achievements(self.db_name, str(self.date_object))
            for _aname, _abonus in _new_ach:
                _mc = sqlite3.connect(self.db_name)
                _mc.execute(
                    "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                    (f'[ТОП] Достижение: «{_aname}»! Бонус: {_abonus}',
                     str(self.date_object), 'Достижения')
                )
                _mc.commit(); _mc.close()
            _rep_bonus = get_rep_monthly_bonus(self.db_name)
            if _rep_bonus:
                _rb = sqlite3.connect(self.db_name)
                _rb.execute(
                    "UPDATE teams SET org_reputation=MIN(100,COALESCE(org_reputation,20)+?) "
                    "WHERE player='yes'", (_rep_bonus,)
                )
                _rb.commit(); _rb.close()
        except Exception:
            pass

        # Fatigue decay (Feature 3): all team players recover 15 fatigue/month
        try:
            _fc = sqlite3.connect(self.db_name)
            _fc.execute(
                "UPDATE players SET fatigue=MAX(0, COALESCE(fatigue,0)-15) "
                "WHERE team_id IN (SELECT id FROM teams WHERE player='yes')"
            )
            _fc.commit()
            _fc.close()
        except Exception:
            pass

        # Meta patch rotation (Feature 1): rotate every even month
        if self.date_object.month % 2 == 0 and self.date_object.day == 1:
            try:
                from logic.meta import rotate_patch
                new_pname, new_prole = rotate_patch(self.db_name, str(self.date_object))
                _ROLE_RU_SHORT = {
                    'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Offlane',
                    'partial_support': 'Sup 4', 'full_support': 'Sup 5',
                }
                _mc2 = sqlite3.connect(self.db_name)
                _mc2.execute(
                    "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                    (f'Вышел патч {new_pname}: '
                     f'{_ROLE_RU_SHORT.get(new_prole, new_prole)} усилен метой.',
                     str(self.date_object), 'Новости')
                )
                _mc2.commit(); _mc2.close()
            except Exception:
                pass

        # Investor income deduction (Feature 8)
        try:
            _ic = sqlite3.connect(self.db_name)
            inv_row = _ic.execute(
                "SELECT id, COALESCE(investor_cut_pct,0), COALESCE(investor_end_date,''), "
                "COALESCE(investor_name,'') FROM teams WHERE player='yes'"
            ).fetchone()
            if inv_row:
                inv_id, inv_cut, inv_end, inv_name = inv_row
                if inv_cut > 0 and inv_end and inv_end >= str(self.date_object):
                    # Deduct cut from streaming income retroactively (estimate)
                    stream_est = max(0, int(
                        _ic.execute(
                            "SELECT COALESCE(rating,0) FROM teams WHERE id=?", (inv_id,)
                        ).fetchone()[0] * 120 * inv_cut / 100
                    ))
                    if stream_est > 0:
                        _ic.execute(
                            "UPDATE teams SET budget=MAX(0,budget-?) WHERE id=?",
                            (stream_est, inv_id)
                        )
                        _ic.execute(
                            "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                            (f'Инвестор {inv_name}: выплата доли {inv_cut}% = −${stream_est:,}',
                             str(self.date_object), 'Финансы')
                        )
                    _ic.commit()
            _ic.close()
        except Exception:
            pass

        # Random monthly event (60% chance)
        import random
        if random.random() < 0.60:
            event = random_event_monthly(self.db_name, str(self.date_object))
            if event:
                if len(event) >= 3 and event[2] == 'investor_pending':
                    _ev_data = event[3] if len(event) > 3 else {}
                    c = sqlite3.connect(self.db_name)
                    c.execute(
                        "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                        (event[1], 'Организация'),
                    )
                    c.commit(); c.close()
                    self._show_investor_popup(_ev_data)
                elif len(event) == 3 and event[2] == 'popup':
                    title, text, _ = event
                    c = sqlite3.connect(self.db_name)
                    c.execute(
                        "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                        (text, 'Новости'),
                    )
                    c.commit()
                    c.close()
                    self._show_event_popup(title, text)
                else:
                    title, text = event[0], event[1]
                    c = sqlite3.connect(self.db_name)
                    c.execute(
                        "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                        (text, title),
                    )
                    c.commit()
                    c.close()

        # Player dialogue
        from logic.player_dialogue import get_player_dialogue
        dialogue = get_player_dialogue(self.db_name)
        if dialogue:
            self._show_player_dialogue(dialogue)

    def _show_retirement_ceremony(self, nick, age, total_games, total_earn):
        try:
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.label import Label
            from kivy.uix.button import Button

            p = Popup(title='Прощание с игроком', size_hint=(0.55, 0.52))
            root = BoxLayout(orientation='vertical', padding=12, spacing=8)

            lines = [
                f'[b][color=ffd700]{nick}[/color][/b] завершает карьеру.',
                f'{age} лет  ·  {total_games} матчей в карьере',
            ]
            if total_earn:
                lines.append(f'Призовые за карьеру: ${total_earn:,}')
            lines.append('')
            lines.append('Спасибо за всё, что ты сделал для команды. Удачи!')

            for line in lines:
                lbl = Label(
                    text=line, markup=True,
                    color=(0.92, 0.92, 0.92, 1) if not line.startswith('[b]') else (1, 1, 1, 1),
                    size_hint_y=None, height=30,
                    halign='center', valign='middle', font_size='13sp',
                )
                lbl.bind(size=lbl.setter('text_size'))
                root.add_widget(lbl)

            close = Button(
                text='Проводить игрока', size_hint_y=None, height=46,
                background_color=(0.18, 0.35, 0.60, 1), background_normal='',
            )
            close.bind(on_press=p.dismiss)
            root.add_widget(close)
            p.content = root
            p.open()
        except Exception:
            pass

    def _check_player_milestones(self):
        """Generate inbox messages for player career milestones."""
        try:
            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()
            pt = c.execute("SELECT id, carry,mid,offlane,partial_support,full_support "
                           "FROM teams WHERE player='yes'").fetchone()
            if not pt:
                conn.close(); return
            pids = [p for p in pt[1:] if p]
            if not pids:
                conn.close(); return

            today = str(self.date_object)
            msgs = []

            for pid in pids:
                p = c.execute(
                    "SELECT nickname, COALESCE(comp_exp,0), "
                    "COALESCE(micro_skills,0)+COALESCE(macro_skills,0), "
                    "COALESCE(achievement_flags,'')"
                    " FROM players WHERE id=?", (pid,)
                ).fetchone()
                if not p:
                    continue
                nick, exp, skill_sum, flags_str = p
                flags = set(flags_str.split(',')) if flags_str else set()
                new_flags = set(flags)

                # Comp_exp milestones
                for milestone, label in [(50, '50 матчей'), (100, '100 матчей'), (200, '200 матчей'), (500, '500 матчей')]:
                    flag = f'exp{milestone}'
                    if exp >= milestone and flag not in flags:
                        new_flags.add(flag)
                        msgs.append(f'{nick} сыграл {label} в профессиональной сцене — настоящий ветеран!')

                # Skill milestones
                for threshold, label in [(140, 'ТОП-класс'), (160, 'элита'), (180, 'легенда сцены')]:
                    flag = f'sk{threshold}'
                    if skill_sum >= threshold and flag not in flags:
                        new_flags.add(flag)
                        msgs.append(f'{nick} достиг уровня «{label}» — micro+macro = {skill_sum}!')

                if new_flags != flags:
                    c.execute("UPDATE players SET achievement_flags=? WHERE id=?",
                              (','.join(sorted(new_flags)), pid))

            conn.commit()
            for msg in msgs:
                conn.execute("INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                             (msg, today, 'Карьера'))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _show_season_review(self, year):
        """Pop up season summary when the year rolls over."""
        try:
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.gridlayout import GridLayout
            from kivy.uix.label import Label
            from kivy.uix.button import Button
            from kivy.uix.scrollview import ScrollView

            conn = sqlite3.connect(self.db_name)
            c = conn.cursor()

            # Team stats
            team = c.execute("SELECT id, name, COALESCE(rating,0), COALESCE(fans,0) "
                             "FROM teams WHERE player='yes'").fetchone()
            if not team:
                conn.close(); return
            tid, tname, rating, fans = team

            # Tournament results this year
            results = []
            for row in c.execute(f"""
                SELECT t.name, t.place1,t.place2,t.place3,t.place4,
                       t.place5,t.place6,t.place7,t.place8
                FROM tournaments t
                WHERE strftime('%Y',t.start_date)='{year}'
                  AND t.place1 IS NOT NULL
            """).fetchall():
                tname_t = row[0]
                for i, p in enumerate(row[1:], 1):
                    if p == tid:
                        results.append((tname_t, i)); break

            # MVP (player with most games this season)
            mvp = c.execute(f"""
                SELECT p.nickname, SUM(cs.games) as g, COALESCE(SUM(cs.earnings),0)
                FROM player_career_stats cs JOIN players p ON p.id=cs.player_id
                WHERE cs.season={year} AND p.team_id={tid}
                GROUP BY cs.player_id ORDER BY g DESC LIMIT 1
            """).fetchone()

            # Best young player (age<=22, highest skill sum on team)
            best_young = c.execute(f"""
                SELECT p.nickname, p.micro_skills+p.macro_skills as sk, COALESCE(p.age,22)
                FROM players p WHERE p.team_id={tid} AND COALESCE(p.age,22)<=22
                ORDER BY sk DESC LIMIT 1
            """).fetchone()

            # Veteran (highest comp_exp on team)
            veteran = c.execute(f"""
                SELECT p.nickname, COALESCE(p.comp_exp,0), COALESCE(p.age,22)
                FROM players p WHERE p.team_id={tid}
                ORDER BY p.comp_exp DESC LIMIT 1
            """).fetchone()

            # Total team earnings this season
            total_prizes = c.execute(f"""
                SELECT COALESCE(SUM(cs.earnings),0) FROM player_career_stats cs
                JOIN players p ON p.id=cs.player_id
                WHERE cs.season={year} AND p.team_id={tid}
            """).fetchone()[0]

            # Goals achieved
            goals_done = c.execute(
                f"SELECT COUNT(*) FROM season_goals WHERE year={year} AND completed=1"
            ).fetchone()[0]
            goals_total = c.execute(
                f"SELECT COUNT(*) FROM season_goals WHERE year={year}"
            ).fetchone()[0]

            conn.close()

            # Build popup
            _BG = (0.07, 0.09, 0.13, 1)
            _ACC = (0.35, 0.85, 1.00, 1)
            _GOLD = (1.00, 0.85, 0.25, 1)
            _WHITE = (0.92, 0.92, 0.92, 1)

            p = Popup(title='', size_hint=(0.60, 0.75))
            root = BoxLayout(orientation='vertical', padding=10, spacing=8)

            def _lbl(text, color=_WHITE, height=32, bold=False, fs='13sp'):
                t = f'[b]{text}[/b]' if bold else text
                l = Label(text=t, markup=True, color=color,
                          size_hint_y=None, height=height,
                          halign='center', valign='middle', font_size=fs)
                l.bind(size=l.setter('text_size'))
                return l

            root.add_widget(_lbl(f'ИТОГИ {year} СЕЗОНА', _ACC, 44, True, '18sp'))
            root.add_widget(_lbl(f'{tname.strip()}', _WHITE, 28, False, '14sp'))

            sv = ScrollView(size_hint=(1, 1))
            gl = GridLayout(cols=1, size_hint_y=None, spacing=4)
            gl.bind(minimum_height=gl.setter('height'))

            if results:
                gl.add_widget(_lbl('Турниры:', _ACC, 28, True))
                MEDALS = {1: '1-е', 2: '2-е', 3: '3-е', 4: '4-е'}
                for tn, place in results:
                    pc = _GOLD if place == 1 else _WHITE
                    gl.add_widget(_lbl(f'{MEDALS.get(place, f"{place}-е")}  {tn[:30]}', pc, 26))
            else:
                gl.add_widget(_lbl('Турниры: не участвовали', (0.5, 0.5, 0.5, 1), 26))

            # Season awards section
            gl.add_widget(_lbl('─── НАГРАДЫ СЕЗОНА ───', _GOLD, 26, True))
            if mvp:
                gl.add_widget(_lbl(
                    f'MVP MVP сезона: {mvp[0]}  ({mvp[1]} матчей, призовые ${mvp[2]:,})',
                    _GOLD, 28, True))
            if best_young:
                gl.add_widget(_lbl(
                    f'[МОЛ] Молодой таланты: {best_young[0]}  ({best_young[2]} лет, скилл {best_young[1]})',
                    (0.50, 0.90, 1.00, 1), 26))
            if veteran:
                gl.add_widget(_lbl(
                    f'[ВЕТ] Ветеран года: {veteran[0]}  ({veteran[2]} лет, опыт {veteran[1]} матчей)',
                    (0.80, 0.65, 1.00, 1), 26))
            if total_prizes:
                gl.add_widget(_lbl(
                    f'$ Всего призовых игрокам: ${total_prizes:,}',
                    (0.40, 0.90, 0.50, 1), 26))

            gl.add_widget(_lbl('─────────────────────', (0.4, 0.4, 0.4, 1), 18))
            gl.add_widget(_lbl(f'Рейтинг: {int(rating)} pts', _WHITE, 26))
            gl.add_widget(_lbl(f'Фанаты: {fans:,}', (1.0, 0.55, 0.80, 1), 26))
            gl.add_widget(_lbl(f'Цели выполнены: {goals_done}/{goals_total}',
                               (0.25, 0.90, 0.42, 1) if goals_done else _WHITE, 26))

            sv.add_widget(gl)
            root.add_widget(sv)

            close = Button(text='Начать новый сезон', size_hint_y=None, height=48,
                           background_color=(0.18, 0.50, 0.22, 1), background_normal='')
            close.bind(on_press=p.dismiss)
            root.add_widget(close)
            p.content = root
            p.open()
        except Exception as _e:
            T.log_err('season_review', _e)

    def _check_planned_bootcamp(self, conn):
        today = str(self.date_object)
        row = conn.execute(
            "SELECT id, COALESCE(planned_bootcamp_date,''), COALESCE(planned_bootcamp_cost,0), "
            "COALESCE(budget,0) FROM teams WHERE player='yes'"
        ).fetchone()
        if not row:
            return
        tid, pbd, pbc, budget = row
        if not pbd or pbd > today:
            return
        # Fire bootcamp
        cost = pbc or 15_000
        coh_gain = 15 if cost >= 25_000 else 10
        mor_gain = 1  if cost >= 25_000 else 0
        if budget >= cost:
            conn.execute(
                "UPDATE teams SET budget=budget-?, cohesion=MIN(100,COALESCE(cohesion,0)+?), "
                "last_bootcamp_date=?, planned_bootcamp_date=NULL, planned_bootcamp_cost=0 WHERE id=?",
                (cost, coh_gain, today, tid),
            )
            if mor_gain:
                slots = conn.execute(
                    "SELECT carry,mid,offlane,partial_support,full_support FROM teams WHERE id=?",
                    (tid,)
                ).fetchone() or ()
                for pid in slots:
                    if pid:
                        conn.execute(
                            "UPDATE players SET morale=MIN(10,COALESCE(morale,5)+1) WHERE id=?",
                            (pid,)
                        )
            conn.execute(
                "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                (f'Запланированный буткемп проведён: +{coh_gain} сыгранности'
                 + (f', +{mor_gain} мораль' if mor_gain else '') + f'  −${cost:,}',
                 today, 'Организация'),
            )
        else:
            # Not enough budget — clear planned
            conn.execute(
                "UPDATE teams SET planned_bootcamp_date=NULL, planned_bootcamp_cost=0 WHERE id=?",
                (tid,)
            )
            conn.execute(
                "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                ('Запланированный буткемп отменён — недостаточно средств.', today, 'Организация'),
            )

    def _send_weekly_standings(self, conn):
        rows = conn.execute(
            "SELECT name, COALESCE(rating,0), player FROM teams "
            "ORDER BY COALESCE(rating,0) DESC LIMIT 5"
        ).fetchall()
        if not rows:
            return
        lines = []
        for i, (name, rating, pl) in enumerate(rows, 1):
            tag = ' ← вы' if pl == 'yes' else ''
            lines.append(f'  {i}. {name.strip()} — {int(rating)} pts{tag}')
        my_row = conn.execute(
            "SELECT COALESCE(rating,0) FROM teams WHERE player='yes'"
        ).fetchone()
        my_rank = next((i+1 for i, (n, r, p) in enumerate(
            conn.execute("SELECT name,COALESCE(rating,0),player FROM teams ORDER BY COALESCE(rating,0) DESC").fetchall()
        ) if p == 'yes'), '?')
        msg = f'Рейтинг-лист недели — вы #{my_rank}:\n' + '\n'.join(lines)
        conn.execute(
            "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
            (msg, str(self.date_object), 'Рейтинг'),
        )

    def _trim_messages(self, conn):
        """Keep only recent messages per noisy category, cap total."""
        # Noisy authors: keep last 25 each
        for author_like, keep in [
            ('Трансфер', 25),
            ('Новости',  20),
            ('Скаутинг', 10),
            ('Цели',     15),
        ]:
            conn.execute("""
                DELETE FROM messages WHERE author LIKE ? AND id NOT IN (
                    SELECT id FROM messages WHERE author LIKE ?
                    ORDER BY id DESC LIMIT ?
                )
            """, (f'%{author_like}%', f'%{author_like}%', keep))
        # Hard cap: never more than 300 messages total
        conn.execute("""
            DELETE FROM messages WHERE id NOT IN (
                SELECT id FROM messages ORDER BY id DESC LIMIT 300
            )
        """)

    def _repay_loan(self, conn):
        row = conn.execute(
            "SELECT id, COALESCE(loan_amount,0), COALESCE(loan_monthly,0) "
            "FROM teams WHERE player='yes'"
        ).fetchone()
        if not row or row[1] <= 0:
            return
        team_id, loan, monthly = row
        payment = min(monthly, loan)
        conn.execute(
            "UPDATE teams SET budget=MAX(0,budget-?), "
            "loan_amount=MAX(0,loan_amount-?) WHERE id=?",
            (payment, payment, team_id),
        )
        if max(0, loan - payment) == 0:
            conn.execute("UPDATE teams SET loan_monthly=0 WHERE id=?", (team_id,))
            conn.execute(
                "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
                ("Кредит полностью погашен!", "Финансы"),
            )

    def _notify_expiring_contracts(self, conn):
        """Send inbox warning once when a player's contract is within 60 days."""
        from datetime import timedelta
        cur = conn.cursor()
        deadline = str(self.date_object + timedelta(days=60))
        cur.execute(
            """SELECT id, nickname, contract_end FROM players
               WHERE team_id != 0
                 AND contract_end IS NOT NULL
                 AND contract_end <= ?
                 AND contract_end > ?
                 AND COALESCE(renewal_notified, 0) = 0""",
            (deadline, str(self.date_object)),
        )
        for pid, nick, cend in cur.fetchall():
            conn.execute(
                "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                (
                    f"Контракт {nick} истекает {cend}. Рассмотрите продление во вкладке Трансферы.",
                    'Спортивный директор',
                ),
            )
            cur.execute("UPDATE players SET renewal_notified=1 WHERE id=?", (pid,))

    def on_next(self, instance):
        if self._auto_advance_event:
            self._stop_auto_advance()
        else:
            self._start_auto_advance()

    def _start_auto_advance(self):
        from settings import AUTO_ADVANCE_SPEED
        self._next_btn.text = '|| Стоп'
        self._next_btn.background_color = (0.75, 0.2, 0.05, 1)
        self._auto_advance_event = Clock.schedule_interval(
            self._auto_advance_step, AUTO_ADVANCE_SPEED)

    def _stop_auto_advance(self):
        if self._auto_advance_event:
            self._auto_advance_event.cancel()
            self._auto_advance_event = None
        self._next_btn.text = 'Далее  >'
        self._next_btn.background_color = (0.75, 0.65, 0.05, 1)

    def _auto_advance_step(self, dt):
        had_notification = self._advance_one_day()
        if had_notification:
            self._stop_auto_advance()

    def on_skip_to_tournament(self, instance):
        if self._auto_advance_event:
            self._stop_auto_advance()

        # Show loading indicator on skip button
        orig_text = self._skip_btn.text if hasattr(self, '_skip_btn') else ''
        if hasattr(self, '_skip_btn'):
            self._skip_btn.text = 'Симуляция...'
            self._skip_btn.disabled = True

        def _restore_btn():
            if hasattr(self, '_skip_btn'):
                self._skip_btn.text = orig_text or '>> Матч'
                self._skip_btn.disabled = False

        at = self._get_active_tournament()
        if at:
            # Skip through non-player matches until player match or end
            _sim_step = [0]
            while True:
                at2 = self._get_active_tournament()
                if not at2:
                    break
                idx = at2['match_idx']
                queue = at2['match_queue']
                total = len(queue)
                if idx >= total:
                    self._finish_active_tournament(at2)
                    break
                next_item = queue[idx]
                if next_item['result_ev'].get('is_player_match') and next_item.get('lineup_ev'):
                    self._play_match_day(suppress_notifications=False)
                    break
                _sim_step[0] += 1
                if hasattr(self, '_skip_btn'):
                    self._skip_btn.text = f'Сим {idx}/{total}'
                self._advance_one_day(suppress_notifications=True)
            _restore_btn()
            return

        # No active tournament: skip to next tournament start
        next_date = self.get_next_tournament_date()
        if not next_date:
            return
        target = date.fromisoformat(next_date)
        days_total = (target - self.date_object).days
        days_done = [0]
        while self.date_object < target:
            days_done[0] += 1
            if hasattr(self, '_skip_btn') and days_total > 5:
                self._skip_btn.text = f'Сим {days_done[0]}/{days_total}д'
            self._advance_one_day(suppress_notifications=True)
        # Trigger tournament start
        if str(self.date_object) == next_date:
            conn2 = sqlite3.connect(self.db_name)
            tourn_row = conn2.execute(
                "SELECT id, name FROM tournaments WHERE start_date=? AND place1 IS NULL LIMIT 1",
                (next_date,)
            ).fetchone()
            conn2.close()
            if tourn_row:
                self._init_tournament(tourn_row[0], tourn_row[1])
                self._play_match_day(suppress_notifications=False)
        _restore_btn()

    def _advance_one_day(self, suppress_notifications=False):
        """Advance date by 1 day. Returns True if a notification was triggered."""
        prev_month = self.date_object.month
        prev_year  = self.date_object.year
        self.date_object += timedelta(days=1)
        database = self.db_name
        conn = None
        notification_triggered = False
        try:
            conn = sqlite3.connect(database)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM messages")
            prev_msg_count = cursor.fetchone()[0]

            cursor.execute("UPDATE save SET date = ? WHERE id = 1", (str(self.date_object),))

            if self.date_object.month != prev_month and self.date_object.day == 1:
                self._deduct_salaries(conn)
                if self.date_object.year != prev_year:
                    from kivy.clock import Clock as _Clk
                    _Clk.schedule_once(
                        lambda dt: self._show_season_review(prev_year), 0.5
                    )

            # Weekly standings update (every 7 days)
            if self.date_object.toordinal() % 7 == 0:
                self._send_weekly_standings(conn)

            # Planned bootcamp auto-fire
            self._check_planned_bootcamp(conn)

            conn.commit()

            cursor.execute("SELECT date FROM save WHERE id = 1")
            updated_date = cursor.fetchone()

            if updated_date:
                updated_date_value = updated_date[0]

                at = self._get_active_tournament()

                if at:
                    # Tournament in progress: play multiple matches per day
                    # so tournament finishes within its scheduled duration
                    mpd = self._matches_per_day(at)
                    for _ in range(mpd):
                        at2 = self._get_active_tournament()
                        if not at2:
                            break
                        triggered = self._play_match_day(suppress_notifications)
                        if triggered:
                            notification_triggered = True
                            break
                else:
                    next_tournament_date = self.get_next_tournament_date()

                    # Day before tournament: AI fills empty slots
                    if next_tournament_date:
                        from datetime import date as _date
                        days_left = (
                            _date.fromisoformat(next_tournament_date) -
                            _date.fromisoformat(updated_date_value)
                        ).days
                        if days_left == 1:
                            from logic.ai import ai_transfers
                            ai_transfers(self.db_name)

                    if next_tournament_date and updated_date_value == next_tournament_date:
                        # Start tournament
                        conn2 = sqlite3.connect(self.db_name)
                        tourn_row = conn2.execute(
                            "SELECT id, name FROM tournaments "
                            "WHERE start_date=? AND place1 IS NULL "
                            "ORDER BY start_date LIMIT 1",
                            (updated_date_value,)
                        ).fetchone()
                        conn2.close()
                        if tourn_row:
                            self._init_tournament(tourn_row[0], tourn_row[1])
                            triggered = self._play_match_day(suppress_notifications)
                            if triggered:
                                notification_triggered = True

                self.today_date_button.text = updated_date_value
                self.tournament_button.text = self.get_next_tournament()
                self._refresh_menu_badges()
                # Don't clear match popup if player is in a match
                if not getattr(self, '_active_inline_popup', None):
                    self._show_dashboard()

                # Новые сообщения — останавливаем авто-листание
                if not suppress_notifications:
                    cursor.execute("SELECT COUNT(*) FROM messages")
                    if cursor.fetchone()[0] > prev_msg_count:
                        notification_triggered = True

                # Бюджет
                cursor.execute("SELECT budget FROM teams WHERE player='yes'")
                budget_row = cursor.fetchone()
                if budget_row and (budget_row[0] or 0) <= 0:
                    self._show_bankruptcy()
                    notification_triggered = True
        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")
        finally:
            if conn:
                conn.close()
        return notification_triggered



    def _show_bankruptcy(self):
        from kivy.uix.label import Label
        content = BoxLayout(orientation='vertical', padding=20, spacing=10)
        content.add_widget(Label(
            text='[b]Организация обанкротилась[/b]', markup=True,
            size_hint_y=None, height=50, color=(1, 0.3, 0.3, 1),
        ))
        content.add_widget(Label(
            text='Бюджет команды достиг нуля.\nМенеджер уволен.',
            size_hint_y=None, height=60, halign='center',
        ))
        ok_btn = Button(text='Вернуться в главное меню',
                        size_hint_y=None, height=48,
                        background_color=(0.7, 0.2, 0.2, 1))
        content.add_widget(ok_btn)
        popup = Popup(title='', content=content,
                      size_hint=(0.55, 0.40), auto_dismiss=False)
        ok_btn.bind(on_press=lambda _: (popup.dismiss(), self.popup.dismiss()))
        popup.open()

    def _refresh_menu_badges(self, *_):
        if not hasattr(self, '_menu_buttons') or not hasattr(self, 'db_name'):
            return
        badges   = _get_menu_badges(self.db_name)
        active   = getattr(self, '_active_nav_btn', None)
        for base in ('Входящие', 'Трансферы', 'Состав'):
            btn = self._menu_buttons.get(base)
            if not btn:
                continue
            suffix = badges.get(base, '')
            btn.text       = base + suffix
            btn._has_alert = bool(suffix)
            if btn is not active:
                btn.background_color = T.NAV_ALERT if suffix else T.NAV_IDLE
        if active:
            active.background_color = T.NAV_ACTIVE
        if hasattr(self, '_budget_lbl'):
            txt, color = self._get_budget_display()
            self._budget_lbl.text  = txt
            self._budget_lbl.color = color
        if hasattr(self, '_rating_lbl'):
            self._rating_lbl.text = self._get_rating_display()
        if hasattr(self, '_inbox_badge_btn'):
            unread = badges.get('Входящие', '')
            n = unread.strip(' ()') if unread else '0'
            has = bool(unread)
            self._inbox_badge_btn.text = (
                f'[b][color=ff4444]{n}[/color][/b]\nписем' if has else 'Письма'
            )
            self._inbox_badge_btn.background_color = (
                (0.70, 0.08, 0.08, 1) if has else (0.22, 0.28, 0.22, 1)
            )

    def on_press(self, instance):
        print(f'Нажата кнопка: {instance.text}')

    def on_achievements(self, instance):
        from ingame_interface.achievements import AchievementsPopup
        self._show_inline(AchievementsPopup(self.db_name), 'Достижения')

    def on_incoming(self, instance):
        messages = self._load_messages()
        if not messages:
            messages = [
                {'date': str(self.date_object), 'author': 'Система',
                 'text': 'Нет новых сообщений.'},
            ]
        try:
            conn = sqlite3.connect(self.db_name)
            conn.execute("UPDATE messages SET read=1 WHERE COALESCE(read,0)=0")
            conn.commit(); conn.close()
        except Exception:
            pass
        from ingame_interface.inbox import MessagePopup
        self._show_inline(MessagePopup(messages, db_name=self.db_name), 'Входящие')
        self._refresh_menu_badges()

    def _load_messages(self):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT date, author, text FROM messages ORDER BY id DESC")
            rows = cursor.fetchall()
            conn.close()
            return [{'date': r[0], 'author': r[1], 'text': r[2]} for r in rows]
        except Exception:
            return []

    def on_roster(self, instance):
        from ingame_interface.squad import SquadPopup
        self._show_inline(SquadPopup(self.db_name), 'Состав')

    def on_organization(self, instance):
        from ingame_interface.organization import OrganizationPopup
        self._show_inline(OrganizationPopup(self.db_name), 'Организация')

    def on_league(self, instance):
        from ingame_interface.team_viewer import LeaguePopup
        self._show_inline(LeaguePopup(self.db_name), 'Команды')

    def on_tournaments(self, instance):
        self._show_inline(TournamentsViewPopup(self.db_name), 'Турниры')

    def on_history(self, instance):
        from ingame_interface.history import HistoryPopup
        self._show_inline(HistoryPopup(self.db_name), 'История')

    def on_transfer_history(self, instance):
        from ingame_interface.history import show_transfer_history_popup
        show_transfer_history_popup(self.db_name)

    def on_stats(self, instance):
        from ingame_interface.stats import StatsPopup
        self._show_inline(StatsPopup(self.db_name), 'Статистика')

    def on_leaderboard(self, instance):
        from ingame_interface.stats import show_leaderboard_popup
        show_leaderboard_popup(self.db_name)

    def on_hero_stats(self, instance):
        from ingame_interface.stats import show_hero_stats_popup
        show_hero_stats_popup(self.db_name)

    def on_goals(self, instance):
        from ingame_interface.goals import GoalsPopup
        self._show_inline(GoalsPopup(self.db_name), 'Цели')

    def on_manual_save(self, instance):
        import shutil
        from datetime import date as _date
        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        backup = self.db_name.replace('.db', f'_save_{_date.today()}.db')
        try:
            shutil.copy(self.db_name, backup)
            msg = f'Сохранено:\n{backup.split("/")[-1]}'
            color = (0.2, 0.9, 0.3, 1)
        except Exception as e:
            msg = f'Ошибка сохранения:\n{e}'
            color = (0.9, 0.3, 0.2, 1)
        p = Popup(content=Label(text=msg, halign='center', color=color),
                  title='', size_hint=(0.55, 0.25))
        p.open()

    def on_transfers(self, instance):
        from ingame_interface.transfers import TransferPopup
        self._show_inline(TransferPopup(self.db_name), 'Трансферы')

    def _show_event_popup(self, title, text):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button

        root = BoxLayout(orientation='vertical', padding=14, spacing=10)
        lbl = Label(
            text=text, markup=True,
            color=(0.92, 0.92, 0.92, 1), halign='center', valign='middle',
            font_size='14sp',
        )
        lbl.bind(size=lbl.setter('text_size'))
        root.add_widget(lbl)
        popup = Popup(title=title, content=root, size_hint=(0.62, 0.38), auto_dismiss=False)
        ok = Button(text='OK', size_hint_y=None, height=44,
                    background_normal='', background_color=(0.22, 0.50, 0.22, 1))
        ok.bind(on_press=popup.dismiss)
        root.add_widget(ok)
        popup.open()

    def _show_investor_popup(self, ev_data):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        from datetime import timedelta

        company = ev_data.get('company', 'Инвестор')
        amount  = ev_data.get('amount', 100_000)
        cut     = ev_data.get('cut', 15)
        team_id = ev_data.get('team_id')
        try:
            game_date = date.fromisoformat(ev_data.get('game_date', str(self.date_object)))
        except Exception:
            game_date = self.date_object
        end_date = str(game_date + timedelta(days=730))

        root = BoxLayout(orientation='vertical', padding=14, spacing=10)
        lbl = Label(
            text=(f'[b]{company}[/b] предлагает [b]${amount:,}[/b] инвестиций.\n'
                  f'Условие: {cut}% доходов от стриминга в течение 2 лет.\n'
                  f'Договор действует до {end_date}.'),
            markup=True,
            color=(0.92, 0.92, 0.92, 1), halign='center', valign='middle', font_size='14sp',
        )
        lbl.bind(size=lbl.setter('text_size'))
        root.add_widget(lbl)
        btn_row = BoxLayout(size_hint_y=None, height=46, spacing=8)

        popup = Popup(title='Предложение инвестора', content=root,
                      size_hint=(0.65, 0.40), auto_dismiss=False)

        def _accept(_):
            if team_id:
                c = sqlite3.connect(self.db_name)
                c.execute(
                    "UPDATE teams SET budget=budget+?, investor_name=?, "
                    "investor_end_date=?, investor_cut_pct=?, investor_bonus=? "
                    "WHERE id=?",
                    (amount, company, end_date, cut, amount, team_id)
                )
                c.execute(
                    "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                    (f'Договор с {company} заключён. Получено ${amount:,}. '
                     f'Ежемесячно {cut}% дохода от стриминга отчисляется инвестору.',
                     str(self.date_object), 'Организация')
                )
                c.commit(); c.close()
            popup.dismiss()
            self._refresh_menu_badges()

        def _reject(_):
            popup.dismiss()

        acc = Button(text='Принять', background_normal='',
                     background_color=(0.18, 0.55, 0.20, 1))
        acc.bind(on_press=_accept)
        rej = Button(text='Отказать', background_normal='',
                     background_color=(0.60, 0.18, 0.18, 1))
        rej.bind(on_press=_reject)
        btn_row.add_widget(acc)
        btn_row.add_widget(rej)
        root.add_widget(btn_row)
        popup.open()

    def _show_player_dialogue(self, dialogue):
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        from logic.player_dialogue import apply_dialogue_choice

        root = BoxLayout(orientation='vertical', padding=14, spacing=10)
        txt = Label(
            text=dialogue['text'], markup=True,
            color=(0.92, 0.92, 0.92, 1), halign='center', valign='middle',
            font_size='14sp',
        )
        txt.bind(size=txt.setter('text_size'))
        root.add_widget(txt)

        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)
        popup = Popup(
            title=dialogue['title'],
            content=root,
            size_hint=(0.65, 0.42),
            auto_dismiss=False,
        )

        def _choose(key):
            popup.dismiss()
            title, result = apply_dialogue_choice(self.db_name, dialogue, key)
            info = Popup(
                title=title,
                content=Label(text=result, halign='center', valign='middle',
                              color=(0.9, 0.9, 0.9, 1)),
                size_hint=(0.55, 0.28),
            )
            info.open()

        for label, key in dialogue['choices']:
            b = Button(text=label, background_normal='',
                       background_color=(0.22, 0.50, 0.22, 1) if 'Согл' in label or 'OK' in label or 'Разреш' in label
                       else (0.55, 0.18, 0.18, 1))
            b.bind(on_press=lambda _, k=key: _choose(k))
            btn_row.add_widget(b)
        root.add_widget(btn_row)
        popup.open()

    def on_finances(self, instance):
        from ingame_interface.finances import FinancesPopup
        self._show_inline(FinancesPopup(self.db_name), 'Финансы')

    def on_academy(self, instance):
        from ingame_interface.academy import AcademyPopup
        self._show_inline(AcademyPopup(self.db_name), 'Академия')

    def on_scrimmage(self, instance):
        from ingame_interface.scrimmage import ScrimmagePopup
        self._show_inline(ScrimmagePopup(self.db_name), 'Кланвары')

    def on_sponsors(self, instance):
        from ingame_interface.sponsors import SponsorsPopup
        self._show_inline(SponsorsPopup(self.db_name), 'Спонсоры')

    def on_settings(self, instance):
        self._show_inline(SettingsPopup(), 'Настройки')

    def on_profile(self, instance):
        from ingame_interface.profile import ProfilePopup
        self._show_inline(ProfilePopup(self.db_name), 'Мой профиль')

    def on_manager_skills(self, instance):
        from ingame_interface.skills import show_skills_popup
        show_skills_popup(self.db_name)

    def on_main_menu(self, instance):
        from ingame_interface.exit_screen import show_exit_screen
        show_exit_screen(self.db_name, on_exit=self.popup.dismiss)

    def close_popup(self, instance):
        pass  # legacy, kept for safety

    def get_team_name(self):
        try:
            # Подключение к базе данных
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Выполнение запроса для получения имени команды
            cursor.execute("SELECT name FROM teams WHERE player = 'yes'")
            result = cursor.fetchone()

            # Закрытие соединения
            conn.close()

            return result[0] if result else None

        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")
            return None

    def get_current_tournament(self):
        """Return name of ongoing tournament (started, not finished), or None."""
        date_object = self.get_date_from_db(1)
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM tournaments "
            "WHERE start_date <= ? AND place1 IS NULL "
            "ORDER BY start_date DESC LIMIT 1",
            (date_object,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_next_tournament(self):
        at = self._get_active_tournament()
        if at:
            idx   = at['match_idx']
            total = len(at['match_queue'])
            name  = at['name']
            short = name[:22] if len(name) > 22 else name
            return f'{short}  {idx}/{total}'
        current = self.get_current_tournament()
        if current:
            return f'{current}'
        date_object = self.get_date_from_db(1)
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM tournaments "
            "WHERE start_date >= ? AND place1 IS NULL "
            "ORDER BY start_date ASC LIMIT 1",
            (date_object,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "Нет турниров"

    def on_tournament_btn(self, instance):
        if self.get_current_tournament():
            self.show_tournament_popup()
        else:
            # Tournament not started yet — show start date
            date_object = self.get_date_from_db(1)
            conn = sqlite3.connect(self.db_name)
            row = conn.execute(
                "SELECT name, start_date FROM tournaments "
                "WHERE start_date >= ? AND place1 IS NULL "
                "ORDER BY start_date ASC LIMIT 1",
                (date_object,)
            ).fetchone()
            conn.close()
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            if row:
                text = f'Турнир начнётся {row[1]}\n{row[0]}'
            else:
                text = 'Нет предстоящих турниров'
            Popup(
                title='Турнир',
                content=Label(text=text, halign='center', valign='middle',
                              color=(0.92, 0.92, 0.92, 1)),
                size_hint=(0.50, 0.25),
            ).open()

    # ── Active-tournament system ──────────────────────────────────────────────

    def _matches_per_day(self, at):
        """How many matches to play today so tournament fits within its scheduled dates."""
        try:
            total     = len(at['match_queue'])
            remaining = total - at['match_idx']
            if remaining <= 0:
                return 1
            conn = sqlite3.connect(self.db_name)
            row  = conn.execute(
                "SELECT end_date FROM tournaments WHERE id=?", (at['tourn_id'],)
            ).fetchone()
            conn.close()
            if row and row[0]:
                end_d     = date.fromisoformat(row[0])
                days_left = max(1, (end_d - self.date_object).days + 1)
                return max(1, -(-remaining // days_left))  # ceil division
        except Exception:
            pass
        return max(1, len(at['match_queue']) // 7 or 1)

    def _get_active_tournament(self):
        """Return active tournament dict or None."""
        import json
        try:
            conn = sqlite3.connect(self.db_name)
            row = conn.execute(
                "SELECT tourn_id, name, match_queue_json, match_idx, standings_json, "
                "final_ev_json, minor_ev_json, draw_ev_json, player_teams_json "
                "FROM active_tournament LIMIT 1"
            ).fetchone()
            conn.close()
            if not row:
                return None
            return {
                'tourn_id':     row[0],
                'name':         row[1],
                'match_queue':  json.loads(row[2]) if row[2] else [],
                'match_idx':    row[3],
                'standings':    json.loads(row[4]) if row[4] else {},
                'final_ev':     json.loads(row[5]) if row[5] else None,
                'minor_ev':     json.loads(row[6]) if row[6] else None,
                'draw_ev':      json.loads(row[7]) if row[7] else None,
                'player_teams': set(json.loads(row[8])) if row[8] else set(),
            }
        except Exception:
            return None

    def _init_tournament(self, tourn_id, tourn_name):
        """Generate events for tournament and store match queue in DB."""
        import json
        from logic.tournaments.runner import generate_tournament_events
        from ingame_interface.tournaments import _add_message

        events, _pl, _ge = generate_tournament_events(self.db_name, tourn_id)

        # Build lineup map (player match logs)
        lineup_map = {}
        for ev in events:
            if ev['type'] == 'match_lineup':
                k = (ev['stage'], ev['team1'], ev['team2'])
                lineup_map[k] = ev

        # Collect ordered match queue
        match_queue = []
        for ev in events:
            if ev['type'] == 'match_result':
                k = (ev['stage'], ev['team1'], ev['team2'])
                item = {'result_ev': ev}
                if k in lineup_map:
                    item['lineup_ev'] = lineup_map[k]
                match_queue.append(item)

        # Find key events
        final_ev   = next((e for e in events if e['type'] == 'tournament_results'), None)
        minor_ev   = next((e for e in events if e['type'] == 'minor_results'), None)
        draw_ev    = next((e for e in events if e['type'] == 'draw'), None)

        # Determine player teams
        player_teams = set()
        for ev in events:
            if ev['type'] == 'draw' and ev.get('player_teams'):
                player_teams = set(ev['player_teams'])

        # No player → silent finalize immediately
        if not player_teams and not any(
            item['result_ev'].get('is_player_match') for item in match_queue
        ):
            champ = final_ev.get('champion', '?') if final_ev else '?'
            _add_message(self.db_name, f"{tourn_name}: чемпион — {champ}.", 'Новости')
            if final_ev:
                from logic.tournaments.runner import finalize_tournament
                finalize_tournament(self.db_name, tourn_id, tourn_name, final_ev,
                                    game_date=str(self.date_object))
            return

        # Determine if player participates in minor tournament
        player_in_minor = any(
            item['result_ev'].get('is_player_match') and
            'Малый' in item['result_ev'].get('stage', '')
            for item in match_queue
        )

        # Minor without player → persist silently now; with player → persist at tournament end
        minor_ev_to_store = minor_ev
        if minor_ev and not player_in_minor:
            try:
                from ingame_interface.tournaments import _persist_minor_results_standalone
                _persist_minor_results_standalone(self.db_name, minor_ev)
                minor_ev_to_store = None  # already done, don't double-persist at end
            except Exception:
                pass

        # Initial standings from draw event
        initial_standings = {}
        if draw_ev:
            for group in draw_ev.get('groups', []):
                for team in group:
                    initial_standings[team] = 0

        # Clear any stale active tournament
        conn = sqlite3.connect(self.db_name)
        conn.execute("DELETE FROM active_tournament")
        conn.execute(
            "INSERT INTO active_tournament "
            "(tourn_id, name, match_queue_json, match_idx, standings_json, "
            " final_ev_json, minor_ev_json, draw_ev_json, player_teams_json) "
            "VALUES (?,?,?,0,?,?,?,?,?)",
            (
                tourn_id, tourn_name,
                json.dumps(match_queue),
                json.dumps(initial_standings),
                json.dumps(final_ev) if final_ev else None,
                json.dumps(minor_ev_to_store) if minor_ev_to_store else None,
                json.dumps(draw_ev) if draw_ev else None,
                json.dumps(list(player_teams)),
            )
        )
        conn.commit()
        conn.close()

    def _play_match_day(self, suppress_notifications=False):
        """Play next match from active tournament. Return True if notification triggered."""
        import json
        at = self._get_active_tournament()
        if not at:
            return False

        queue = at['match_queue']
        idx   = at['match_idx']

        if idx >= len(queue):
            self._finish_active_tournament(at)
            return True

        item      = queue[idx]
        result_ev = item['result_ev']
        lineup_ev = item.get('lineup_ev')
        is_player = result_ev.get('is_player_match', False)

        # Merge standings — each match event only has its group's standings
        new_standings = dict(at['standings'])
        if result_ev.get('standings'):
            new_standings.update(result_ev['standings'])
        new_idx = idx + 1

        conn = sqlite3.connect(self.db_name)
        conn.execute(
            "UPDATE active_tournament SET match_idx=?, standings_json=? WHERE id=1",
            (new_idx, json.dumps(new_standings))
        )
        conn.commit()
        conn.close()

        is_last = (new_idx >= len(queue))

        if is_player and lineup_ev and not suppress_notifications:
            on_done = (lambda: self._finish_active_tournament(
                self._get_active_tournament()
            )) if is_last else None
            self._show_player_match_day(lineup_ev, result_ev, at, on_done)
            return True

        if is_last:
            self._finish_active_tournament(self._get_active_tournament())
            return True

        return False

    def _show_player_match_day(self, lineup_ev, result_ev, at, on_done=None):
        """Show MatchLogPopup for a player match inline."""
        from ingame_interface.tournaments import MatchLogPopup

        logo_map = {}
        try:
            conn = sqlite3.connect(self.db_name)
            logo_map = {
                r[0].strip(): r[1]
                for r in conn.execute("SELECT name, logo FROM teams").fetchall()
            }
            conn.close()
        except Exception:
            pass

        t1, t2 = lineup_ev['team1'], lineup_ev['team2']
        player_teams = at.get('player_teams', set())
        pre_match_team = t1 if t1 in player_teams else (t2 if t2 in player_teams else None)

        # Stop auto-advance and disable nav buttons while match plays
        if getattr(self, '_auto_advance_event', None):
            self._stop_auto_advance()
        for btn in (getattr(self, '_next_btn', None), getattr(self, '_skip_btn', None)):
            if btn:
                btn.disabled = True

        def _on_close():
            for btn in (getattr(self, '_next_btn', None), getattr(self, '_skip_btn', None)):
                if btn:
                    btn.disabled = False
            if on_done:
                on_done()
            else:
                self._show_dashboard()

        popup = MatchLogPopup(
            team1=t1, team2=t2,
            winner=lineup_ev.get('winner', t1),
            log_lines=lineup_ev.get('match_log', []),
            snapshots=lineup_ev.get('match_snaps', []),
            best_of=lineup_ev.get('best_of', 1),
            final_score=(lineup_ev.get('score_t1', 0), lineup_ev.get('score_t2', 0)),
            match_stats=lineup_ev.get('match_stats', {}),
            on_close=_on_close,
            t1_logo=logo_map.get(t1),
            t2_logo=logo_map.get(t2),
            pre_match_team=pre_match_team,
            db_name=self.db_name,
            on_result_update=lambda w, s1, s2: self._apply_actual_match_result(
                t1, t2, result_ev, w, s1, s2),
        )
        popup.title = f"{at['name']} — {lineup_ev.get('stage', '')}"
        self._show_inline(popup, at['name'])
        popup.dismiss = _on_close

    def _apply_actual_match_result(self, t1, t2, result_ev, actual_winner, s1, s2):
        """Called when player completes a draft: update standings with actual result."""
        import json as _json

        stage = result_ev.get('stage', '')
        is_group = 'Группа' in stage or 'Лига' in stage

        pre_s1 = result_ev.get('score_t1', 0)
        pre_s2 = result_ev.get('score_t2', 0)

        # Points for BO2: win=2, draw=1, loss=0
        def _pts(sc1, sc2):
            if sc1 > sc2: return 2, 0
            if sc2 > sc1: return 0, 2
            return 1, 1

        old_p1, old_p2 = _pts(pre_s1, pre_s2)
        new_p1, new_p2 = _pts(s1, s2)

        if (old_p1, old_p2) == (new_p1, new_p2):
            return  # same outcome, no update needed

        try:
            conn = sqlite3.connect(self.db_name)
            row = conn.execute(
                "SELECT standings_json, match_queue_json, final_ev_json "
                "FROM active_tournament WHERE id=1"
            ).fetchone()
            if not row:
                conn.close()
                return

            standings = _json.loads(row[0]) if row[0] else {}
            queue     = _json.loads(row[1]) if row[1] else []
            final_ev  = _json.loads(row[2]) if row[2] else None

            # Update standings delta
            if is_group:
                standings[t1] = standings.get(t1, 0) + (new_p1 - old_p1)
                standings[t2] = standings.get(t2, 0) + (new_p2 - old_p2)

            # Update match_queue result_ev for this match
            actual_loser = t2 if actual_winner == t1 else t1
            for item in queue:
                rev = item['result_ev']
                if rev['team1'] == t1 and rev['team2'] == t2 and rev.get('stage') == stage:
                    rev['winner']    = actual_winner
                    rev['loser']     = actual_loser
                    rev['score_t1']  = s1
                    rev['score_t2']  = s2
                    if is_group and rev.get('standings'):
                        rev['standings'] = dict(standings)
                    break

            # Update final_ev placements for player team if result changed
            if final_ev and is_group:
                pt = conn.execute("SELECT name FROM teams WHERE player='yes'").fetchone()
                if pt:
                    my_team = pt[0].strip()
                    # Recompute player's group placement from actual standings
                    draw_row = conn.execute(
                        "SELECT draw_ev_json FROM active_tournament WHERE id=1"
                    ).fetchone()
                    if draw_row and draw_row[0]:
                        draw_ev = _json.loads(draw_row[0])
                        for group in draw_ev.get('groups', []):
                            if my_team in group:
                                grp_standings = sorted(
                                    [(t, standings.get(t, 0)) for t in group],
                                    key=lambda x: x[1], reverse=True
                                )
                                actual_rank = next(
                                    (i+1 for i, (t, _) in enumerate(grp_standings) if t == my_team),
                                    None
                                )
                                if actual_rank and my_team in final_ev.get('placements', {}):
                                    pre_rank = final_ev['placements'][my_team]
                                    if actual_rank != pre_rank:
                                        final_ev['placements'][my_team] = actual_rank

            conn.execute(
                "UPDATE active_tournament SET standings_json=?, match_queue_json=?, final_ev_json=? WHERE id=1",
                (_json.dumps(standings), _json.dumps(queue),
                 _json.dumps(final_ev) if final_ev else None)
            )
            conn.commit()
            conn.close()
        except Exception as _e:
            T.log_err('_apply_actual_match_result', _e)

    def _finish_active_tournament(self, at=None):
        """Persist results and clear active tournament."""
        if at is None:
            at = self._get_active_tournament()
        if not at:
            return
        # Guard: if active_tournament was already cleared (race/double-call) abort
        live = self._get_active_tournament()
        if not live or live['tourn_id'] != at['tourn_id']:
            return

        # Collect player match lineup events for match_history
        player_matches = [
            item['lineup_ev']
            for item in at['match_queue']
            if item.get('lineup_ev') and item['result_ev'].get('is_player_match')
        ]

        from logic.tournaments.runner import finalize_tournament
        finalize_tournament(
            self.db_name,
            at['tourn_id'],
            at['name'],
            at['final_ev'],
            minor_ev=at.get('minor_ev'),
            player_matches=player_matches,
            game_date=str(self.date_object),
        )

        # Clear
        conn = sqlite3.connect(self.db_name)
        conn.execute("DELETE FROM active_tournament")
        conn.commit()
        conn.close()

        # Check season over
        self._check_season_over_core(at['tourn_id'])
        self._refresh_tournament_btn()
        self._show_dashboard()

    def _check_season_over_core(self, tournament_id):
        """Check if all tournaments for the year are done; open SeasonEndPopup if so."""
        try:
            conn = sqlite3.connect(self.db_name)
            row = conn.execute(
                "SELECT start_date FROM tournaments WHERE id=?", (tournament_id,)
            ).fetchone()
            if not row:
                conn.close()
                return
            year = row[0][:4]
            remaining = conn.execute(
                "SELECT COUNT(*) FROM tournaments WHERE start_date LIKE ? AND place1 IS NULL",
                (f'{year}%',)
            ).fetchone()[0]
            conn.close()
            if remaining == 0:
                from ingame_interface.season_end import SeasonEndPopup
                SeasonEndPopup(
                    self.db_name, int(year),
                    on_confirmed=self._refresh_tournament_btn,
                ).open()
        except Exception as e:
            T.log_err('_check_season_over_core', e)

    # ── Tournament popup (legacy path + tournament-btn handler) ───────────────

    def show_tournament_popup(self):
        """Init the next tournament and play its first match day."""
        conn = sqlite3.connect(self.db_name)
        row = conn.execute(
            "SELECT id, name FROM tournaments WHERE place1 IS NULL ORDER BY start_date LIMIT 1"
        ).fetchone()
        conn.close()
        if not row:
            return
        tourn_id, tourn_name = row

        # If already active (e.g. button pressed mid-tournament), play next match
        at = self._get_active_tournament()
        if at and at['tourn_id'] == tourn_id:
            triggered = self._play_match_day(suppress_notifications=False)
            if not triggered:
                self._show_dashboard()
            return

        # Fresh start
        self._init_tournament(tourn_id, tourn_name)
        at = self._get_active_tournament()
        if at:
            triggered = self._play_match_day(suppress_notifications=False)
            if not triggered:
                self._show_dashboard()

    def _refresh_tournament_btn(self):
        self.tournament_button.text = self.get_next_tournament()




class DotaPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super(DotaPopup, self).__init__(**kwargs)
        self.title = ""
        self.content = MainWindow(db_name,self)
        self.size_hint = (1, 1)
        self.auto_dismiss = False

    def open_popup(self, db_name):
        DotaPopup(db_name).open()
