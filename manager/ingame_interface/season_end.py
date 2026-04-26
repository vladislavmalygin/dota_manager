import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

from logic.ai import decay_ratings_season_end
from logic.tournaments.runner import ensure_next_year_tournaments
from logic.sponsors import check_and_pay_season_bonus

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
        ensure_next_year_tournaments(self.db_name, self.year + 1)
        self.dismiss()
        if self._on_confirmed:
            self._on_confirmed()
