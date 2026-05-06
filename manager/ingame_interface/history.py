import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

_GOLD   = (1.00, 0.85, 0.25, 1)
_SILVER = (0.80, 0.80, 0.80, 1)
_BRONZE = (0.78, 0.52, 0.25, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_ACCENT = (0.35, 0.85, 1.00, 1)


def _lbl(text, sw=1.0, color=_WHITE, bold=False):
    t = f'[b]{text}[/b]' if bold else text
    lbl = Label(text=t, markup=True, size_hint_x=sw,
                color=color, halign='center', valign='middle')
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _place_color(place):
    if place == 1:   return _GOLD
    if place == 2:   return _SILVER
    if place <= 4:   return _BRONZE
    if place <= 8:   return _WHITE
    return _DIM


def _place_medal(place):
    if place == 1:  return '🥇 1'
    if place == 2:  return '🥈 2'
    if place == 3:  return '🥉 3'
    return str(place)


class HistoryPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.88, 0.88)
        self.background_color = (1, 1, 1, 0)

        layout = BoxLayout(orientation='vertical', padding=6, spacing=6)
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=3)
        grid.bind(minimum_height=grid.setter('height'))

        self._build(db_name, grid)

        scroll.add_widget(grid)
        layout.add_widget(scroll)
        close = Button(text='Закрыть', size_hint_y=None, height=50,
                       background_color=(0.8, 0.2, 0.2, 0.8))
        close.bind(on_press=self.dismiss)
        layout.add_widget(close)
        self.add_widget(layout)

    def _build(self, db_name, grid):
        conn = sqlite3.connect(db_name)
        c = conn.cursor()

        row = c.execute("SELECT id, name FROM teams WHERE player='yes'").fetchone()
        if not row:
            grid.add_widget(_lbl('Команда не найдена.'))
            conn.close()
            return
        team_id, team_name = row[0], row[1].strip()

        # Header
        hdr = Label(
            text=f'[b]История результатов: {team_name}[/b]',
            markup=True, size_hint_y=None, height=44,
            color=_ACCENT, halign='center', valign='middle',
        )
        hdr.bind(size=hdr.setter('text_size'))
        grid.add_widget(hdr)

        # Column headers
        hrow = BoxLayout(size_hint_y=None, height=28)
        for txt, sw in [('Турнир', 0.45), ('Дата', 0.18), ('Место', 0.17), ('Приз', 0.20)]:
            hrow.add_widget(_lbl(f'[b]{txt}[/b]', sw=sw, color=_ACCENT, bold=False))
        grid.add_widget(hrow)

        # Collect results
        c.execute("""
            SELECT name, start_date,
                   place1,  place2,  place3,  place4,
                   place5,  place6,  place7,  place8,
                   place9,  place10, place11, place12,
                   place13, place14, place15, place16,
                   prizepool
            FROM tournaments
            WHERE place1 IS NOT NULL
            ORDER BY start_date DESC
        """)
        results = []
        for r in c.fetchall():
            t_name, t_date = r[0], r[1]
            places = r[2:18]
            prize  = r[18] or 0
            for i, p in enumerate(places, 1):
                if p == team_id:
                    results.append((t_name, t_date, i, prize))
                    break

        conn.close()

        if not results:
            grid.add_widget(_lbl('Ещё нет сыгранных турниров.', color=_DIM))
            return

        for t_name, t_date, place, prize in results:
            color = _place_color(place)
            row = BoxLayout(size_hint_y=None, height=36)
            row.add_widget(_lbl(t_name, sw=0.45, color=color))
            row.add_widget(_lbl(t_date[:7] if t_date else '—', sw=0.18, color=color))
            row.add_widget(_lbl(_place_medal(place), sw=0.17, color=color))
            prize_txt = f'${prize:,}' if prize else '—'
            row.add_widget(_lbl(prize_txt, sw=0.20, color=color))
            grid.add_widget(row)

        # Summary
        wins   = sum(1 for _, _, p, _ in results if p == 1)
        top4   = sum(1 for _, _, p, _ in results if p <= 4)
        total_prize = sum(pr for _, _, _, pr in results)
        grid.add_widget(_lbl(
            f'Турниров: {len(results)}  |  Побед: {wins}  |  Топ-4: {top4}  |  '
            f'Призовых: ${total_prize:,}',
            color=_ACCENT,
        ))


def show_history_popup(db_name):
    HistoryPopup(db_name=db_name).open()
