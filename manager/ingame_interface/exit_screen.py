import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

_ACCENT = (0.35, 0.85, 1.00, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_SILVER = (0.80, 0.80, 0.80, 1)
_BRONZE = (0.78, 0.52, 0.25, 1)

_REP_LEVELS = [
    (200, 'Икона'), (100, 'Легенда'), (50, 'Ветеран'),
    (25, 'Опытный'), (10, 'Известный'), (0, 'Новичок'),
]


def _lbl(text, height=28, color=_WHITE, bold=False, halign='center'):
    t = f'[b]{text}[/b]' if bold else text
    l = Label(text=t, markup=True, size_hint_y=None, height=height,
              color=color, halign=halign, valign='middle')
    l.bind(size=l.setter('text_size'))
    return l


def _row(label, val, vc=_WHITE):
    box = BoxLayout(size_hint_y=None, height=28)
    box.add_widget(_lbl(f'  {label}:', color=_DIM, halign='left'))
    box.add_widget(_lbl(val, color=vc, halign='right'))
    return box


class ExitScreenPopup(Popup):
    def __init__(self, db_name, on_exit, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.80, 0.88)
        self.background_color = (1, 1, 1, 0)
        self.auto_dismiss = False
        self._on_exit = on_exit
        self._build(db_name)

    def _build(self, db_name):
        conn = sqlite3.connect(db_name)
        c = conn.cursor()

        char = c.execute(
            "SELECT name, surname, nickname, COALESCE(reputation,0) FROM characters LIMIT 1"
        ).fetchone()
        team_row = c.execute(
            "SELECT id, name, COALESCE(rating,0) FROM teams WHERE player='yes'"
        ).fetchone()
        gd = c.execute("SELECT date FROM save WHERE id=1").fetchone()

        team_id     = team_row[0] if team_row else None
        team_name   = team_row[1].strip() if team_row else '—'
        team_rating = int(team_row[2]) if team_row else 0
        game_date = gd[0] if gd else '—'

        # Tournament results
        c.execute("""
            SELECT name, start_date,
                   place1, place2, place3, place4, place5, place6, place7, place8,
                   place9, place10, place11, place12, place13, place14, place15, place16,
                   COALESCE(prizepool,0)
            FROM tournaments WHERE place1 IS NOT NULL ORDER BY start_date
        """)
        results = []
        for row in c.fetchall():
            t_name, t_date, *places_prize = row
            places = places_prize[:16]
            prize  = places_prize[16]
            for i, p in enumerate(places, 1):
                if p == team_id:
                    results.append((t_name, t_date, i, prize))
                    break
        conn.close()

        wins        = sum(1 for *_, p, _ in results if p == 1)
        top3        = sum(1 for *_, p, _ in results if p <= 3)
        top8        = sum(1 for *_, p, _ in results if p <= 8)
        prize_total = sum(pr for *_, pr in results)
        best        = min((p for *_, p, _ in results), default=None)

        root = BoxLayout(orientation='vertical', padding=8, spacing=6)

        root.add_widget(_lbl('── КАРЬЕРНАЯ СВОДКА ──', height=36, color=_ACCENT, bold=True))

        if char:
            name, surname, nick, rep = char
            rep_label = next((l for th, l in _REP_LEVELS if rep >= th), 'Новичок')
            root.add_widget(_lbl(f"{name} '{nick}' {surname}", height=30, color=_WHITE, bold=True))
            root.add_widget(_lbl(
                f"Репутация: {rep} пт  [{rep_label}]", height=26, color=_GOLD
            ))

        root.add_widget(_lbl(f"Команда: {team_name}  |  Рейтинг: {team_rating} пт",
                             height=26, color=_ACCENT))
        root.add_widget(_lbl(f"Дата: {game_date}", height=22, color=_DIM))

        root.add_widget(_lbl('──────────────────────', height=16, color=_DIM))

        grid = GridLayout(cols=2, size_hint_y=None, spacing=2, padding=(4, 0))
        grid.bind(minimum_height=grid.setter('height'))
        for label, val, vc in [
            ('Турниров',       str(len(results)),          _WHITE),
            ('Победы (1 м.)',  str(wins),                  _GOLD),
            ('Топ-3',          str(top3),                  _BRONZE),
            ('Топ-8',          str(top8),                  _WHITE),
            ('Лучший результат', f'{best}-е место' if best else '—', _GREEN),
            ('Всего призовых', f'${prize_total:,}',        _GOLD),
        ]:
            grid.add_widget(_lbl(f'  {label}:', color=_DIM, height=26, halign='left'))
            grid.add_widget(_lbl(val, color=vc, height=26, halign='right'))
        root.add_widget(grid)

        # Recent results (last 5)
        if results:
            root.add_widget(_lbl('── Последние турниры ──', height=24, color=_ACCENT))
            for t_name, t_date, place, prize in results[-5:]:
                color = (_GOLD if place == 1 else _SILVER if place == 2 else
                         _BRONZE if place <= 4 else _WHITE)
                medal = ('🥇' if place == 1 else '🥈' if place == 2 else
                         '🥉' if place == 3 else f'{place}.')
                row = BoxLayout(size_hint_y=None, height=28)
                row.add_widget(_lbl(f'  {medal} {t_name}',
                                    color=color, halign='left', height=28))
                row.add_widget(_lbl(t_date[:7] if t_date else '—',
                                    color=_DIM, halign='right', height=28))
                root.add_widget(row)

        root.add_widget(_lbl('──────────────────────', height=12, color=_DIM))

        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=6)
        exit_btn = Button(
            text='Выйти в главное меню',
            background_color=(0.65, 0.18, 0.18, 1),
            background_normal='',
        )
        stay_btn = Button(
            text='Остаться в игре',
            background_color=(0.18, 0.55, 0.20, 1),
            background_normal='',
        )
        def _do_exit(_):
            self.dismiss()
            try:
                from core import _unpatch_popups
                _unpatch_popups()
            except Exception:
                pass
            self._on_exit()

        exit_btn.bind(on_press=_do_exit)
        stay_btn.bind(on_press=self.dismiss)
        btn_row.add_widget(exit_btn)
        btn_row.add_widget(stay_btn)
        root.add_widget(btn_row)

        self.content = root


def show_exit_screen(db_name, on_exit):
    ExitScreenPopup(db_name=db_name, on_exit=on_exit).open()
