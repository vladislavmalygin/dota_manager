import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from logic.dota.strategies import (
    EARLY_STRATEGIES, MID_STRATEGIES, LATE_STRATEGIES,
)

_ACCENT = (0.35, 0.85, 1.00, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_RED    = (0.90, 0.28, 0.20, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_BG     = (0.10, 0.10, 0.12, 1)
_BG_MED = (0.14, 0.14, 0.18, 1)
_BG_SEL = (0.10, 0.28, 0.14, 1)
_BG_HDR = (0.10, 0.22, 0.32, 1)

_PHASE_LABEL = {
    'early': 'РАННЯЯ ИГРА',
    'mid':   'СРЕДНЯЯ ИГРА',
    'late':  'ПОЗДНЯЯ ИГРА',
}
_PHASE_STRATS = {
    'early': EARLY_STRATEGIES,
    'mid':   MID_STRATEGIES,
    'late':  LATE_STRATEGIES,
}
_DB_COL = {
    'early': 'strat_early',
    'mid':   'strat_mid',
    'late':  'strat_late',
}
_BEST_COLOR = {
    'micro': (0.35, 0.85, 1.00, 1),
    'macro': (1.00, 0.85, 0.25, 1),
    'soft':  (0.55, 0.90, 0.55, 1),
}


class _BgBox(BoxLayout):
    def __init__(self, bg=_BG_MED, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*bg)
            self._r = Rectangle()
        self.bind(pos=self._upd, size=self._upd)

    def set_bg(self, rgba):
        self._c.rgba = rgba

    def _upd(self, *_):
        self._r.pos  = self.pos
        self._r.size = self.size


def _lbl(text, color=_WHITE, height=28, halign='left', bold=False, fs='12sp'):
    t = f'[b]{text}[/b]' if bold else text
    l = Label(text=t, markup=True, color=color,
              size_hint_y=None, height=height,
              halign=halign, valign='middle', font_size=fs)
    l.bind(size=l.setter('text_size'))
    return l


class StrategyPickerPopup(Popup):

    def __init__(self, db_name, team_name, on_confirmed=None, **kw):
        super().__init__(**kw)
        self.title       = f'Выбор стратегии — {team_name}'
        self.size_hint   = (0.88, 0.92)
        self._db         = db_name
        self._team       = team_name
        self._on_confirmed = on_confirmed
        self._selected   = {}   # phase → key
        self._btn_groups = {}   # phase → {key → button}
        self._load_current()
        self._build()

    def _load_current(self):
        conn = sqlite3.connect(self._db)
        row = conn.execute(
            "SELECT COALESCE(strat_early,'safe_farm'), "
            "COALESCE(strat_mid,'map_control'), "
            "COALESCE(strat_late,'teamfight') FROM teams WHERE name=?",
            (self._team,)
        ).fetchone()
        conn.close()
        if row:
            self._selected = {'early': row[0], 'mid': row[1], 'late': row[2]}
        else:
            self._selected = {'early': 'safe_farm', 'mid': 'map_control', 'late': 'teamfight'}

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=4, padding=6)
        sv   = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=4)
        grid.bind(minimum_height=grid.setter('height'))

        for phase in ('early', 'mid', 'late'):
            strats = _PHASE_STRATS[phase]
            current = self._selected.get(phase, '')

            # Phase header
            hdr = _BgBox(bg=_BG_HDR, orientation='horizontal',
                         size_hint_y=None, height=34, padding=(8, 0))
            hdr.add_widget(_lbl(_PHASE_LABEL[phase], _ACCENT, height=34,
                                bold=True, fs='13sp'))
            grid.add_widget(hdr)

            self._btn_groups[phase] = {}

            for key, s in strats.items():
                is_sel = key == current
                card = _BgBox(bg=_BG_SEL if is_sel else _BG_MED,
                              orientation='vertical',
                              size_hint_y=None, height=100,
                              padding=(10, 6), spacing=2)

                # Name row
                best_c = _BEST_COLOR.get(s.get('best_skill', 'micro'), _WHITE)
                name_row = BoxLayout(size_hint_y=None, height=26, spacing=6)
                sel_mark = 'OK ' if is_sel else '   '
                name_row.add_widget(_lbl(f'{sel_mark}[b]{s["name"]}[/b]',
                                         best_c, height=26, fs='13sp'))
                best_tag = {'micro': 'Micro', 'macro': 'Macro', 'soft': 'Soft'}.get(
                    s.get('best_skill', ''), '')
                name_row.add_widget(_lbl(f'[лучше при высоком {best_tag}]',
                                         _DIM, height=26, halign='right', fs='10sp'))
                card.add_widget(name_row)

                card.add_widget(_lbl(f'+ {s["pros"]}', _GREEN, height=20, fs='10sp'))
                card.add_widget(_lbl(f'− {s["cons"]}', _RED,   height=20, fs='10sp'))

                btn = Button(
                    text='OK Выбрано' if is_sel else 'Выбрать',
                    size_hint_y=None, height=26,
                    background_color=(0.12, 0.50, 0.18, 1) if is_sel else (0.28, 0.28, 0.38, 1),
                    background_normal='', font_size='11sp',
                )
                btn.bind(on_press=lambda _, p=phase, k=key, c=card: self._select(p, k, c))
                card.add_widget(btn)
                self._btn_groups[phase][key] = (card, btn)
                grid.add_widget(card)

        sv.add_widget(grid)
        root.add_widget(sv)

        confirm = Button(text='OK Подтвердить стратегию', size_hint_y=None, height=50,
                         background_color=(0.15, 0.55, 0.20, 1), background_normal='',
                         font_size='14sp')
        confirm.bind(on_press=self._confirm)
        root.add_widget(confirm)
        self.content = root

    def _select(self, phase, key, _card):
        prev = self._selected.get(phase)
        if prev and prev in self._btn_groups.get(phase, {}):
            old_card, old_btn = self._btn_groups[phase][prev]
            old_card.set_bg(_BG_MED)
            old_btn.text = 'Выбрать'
            old_btn.background_color = (0.28, 0.28, 0.38, 1)

        self._selected[phase] = key
        card, btn = self._btn_groups[phase][key]
        card.set_bg(_BG_SEL)
        btn.text = 'OK Выбрано'
        btn.background_color = (0.12, 0.50, 0.18, 1)

    def _confirm(self, _):
        conn = sqlite3.connect(self._db)
        conn.execute(
            "UPDATE teams SET strat_early=?, strat_mid=?, strat_late=? WHERE name=?",
            (self._selected.get('early', 'safe_farm'),
             self._selected.get('mid',   'map_control'),
             self._selected.get('late',  'teamfight'),
             self._team),
        )
        conn.commit()
        conn.close()
        self.dismiss()
        if self._on_confirmed:
            self._on_confirmed()
