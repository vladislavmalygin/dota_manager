import sqlite3
import os

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line, Triangle

from logic.tournaments.runner import (
    generate_tournament_events,
    save_tournament_results,
    get_lineup,
)
from logic.ai import update_morale_after_tournament, ai_transfers, apply_training_from_games


# ── palette ──────────────────────────────────────────────────────────────────
_ACCENT   = (0.35, 0.85, 1.00, 1)
_GOLD     = (1.00, 0.85, 0.25, 1)
_SILVER   = (0.85, 0.85, 0.85, 1)
_BRONZE   = (0.80, 0.55, 0.30, 1)
_GREEN    = (0.20, 0.88, 0.35, 1)
_RED      = (0.90, 0.28, 0.20, 1)
_PLAYER   = (0.30, 1.00, 0.50, 1)
_DIM      = (0.55, 0.55, 0.55, 1)
_WHITE    = (0.92, 0.92, 0.92, 1)
_YELLOW   = (1.00, 0.90, 0.25, 1)

_BG_DARK  = (0.10, 0.10, 0.12, 1)
_BG_MED   = (0.15, 0.15, 0.18, 1)
_BG_PANEL = (0.12, 0.18, 0.22, 1)
_BG_WIN   = (0.08, 0.28, 0.10, 1)
_BG_LOSE  = (0.28, 0.08, 0.08, 1)
_BG_HEAD  = (0.10, 0.22, 0.32, 1)


# ── widget helpers ────────────────────────────────────────────────────────────

def _lbl(text, height=32, color=_WHITE, bold=False, halign='left', font_size='13sp'):
    t = f'[b]{text}[/b]' if bold else text
    lbl = Label(
        text=t, markup=True,
        size_hint_y=None, height=height,
        color=color, halign=halign, valign='middle',
        font_size=font_size,
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


def _add_message(db_name, text, author='Система'):
    conn = sqlite3.connect(db_name)
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
        (text, author),
    )
    conn.commit()
    conn.close()


def _logo_path(logo):
    if logo:
        p = f"images/{logo}"
        if os.path.exists(p):
            return p
    return None


class _BgBox(BoxLayout):
    """BoxLayout with a mutable solid background colour."""
    def __init__(self, bg=_BG_MED, radius=0, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._color_obj = Color(*bg)
            if radius:
                self._rect = RoundedRectangle(radius=[radius])
            else:
                self._rect = Rectangle()
        self.bind(pos=self._upd, size=self._upd)

    def set_bg(self, rgba):
        self._color_obj.rgba = rgba

    def _upd(self, *_):
        self._rect.pos  = self.pos
        self._rect.size = self.size


def _section_title(text, color=_ACCENT):
    box = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                 size_hint_y=None, height=40)
    lbl = Label(
        text=f'[b]{text}[/b]', markup=True,
        color=color, halign='center', valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    box.add_widget(lbl)
    return box


def _divider(height=2, color=(0.25, 0.35, 0.45, 1)):
    return _BgBox(bg=color, size_hint_y=None, height=height)


def _auto_grid():
    g = GridLayout(cols=1, size_hint_y=None, spacing=2)
    g.bind(minimum_height=g.setter('height'))
    return g


def _team_logo_widget(logo, size=40):
    path = _logo_path(logo)
    if path:
        return Image(source=path, size_hint=(None, None), size=(size, size),
                     allow_stretch=True, keep_ratio=True)
    return Label(text='', size_hint=(None, None), size=(size, size))


# ── match log schedule ────────────────────────────────────────────────────────

def _build_log_schedule(lines):
    """Return [(cumulative_seconds, line)] for timed display."""
    schedule = []
    t = 0.0
    speed = 0.5   # laning: 0.5s per event

    for line in lines:
        s = line.strip()
        if line.startswith('─'):
            schedule.append((t, line))            # separators: instant
        elif s == 'ЛАЙНСТЕЙДЖ':
            schedule.append((t, line))            # instant
        elif 'МИДГЕЙМ' in s:
            t += 2.0                              # pause before midgame
            schedule.append((t, line))
            speed = 1.0
        elif s == 'ЛЕЙТГЕЙМ':
            t += 2.0
            schedule.append((t, line))
            speed = 1.4
        elif s.startswith('ПОБЕДИТЕЛЬ'):
            t += 2.0
            schedule.append((t, line))
        else:
            t += speed
            schedule.append((t, line))

    return schedule


# ── GroupTableWidget ──────────────────────────────────────────────────────────

class GroupTableWidget(BoxLayout):
    """Live-updating group standings table."""

    _ROW_H = 34

    def __init__(self, group_idx, teams, player_teams, logo_map=None, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('spacing', 0)
        super().__init__(**kw)
        self._player_teams = set(player_teams)
        self._standings = {t: 0 for t in teams}
        self._logo_map = logo_map or {}
        self._team_data = {}   # team → (tbox, name_lbl, pts_lbl)
        self._rows_grid = GridLayout(cols=1, size_hint_y=None, spacing=0)
        self._rows_grid.bind(minimum_height=self._rows_grid.setter('height'))
        self._last_lbl = None
        self._build(group_idx, teams)
        self._rows_grid.bind(height=self._on_rows_h)
        self._on_rows_h(None, self._rows_grid.height)

    def _on_rows_h(self, inst, h):
        self.height = 28 + 22 + h + 26

    def _build(self, group_idx, teams):
        # Header
        hdr = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                     size_hint_y=None, height=28)
        hdr.add_widget(_lbl(f'  Группа {group_idx + 1}',
                            color=_ACCENT, bold=True, height=28))
        self.add_widget(hdr)

        # Column header
        chdr = _BgBox(bg=(0.08, 0.10, 0.14, 1), orientation='horizontal',
                      size_hint_y=None, height=22, padding=(4, 0))
        chdr.add_widget(_lbl('  Команда', color=_DIM, height=22, font_size='11sp'))
        chdr.add_widget(_lbl('Очки  ', color=_DIM, height=22,
                             halign='right', font_size='11sp'))
        self.add_widget(chdr)

        # Team rows
        for i, team in enumerate(teams):
            is_p = team in self._player_teams
            bg = _BG_MED if i % 2 == 0 else _BG_DARK
            tbox = _BgBox(bg=bg, orientation='horizontal',
                          size_hint_y=None, height=self._ROW_H, padding=(4, 0),
                          spacing=4)
            logo = self._logo_map.get(team)
            if logo:
                tbox.add_widget(_team_logo_widget(logo, size=28))

            name_lbl = Label(
                text=('★ ' if is_p else '') + team,
                color=_PLAYER if is_p else _WHITE,
                halign='left', valign='middle', font_size='12sp',
            )
            name_lbl.bind(size=name_lbl.setter('text_size'))

            pts_lbl = Label(
                text='0  ', color=_WHITE,
                size_hint_x=None, width=40,
                halign='right', valign='middle', font_size='12sp',
            )
            tbox.add_widget(name_lbl)
            tbox.add_widget(pts_lbl)
            self._rows_grid.add_widget(tbox)
            self._team_data[team] = (tbox, name_lbl, pts_lbl)

        self.add_widget(self._rows_grid)

        self._last_lbl = Label(
            text='', size_hint_y=None, height=26,
            color=_DIM, halign='left', valign='middle', font_size='11sp',
        )
        self._last_lbl.bind(size=self._last_lbl.setter('text_size'))
        self.add_widget(self._last_lbl)

    def update_standings(self, standings, last_match=None):
        self._standings = dict(standings)
        sorted_s = sorted(standings.items(), key=lambda x: x[1], reverse=True)

        self._rows_grid.clear_widgets()
        for i, (team, pts) in enumerate(sorted_s):
            if team not in self._team_data:
                continue
            tbox, name_lbl, pts_lbl = self._team_data[team]
            pts_lbl.text = f'{pts}  '
            bg = _BG_MED if i % 2 == 0 else _BG_DARK
            tbox.set_bg(bg)
            self._rows_grid.add_widget(tbox)

        if last_match:
            w, l = last_match
            self._last_lbl.text = f'  {w}  →  победил  {l}'
            self._last_lbl.color = _GREEN

    def finalize(self):
        sorted_s = sorted(self._standings.items(), key=lambda x: x[1], reverse=True)
        self._rows_grid.clear_widgets()
        for rank, (team, pts) in enumerate(sorted_s):
            if team not in self._team_data:
                continue
            tbox, name_lbl, pts_lbl = self._team_data[team]
            if rank < 2:
                tbox.set_bg(_BG_WIN)
                name_lbl.color = _GREEN
                pts_lbl.color = _GREEN
            else:
                tbox.set_bg(_BG_LOSE)
                name_lbl.color = _RED
                pts_lbl.color = _RED
            self._rows_grid.add_widget(tbox)
        self._last_lbl.text = '  → Плей-офф определён'
        self._last_lbl.color = _ACCENT


# ── DotaMapWidget ─────────────────────────────────────────────────────────────

# Normalized (x, y) positions per role per phase. (0,0)=bottom-left, (1,1)=top-right.
_MAP_POS = {
    'laning': {
        'team1_carry':           (0.22, 0.12),
        'team1_mid':             (0.38, 0.36),
        'team1_offlane':         (0.12, 0.76),
        'team1_partial_support': (0.16, 0.70),
        'team1_full_support':    (0.20, 0.20),
        'team2_carry':           (0.78, 0.88),
        'team2_mid':             (0.62, 0.64),
        'team2_offlane':         (0.88, 0.24),
        'team2_partial_support': (0.84, 0.30),
        'team2_full_support':    (0.80, 0.80),
    },
    'midgame': {
        'team1_carry':           (0.38, 0.30),
        'team1_mid':             (0.45, 0.48),
        'team1_offlane':         (0.30, 0.55),
        'team1_partial_support': (0.28, 0.50),
        'team1_full_support':    (0.35, 0.42),
        'team2_carry':           (0.62, 0.70),
        'team2_mid':             (0.55, 0.52),
        'team2_offlane':         (0.70, 0.45),
        'team2_partial_support': (0.72, 0.50),
        'team2_full_support':    (0.65, 0.58),
    },
    'lategame': {
        'team1_carry':           (0.50, 0.46),
        'team1_mid':             (0.48, 0.50),
        'team1_offlane':         (0.44, 0.52),
        'team1_partial_support': (0.42, 0.48),
        'team1_full_support':    (0.46, 0.54),
        'team2_carry':           (0.56, 0.52),
        'team2_mid':             (0.58, 0.50),
        'team2_offlane':         (0.60, 0.48),
        'team2_partial_support': (0.62, 0.52),
        'team2_full_support':    (0.54, 0.46),
    },
}

_ROLE_LABELS = {
    'team1_carry': 'C', 'team1_mid': 'M', 'team1_offlane': 'O',
    'team1_partial_support': '4', 'team1_full_support': '5',
    'team2_carry': 'C', 'team2_mid': 'M', 'team2_offlane': 'O',
    'team2_partial_support': '4', 'team2_full_support': '5',
}


class DotaMapWidget(Widget):

    def __init__(self, team1, team2, **kwargs):
        super().__init__(**kwargs)
        self._team1  = team1
        self._team2  = team2
        self._snap   = {
            'phase': 'laning', 'minute': 0,
            'kills_t1': 0, 'kills_t2': 0,
            'tokens_t1': 0, 'tokens_t2': 0,
        }
        self._roshan = True
        self.bind(size=self._draw, pos=self._draw)

    def apply_snap(self, snap):
        self._snap = snap
        old_phase = getattr(self, '_last_phase', 'laning')
        if 'забрала Рошана' in str(snap.get('_event', '')):
            self._roshan = False
        if snap.get('phase') != old_phase:
            self._last_phase = snap['phase']
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.size
        x0, y0 = self.pos
        if w < 10 or h < 10:
            return

        snap   = self._snap
        phase  = snap.get('phase', 'laning')
        minute = snap.get('minute', 0)
        kt1    = snap.get('kills_t1', 0)
        kt2    = snap.get('kills_t2', 0)
        tok1   = snap.get('tokens_t1', 0)
        tok2   = snap.get('tokens_t2', 0)
        total  = max(tok1 + tok2, 1)
        adv    = (tok1 - tok2) / total  # -1..+1

        with self.canvas:
            # ── background ──────────────────────────────────────
            Color(0.08, 0.14, 0.08, 1)
            Rectangle(pos=(x0, y0), size=(w, h))

            # ── river (diagonal blue band) ───────────────────────
            Color(0.10, 0.25, 0.45, 0.7)
            # draw as a rotated parallelogram approximated by two triangles
            rw = w * 0.13
            # top-left to bottom-right diagonal strip
            pts1 = [
                x0 + w * 0.0,  y0 + h * 0.55,
                x0 + w * 0.10, y0 + h * 0.65,
                x0 + w * 0.90, y0 + h * 0.35,
            ]
            pts2 = [
                x0 + w * 0.0,  y0 + h * 0.55,
                x0 + w * 0.90, y0 + h * 0.35,
                x0 + w * 0.90, y0 + h * 0.45,
            ]
            pts3 = [
                x0 + w * 0.0,  y0 + h * 0.55,
                x0 + w * 0.0,  y0 + h * 0.45,
                x0 + w * 0.90, y0 + h * 0.35,
            ]
            Triangle(points=pts1)
            Triangle(points=pts3)

            # ── lane paths ───────────────────────────────────────
            Color(0.22, 0.30, 0.18, 1)
            lw = max(3, w * 0.04)
            # top lane
            Line(points=[x0+w*0.12, y0+h*0.88, x0+w*0.88, y0+h*0.88], width=lw)
            # bot lane
            Line(points=[x0+w*0.12, y0+h*0.12, x0+w*0.88, y0+h*0.12], width=lw)
            # mid lane (diagonal)
            Line(points=[x0+w*0.18, y0+h*0.18, x0+w*0.82, y0+h*0.82], width=lw)

            # ── Radiant base (bottom-left) ───────────────────────
            Color(0.15, 0.65, 0.25, 0.9)
            bsz = w * 0.12
            Rectangle(pos=(x0 + w*0.04, y0 + h*0.04), size=(bsz, bsz))

            # ── Dire base (top-right) ─────────────────────────────
            Color(0.80, 0.22, 0.18, 0.9)
            Rectangle(pos=(x0 + w*0.84, y0 + h*0.84), size=(bsz, bsz))

            # ── Roshan pit ───────────────────────────────────────
            rosh_x = x0 + w * 0.28
            rosh_y = y0 + h * 0.52
            rsz = max(8, w * 0.055)
            if self._roshan:
                Color(0.85, 0.65, 0.10, 1)
                Ellipse(pos=(rosh_x - rsz/2, rosh_y - rsz/2), size=(rsz, rsz))
            else:
                Color(0.4, 0.4, 0.4, 0.5)
                Ellipse(pos=(rosh_x - rsz/2, rosh_y - rsz/2), size=(rsz, rsz))

            # ── players ──────────────────────────────────────────
            positions = _MAP_POS.get(phase, _MAP_POS['laning'])
            dot_r = max(7, w * 0.055)

            for role, (nx, ny) in positions.items():
                px = x0 + nx * w
                py = y0 + ny * h
                is_t1 = role.startswith('team1')
                if is_t1:
                    Color(0.20, 0.90, 0.35, 1)
                else:
                    Color(0.95, 0.30, 0.25, 1)
                Ellipse(pos=(px - dot_r/2, py - dot_r/2), size=(dot_r, dot_r))
                # border
                Color(0.0, 0.0, 0.0, 0.8)
                Line(circle=(px, py, dot_r/2 + 1), width=1)

            # ── advantage bar at bottom ──────────────────────────
            bar_h = max(10, h * 0.055)
            bar_y = y0 + 2
            mid_x = x0 + w / 2

            Color(0.55, 0.25, 0.18, 1)
            Rectangle(pos=(x0, bar_y), size=(w, bar_h))

            if adv >= 0:
                Color(0.20, 0.85, 0.35, 1)
                Rectangle(pos=(mid_x, bar_y), size=(adv * w / 2, bar_h))
            else:
                Color(0.90, 0.28, 0.22, 1)
                Rectangle(pos=(mid_x + adv * w / 2, bar_y),
                          size=(-adv * w / 2, bar_h))

            # center tick
            Color(0.9, 0.9, 0.9, 0.8)
            Line(points=[mid_x, bar_y, mid_x, bar_y + bar_h], width=1.5)

        # ── overlay labels (kills + timer) drawn via canvas ──────
        # We don't use Label here to avoid widget tree overhead;
        # instead the parent popup owns those labels.

    def get_kills(self):
        return self._snap.get('kills_t1', 0), self._snap.get('kills_t2', 0)

    def get_minute(self):
        return self._snap.get('minute', 0)


# ── MatchLogPopup – animated match with phase pauses ─────────────────────────

class MatchLogPopup(Popup):

    def __init__(self, team1, team2, winner, log_lines, on_close,
                 t1_logo=None, t2_logo=None, snapshots=None,
                 best_of=1, final_score=(0, 0), **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        self._lines     = log_lines
        self._snapshots    = snapshots or []
        self._best_of      = best_of
        self._final_score  = final_score
        self._schedule  = _build_log_schedule(log_lines)
        self._sched_idx = 0
        self._elapsed   = 0.0
        self._on_close  = on_close
        self._interval  = None
        self._winner    = winner
        self._team1     = team1
        self._team2     = team2
        self._t1_logo   = t1_logo
        self._t2_logo   = t2_logo
        self._build()
        Clock.schedule_once(lambda dt: self._start(), 0.15)

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=0, padding=0)

        # ── header: teams + score + timer ─────────────────────
        header = _BgBox(bg=_BG_PANEL, orientation='horizontal',
                        size_hint_y=None, height=70, padding=(8, 4), spacing=6)

        def _team_hdr(name, logo, align):
            box = BoxLayout(orientation='horizontal', spacing=6)
            img = _team_logo_widget(logo, size=44) if logo else None
            lbl = Label(text=f'[b]{name}[/b]', markup=True,
                        color=_PLAYER, halign=align, valign='middle', font_size='13sp')
            lbl.bind(size=lbl.setter('text_size'))
            if align == 'right' and img:
                box.add_widget(lbl); box.add_widget(img)
            else:
                if img: box.add_widget(img)
                box.add_widget(lbl)
            return box

        header.add_widget(_team_hdr(self._team1, self._t1_logo, 'right'))

        # center panel: score + timer
        center = BoxLayout(orientation='vertical', size_hint_x=None, width=140,
                           spacing=2, padding=(4, 2))
        self._score_lbl = Label(
            text='[b]0  —  0[/b]', markup=True,
            color=_YELLOW, halign='center', valign='middle', font_size='18sp',
            size_hint_y=0.6,
        )
        self._score_lbl.bind(size=self._score_lbl.setter('text_size'))
        self._timer_lbl = Label(
            text='0:00', color=_DIM, halign='center', valign='middle',
            font_size='11sp', size_hint_y=0.4,
        )
        self._timer_lbl.bind(size=self._timer_lbl.setter('text_size'))
        center.add_widget(self._score_lbl)
        center.add_widget(self._timer_lbl)
        header.add_widget(center)

        header.add_widget(_team_hdr(self._team2, self._t2_logo, 'left'))
        root.add_widget(header)
        root.add_widget(_divider())

        # ── body: map (left) + log (right) ────────────────────
        body = BoxLayout(orientation='horizontal', size_hint=(1, 1), spacing=4)

        # map panel
        map_panel = _BgBox(bg=(0.06, 0.10, 0.06, 1), orientation='vertical',
                           size_hint=(0.42, 1), padding=(4, 4), spacing=0)
        self._map = DotaMapWidget(self._team1, self._team2, size_hint=(1, 1))
        map_panel.add_widget(self._map)

        # team legend
        legend = BoxLayout(orientation='horizontal', size_hint_y=None, height=22,
                           spacing=4, padding=(4, 0))
        def _leg_lbl(text, color):
            l = Label(text=text, color=color, font_size='10sp',
                      halign='center', valign='middle')
            l.bind(size=l.setter('text_size'))
            return l
        legend.add_widget(_leg_lbl(f'● {self._team1}', _GREEN))
        legend.add_widget(_leg_lbl(f'● {self._team2}', _RED))
        map_panel.add_widget(legend)

        body.add_widget(map_panel)

        # log panel
        log_panel = BoxLayout(orientation='vertical', size_hint=(0.58, 1))
        self._log_lbl = Label(
            text='', size_hint_y=None,
            color=(0.88, 0.88, 0.88, 1),
            halign='left', valign='top',
            padding=(10, 6), font_size='12sp',
        )
        self._log_lbl.bind(texture_size=self._log_lbl.setter('size'))
        self._scroll = ScrollView(size_hint=(1, 1))
        self._scroll.add_widget(self._log_lbl)
        log_panel.add_widget(self._scroll)
        body.add_widget(log_panel)

        root.add_widget(body)
        root.add_widget(_divider())

        # ── status ────────────────────────────────────────────
        status_box = _BgBox(bg=(0.08, 0.08, 0.10, 1), orientation='horizontal',
                            size_hint_y=None, height=32, padding=(10, 0))
        self._status_lbl = Label(
            text='Матч идёт...', color=_DIM,
            halign='left', valign='middle', font_size='12sp',
        )
        self._status_lbl.bind(size=self._status_lbl.setter('text_size'))
        status_box.add_widget(self._status_lbl)
        root.add_widget(status_box)

        # ── buttons ───────────────────────────────────────────
        btn_bar = _BgBox(bg=_BG_DARK, orientation='horizontal',
                         size_hint_y=None, height=48, spacing=6, padding=(6, 4))
        skip_btn = Button(text='Пропустить',
                          background_color=(0.45, 0.45, 0.15, 1),
                          background_normal='')
        skip_btn.bind(on_press=self._skip)
        self._done_btn = Button(text='Закрыть матч  ✓',
                                background_color=(0.12, 0.55, 0.20, 1),
                                background_normal='', disabled=True)
        self._done_btn.bind(on_press=self._done)
        btn_bar.add_widget(skip_btn)
        btn_bar.add_widget(self._done_btn)
        root.add_widget(btn_bar)

        self.content = root

    def _start(self):
        self._interval = Clock.schedule_interval(self._tick, 0.05)

    def _tick(self, dt):
        self._elapsed += dt
        changed = False
        while self._sched_idx < len(self._schedule):
            target_t, line = self._schedule[self._sched_idx]
            if self._elapsed >= target_t:
                sep = '\n' if self._log_lbl.text else ''
                self._log_lbl.text += sep + line
                self._apply_snap(self._sched_idx)
                self._sched_idx += 1
                changed = True
            else:
                break
        if changed:
            Clock.schedule_once(lambda dt: setattr(self._scroll, 'scroll_y', 0), 0.02)
        if self._sched_idx >= len(self._schedule):
            self._finish()

    def _apply_snap(self, idx):
        if not self._snapshots or idx >= len(self._snapshots):
            return
        snap = self._snapshots[idx]
        self._map.apply_snap(snap)
        kt1 = snap.get('kills_t1', 0)
        kt2 = snap.get('kills_t2', 0)
        self._score_lbl.text = f'[b]{kt1}  —  {kt2}[/b]'
        m = snap.get('minute', 0)
        self._timer_lbl.text = f'{m}:00'

    def _finish(self):
        if self._interval:
            self._interval.cancel()
            self._interval = None
        s1, s2 = self._final_score
        bo_str = f'  BO{self._best_of}' if self._best_of > 1 else ''
        self._status_lbl.text = (
            f'Победитель:  {self._winner}  [{s1}:{s2}]{bo_str}'
        )
        self._status_lbl.color = _GREEN
        self._done_btn.disabled = False

    def _skip(self, _):
        if self._interval:
            self._interval.cancel()
            self._interval = None
        self._log_lbl.text = '\n'.join(self._lines)
        self._sched_idx = len(self._schedule)
        if self._snapshots:
            self._apply_snap(len(self._snapshots) - 1)
        Clock.schedule_once(lambda dt: setattr(self._scroll, 'scroll_y', 0), 0.02)
        self._finish()

    def _done(self, _):
        self.dismiss()
        if self._on_close:
            self._on_close()


# ── TournamentPopup ───────────────────────────────────────────────────────────

class TournamentPopup(Popup):

    _BTN_LABELS = {
        'draw':               'Начать групповой этап',
        'match_lineup':       'Сыграть матч  ▶',
        'match_result':       'Следующий матч  →',
        'groups_complete':    'Итоги групп  →',
        'stage_header':       'Начать матчи',
        'tournament_results': 'Завершить турнир',
    }

    def __init__(self, db_name, on_finish=None, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.size_hint = (0.96, 0.96)
        self.auto_dismiss = False
        self._results_saved = False
        self._group_tables = []
        self._on_finish = on_finish
        self._season_over = False
        self._season_year = None

        # Load logo map once
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM tournaments WHERE place1 IS NULL ORDER BY start_date LIMIT 1")
        row = cur.fetchone()
        cur.execute("SELECT name, logo FROM teams")
        self._logo_map = {r[0].strip(): r[1] for r in cur.fetchall()}
        conn.close()

        if not row:
            self.title = 'Нет турниров'
            self.content = Label(text='Все турниры сезона сыграны.')
            return

        self.tournament_id, tournament_name = row
        self.title = tournament_name

        self.events, self.placements, self.group_eliminated = \
            generate_tournament_events(db_name, self.tournament_id)
        self.event_idx = 0

        # ── layout ────────────────────────────────────────────
        self._content_grid = _auto_grid()

        # Tournament name banner
        banner = _BgBox(bg=_BG_PANEL, orientation='horizontal',
                        size_hint_y=None, height=48)
        lbl = Label(text=f'[b]{tournament_name}[/b]', markup=True,
                    color=_ACCENT, halign='center', valign='middle', font_size='16sp')
        lbl.bind(size=lbl.setter('text_size'))
        banner.add_widget(lbl)
        self._content_grid.add_widget(banner)

        self._scroll = ScrollView(size_hint=(1, 1))
        self._scroll.add_widget(self._content_grid)

        self._next_btn = Button(
            text='Показать жеребьёвку',
            size_hint=(0.75, None), height=52,
            background_color=(0.18, 0.55, 0.85, 1), background_normal='',
        )
        self._next_btn.bind(on_press=self._on_next)
        close_btn = Button(
            text='Закрыть', size_hint=(0.25, None), height=52,
            background_color=(0.65, 0.18, 0.18, 1), background_normal='',
        )
        close_btn.bind(on_press=self.dismiss)

        btn_row = BoxLayout(orientation='horizontal',
                            size_hint_y=None, height=56, spacing=4)
        btn_row.add_widget(self._next_btn)
        btn_row.add_widget(close_btn)

        layout = BoxLayout(orientation='vertical', spacing=2, padding=4)
        layout.add_widget(self._scroll)
        layout.add_widget(btn_row)
        self.content = layout

    # ── stepping ──────────────────────────────────────────────

    def _on_next(self, _):
        if self.event_idx >= len(self.events):
            return
        event = self.events[self.event_idx]
        self.event_idx += 1

        block = self._render(event)
        if block:
            self._content_grid.add_widget(_divider(height=1))
            self._content_grid.add_widget(block)

        if event['type'] == 'tournament_results' and not self._results_saved:
            self._persist_results(event)
            self._results_saved = True

        if event['type'] == 'match_lineup' and event.get('match_log'):
            self._next_btn.disabled = True
            t1, t2 = event['team1'], event['team2']
            bo = event.get('best_of', 1)
            s1 = event.get('score_t1', 0)
            s2 = event.get('score_t2', 0)
            MatchLogPopup(
                team1=t1, team2=t2,
                winner=event['winner'],
                log_lines=event['match_log'],
                snapshots=event.get('match_snaps', []),
                on_close=self._after_match_log,
                t1_logo=self._logo_map.get(t1),
                t2_logo=self._logo_map.get(t2),
                best_of=bo, final_score=(s1, s2),
            ).open()
            Clock.schedule_once(lambda dt: setattr(self._scroll, 'scroll_y', 0), 0.05)
            return

        self._update_btn()
        Clock.schedule_once(lambda dt: setattr(self._scroll, 'scroll_y', 0), 0.05)

    def _after_match_log(self):
        self._next_btn.disabled = False
        self._on_next(None)

    def _update_btn(self):
        if self.event_idx >= len(self.events):
            self._next_btn.disabled = True
            self._next_btn.text = 'Завершено'
            return
        nxt = self.events[self.event_idx]['type']
        self._next_btn.text = self._BTN_LABELS.get(nxt, 'Далее')

    # ── rendering ─────────────────────────────────────────────

    def _render(self, ev):
        t = ev['type']
        if t == 'draw':              return self._render_draw(ev)
        if t == 'match_lineup':      return self._render_lineup(ev)
        if t == 'match_result':      return self._render_match_result(ev)
        if t == 'groups_complete':   return self._render_groups_complete(ev)
        if t == 'stage_header':      return self._render_stage_header(ev)
        if t == 'tournament_results': return self._render_results(ev)
        return None

    # ── draw ──────────────────────────────────────────────────

    def _render_draw(self, ev):
        player_teams = set(ev.get('player_teams', []))
        block = _auto_grid()
        block.add_widget(_section_title('ЖЕРЕБЬЁВКА'))

        # 4 GroupTableWidgets side by side
        groups_row = BoxLayout(orientation='horizontal',
                               size_hint_y=None, height=220,
                               spacing=6, padding=(4, 4))
        self._group_tables = []
        for i, group in enumerate(ev['groups']):
            gtw = GroupTableWidget(
                group_idx=i,
                teams=group,
                player_teams=player_teams,
                logo_map=self._logo_map,
            )
            self._group_tables.append(gtw)
            groups_row.add_widget(gtw)

        block.add_widget(groups_row)
        return block

    # ── lineup ────────────────────────────────────────────────

    def _render_lineup(self, ev):
        t1, t2 = ev['team1'], ev['team2']
        stage  = ev.get('stage', '')
        l1, l2 = ev.get('t1_lineup', []), ev.get('t2_lineup', [])

        block = _auto_grid()
        block.add_widget(_section_title(f'МАТЧ  [{stage}]', color=_YELLOW))

        # Team header with logos
        name_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=48, spacing=4)
        for team in [t1, t2]:
            nb = _BgBox(bg=_BG_PANEL, orientation='horizontal',
                        size_hint_y=None, height=48, padding=(8, 4), spacing=6)
            logo = self._logo_map.get(team)
            if logo:
                nb.add_widget(_team_logo_widget(logo, size=38))
            lbl = Label(text=f'[b]{team}[/b]', markup=True,
                        color=_PLAYER, halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            nb.add_widget(lbl)
            name_row.add_widget(nb)
        block.add_widget(name_row)

        # Column header
        hdr = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                     size_hint_y=None, height=26, spacing=2)
        for txt in ['  Роль', f'  {t1[:18]}', f'  {t2[:18]}']:
            hdr.add_widget(_lbl(txt, color=_ACCENT, bold=True, height=26))
        block.add_widget(hdr)

        for i in range(max(len(l1), len(l2))):
            p1 = l1[i] if i < len(l1) else {}
            p2 = l2[i] if i < len(l2) else {}
            role = (p1 or p2).get('role', '')
            bg = (0.12, 0.12, 0.16, 1) if i % 2 == 0 else _BG_MED
            rrow = _BgBox(bg=bg, orientation='horizontal',
                          size_hint_y=None, height=34, spacing=2)

            def _pt(p):
                return f"{p['nick']}  ({p['micro']}/{p['macro']})" if p else '—'

            rrow.add_widget(_lbl(f'  {role}', color=_DIM, height=34))
            rrow.add_widget(_lbl(f'  {_pt(p1)}', color=_WHITE, height=34))
            rrow.add_widget(_lbl(f'  {_pt(p2)}', color=_WHITE, height=34))
            block.add_widget(rrow)

        return block

    # ── match result ──────────────────────────────────────────

    def _render_match_result(self, ev):
        t1, t2, winner, loser = ev['team1'], ev['team2'], ev['winner'], ev['loser']
        stage    = ev.get('stage', '')
        is_player = ev.get('is_player_match', False)
        s1, s2   = ev.get('score_t1', 0), ev.get('score_t2', 0)
        score_str = f' [{s1}:{s2}]' if (s1 or s2) else ''

        # Group stage: update live table silently for bots
        is_draw = (not winner and not loser) or (winner == '' and loser == '')
        if 'standings' in ev:
            gi = ev.get('group_idx', -1)
            last = None if is_draw else (winner, loser)
            if 0 <= gi < len(self._group_tables):
                self._group_tables[gi].update_standings(ev['standings'], last_match=last)
            if not is_player:
                return None
            if is_draw:
                rbox = _BgBox(bg=_BG_MED, orientation='horizontal',
                              size_hint_y=None, height=34)
                rbox.add_widget(_lbl(
                    f'  ★  {t1}  —  {t2}  Ничья{score_str}  [{stage}]',
                    color=_YELLOW, height=34,
                ))
            else:
                rbox = _BgBox(bg=_BG_WIN, orientation='horizontal',
                              size_hint_y=None, height=34)
                rbox.add_widget(_lbl(
                    f'  ★  {winner}  побеждает  {loser}{score_str}  [{stage}]',
                    color=_GREEN, height=34,
                ))
            return rbox

        if is_draw:
            bg, color = _BG_MED, _YELLOW
            text = f'  ★  {t1}  —  {t2}  Ничья{score_str}  [{stage}]'
        elif is_player:
            bg, color = _BG_WIN, _GREEN
            text = f'  ★  {winner}  побеждает  {loser}{score_str}  [{stage}]'
        else:
            score_part = f'  {s1}:{s2}' if (s1 or s2) else ''
            text = f'  {stage}:  {t1}  vs  {t2}  →  {winner}{score_part}'
            bg, color = _BG_MED, _WHITE
        rbox = _BgBox(bg=bg, orientation='horizontal',
                      size_hint_y=None, height=34)
        rbox.add_widget(_lbl(text, color=color, height=34))
        return rbox

    # ── groups complete ───────────────────────────────────────

    def _render_groups_complete(self, ev):
        for gt in self._group_tables:
            gt.finalize()

        block = _auto_grid()
        block.add_widget(_section_title('ПЛЕЙ-ОФФ — КВАЛИФИЦИРОВАВШИЕСЯ', color=_GREEN))
        top = ev.get('top_teams', [])
        for i in range(0, len(top), 4):
            row = BoxLayout(orientation='horizontal',
                            size_hint_y=None, height=36, spacing=4)
            for team in top[i:i+4]:
                tbox = _BgBox(bg=_BG_WIN, orientation='horizontal',
                              size_hint_y=None, height=36, padding=(6, 0), spacing=4)
                logo = self._logo_map.get(team)
                if logo:
                    tbox.add_widget(_team_logo_widget(logo, size=28))
                tbox.add_widget(_lbl(team, color=_GREEN, height=36))
                row.add_widget(tbox)
            block.add_widget(row)
        return block

    # ── stage header ──────────────────────────────────────────

    def _render_stage_header(self, ev):
        stage = ev['stage']
        pairs = ev['pairs']
        block = _auto_grid()
        block.add_widget(_section_title(stage.upper()))

        for t1, t2 in pairs:
            prow = _BgBox(bg=_BG_MED, orientation='horizontal',
                          size_hint_y=None, height=44,
                          padding=(8, 4), spacing=8)
            for team in [t1, t2]:
                tbox = BoxLayout(orientation='horizontal', spacing=6)
                logo = self._logo_map.get(team)
                if logo:
                    tbox.add_widget(_team_logo_widget(logo, size=32))
                tbox.add_widget(_lbl(team, color=_WHITE, height=34))
                prow.add_widget(tbox)
            prow.add_widget(_lbl('VS', color=_YELLOW, height=34,
                                 halign='center', font_size='14sp'))
            # fix order: t1 | VS | t2
            prow.clear_widgets()
            for team in [t1]:
                tbox = BoxLayout(orientation='horizontal', spacing=6)
                logo = self._logo_map.get(team)
                if logo:
                    tbox.add_widget(_team_logo_widget(logo, size=32))
                tbox.add_widget(_lbl(team, color=_WHITE, height=34))
                prow.add_widget(tbox)
            prow.add_widget(_lbl('  VS  ', color=_YELLOW, height=34,
                                 halign='center', font_size='14sp'))
            for team in [t2]:
                tbox = BoxLayout(orientation='horizontal', spacing=6)
                logo = self._logo_map.get(team)
                if logo:
                    tbox.add_widget(_team_logo_widget(logo, size=32))
                tbox.add_widget(_lbl(team, color=_WHITE, height=34))
                prow.add_widget(tbox)
            block.add_widget(prow)
        return block

    # ── tournament results ────────────────────────────────────

    def _render_results(self, ev):
        champion   = ev['champion']
        placements = ev['placements']
        eliminated = ev['group_eliminated']

        block = _auto_grid()
        block.add_widget(_section_title(
            f'ИТОГИ ТУРНИРА  —  ЧЕМПИОН: {champion}', color=_GOLD))

        medals = {1: '🥇', 2: '🥈', 3: '🥉', 4: ' 4.'}
        for team, place in sorted(placements.items(), key=lambda x: x[1]):
            medal = medals.get(place, f'{place:2}.')
            if place == 1:
                bg, color = (0.22, 0.18, 0.04, 1), _GOLD
            elif place == 2:
                bg, color = (0.14, 0.14, 0.14, 1), _SILVER
            elif place <= 4:
                bg, color = (0.18, 0.10, 0.04, 1), _BRONZE
            else:
                bg, color = _BG_MED, _WHITE

            rrow = _BgBox(bg=bg, orientation='horizontal',
                          size_hint_y=None, height=38, padding=(8, 0), spacing=6)
            logo = self._logo_map.get(team)
            if logo:
                rrow.add_widget(_team_logo_widget(logo, size=30))
            rrow.add_widget(_lbl(f'{medal}  {team}', color=color, height=38))
            block.add_widget(rrow)

        block.add_widget(_divider(height=2, color=(0.25, 0.35, 0.45, 1)))
        block.add_widget(_lbl('  Вылет в групповом этапе:', color=_DIM, height=28))
        for i, (team, _) in enumerate(
            sorted(eliminated, key=lambda x: x[1], reverse=True)
        ):
            ebox = _BgBox(bg=_BG_DARK, orientation='horizontal',
                          size_hint_y=None, height=30)
            ebox.add_widget(_lbl(f'  {9+i:2}.  {team}', color=_DIM, height=30))
            block.add_widget(ebox)

        return block

    # ── DB persistence ────────────────────────────────────────

    def _persist_results(self, event):
        save_tournament_results(
            event['tournament_id'],
            event['placements'],
            event['group_eliminated'],
            self.db_name,
        )
        update_morale_after_tournament(
            self.db_name, event['placements'], event['group_eliminated'],
        )
        apply_training_from_games(self.db_name, event.get('games_played', {}))
        ai_transfers(
            self.db_name,
            placements=event['placements'],
            group_eliminated=event['group_eliminated'],
        )

        # Season-end check
        self._season_over, self._season_year = self._check_season_over(
            event['tournament_id']
        )
        if not self._season_over and self._on_finish:
            self._on_finish()
        self.bind(on_dismiss=self._maybe_show_season_end)

        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT name FROM teams WHERE player='yes'")
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        my_team = row[0]
        place = event['placements'].get(my_team)
        if not place:
            for i, (t, _) in enumerate(
                sorted(event['group_eliminated'], key=lambda x: x[1], reverse=True)
            ):
                if t == my_team:
                    place = 9 + i
                    break
        if place:
            _add_message(
                self.db_name,
                f"{self.title} завершён. {my_team} заняла {place}-е место.",
                'Спортивный директор',
            )

    def _check_season_over(self, tournament_id):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT start_date FROM tournaments WHERE id=?", (tournament_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False, None
        year = row[0][:4]
        cur.execute(
            "SELECT COUNT(*) FROM tournaments WHERE start_date LIKE ? AND place1 IS NULL",
            (f'{year}%',),
        )
        remaining = cur.fetchone()[0]
        conn.close()
        return remaining == 0, int(year)

    def _maybe_show_season_end(self, _):
        if getattr(self, '_season_over', False):
            from ingame_interface.season_end import SeasonEndPopup
            SeasonEndPopup(
                self.db_name,
                self._season_year,
                on_confirmed=self._on_finish,
            ).open()


# ── TournamentsViewPopup ──────────────────────────────────────────────────────

class TournamentsViewPopup(Popup):

    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Турниры'
        self.size_hint = (0.92, 0.92)

        grid = _auto_grid()
        grid.spacing = 3
        grid.padding = (8, 4)
        self._fill(db_name, grid)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=50,
            background_color=(0.65, 0.18, 0.18, 1), background_normal='',
        )
        close_btn.bind(on_press=self.dismiss)

        layout = BoxLayout(orientation='vertical', spacing=4, padding=4)
        layout.add_widget(scroll)
        layout.add_widget(close_btn)
        self.content = layout

    def _fill(self, db_name, grid):
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()

        # season rating
        grid.add_widget(_section_title('═══  РЕЙТИНГ СЕЗОНА  ═══'))
        cur.execute("SELECT name, logo, COALESCE(rating,0) FROM teams ORDER BY COALESCE(rating,0) DESC, name")
        teams = cur.fetchall()
        cur.execute("SELECT name FROM teams WHERE player='yes'")
        pr = cur.fetchone()
        player_team = (pr[0] if pr else '').strip()

        hrow = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                      size_hint_y=None, height=28, padding=(8, 0))
        hrow.add_widget(_lbl('  #   Команда', color=_ACCENT, bold=True, height=28))
        hrow.add_widget(_lbl('Rating', color=_ACCENT, bold=True,
                             height=28, halign='right'))
        grid.add_widget(hrow)

        for rank, (name, logo, rating) in enumerate(teams):
            name = name.strip()
            is_p = name == player_team
            if rank == 0:
                bg, color = (0.20, 0.18, 0.04, 1), _GOLD
            elif rank == 1:
                bg, color = (0.14, 0.14, 0.14, 1), _SILVER
            elif rank == 2:
                bg, color = (0.16, 0.10, 0.04, 1), _BRONZE
            elif is_p:
                bg, color = (0.05, 0.20, 0.08, 1), _PLAYER
            else:
                bg, color = (_BG_MED if rank % 2 == 0 else _BG_DARK), _WHITE

            rrow = _BgBox(bg=bg, orientation='horizontal',
                          size_hint_y=None, height=36, padding=(6, 2), spacing=6)
            if logo:
                rrow.add_widget(_team_logo_widget(logo, size=28))
            mark = ' ★' if is_p else '  '
            rrow.add_widget(_lbl(f'  {rank+1:2}.{mark}  {name}',
                                 color=color, height=32))
            rrow.add_widget(_lbl(f'{int(rating):>5} pts  ',
                                 color=color, height=32, halign='right'))
            grid.add_widget(rrow)

        # tournament schedule
        grid.add_widget(_lbl('', height=10))
        grid.add_widget(_section_title('═══  РАСПИСАНИЕ ТУРНИРОВ  ═══'))

        cur.execute(
            """SELECT t.id, t.name, t.start_date, t.prizepool, t.ratingpool,
                      t.place1, tm.name
               FROM tournaments t
               LEFT JOIN teams tm ON t.place1=tm.id
               ORDER BY t.start_date"""
        )
        for tid, name, start, prize, rpool, place1, winner in cur.fetchall():
            done = bool(place1 and winner)
            hdr_color = _GREEN if done else _YELLOW
            bg = (0.06, 0.18, 0.06, 1) if done else (0.14, 0.14, 0.06, 1)
            status = f'✓  {winner.strip()}' if done else '→  Предстоит'

            trow = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                          size_hint_y=None, height=36, padding=(8, 0))
            trow.add_widget(_lbl(f'  {start}  ─  {name}',
                                 color=hdr_color, bold=True, height=36))
            grid.add_widget(trow)

            irow = _BgBox(bg=bg, orientation='horizontal',
                          size_hint_y=None, height=28, padding=(16, 0))
            irow.add_widget(_lbl(
                f'${prize:,}  |  {rpool or 0} pts  |  {status}',
                color=_WHITE, height=28,
            ))
            grid.add_widget(irow)

            if place1:
                row = cur.execute(
                    "SELECT place1,place2,place3,place4,place5,place6,place7,place8 "
                    "FROM tournaments WHERE id=?", (tid,)
                ).fetchone()
                if row:
                    pnames = []
                    for pid in row:
                        if pid:
                            n = cur.execute("SELECT name FROM teams WHERE id=?", (pid,)).fetchone()
                            if n:
                                pnames.append(n[0].strip())
                    if pnames:
                        prow = _BgBox(bg=_BG_DARK, orientation='horizontal',
                                      size_hint_y=None, height=26, padding=(16, 0))
                        prow.add_widget(_lbl(
                            'Топ-8: ' + ', '.join(f'{i+1}.{n}' for i, n in enumerate(pnames)),
                            color=(0.70, 0.90, 0.70, 1), height=26,
                        ))
                        grid.add_widget(prow)

        conn.close()
