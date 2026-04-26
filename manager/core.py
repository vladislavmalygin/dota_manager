import sqlite3
from datetime import date, timedelta

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock

from settings import SettingsPopup
from ingame_interface.inbox import show_message
from ingame_interface.mixin import show_custom_popup
from ingame_interface.squad import show_squad_popup
from ingame_interface.tournaments import TournamentPopup, TournamentsViewPopup
from ingame_interface.organization import show_organization_popup
from ingame_interface.profile import show_profile_popup
from ingame_interface.transfers import show_transfers_popup
from logic.tournaments.invites import invites
from logic.tournaments.runner import ensure_season_tournaments
from logic.ai import update_morale_monthly, ai_transfers, ai_poach_attempt
from logic.events import random_event_monthly
from logic.sponsors import ensure_sponsors_table, pay_monthly_income
from db_migrate2 import migrate as _migrate2
import random as _random
from db_migrate3 import migrate as _migrate3
from db_migrate4 import migrate as _migrate4
from db_migrate5 import migrate as _migrate5
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


class MainWindow(BoxLayout):
    def __init__(self, db_name, popup, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.db_name = db_name
        self.popup = popup

        # Ensure all season tournaments exist in this save
        ensure_season_tournaments(db_name)
        self._migrate_db(db_name)

        self.date_object = self.get_date_from_db(1)

        self.today_date_button = Button(text=f'{self.date_object}', background_color=(0.5, 0.5, 0.2, 1),
                                        on_press=self.on_press)

        # Установка фона с изображением
        with self.canvas.before:
            Color(1, 1, 1, 0.5)  # Белый цвет фона
            self.rect = Rectangle(source='images/core1.png', pos=self.pos, size=self.size)

        # Обновление размера прямоугольника при изменении размера окна
        self.bind(size=self._update_rect, pos=self._update_rect)

        # Верхняя часть интерфейса
        top_layout = GridLayout(cols=5, size_hint_y=0.1)

        team_name = self.get_team_name()
        tournament_name = self.get_next_tournament()

        # Добавляем кнопки в верхнюю часть с цветами
        top_layout.add_widget(Button(text='Dota Manager', background_color=(0.2, 0.6, 0.8, 1), on_press=self.on_press))
        top_layout.add_widget(Button(text=team_name, background_color=(0.2, 0.8, 0.2, 1), on_press=self.on_press))
        self.tournament_button = Button(text=tournament_name, background_color=(0.8, 0.2, 0.2, 1), on_press=self.on_press)
        top_layout.add_widget(self.tournament_button)
        top_layout.add_widget(self.today_date_button)
        top_layout.add_widget(Button(text='Далее', background_color=(0.8, 0.8, 0.2, 1), on_press=self.on_next))

        # Добавляем верхнюю часть в основной макет
        self.add_widget(top_layout)

        # Создаем основной макет для левой и правой части интерфейса
        main_layout = BoxLayout(orientation='horizontal')

        # Левая часть
        left_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 1))

        # Заполняем левую часть кнопками с цветами
        buttons = {
            'Входящие': self.on_incoming,
            'Состав': self.on_roster,
            'Организация': self.on_organization,
            'Команды': self.on_league,
            'Турниры': self.on_tournaments,
            'Трансферы': self.on_transfers,
            'Спонсоры': self.on_sponsors,
            'Настройки': self.on_settings,
            'Мой профиль': self.on_profile,
            'Главное меню': self.on_main_menu,
        }

        for btn_text, action in buttons.items():
            button = Button(text=btn_text, background_color=(0.4, 0.4, 0.8, 0.8))
            button.bind(on_press=action)  # Привязываем отдельный обработчик к кнопке
            left_layout.add_widget(button)

        # Создаем основной область экрана для переменного контента
        self.main_area = BoxLayout(size_hint_x=0.8)

        # Создаем полупрозрачный белый фон для основной области контента
        with self.main_area.canvas.before:
            Color(0.4, 0.4, 0.4, 0.2)  # Полупрозрачный белый цвет фона
            self.rect_main_area = Rectangle(pos=self.main_area.pos, size=self.main_area.size)

        # Обновление размера прямоугольника основной области при изменении размера окна
        self.main_area.bind(size=self._update_main_area_rect)

        # Добавляем левую часть и основную область к главному окну
        main_layout.add_widget(left_layout)
        main_layout.add_widget(self.main_area)

        self.add_widget(main_layout)

        Clock.schedule_once(lambda dt: self.on_incoming(None), 0.3)

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
        ]:
            try:
                conn.execute(ddl)
            except Exception:
                pass
        conn.commit()
        conn.close()
        _migrate2(db_name)
        _migrate3(db_name)
        _migrate4(db_name)
        _migrate5(db_name)
        _fix_orphans(db_name)
        _fix_team_regions(db_name)
        _fix_contracts(db_name)
        ensure_sponsors_table(db_name)

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
                "COALESCE(poaching_team_id,0) FROM players WHERE id=?",
                (pid,),
            )
            pr = cur.fetchone()
            if pr:
                avg = ((pr[0] or 10) + (pr[1] or 10)) // 2
                expected = max(avg * 180, int((pr[2] or 0) * 0.85))
                role = pr[3]
                poaching_tid = pr[4] or 0
            else:
                expected = 0
                role = None
                poaching_tid = 0

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

    def get_next_tournament_date(self):
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

        self._expire_contracts(conn)
        self._notify_expiring_contracts(conn)
        conn.commit()

        update_morale_monthly(self.db_name)
        ai_transfers(self.db_name)
        ai_poach_attempt(self.db_name, str(self.date_object))

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

        # Random monthly event (60% chance)
        import random
        if random.random() < 0.60:
            event = random_event_monthly(self.db_name)
            if event:
                title, text = event
                c = sqlite3.connect(self.db_name)
                c.execute(
                    "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
                    (text, title),
                )
                c.commit()
                c.close()

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
        prev_month = self.date_object.month
        self.date_object += timedelta(days=1)
        database = self.db_name
        conn = None
        try:
            conn = sqlite3.connect(database)
            cursor = conn.cursor()

            cursor.execute("UPDATE save SET date = ? WHERE id = 1", (str(self.date_object),))

            # Ежемесячное списание зарплат (1-го числа каждого месяца)
            if self.date_object.month != prev_month and self.date_object.day == 1:
                self._deduct_salaries(conn)

            conn.commit()

            cursor.execute("SELECT date FROM save WHERE id = 1")
            updated_date = cursor.fetchone()

            if updated_date:
                updated_date_value = updated_date[0]

                next_tournament_date = self.get_next_tournament_date()

                if next_tournament_date and updated_date_value == next_tournament_date:
                    self.show_tournament_popup()

                self.today_date_button.text = updated_date_value
                self.tournament_button.text = self.get_next_tournament()

                # ── Budget check ──────────────────────────────────
                cursor.execute(
                    "SELECT budget FROM teams WHERE player='yes'"
                )
                budget_row = cursor.fetchone()
                if budget_row and (budget_row[0] or 0) <= 0:
                    self._show_bankruptcy()
        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")
        finally:
            if conn:
                conn.close()



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

    def on_press(self, instance):
        print(f'Нажата кнопка: {instance.text}')

    def on_incoming(self, instance):
        messages = self._load_messages()
        if not messages:
            messages = [
                {'date': str(self.date_object), 'author': 'Система',
                 'text': 'Нет новых сообщений.'},
            ]
        show_message(messages)

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
        show_squad_popup(self.db_name)

    def on_organization(self, instance):
        show_organization_popup(self.db_name)

    def on_league(self, instance):
        from ingame_interface.team_viewer import LeaguePopup
        LeaguePopup(self.db_name).open()

    def on_tournaments(self, instance):
        TournamentsViewPopup(self.db_name).open()

    def on_transfers(self, instance):
        show_transfers_popup(self.db_name)

    def on_sponsors(self, instance):
        from ingame_interface.sponsors import show_sponsors_popup
        show_sponsors_popup(self.db_name)

    def on_settings(self, instance):
        SettingsPopup().open()

    def on_profile(self, instance):
        show_profile_popup(self.db_name)

    def on_main_menu(self, instance):
        content = BoxLayout(orientation='vertical')

        label = Button(text='Хотите ли вы выйти в главное меню?', size_hint_y=None, height=44)

        yes_button = Button(text='Да', size_hint_y=None, height=44)
        yes_button.bind(on_press=self.exit_to_main_menu)

        no_button = Button(text='Нет', size_hint_y=None, height=44)
        no_button.bind(on_press=self.close_popup)

        content.add_widget(label)
        content.add_widget(yes_button)
        content.add_widget(no_button)

        self.popup_confirm = Popup(title='Подтверждение', content=content, size_hint=(0.6, 0.4))
        self.popup_confirm.open()

    def exit_to_main_menu(self, instance):
        self.popup_confirm.dismiss()
        self.popup.dismiss()

    def close_popup(self, instance):
        self.popup_confirm.dismiss()

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

    def get_next_tournament(self):
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

    def show_tournament_popup(self):
        popup = TournamentPopup(self.db_name,
                                on_finish=self._refresh_tournament_btn)
        popup.open()

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
