import sqlite3
import os
import re

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
    replay_match_with_heroes,
)
from logic.heroes import HEROES, ROLE_ORDER, random_picks
from logic.ai import (update_morale_after_tournament, ai_transfers,
                       apply_training_from_games, update_form_after_tournament)
from ingame_interface.transfers import is_transfer_window as _is_transfer_window


# ── palette (from shared theme) ───────────────────────────────────────────────
import ui_theme as _T

_ACCENT   = _T.ACCENT
_GOLD     = _T.GOLD
_SILVER   = _T.SILVER
_BRONZE   = _T.BRONZE
_GREEN    = _T.POSITIVE
_RED      = _T.NEGATIVE
_PLAYER   = _T.PLAYER_CLR
_DIM      = _T.TEXT_DIM
_WHITE    = _T.TEXT_MAIN
_YELLOW   = _T.WARNING

_BG_DARK  = _T.BG_ROW_B
_BG_MED   = _T.BG_ROW_A
_BG_PANEL = (0.12, 0.18, 0.22, 1)
_BG_WIN   = _T.BG_WIN
_BG_LOSE  = _T.BG_LOSE
_BG_HEAD  = _T.BG_HEADER


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


def _update_reputation(db_name, delta):
    try:
        conn = sqlite3.connect(db_name)
        conn.execute(
            "UPDATE characters SET reputation=MAX(0, COALESCE(reputation,0)+?)",
            (delta,),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _logo_path(logo):
    return _T.logo_path(logo)


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

def _plain(line):
    """Strip Kivy color markup for string comparisons."""
    return re.sub(r'\[/?[^\]]*\]', '', line).strip()


def _build_log_schedule(lines):
    """Return [(cumulative_seconds, line)] for timed display."""
    schedule = []
    t = 0.0
    speed = 0.5

    for line in lines:
        p = _plain(line)
        if line.startswith('─') or p.startswith('─'):
            schedule.append((t, line))
        elif p in ('ЛАЙНСТЕЙДЖ', 'ЛАЙНИНГ'):
            schedule.append((t, line))
        elif 'МИДГЕЙМ' in p:
            t += 1.8
            schedule.append((t, line))
            speed = 0.9
        elif p in ('ЛЕЙТГЕЙМ',):
            t += 1.8
            schedule.append((t, line))
            speed = 1.3
        elif p.startswith('ПОБЕДИТЕЛЬ') or p.startswith('РАЗГРОМ'):
            t += 1.5
            schedule.append((t, line))
        elif 'ПЕРВАЯ КРОВЬ' in p:
            schedule.append((t, line))
            t += 0.3
        elif 'ИГРА' in p and '·' in p:   # game header in BO series
            t += 1.0
            schedule.append((t, line))
            t += 0.5
        else:
            t += speed
            schedule.append((t, line))

    return schedule


class _GoldBar(Widget):
    """Horizontal token-advantage bar: green=team1, red=team2."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self._adv = 0.0
        self.bind(size=self._draw, pos=self._draw)

    def update(self, tok1, tok2):
        total = max(tok1 + tok2, 1)
        self._adv = (tok1 - tok2) / total
        self._draw()

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.size
        x0, y0 = self.pos
        if w < 4:
            return
        mid = x0 + w / 2
        with self.canvas:
            Color(0.18, 0.18, 0.20, 1)
            Rectangle(pos=(x0, y0), size=(w, h))
            adv = self._adv
            if adv > 0:
                Color(0.20, 0.85, 0.35, 0.9)
                Rectangle(pos=(mid, y0), size=(adv * w / 2, h))
            elif adv < 0:
                Color(0.90, 0.28, 0.22, 0.9)
                Rectangle(pos=(mid + adv * w / 2, y0), size=(-adv * w / 2, h))
            Color(0.75, 0.75, 0.75, 0.6)
            Line(points=[mid, y0, mid, y0 + h], width=1.2)


# ── GroupTableWidget ──────────────────────────────────────────────────────────

class GroupTableWidget(BoxLayout):
    """Live-updating group standings table."""

    _ROW_H = 34

    def __init__(self, group_idx, teams, player_teams, logo_map=None, ratings_map=None, **kw):
        kw.setdefault('orientation', 'vertical')
        kw.setdefault('size_hint_y', None)
        kw.setdefault('spacing', 0)
        super().__init__(**kw)
        self._player_teams = set(player_teams)
        self._standings = {t: 0 for t in teams}
        self._logo_map = logo_map or {}
        self._ratings_map = ratings_map or {}
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

            rating = self._ratings_map.get(team)
            rating_suffix = f'  [{int(rating)}]' if rating is not None else ''
            name_lbl = Label(
                text=('* ' if is_p else '') + team + rating_suffix,
                color=_PLAYER if is_p else _WHITE,
                halign='left', valign='middle', font_size='11sp',
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
            t1, t2, winner = last_match
            loser = t2 if winner == t1 else t1
            self._last_lbl.text = f'  {winner}  победил  {loser}'
            self._last_lbl.color = _GREEN

    def finalize(self):
        sorted_s = sorted(self._standings.items(), key=lambda x: x[1], reverse=True)
        self._rows_grid.clear_widgets()
        for rank, (team, pts) in enumerate(sorted_s):
            if team not in self._team_data:
                continue
            tbox, name_lbl, pts_lbl = self._team_data[team]
            if rank < 4:
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

# ── Map layout constants ──────────────────────────────────────────────────────
# Radiant = team1 (green, bottom-left), Dire = team2 (red, top-right)
# (0,0)=bottom-left, (1,1)=top-right

_LANE_PATH_BOT = [(0.16, 0.09), (0.80, 0.09), (0.91, 0.09), (0.91, 0.20), (0.91, 0.84)]
_LANE_PATH_MID = [(0.16, 0.16), (0.84, 0.84)]
_LANE_PATH_TOP = [(0.09, 0.16), (0.09, 0.80), (0.09, 0.91), (0.20, 0.91), (0.84, 0.91)]

# Tower positions per team: each lane list is [T1_outermost, T2, T3]
_MAP_TWR_T1 = {
    'bot': [(0.65, 0.09), (0.46, 0.09), (0.27, 0.12)],
    'mid': [(0.51, 0.37), (0.40, 0.46), (0.29, 0.55)],
    'top': [(0.09, 0.65), (0.09, 0.46), (0.12, 0.27)],
    'hg':  [(0.19, 0.22), (0.22, 0.15)],
    'throne': (0.10, 0.10),
}
_MAP_TWR_T2 = {
    'bot': [(0.91, 0.35), (0.91, 0.54), (0.88, 0.73)],
    'mid': [(0.49, 0.63), (0.60, 0.54), (0.71, 0.45)],
    'top': [(0.35, 0.91), (0.54, 0.91), (0.73, 0.88)],
    'hg':  [(0.81, 0.78), (0.78, 0.85)],
    'throne': (0.90, 0.90),
}

_MAP_POS = {
    'laning': {
        'team1_carry':           (0.43, 0.09),
        'team1_mid':             (0.34, 0.29),
        'team1_offlane':         (0.09, 0.43),
        'team1_partial_support': (0.13, 0.37),
        'team1_full_support':    (0.38, 0.13),
        'team2_carry':           (0.57, 0.91),
        'team2_mid':             (0.66, 0.71),
        'team2_offlane':         (0.91, 0.57),
        'team2_partial_support': (0.87, 0.63),
        'team2_full_support':    (0.62, 0.87),
    },
    'midgame': {
        'team1_carry':           (0.40, 0.32),
        'team1_mid':             (0.42, 0.46),
        'team1_offlane':         (0.28, 0.52),
        'team1_partial_support': (0.30, 0.44),
        'team1_full_support':    (0.36, 0.38),
        'team2_carry':           (0.60, 0.68),
        'team2_mid':             (0.58, 0.54),
        'team2_offlane':         (0.72, 0.48),
        'team2_partial_support': (0.70, 0.56),
        'team2_full_support':    (0.64, 0.62),
    },
    'lategame': {
        'team1_carry':           (0.46, 0.44),
        'team1_mid':             (0.44, 0.48),
        'team1_offlane':         (0.40, 0.52),
        'team1_partial_support': (0.38, 0.46),
        'team1_full_support':    (0.42, 0.54),
        'team2_carry':           (0.58, 0.56),
        'team2_mid':             (0.56, 0.52),
        'team2_offlane':         (0.62, 0.50),
        'team2_partial_support': (0.64, 0.54),
        'team2_full_support':    (0.54, 0.46),
    },
}

_ROLE_LABELS = {
    'team1_carry': 'C', 'team1_mid': 'M', 'team1_offlane': 'O',
    'team1_partial_support': '4', 'team1_full_support': '5',
    'team2_carry': 'C', 'team2_mid': 'M', 'team2_offlane': 'O',
    'team2_partial_support': '4', 'team2_full_support': '5',
}

_PHASE_LABEL = {'laning': 'ЛАЙНИНГ', 'midgame': 'МИДГЕЙМ', 'lategame': 'ЛЕЙТГЕЙМ'}

_FRESH_TOWERS = {
    'top': [True, True, True], 'mid': [True, True, True], 'bot': [True, True, True],
    'hg': [True, True], 'throne': True,
}


class DotaMapWidget(Widget):

    def __init__(self, team1, team2, **kwargs):
        super().__init__(**kwargs)
        self._team1      = team1
        self._team2      = team2
        self._snap       = {'phase': 'laning', 'minute': 0,
                            'kills_t1': 0, 'kills_t2': 0,
                            'tokens_t1': 0, 'tokens_t2': 0}
        self._roshan     = True
        self._hero_names = {}   # role_key → hero_name (e.g. 'team1_carry' → 'Anti-Mage')
        # Animated positions: current (drawn) and target (from snap)
        from logic.dota.game import _BASE_POS
        self._cur_pos    = dict(_BASE_POS['laning'])
        self._tgt_pos    = dict(_BASE_POS['laning'])
        self._anim_t     = 0.0   # 0=at cur, 1=at tgt
        self._anim_clock = None
        self.bind(size=self._draw, pos=self._draw)

    def set_heroes(self, hero_names):
        """hero_names: {'team1_carry': 'Anti-Mage', ...}"""
        self._hero_names = hero_names or {}

    def apply_snap(self, snap):
        self._snap = snap
        if 'забрала Рошана' in str(snap.get('_event', '')):
            self._roshan = False
        # Update hero names if snap carries them
        hn = snap.get('hero_names', {})
        if hn:
            self._hero_names = hn
        # Trigger animated transition to new positions
        new_pos = snap.get('positions') or {}
        if new_pos:
            self._cur_pos = dict(self._tgt_pos)
            self._tgt_pos = new_pos
            self._anim_t  = 0.0
            if self._anim_clock:
                self._anim_clock.cancel()
            self._anim_clock = Clock.schedule_interval(self._anim_step, 1/30)
        else:
            self._draw()

    def _anim_step(self, dt):
        self._anim_t = min(1.0, self._anim_t + dt * 3.5)  # ~0.28s full transition
        self._draw()
        if self._anim_t >= 1.0:
            self._anim_clock.cancel()
            self._anim_clock = None

    def _interp_pos(self, role):
        """Lerp between cur and tgt position for this role."""
        cx, cy = self._cur_pos.get(role, (0.5, 0.5))
        tx, ty = self._tgt_pos.get(role, (cx, cy))
        t = self._anim_t
        return cx + (tx - cx) * t, cy + (ty - cy) * t

    def _draw(self, *_):
        self.canvas.clear()
        w, h = self.size
        x0, y0 = self.pos
        if w < 10 or h < 10:
            return

        snap  = self._snap
        phase = snap.get('phase', 'laning')
        twr1  = snap.get('towers_state_t1') or _FRESH_TOWERS
        twr2  = snap.get('towers_state_t2') or _FRESH_TOWERS

        def px(nx): return x0 + nx * w
        def py(ny): return y0 + ny * h
        def pts(path): return [c for nx, ny in path for c in (px(nx), py(ny))]

        with self.canvas:
            # ── background ──────────────────────────────────────
            Color(0.04, 0.10, 0.04, 1)
            Rectangle(pos=(x0, y0), size=(w, h))

            # ── forest patches ───────────────────────────────────
            Color(0.07, 0.15, 0.07, 1)
            for fx, fy, fw, fh in [
                (0.20, 0.56, 0.14, 0.18), (0.66, 0.26, 0.12, 0.18),
                (0.38, 0.40, 0.10, 0.12), (0.50, 0.22, 0.08, 0.10),
                (0.26, 0.70, 0.08, 0.10), (0.64, 0.48, 0.07, 0.09),
            ]:
                Rectangle(pos=(px(fx), py(fy)), size=(fw*w, fh*h))

            # ── river (diagonal band) ─────────────────────────────
            Color(0.08, 0.20, 0.45, 0.55)
            Triangle(points=[
                px(0.00), py(0.50),  px(0.50), py(1.00),  px(0.60), py(1.00)])
            Triangle(points=[
                px(0.00), py(0.50),  px(0.00), py(0.40),  px(0.60), py(1.00)])
            Triangle(points=[
                px(0.00), py(0.40),  px(0.40), py(0.00),  px(0.60), py(0.00)])
            Triangle(points=[
                px(0.00), py(0.40),  px(0.60), py(0.00),  px(0.60), py(1.00)])

            # ── lanes ─────────────────────────────────────────────
            lw = max(4, w * 0.042)
            Color(0.36, 0.44, 0.26, 1)
            Line(points=pts(_LANE_PATH_BOT), width=lw, joint='miter', cap='round')
            Line(points=pts(_LANE_PATH_MID), width=lw, cap='round')
            Line(points=pts(_LANE_PATH_TOP), width=lw, joint='miter', cap='round')

            # ── bases ─────────────────────────────────────────────
            bsz = w * 0.15
            Color(0.10, 0.55, 0.18, 1)
            Ellipse(pos=(px(0.01), py(0.01)), size=(bsz, bsz))
            Color(0.55, 0.10, 0.08, 1)
            Ellipse(pos=(px(1.0 - 0.01) - bsz, py(1.0 - 0.01) - bsz), size=(bsz, bsz))
            Color(0, 0, 0, 0.40)
            Line(circle=(px(0.01)+bsz/2, py(0.01)+bsz/2, bsz/2+1.5), width=1.5)
            Line(circle=(px(1.0-0.01)-bsz/2, py(1.0-0.01)-bsz/2, bsz/2+1.5), width=1.5)

            # ── draw towers ───────────────────────────────────────
            tsz_lane = max(6, w * 0.042)
            tsz_hg   = max(7, w * 0.052)
            tsz_thr  = max(9, w * 0.065)

            def _tower(nx, ny, alive, c_alive, sz):
                tx, ty = px(nx) - sz/2, py(ny) - sz/2
                if alive:
                    Color(*c_alive)
                    Rectangle(pos=(tx, ty), size=(sz, sz))
                    Color(0, 0, 0, 0.55)
                    Line(rectangle=(tx, ty, sz, sz), width=1.1)
                else:
                    Color(0.20, 0.20, 0.20, 0.45)
                    Rectangle(pos=(tx, ty), size=(sz, sz))
                    # X mark
                    Color(0.55, 0.18, 0.18, 0.70)
                    Line(points=[tx+2, ty+2, tx+sz-2, ty+sz-2], width=1.0)
                    Line(points=[tx+sz-2, ty+2, tx+2, ty+sz-2], width=1.0)

            def _throne(nx, ny, alive, c_alive):
                cx, cy = px(nx), py(ny)
                r = tsz_thr / 2
                if alive:
                    Color(*c_alive)
                    Ellipse(pos=(cx-r, cy-r), size=(tsz_thr, tsz_thr))
                    Color(1.0, 0.85, 0.0, 0.9)
                    Line(circle=(cx, cy, r+2), width=2.0)
                else:
                    Color(0.25, 0.25, 0.25, 0.45)
                    Ellipse(pos=(cx-r, cy-r), size=(tsz_thr, tsz_thr))

            T1C = (0.22, 0.88, 0.36, 0.92)
            T2C = (0.92, 0.26, 0.20, 0.92)

            for lane in ('bot', 'mid', 'top'):
                st1 = twr1.get(lane, [True, True, True])
                st2 = twr2.get(lane, [True, True, True])
                for i, (nx, ny) in enumerate(_MAP_TWR_T1[lane]):
                    _tower(nx, ny, st1[i] if i < len(st1) else False, T1C, tsz_lane)
                for i, (nx, ny) in enumerate(_MAP_TWR_T2[lane]):
                    _tower(nx, ny, st2[i] if i < len(st2) else False, T2C, tsz_lane)

            hg1 = twr1.get('hg', [True, True])
            hg2 = twr2.get('hg', [True, True])
            for i, (nx, ny) in enumerate(_MAP_TWR_T1['hg']):
                _tower(nx, ny, hg1[i] if i < len(hg1) else False, T1C, tsz_hg)
            for i, (nx, ny) in enumerate(_MAP_TWR_T2['hg']):
                _tower(nx, ny, hg2[i] if i < len(hg2) else False, T2C, tsz_hg)

            _throne(*_MAP_TWR_T1['throne'], twr1.get('throne', True), T1C)
            _throne(*_MAP_TWR_T2['throne'], twr2.get('throne', True), T2C)

            # ── Roshan ───────────────────────────────────────────
            rcx, rcy = px(0.31), py(0.56)
            rsz = max(8, w * 0.055)
            if self._roshan:
                Color(0.88, 0.65, 0.08, 1)
                Ellipse(pos=(rcx-rsz/2, rcy-rsz/2), size=(rsz, rsz))
                Color(0.55, 0.38, 0.04, 0.9)
                Line(circle=(rcx, rcy, rsz/2 + 2), width=2.0)
            else:
                Color(0.30, 0.30, 0.30, 0.45)
                Ellipse(pos=(rcx-rsz/2, rcy-rsz/2), size=(rsz, rsz))

            # ── hero dots with nicks + hero names ────────────────
            _ROLES_T1 = ['team1_carry', 'team1_mid', 'team1_offlane',
                         'team1_partial_support', 'team1_full_support']
            _ROLES_T2 = ['team2_carry', 'team2_mid', 'team2_offlane',
                         'team2_partial_support', 'team2_full_support']
            # Role-size multipliers: carry=largest, supports=smallest
            _DOT_MULT = {
                'team1_carry': 1.20, 'team2_carry': 1.20,
                'team1_mid':   1.12, 'team2_mid':   1.12,
                'team1_offlane': 1.06, 'team2_offlane': 1.06,
                'team1_partial_support': 0.90, 'team2_partial_support': 0.90,
                'team1_full_support': 0.84,    'team2_full_support': 0.84,
            }
            base_dot_r = max(10, w * 0.072)
            players_t1 = snap.get('players_t1', {})
            players_t2 = snap.get('players_t2', {})
            nick_map = {
                'team1_carry':           players_t1.get('carry', 'C'),
                'team1_mid':             players_t1.get('mid',   'M'),
                'team1_offlane':         players_t1.get('off',   'O'),
                'team1_partial_support': players_t1.get('ps',    '4'),
                'team1_full_support':    players_t1.get('fs',    '5'),
                'team2_carry':           players_t2.get('carry', 'C'),
                'team2_mid':             players_t2.get('mid',   'M'),
                'team2_offlane':         players_t2.get('off',   'O'),
                'team2_partial_support': players_t2.get('ps',    '4'),
                'team2_full_support':    players_t2.get('fs',    '5'),
            }

            for role in _ROLES_T1 + _ROLES_T2:
                nx, ny = self._interp_pos(role)
                hx, hy = px(nx), py(ny)
                is_t1  = role.startswith('team1')
                dot_r  = base_dot_r * _DOT_MULT.get(role, 1.0)
                hr     = dot_r / 2

                # Glow ring
                glow_c = (0.18, 0.92, 0.38, 0.30) if is_t1 else (0.96, 0.26, 0.20, 0.30)
                Color(*glow_c)
                Ellipse(pos=(hx - hr - 3, hy - hr - 3), size=(dot_r + 6, dot_r + 6))

                # Main dot
                fill_c = (0.14, 0.82, 0.34, 1.0) if is_t1 else (0.94, 0.22, 0.16, 1.0)
                Color(*fill_c)
                Ellipse(pos=(hx - hr, hy - hr), size=(dot_r, dot_r))

                # Border
                border_c = (0.90, 1.00, 0.90, 1) if is_t1 else (1.00, 0.90, 0.90, 1)
                Color(*border_c)
                Line(circle=(hx, hy, hr + 1.2), width=1.4)

            # ── Text labels (drawn via canvas InstructionGroup) ─
            # Use kivy's CoreLabel for per-dot text
            from kivy.core.text import Label as CoreLabel
            from kivy.graphics.texture import Texture

            for role in _ROLES_T1 + _ROLES_T2:
                nx, ny = self._interp_pos(role)
                hx, hy = px(nx), py(ny)
                is_t1  = role.startswith('team1')
                dot_r  = base_dot_r * _DOT_MULT.get(role, 1.0)
                hr     = dot_r / 2

                nick  = nick_map.get(role, '')
                hname = self._hero_names.get(role, '')

                # Short nick inside dot
                nick_short = nick[:5] if nick else ''
                fs_nick = max(8, int(dot_r * 0.40))
                lbl_nick = CoreLabel(text=nick_short, font_size=fs_nick,
                                     color=(1, 1, 1, 1))
                lbl_nick.refresh()
                tex = lbl_nick.texture
                if tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex,
                               pos=(hx - tex.width/2, hy - tex.height/2),
                               size=(tex.width, tex.height))

                # Hero name above dot
                if hname:
                    hname_short = hname[:9]
                    fs_hero = max(7, int(dot_r * 0.32))
                    lbl_hero = CoreLabel(text=hname_short, font_size=fs_hero,
                                        color=(1.0, 0.92, 0.45, 1) if is_t1
                                              else (1.0, 0.78, 0.78, 1))
                    lbl_hero.refresh()
                    tex2 = lbl_hero.texture
                    if tex2:
                        Color(0, 0, 0, 0.55)
                        Rectangle(pos=(hx - tex2.width/2 - 1, hy + hr + 1),
                                  size=(tex2.width + 2, tex2.height + 1))
                        Color(1, 1, 1, 1)
                        Rectangle(texture=tex2,
                                  pos=(hx - tex2.width/2, hy + hr + 1),
                                  size=(tex2.width, tex2.height))

    def get_kills(self):
        return self._snap.get('kills_t1', 0), self._snap.get('kills_t2', 0)

    def get_minute(self):
        return self._snap.get('minute', 0)


# ── MatchLogPopup – animated match with phase pauses ─────────────────────────

class MatchLogPopup(Popup):

    def __init__(self, team1, team2, winner, log_lines, on_close,
                 t1_logo=None, t2_logo=None, snapshots=None,
                 best_of=1, final_score=(0, 0), match_stats=None,
                 pre_match_team=None, db_name=None,
                 on_result_update=None, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        self._lines            = log_lines
        self._snapshots        = snapshots or []
        self._best_of          = best_of
        self._final_score      = final_score
        self._match_stats      = match_stats or {}
        self._schedule         = _build_log_schedule(log_lines)
        self._sched_idx        = 0
        self._elapsed          = 0.0
        self._on_close         = on_close
        self._on_result_update = on_result_update
        self._interval         = None
        self._winner           = winner
        self._team1            = team1
        self._team2            = team2
        self._t1_logo          = t1_logo
        self._t2_logo          = t2_logo
        self._pre_match_team   = pre_match_team
        self._pre_match_db     = db_name
        self._pre_strats       = {}   # phase → selected key
        self._pre_strat_btns   = {}   # (phase, key) → Button
        self._hero_picks       = {}   # role → hero tuple (player team)
        self._hero_btns        = {}   # (role, hero_name) → Button
        # BO per-map state
        self._map_wins         = {team1: 0, team2: 0}
        self._bo_needed        = best_of // 2 + 1 if best_of > 1 else 1
        self._build()   # builds self._match_content and all live attrs
        if pre_match_team and db_name:
            self.content = self._match_content  # placeholder until draft opens
            Clock.schedule_once(lambda dt: self._launch_prematch_draft(), 0.1)
        else:
            self.content = self._match_content
            Clock.schedule_once(lambda dt: self._start(), 0.15)

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=0, padding=0)

        # ── header: teams + kills + bo score ──────────────────
        header = _BgBox(bg=_BG_PANEL, orientation='horizontal',
                        size_hint_y=None, height=80, padding=(6, 4), spacing=4)

        def _make_team_side(name, logo, align):
            box = BoxLayout(orientation='vertical', spacing=2)
            # logo + name row
            name_row = BoxLayout(orientation='horizontal', spacing=6,
                                 size_hint_y=None, height=42)
            img = _team_logo_widget(logo, size=36) if logo else None
            nl = Label(text=f'[b]{name}[/b]', markup=True,
                       color=_PLAYER, halign=align, valign='middle', font_size='13sp')
            nl.bind(size=nl.setter('text_size'))
            if align == 'right':
                name_row.add_widget(nl)
                if img: name_row.add_widget(img)
            else:
                if img: name_row.add_widget(img)
                name_row.add_widget(nl)
            box.add_widget(name_row)
            # gold advantage label
            gl = Label(text='', color=_DIM, halign=align, valign='middle',
                       font_size='11sp', size_hint_y=None, height=18)
            gl.bind(size=gl.setter('text_size'))
            box.add_widget(gl)
            return box, gl

        t1_box, self._gold_t1_lbl = _make_team_side(
            self._team1, self._t1_logo, 'right')
        t2_box, self._gold_t2_lbl = _make_team_side(
            self._team2, self._t2_logo, 'left')

        # center: kills + bo squares + timer/phase
        center = BoxLayout(orientation='vertical', size_hint_x=None, width=160,
                           spacing=2, padding=(4, 2))
        self._score_lbl = Label(
            text='[b]0  —  0[/b]', markup=True,
            color=_YELLOW, halign='center', valign='middle', font_size='20sp',
            size_hint_y=None, height=30,
        )
        self._score_lbl.bind(size=self._score_lbl.setter('text_size'))

        self._bo_lbl = Label(
            text='', color=_DIM,
            halign='center', valign='middle', font_size='11sp',
            size_hint_y=None, height=16,
        )
        self._bo_lbl.bind(size=self._bo_lbl.setter('text_size'))

        self._timer_lbl = Label(
            text='0:00', color=_DIM, halign='center', valign='middle',
            font_size='11sp', size_hint_y=None, height=14,
        )
        self._timer_lbl.bind(size=self._timer_lbl.setter('text_size'))
        center.add_widget(self._score_lbl)
        center.add_widget(self._bo_lbl)
        center.add_widget(self._timer_lbl)

        header.add_widget(t1_box)
        header.add_widget(center)
        header.add_widget(t2_box)
        root.add_widget(header)
        root.add_widget(_divider())

        # ── body: map (left) + log (right) ────────────────────
        body = BoxLayout(orientation='horizontal', size_hint=(1, 1), spacing=4)

        # map panel
        map_panel = _BgBox(bg=(0.04, 0.08, 0.04, 1), orientation='vertical',
                           size_hint=(0.44, 1), padding=(3, 3), spacing=2)

        self._phase_lbl = Label(
            text='ЛАЙНИНГ', color=_ACCENT,
            halign='center', valign='middle', font_size='12sp',
            size_hint_y=None, height=20, bold=True,
        )
        self._phase_lbl.bind(size=self._phase_lbl.setter('text_size'))
        map_panel.add_widget(self._phase_lbl)

        self._map = DotaMapWidget(self._team1, self._team2, size_hint=(1, 1))
        map_panel.add_widget(self._map)

        legend = BoxLayout(orientation='horizontal', size_hint_y=None, height=20,
                           spacing=4, padding=(4, 0))
        def _leg_lbl(text, color):
            l = Label(text=text, color=color, font_size='10sp',
                      halign='center', valign='middle')
            l.bind(size=l.setter('text_size'))
            return l
        legend.add_widget(_leg_lbl(f'● {self._team1[:12]}', _GREEN))
        legend.add_widget(_leg_lbl(f'● {self._team2[:12]}', _RED))
        map_panel.add_widget(legend)

        body.add_widget(map_panel)

        # log panel
        log_panel = BoxLayout(orientation='vertical', size_hint=(0.58, 1))
        self._log_lbl = Label(
            text='', size_hint_y=None,
            color=(0.88, 0.88, 0.88, 1),
            halign='left', valign='top',
            padding=(12, 8), font_size='14sp',
            markup=True,
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
        self._skip_btn = Button(text='Пропустить',
                               background_color=(0.45, 0.45, 0.15, 1),
                               background_normal='')
        self._skip_btn.bind(on_press=self._skip)
        self._done_btn = Button(text='Закрыть матч  OK',
                                background_color=(0.12, 0.55, 0.20, 1),
                                background_normal='', disabled=True)
        self._done_btn.bind(on_press=self._done)
        btn_bar.add_widget(self._skip_btn)
        btn_bar.add_widget(self._done_btn)
        root.add_widget(btn_bar)

        self._match_content = root

    # ── pre-match strategy selector ───────────────────────────

    def _build_pre_match_content(self):
        import sqlite3 as _sq
        from logic.dota.strategies import EARLY_STRATEGIES, MID_STRATEGIES, LATE_STRATEGIES

        _PHASE_META = [
            ('early', 'Ранняя игра',   EARLY_STRATEGIES, 'strat_early', 'safe_farm'),
            ('mid',   'Средняя игра',  MID_STRATEGIES,   'strat_mid',   'map_control'),
            ('late',  'Поздняя игра',  LATE_STRATEGIES,  'strat_late',  'teamfight'),
        ]

        try:
            row = _sq.connect(self._pre_match_db).execute(
                "SELECT COALESCE(strat_early,'safe_farm'), "
                "COALESCE(strat_mid,'map_control'), "
                "COALESCE(strat_late,'teamfight') FROM teams WHERE name=?",
                (self._pre_match_team,),
            ).fetchone()
            self._pre_strats = {
                'early': row[0] if row else 'safe_farm',
                'mid':   row[1] if row else 'map_control',
                'late':  row[2] if row else 'teamfight',
            }
        except Exception:
            self._pre_strats = {'early': 'safe_farm', 'mid': 'map_control', 'late': 'teamfight'}

        root = BoxLayout(orientation='vertical', spacing=6, padding=10)

        # header
        hdr = _BgBox(bg=_BG_PANEL, orientation='horizontal',
                     size_hint_y=None, height=50, padding=(8, 4))
        hl = Label(
            text=f'[b]Тактика: {self._team1}  vs  {self._team2}  '
                 f'(BO{self._best_of})[/b]',
            markup=True, color=_ACCENT,
            halign='center', valign='middle', font_size='14sp',
        )
        hl.bind(size=hl.setter('text_size'))
        hdr.add_widget(hl)
        root.add_widget(hdr)

        _SEL_BG   = (0.10, 0.45, 0.18, 1)
        _UNSEL_BG = (0.22, 0.22, 0.30, 1)

        for phase, phase_label, strats, _col, _def in _PHASE_META:
            ph_box = _BgBox(bg=_BG_MED, orientation='vertical',
                            size_hint_y=None, height=82, padding=(6, 4), spacing=3)
            ph_lbl = Label(
                text=f'[b]{phase_label}[/b]', markup=True,
                color=_ACCENT, halign='left', valign='middle',
                size_hint_y=None, height=22, font_size='12sp',
            )
            ph_lbl.bind(size=ph_lbl.setter('text_size'))
            ph_box.add_widget(ph_lbl)

            btn_row = BoxLayout(size_hint_y=None, height=46, spacing=4)
            for key, s in strats.items():
                is_sel = key == self._pre_strats.get(phase, _def)
                btn = Button(
                    text=s['name'],
                    background_color=_SEL_BG if is_sel else _UNSEL_BG,
                    background_normal='', font_size='11sp',
                )
                btn.bind(on_press=lambda _, p=phase, k=key: self._pre_select(p, k))
                self._pre_strat_btns[(phase, key)] = btn
                btn_row.add_widget(btn)
            ph_box.add_widget(btn_row)
            root.add_widget(ph_box)

        # ── Hero picks ────────────────────────────────────────────────────────
        hero_hdr = Label(
            text='[b]ВЫБОР ГЕРОЕВ[/b]', markup=True, color=(0.85,0.70,0.20,1),
            size_hint_y=None, height=26, halign='left', valign='middle', font_size='12sp',
        )
        hero_hdr.bind(size=hero_hdr.setter('text_size'))
        root.add_widget(hero_hdr)

        _ROLE_NAMES = {
            'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Offlane',
            'partial_support': 'Sup 4', 'full_support': 'Sup 5',
        }
        _HERO_SEL = (0.55, 0.40, 0.05, 1)
        _HERO_UNS = (0.20, 0.20, 0.28, 1)

        for role in ROLE_ORDER:
            pool = HEROES[role]
            # Default: random pick
            if role not in self._hero_picks:
                import random as _r
                self._hero_picks[role] = _r.choice(pool)

            row = BoxLayout(size_hint_y=None, height=34, spacing=3)
            rl = Label(
                text=f'[b]{_ROLE_NAMES[role]}[/b]', markup=True, color=(0.75,0.85,1,1),
                size_hint_x=None, width=58, halign='center', valign='middle', font_size='10sp',
            )
            rl.bind(size=rl.setter('text_size'))
            row.add_widget(rl)
            for hero in pool[:6]:   # show up to 6 heroes per role
                hname = hero[0]
                is_sel = self._hero_picks.get(role, (None,))[0] == hname
                hbtn = Button(
                    text=hname, font_size='9sp', background_normal='',
                    background_color=_HERO_SEL if is_sel else _HERO_UNS,
                )
                hbtn.bind(on_press=lambda _, r=role, h=hero: self._pick_hero(r, h))
                self._hero_btns[(role, hname)] = hbtn
                row.add_widget(hbtn)
            root.add_widget(row)

        start_btn = Button(
            text='> Начать матч',
            size_hint_y=None, height=50,
            background_color=(0.15, 0.60, 0.22, 1),
            background_normal='', font_size='14sp',
        )
        start_btn.bind(on_press=self._confirm_strategy)
        root.add_widget(start_btn)
        return root

    def _pick_hero(self, role, hero):
        prev = self._hero_picks.get(role)
        if prev:
            k = (role, prev[0])
            if k in self._hero_btns:
                self._hero_btns[k].background_color = (0.20, 0.20, 0.28, 1)
        self._hero_picks[role] = hero
        k2 = (role, hero[0])
        if k2 in self._hero_btns:
            self._hero_btns[k2].background_color = (0.55, 0.40, 0.05, 1)

    def _pre_select(self, phase, key):
        _PHASE_META = {'early': 'safe_farm', 'mid': 'map_control', 'late': 'teamfight'}
        from logic.dota.strategies import EARLY_STRATEGIES, MID_STRATEGIES, LATE_STRATEGIES
        _ALL = {'early': EARLY_STRATEGIES, 'mid': MID_STRATEGIES, 'late': LATE_STRATEGIES}
        prev = self._pre_strats.get(phase, _PHASE_META[phase])
        if (phase, prev) in self._pre_strat_btns:
            self._pre_strat_btns[(phase, prev)].background_color = (0.22, 0.22, 0.30, 1)
        self._pre_strats[phase] = key
        if (phase, key) in self._pre_strat_btns:
            self._pre_strat_btns[(phase, key)].background_color = (0.10, 0.45, 0.18, 1)

    def _launch_prematch_draft(self):
        """Open CM draft popup; on confirm start the map."""
        _open_prematch_popup(
            self._pre_match_db,
            self._team1, self._team2, self._pre_match_team,
            self._best_of,
            on_confirm=self._on_draft_confirmed,
        )

    def _on_draft_confirmed(self, hero_picks, confirmed):
        if hero_picks and confirmed:
            self._hero_picks = hero_picks
        else:
            import random as _r
            from logic.heroes import HEROES, ROLE_ORDER as _RO
            self._hero_picks = {role: _r.choice(HEROES[role]) for role in _RO}
        self._run_simulation()

    def _run_simulation(self):
        """Simulate one map with self._hero_picks and start the match animation."""
        try:
            opp_picks = random_picks(exclude=[h[0] for h in self._hero_picks.values()])
            is_t1 = (self._pre_match_team == self._team1)
            hero_picks = {
                'team1': self._hero_picks if is_t1 else opp_picks,
                'team2': opp_picks         if is_t1 else self._hero_picks,
            }
            map_winner, new_lines, new_snaps, new_stats = replay_match_with_heroes(
                self._team1, self._team2, self._pre_match_db, hero_picks
            )
            pre_w1 = self._map_wins.get(self._team1, 0)
            pre_w2 = self._map_wins.get(self._team2, 0)
            self._map_wins[map_winner] = self._map_wins.get(map_winner, 0) + 1
            w1 = self._map_wins[self._team1]
            w2 = self._map_wins[self._team2]
            self._winner      = self._team1 if w1 > w2 else (
                                self._team2 if w2 > w1 else map_winner)
            self._final_score = (w1, w2)
            self._lines       = new_lines
            self._snapshots   = new_snaps
            self._match_stats = new_stats
            self._schedule    = _build_log_schedule(new_lines)
            self._sched_idx   = 0
            self._elapsed     = 0.0
            for snp in self._snapshots:
                snp['game_score_t1'] = pre_w1
                snp['game_score_t2'] = pre_w2
                snp['best_of']       = self._best_of
            self._build()
        except Exception:
            pass
        self.content = self._match_content
        Clock.schedule_once(lambda dt: self._start(), 0.15)

    def _confirm_strategy(self, _):
        import sqlite3 as _sq
        try:
            conn = _sq.connect(self._pre_match_db)
            conn.execute(
                "UPDATE teams SET strat_early=?, strat_mid=?, strat_late=? WHERE name=?",
                (self._pre_strats.get('early', 'safe_farm'),
                 self._pre_strats.get('mid',   'map_control'),
                 self._pre_strats.get('late',  'teamfight'),
                 self._pre_match_team),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
        self._run_simulation()

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
        kt1  = snap.get('kills_t1', 0)
        kt2  = snap.get('kills_t2', 0)
        tok1 = snap.get('tokens_t1', 0)
        tok2 = snap.get('tokens_t2', 0)
        self._score_lbl.text = f'[b]{kt1}  —  {kt2}[/b]'
        m = snap.get('minute', 0)
        self._timer_lbl.text = f'{m}:00'
        phase = snap.get('phase', 'laning')
        self._phase_lbl.text = _PHASE_LABEL.get(phase, phase.upper())

        # Gold advantage
        gold_diff = tok1 - tok2
        if gold_diff > 0:
            self._gold_t1_lbl.text = f'[color=44dd66]+{gold_diff:,}g[/color]'
            self._gold_t1_lbl.markup = True
            self._gold_t2_lbl.text = ''
        elif gold_diff < 0:
            self._gold_t1_lbl.text = ''
            self._gold_t2_lbl.text = f'[color=44dd66]+{-gold_diff:,}g[/color]'
            self._gold_t2_lbl.markup = True
        else:
            self._gold_t1_lbl.text = ''
            self._gold_t2_lbl.text = ''

        # BO map score squares
        bo = snap.get('best_of', self._best_of)
        gs1 = snap.get('game_score_t1', 0)
        gs2 = snap.get('game_score_t2', 0)
        if bo and bo > 1:
            needed = bo // 2 + 1
            def _squares(wins, total, color_on):
                parts = []
                for i in range(total):
                    if i < wins:
                        parts.append(f'[color={color_on}]■[/color]')
                    else:
                        parts.append('[color=444444]□[/color]')
                return ' '.join(parts)
            self._bo_lbl.text = (
                f'{_squares(gs1, needed, "44dd66")}  '
                f'[color=666666]BO{bo}[/color]  '
                f'{_squares(gs2, needed, "dd4444")}'
            )
            self._bo_lbl.markup = True
        else:
            self._bo_lbl.text = ''

    def _finish(self):
        if self._interval:
            self._interval.cancel()
            self._interval = None
        s1, s2 = self._final_score

        # Per-map BO mode: check if more maps needed
        if self._pre_match_team and self._pre_match_db and self._best_of > 1:
            w1 = self._map_wins.get(self._team1, 0)
            w2 = self._map_wins.get(self._team2, 0)
            maps_played = w1 + w2
            # BO2: always exactly 2 maps; BO3+: stop when someone clinches
            if self._best_of == 2:
                match_over = maps_played >= 2
            else:
                match_over = (w1 >= self._bo_needed or w2 >= self._bo_needed)
            if not match_over:
                # Match not decided — repurpose Skip button to go to next map
                map_num = maps_played + 1
                self._status_lbl.text = (
                    f'Карта {maps_played} завершена  ·  '
                    f'{self._team1} [{w1}:{w2}] {self._team2}'
                )
                self._status_lbl.color = _DIM
                self._hero_picks     = {}
                self._hero_btns      = {}
                self._pre_strat_btns = {}
                self._skip_btn.text             = f'Карта {map_num}: Драфт  →'
                self._skip_btn.background_color = (0.15, 0.55, 0.25, 1)
                self._skip_btn.unbind(on_press=self._skip)
                self._skip_btn.bind(on_press=lambda _: self._next_map_draft())
                return
            # Match decided — set final winner
            if self._best_of == 2:
                import random as _r2
                self._winner = (self._team1 if w1 > w2 else
                                self._team2 if w2 > w1 else
                                _r2.choice([self._team1, self._team2]))
            else:
                self._winner = self._team1 if w1 >= self._bo_needed else self._team2
            self._final_score = (w1, w2)
            s1, s2 = w1, w2
            # Notify parent of final result
            if self._on_result_update:
                self._on_result_update(self._winner, s1, s2)

        elif self._pre_match_team and self._on_result_update:
            # BO1 re-simulation: update bracket with actual result
            self._on_result_update(self._winner, s1, s2)

        bo_str = f'  BO{self._best_of}' if self._best_of > 1 else ''
        self._status_lbl.text = (
            f'Победитель:  {self._winner}  [{s1}:{s2}]{bo_str}'
        )
        self._status_lbl.color = _GREEN
        self._done_btn.disabled = False

        # MVP summary card appended to log
        st = self._match_stats
        if st:
            kt1 = st.get('kills_t1', 0)
            kt2 = st.get('kills_t2', 0)
            dur = st.get('duration', 0)
            mvp = st.get('mvp_nick', '')
            rol = st.get('mvp_role', '')
            sep = '[color=444444]' + '─' * 44 + '[/color]'
            card = (
                f'\n{sep}'
                f'\n  [color=55ccff][b]ИТОГИ МАТЧА[/b][/color]'
                f'\n  Убийства:  [color=44ff88]{kt1}[/color]  —  [color=ff5555]{kt2}[/color]'
                f'   Продолжительность: {dur} мин'
                f'\n  [color=ffd700]MVP: {mvp}  ({rol})[/color]'
            )
            # Tactical analysis
            tac_text = self._build_tactic_analysis()
            if tac_text:
                card += f'\n{sep}\n  [color=aaddff][b]ТАКТИЧЕСКИЙ РАЗБОР[/b][/color]\n{tac_text}'
            card += f'\n{sep}'
            self._log_lbl.text += card
            Clock.schedule_once(lambda dt: setattr(self._scroll, 'scroll_y', 0), 0.05)

    def _next_map_draft(self):
        """Show CM draft for the next map in a BO series."""
        self._hero_picks     = {}
        self._hero_btns      = {}
        self._pre_strat_btns = {}
        self._launch_prematch_draft()

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

    def _build_tactic_analysis(self):
        if not self._pre_match_db:
            return ''
        try:
            import sqlite3 as _sq
            conn = _sq.connect(self._pre_match_db)
            t1 = conn.execute(
                "SELECT COALESCE(tactic,'balanced'), "
                "COALESCE(carry,0)+COALESCE(mid,0)+COALESCE(offlane,0) FROM teams WHERE name=?",
                (self._team1,)
            ).fetchone()
            t2 = conn.execute(
                "SELECT COALESCE(tactic,'balanced'), "
                "COALESCE(carry,0)+COALESCE(mid,0)+COALESCE(offlane,0) FROM teams WHERE name=?",
                (self._team2,)
            ).fetchone()
            conn.close()
            if not t1 or not t2:
                return ''
            tac1, tac2 = t1[0], t2[0]
            _TAC_RU = {
                'aggressive': 'Агрессия (бонус Micro)',
                'farming':    'Фарм (бонус Macro)',
                'teamplay':   'Командная игра (бонус Soft)',
                'balanced':   'Сбалансированная',
            }
            _TAC_COUNTER = {
                'aggressive': 'teamplay',
                'farming':    'aggressive',
                'teamplay':   'farming',
            }
            won1 = self._winner == self._team1
            lines = [
                f'  {self._team1}: {_TAC_RU.get(tac1, tac1)}',
                f'  {self._team2}: {_TAC_RU.get(tac2, tac2)}',
            ]
            counter = _TAC_COUNTER.get(tac2)
            if counter and tac1 == counter:
                lines.append(f'  OK Тактика {self._team1} контрит стиль соперника.')
            elif _TAC_COUNTER.get(tac1) == tac2:
                lines.append(f'  X  Тактика {self._team2} контрит ваш стиль.')
            else:
                lines.append(f'  Нейтральный тактический матч-ап.')
            st = self._match_stats
            if st:
                kt1, kt2 = st.get('kills_t1', 0), st.get('kills_t2', 0)
                if kt1 > kt2 * 1.4:
                    lines.append(f'  Доминация в убийствах ({kt1} vs {kt2}) дала преимущество.')
                elif kt2 > kt1 * 1.4:
                    lines.append(f'  Соперник доминировал ({kt2} vs {kt1}).')
            return '\n'.join(lines)
        except Exception:
            return ''

    def _done(self, _):
        self.dismiss()
        if self._on_close:
            self._on_close()


def _show_press_conference(db_name, player_team, winner, on_done):
    """Post-match press conference popup. 3 responses with minor morale/rep effects."""
    won = (winner.strip() == player_team.strip())
    title_txt = 'ПОБЕДА!' if won else 'ПОРАЖЕНИЕ'
    title_color = (0.20, 0.90, 0.35, 1) if won else (0.90, 0.30, 0.20, 1)

    _RESPONSES = [
        ('Отличная работа команды!',
         {'morale': +2, 'rep': +1},
         (0.15, 0.50, 0.20, 1)),
        ('Соперник был достоин уважения.',
         {'morale': 0, 'rep': 0},
         (0.25, 0.35, 0.50, 1)),
        ('Нам не повезло сегодня.',
         {'morale': -1, 'rep': 0},
         (0.45, 0.30, 0.10, 1)),
    ] if won else [
        ('Мы проанализируем ошибки.',
         {'morale': +1, 'rep': 0},
         (0.15, 0.45, 0.25, 1)),
        ('Соперник сыграл лучше.',
         {'morale': 0, 'rep': +1},
         (0.25, 0.35, 0.50, 1)),
        ('Это была случайность.',
         {'morale': -2, 'rep': -1},
         (0.45, 0.20, 0.15, 1)),
    ]

    content = BoxLayout(orientation='vertical', spacing=8, padding=12)
    title_lbl = Label(
        text=f'[b]{title_txt}[/b]', markup=True, color=title_color,
        size_hint_y=None, height=50, font_size='20sp',
        halign='center', valign='middle',
    )
    title_lbl.bind(size=title_lbl.setter('text_size'))
    content.add_widget(title_lbl)

    prompt = Label(
        text='Что скажете прессе?', color=(0.85, 0.85, 0.85, 1),
        size_hint_y=None, height=32, font_size='13sp',
        halign='center', valign='middle',
    )
    prompt.bind(size=prompt.setter('text_size'))
    content.add_widget(prompt)

    popup = Popup(content=content, title='', size_hint=(0.60, 0.48),
                  auto_dismiss=False)

    def _respond(effects):
        popup.dismiss()
        try:
            import sqlite3 as _sq
            conn = _sq.connect(db_name)
            dm = effects.get('morale', 0)
            dr = effects.get('rep', 0)
            if dm:
                conn.execute(
                    "UPDATE players SET morale=MAX(1,MIN(10,COALESCE(morale,5)+?)) "
                    "WHERE id IN ("
                    "  SELECT carry FROM teams WHERE player='yes' UNION ALL "
                    "  SELECT mid FROM teams WHERE player='yes' UNION ALL "
                    "  SELECT offlane FROM teams WHERE player='yes' UNION ALL "
                    "  SELECT partial_support FROM teams WHERE player='yes' UNION ALL "
                    "  SELECT full_support FROM teams WHERE player='yes'"
                    ")",
                    (dm,)
                )
            if dr:
                conn.execute(
                    "UPDATE characters SET reputation=COALESCE(reputation,0)+?",
                    (dr,)
                )
            conn.commit()
            conn.close()
        except Exception:
            pass
        if on_done:
            on_done()

    for txt, effects, color in _RESPONSES:
        btn = Button(
            text=txt, size_hint_y=None, height=46,
            background_color=color, background_normal='', font_size='12sp',
        )
        btn.bind(on_press=lambda _, e=effects: _respond(e))
        content.add_widget(btn)

    popup.open()


# ── PreMatch popup (strategy + hero picks) ───────────────────────────────────

def _open_prematch_popup(db_name, team1, team2, my_team, best_of, on_confirm):
    """
    Full-screen pre-match: strategy + Captains Mode draft (5 bans + 5 picks each).
    on_confirm(hero_picks, confirmed_play=True) / on_confirm(None, False) if skipped.
    """
    import random as _rnd
    from kivy.clock import Clock as _Clock
    from logic.dota.strategies import EARLY_STRATEGIES, MID_STRATEGIES, LATE_STRATEGIES
    from logic.heroes import HEROES, ROLE_ORDER, ai_draft_picks, ai_draft_bans

    enemy_team = team2 if my_team == team1 else team1

    # ── Strategies ───────────────────────────────────────────────────────────
    try:
        _conn = sqlite3.connect(db_name)
        _row = _conn.execute(
            "SELECT COALESCE(strat_early,'safe_farm'),COALESCE(strat_mid,'map_control'),"
            "COALESCE(strat_late,'teamfight') FROM teams WHERE name=?", (my_team,)
        ).fetchone()
        _conn.close()
        cur_strats = {'early': _row[0], 'mid': _row[1], 'late': _row[2]} if _row else \
                     {'early': 'safe_farm', 'mid': 'map_control', 'late': 'teamfight'}
    except Exception:
        cur_strats = {'early': 'safe_farm', 'mid': 'map_control', 'late': 'teamfight'}

    strat_state = dict(cur_strats)
    strat_btns  = {}

    # ── CM Draft sequence ────────────────────────────────────────────────────
    # 20 steps: 5 player bans, 5 ai bans, 5 player picks (by role), 5 ai picks
    DRAFT_SEQ = [
        ('ban',  'player', None),
        ('ban',  'ai',     None),
        ('ban',  'player', None),
        ('ban',  'ai',     None),
        ('pick', 'player', 'carry'),
        ('pick', 'ai',     None),
        ('pick', 'ai',     None),
        ('pick', 'player', 'mid'),
        ('ban',  'ai',     None),
        ('ban',  'player', None),
        ('ban',  'ai',     None),
        ('ban',  'player', None),
        ('pick', 'player', 'offlane'),
        ('pick', 'ai',     None),
        ('pick', 'player', 'partial_support'),
        ('pick', 'ai',     None),
        ('ban',  'player', None),
        ('ban',  'ai',     None),
        ('pick', 'ai',     None),
        ('pick', 'player', 'full_support'),
    ]
    # AI needs these roles for picks (5 picks total, same as player)
    _AI_PICK_ROLES = [ROLE_ORDER[i] for i in range(5)]
    _ai_pick_idx   = [0]   # mutable counter

    draft = {
        'step':         0,
        'player_bans':  [],
        'ai_bans':      [],
        'player_picks': {},   # role → hero_tuple
        'ai_picks':     [],   # hero_tuples in order
        'done':         False,
    }

    picks = draft['player_picks']   # alias

    # ── Colors ───────────────────────────────────────────────────────────────
    _BG    = (0.07, 0.09, 0.13, 1)
    _SEL   = (0.10, 0.45, 0.18, 1)
    _UNS   = (0.18, 0.20, 0.30, 1)
    _PBANN = (0.55, 0.10, 0.10, 1)   # player ban
    _AIBANN= (0.35, 0.05, 0.40, 1)   # ai ban
    _PPICK = (0.12, 0.50, 0.20, 1)   # player picked
    _AIPICK= (0.30, 0.10, 0.50, 1)   # ai picked
    _AVAIL = (0.16, 0.18, 0.26, 1)   # available
    _ACC   = (0.35, 0.85, 1.00, 1)

    _ROLE_RU = {
        'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Offlane',
        'partial_support': 'Sup4', 'full_support': 'Sup5',
    }

    # ── Root layout ───────────────────────────────────────────────────────────
    root = BoxLayout(orientation='vertical', spacing=4, padding=8)
    with root.canvas.before:
        from kivy.graphics import Color as _C, Rectangle as _R
        _bgc = _C(*_BG); _bgr = _R()
    root.bind(pos=lambda w, _: setattr(_bgr, 'pos', w.pos),
              size=lambda w, _: setattr(_bgr, 'size', w.size))

    def _lbl(text, color=_ACC, fs='13sp', bold=False, height=26, halign='left'):
        t = f'[b]{text}[/b]' if bold else text
        l = Label(text=t, markup=True, color=color, size_hint_y=None, height=height,
                  font_size=fs, halign=halign, valign='middle')
        l.bind(size=l.setter('text_size'))
        return l

    # Header
    root.add_widget(_lbl(
        f'  {my_team}  vs  {enemy_team}  •  BO{best_of}  •  Captains Mode',
        color=(0.25, 1.00, 0.45, 1), fs='16sp', bold=True, height=34, halign='left',
    ))

    body = BoxLayout(orientation='horizontal', spacing=8, size_hint=(1, 1))

    # ══════════════════════════════════════════════════════════════════════════
    # LEFT: strategy
    # ══════════════════════════════════════════════════════════════════════════
    left = BoxLayout(orientation='vertical', size_hint_x=0.28, spacing=3)
    left.add_widget(_lbl('СТРАТЕГИЯ', bold=True, height=24, color=_ACC))

    def _sel_strat(phase, key):
        prev = strat_state.get(phase)
        if prev and (phase, prev) in strat_btns:
            strat_btns[(phase, prev)].background_color = _UNS
        strat_state[phase] = key
        if (phase, key) in strat_btns:
            strat_btns[(phase, key)].background_color = _SEL

    for phase, label, strats, default in [
        ('early', 'Ранняя',   EARLY_STRATEGIES, 'safe_farm'),
        ('mid',   'Средняя',  MID_STRATEGIES,   'map_control'),
        ('late',  'Поздняя',  LATE_STRATEGIES,  'teamfight'),
    ]:
        left.add_widget(_lbl(label, color=(0.70, 0.85, 1.00, 1), height=20))
        ph_row = BoxLayout(size_hint_y=None, height=36, spacing=2)
        for key, s in strats.items():
            btn = Button(text=s['name'], font_size='11sp', background_normal='',
                         background_color=_SEL if key == strat_state.get(phase, default) else _UNS)
            btn.bind(on_press=lambda _, p=phase, k=key: _sel_strat(p, k))
            strat_btns[(phase, key)] = btn
            ph_row.add_widget(btn)
        left.add_widget(ph_row)

    body.add_widget(left)

    # ══════════════════════════════════════════════════════════════════════════
    # RIGHT: CM draft
    # ══════════════════════════════════════════════════════════════════════════
    right = BoxLayout(orientation='vertical', size_hint_x=0.72, spacing=3)

    # ── Draft board: bans row + picks row ─────────────────────────────────────
    board = BoxLayout(orientation='vertical', size_hint_y=None, height=96, spacing=2)

    def _slot_lbl(text='—', color=_AVAIL, w=68):
        b = Button(text=text, font_size='9sp', background_normal='',
                   background_color=color, size_hint_x=None, width=w, disabled=True)
        return b

    # bans row
    bans_row = BoxLayout(size_hint_y=None, height=44, spacing=3)
    bans_row.add_widget(_lbl(f'[b]{my_team[:12]}[/b]', color=(0.30, 1.00, 0.50, 1),
                             fs='11sp', height=44, bold=False))
    p_ban_slots = [_slot_lbl('БАН') for _ in range(5)]
    for s in p_ban_slots:
        bans_row.add_widget(s)
    bans_row.add_widget(_lbl('  БН  ', color=(0.55, 0.55, 0.55, 1), height=44,
                             halign='center', fs='10sp'))
    ai_ban_slots = [_slot_lbl('БАН') for _ in range(5)]
    for s in ai_ban_slots:
        bans_row.add_widget(s)
    bans_row.add_widget(_lbl(f'[b]{enemy_team[:12]}[/b]', color=(1.00, 0.45, 0.45, 1),
                             fs='11sp', height=44, halign='right', bold=False))
    board.add_widget(bans_row)

    # picks row
    picks_row = BoxLayout(size_hint_y=None, height=44, spacing=3)
    picks_row.add_widget(_lbl('ПИКИ', color=(0.30, 1.00, 0.50, 1),
                              fs='11sp', height=44, bold=True))
    p_pick_slots = {role: _slot_lbl(_ROLE_RU[role], color=(0.15, 0.28, 0.18, 1))
                    for role in ROLE_ORDER}
    for role in ROLE_ORDER:
        picks_row.add_widget(p_pick_slots[role])
    picks_row.add_widget(_lbl('  ПК  ', color=(0.55, 0.55, 0.55, 1), height=44,
                              halign='center', fs='10sp'))
    ai_pick_slots = [_slot_lbl(_ROLE_RU[ROLE_ORDER[i]], color=(0.25, 0.10, 0.30, 1))
                     for i in range(5)]
    for s in ai_pick_slots:
        picks_row.add_widget(s)
    picks_row.add_widget(_lbl('ПИКИ', color=(1.00, 0.45, 0.45, 1),
                              fs='11sp', height=44, halign='right', bold=True))
    board.add_widget(picks_row)
    right.add_widget(board)

    # ── Instruction ───────────────────────────────────────────────────────────
    instr_lbl = Label(
        text='', markup=True, color=(1.00, 0.90, 0.30, 1),
        size_hint_y=None, height=28, font_size='13sp',
        halign='center', valign='middle',
    )
    instr_lbl.bind(size=instr_lbl.setter('text_size'))
    right.add_widget(instr_lbl)

    # ── Role filter ───────────────────────────────────────────────────────────
    filter_state = {'role': None}
    filter_row   = BoxLayout(size_hint_y=None, height=32, spacing=3)
    filter_btns  = {}
    _ROLE_CLR = (0.22, 0.50, 0.80, 1)
    _ROLE_SEL = (0.10, 0.70, 0.40, 1)

    def _set_filter(role, btn):
        if filter_state['role'] == role:
            filter_state['role'] = None
            btn.background_color = _ROLE_CLR
        else:
            for r2, b2 in filter_btns.items():
                b2.background_color = _ROLE_CLR
            filter_state['role'] = role
            btn.background_color = _ROLE_SEL
        _rebuild_hero_grid()

    for role in ROLE_ORDER:
        fb = Button(text=_ROLE_RU[role], font_size='11sp', background_normal='',
                    background_color=_ROLE_CLR)
        fb.bind(on_press=lambda _, r=role, b=fb: _set_filter(r, b))
        filter_btns[role] = fb
        filter_row.add_widget(fb)
    right.add_widget(filter_row)

    # ── Hero grid ─────────────────────────────────────────────────────────────
    hero_sv   = ScrollView(size_hint=(1, 1))
    hero_grid = GridLayout(cols=8, size_hint_y=None, spacing=2, padding=(2, 2))
    hero_grid.bind(minimum_height=hero_grid.setter('height'))
    hero_sv.add_widget(hero_grid)
    right.add_widget(hero_sv)

    # All hero buttons keyed by name
    all_hero_btns = {}  # hero_name → Button

    def _hero_color(hname):
        if hname in draft['player_bans']:    return _PBANN
        if hname in draft['ai_bans']:        return _AIBANN
        if any(h[0] == hname for h in draft['player_picks'].values()):  return _PPICK
        if any(h[0] == hname for h in draft['ai_picks']):               return _AIPICK
        return _AVAIL

    def _rebuild_hero_grid():
        hero_grid.clear_widgets()
        role_filter = filter_state['role']
        roles_to_show = [role_filter] if role_filter else ROLE_ORDER
        banned_or_picked = (set(draft['player_bans']) | set(draft['ai_bans']) |
                            {h[0] for h in draft['player_picks'].values()} |
                            {h[0] for h in draft['ai_picks']})
        for role in roles_to_show:
            for hero in HEROES[role]:
                hname = hero[0]
                if hname in all_hero_btns:
                    # reuse existing button
                    btn = all_hero_btns[hname]
                else:
                    btn = Button(text=hname, font_size='9sp', background_normal='',
                                 size_hint_y=None, height=30)
                    btn.bind(on_press=lambda _, h=hero, r=role: _on_hero_click(r, h))
                    all_hero_btns[hname] = btn
                btn.background_color = _hero_color(hname)
                btn.disabled = hname in banned_or_picked
                hero_grid.add_widget(btn)

    _rebuild_hero_grid()

    # ── Draft logic ───────────────────────────────────────────────────────────
    start_btn_ref = [None]   # filled later

    def _step_desc(step_idx):
        if step_idx >= len(DRAFT_SEQ):
            return '[b][color=44ff88]Драфт завершён — нажми Начать матч[/color][/b]'
        action, who, role = DRAFT_SEQ[step_idx]
        bans_done  = sum(1 for s in DRAFT_SEQ[:step_idx] if s[0]=='ban'  and s[1]=='player')
        picks_done = sum(1 for s in DRAFT_SEQ[:step_idx] if s[0]=='pick' and s[1]=='player')
        if who == 'player':
            if action == 'ban':
                return f'[b]ВАШ БАН  {bans_done+1}/5[/b]  — кликни героя для бана'
            else:
                return f'[b]ВАШ ПИК  {picks_done+1}/5  →  {_ROLE_RU[role]}[/b]  — выбери героя'
        else:
            return f'[color=aaaaaa]AI {"банит" if action=="ban" else "пикает"}...[/color]'

    def _advance():
        """Process next step(s). If AI — auto-execute with delay."""
        step = draft['step']
        if step >= len(DRAFT_SEQ):
            draft['done'] = True
            instr_lbl.text = _step_desc(step)
            if start_btn_ref[0]:
                start_btn_ref[0].disabled = False
                start_btn_ref[0].background_color = (0.10, 0.65, 0.22, 1)
            return

        action, who, role = DRAFT_SEQ[step]
        instr_lbl.text = _step_desc(step)

        if who == 'ai':
            _Clock.schedule_once(lambda dt: _do_ai_step(), 0.55)
        # else: wait for player click

    def _do_ai_step():
        step = draft['step']
        if step >= len(DRAFT_SEQ):
            return
        action, who, role = DRAFT_SEQ[step]
        if who != 'ai':
            return

        all_banned_picked = (set(draft['player_bans']) | set(draft['ai_bans']) |
                             {h[0] for h in draft['player_picks'].values()} |
                             {h[0] for h in draft['ai_picks']})

        if action == 'ban':
            available = {h[0] for r in ROLE_ORDER for h in HEROES[r]
                         if h[0] not in all_banned_picked}
            banned = ai_draft_bans(available, 1, draft['player_picks'])
            if banned:
                hname = banned[0]
                draft['ai_bans'].append(hname)
                idx = len(draft['ai_bans']) - 1
                if idx < 5:
                    ai_ban_slots[idx].text = hname[:10]
                    ai_ban_slots[idx].background_color = _AIBANN
        else:
            ai_roles_needed = ROLE_ORDER
            already_ai = {h[0] for h in draft['ai_picks']}
            # Pick for the next needed AI role
            ai_role_idx = _ai_pick_idx[0]
            if ai_role_idx < len(ai_roles_needed):
                needed_role = ai_roles_needed[ai_role_idx]
                result = ai_draft_picks(all_banned_picked, [needed_role])
                if result and needed_role in result:
                    h = result[needed_role]
                    draft['ai_picks'].append(h)
                    _ai_pick_idx[0] += 1
                    idx = len(draft['ai_picks']) - 1
                    if idx < 5:
                        ai_pick_slots[idx].text = h[0][:10]
                        ai_pick_slots[idx].background_color = _AIPICK

        draft['step'] += 1
        _rebuild_hero_grid()
        _advance()

    def _on_hero_click(role, hero):
        if draft['done']:
            return
        step = draft['step']
        if step >= len(DRAFT_SEQ):
            return
        action, who, role_needed = DRAFT_SEQ[step]
        if who != 'player':
            return

        hname = hero[0]
        all_used = (set(draft['player_bans']) | set(draft['ai_bans']) |
                    {h[0] for h in draft['player_picks'].values()} |
                    {h[0] for h in draft['ai_picks']})
        if hname in all_used:
            return

        if action == 'ban':
            draft['player_bans'].append(hname)
            idx = len(draft['player_bans']) - 1
            if idx < 5:
                p_ban_slots[idx].text = hname[:10]
                p_ban_slots[idx].background_color = _PBANN
        else:
            # role_needed comes from DRAFT_SEQ
            actual_role = role_needed
            # Also accept pick if hero is in that role's pool
            draft['player_picks'][actual_role] = hero
            p_pick_slots[actual_role].text = hname[:8]
            p_pick_slots[actual_role].background_color = _PPICK

        draft['step'] += 1
        _rebuild_hero_grid()
        _advance()

    body.add_widget(right)
    root.add_widget(body)

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_row = BoxLayout(size_hint_y=None, height=48, spacing=8)

    popup = Popup(
        title='', content=root,
        size_hint=(1.0, 1.0), auto_dismiss=False,
        background='', background_color=(0, 0, 0, 0),
        separator_color=(0, 0, 0, 0),
    )
    popup.title_bar_height = 0

    def _confirm(_):
        # Fill any unpicked roles with random available heroes
        all_banned = set(draft['player_bans']) | set(draft['ai_bans'])
        for role in ROLE_ORDER:
            if role not in draft['player_picks']:
                pool = [h for h in HEROES[role] if h[0] not in all_banned]
                draft['player_picks'][role] = _rnd.choice(pool) if pool else HEROES[role][0]
        try:
            _c2 = sqlite3.connect(db_name)
            _c2.execute(
                "UPDATE teams SET strat_early=?,strat_mid=?,strat_late=? WHERE name=?",
                (strat_state.get('early', 'safe_farm'),
                 strat_state.get('mid',   'map_control'),
                 strat_state.get('late',  'teamfight'), my_team),
            )
            _c2.commit(); _c2.close()
        except Exception:
            pass
        popup.dismiss()
        on_confirm(dict(draft['player_picks']), True)

    def _skip(_):
        popup.dismiss()
        on_confirm(None, False)

    start_btn = Button(text='Начать матч', font_size='14sp', background_normal='',
                       background_color=(0.25, 0.25, 0.28, 1), disabled=True)
    skip_btn  = Button(text='Авто (пропустить)', font_size='13sp', background_normal='',
                       background_color=(0.35, 0.25, 0.10, 1), size_hint_x=0.4)
    start_btn.bind(on_press=_confirm)
    skip_btn.bind(on_press=_skip)
    start_btn_ref[0] = start_btn
    btn_row.add_widget(start_btn)
    btn_row.add_widget(skip_btn)
    root.add_widget(btn_row)

    popup.open()
    _advance()  # kick off first step


# ── TournamentPopup ───────────────────────────────────────────────────────────

def _bo_from_stage(stage):
    """Infer best-of count from stage name string."""
    if 'BO5' in stage or 'Гранд' in stage: return 5
    if 'BO2' in stage or 'Группа' in stage: return 2
    if 'BO1' in stage: return 1
    return 3


_BRACKET_ORDER = [
    'LB — Раунд 1 (BO1)',
    'UB — Раунд 1 (BO3)',
    'LB — Раунд 2 (BO3)',
    'LB — Раунд 3 (BO3)',
    'UB — Полуфиналы (BO3)',
    'LB — Четвертьфиналы (BO3)',
    'UB — Финал (BO3)',
    'LB — Полуфинал (BO3)',
    'LB — Финал (BO3)',
    'Гранд-финал (BO5)',
    'Малый Т. — Швейцарка Р1 (BO1)',
    'Малый Т. — Швейцарка Р2 (BO1)',
    'Малый Т. — Швейцарка Р3 (BO1)',
    'Малый Т. — Швейцарка Р4 (BO1)',
    'Малый Т. Полуфинал',
    'Малый Т. Финал',
]


class TournamentPopup(Popup):

    _BTN_LABELS = {}  # kept for compatibility

    def __init__(self, db_name, on_finish=None, **kwargs):
        super().__init__(**kwargs)
        self.db_name       = db_name
        self.size_hint     = (0.96, 0.96)
        self.auto_dismiss  = False
        self._on_finish    = on_finish
        self._season_over  = False
        self._season_year  = None
        self._player_teams = set()
        self._seq          = []
        self._seq_idx      = 0
        self._feed_grid    = None
        self._feed_sv      = None
        self._clock_ev     = None
        self._close_btn    = None

        conn = sqlite3.connect(db_name)
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, name FROM tournaments WHERE place1 IS NULL ORDER BY start_date LIMIT 1"
        )
        row = cur.fetchone()
        cur.execute("SELECT name, logo FROM teams")
        self._logo_map = {r[0].strip(): r[1] for r in cur.fetchall()}
        conn.close()

        if not row:
            self.title   = 'Нет турниров'
            self.content = Label(text='Все турниры сезона сыграны.')
            return

        self.tournament_id, tournament_name = row
        self.title = tournament_name

        events, _pl, _ge = generate_tournament_events(db_name, self.tournament_id)
        self._build_state(events)

        # Minor without player: silent save + inbox
        if self._minor_result_ev and not self._player_in_minor:
            self._persist_minor_results(self._minor_result_ev)
            champ = self._minor_result_ev.get('champion', '?')
            _add_message(db_name,
                         f"Малый турнир завершён. Чемпион: {champ}.", 'Новости')
        # If player is in minor, persist main tournament silently
        if self._player_in_minor and not self._player_qualified and self._tournament_ev:
            pass  # main tournament was already persisted above; minor persisted after feed

        self._build_ui(tournament_name)

    # ── state builder ─────────────────────────────────────────

    def _build_state(self, events):
        self._qualifier_ev      = None
        self._qualifier_header  = None
        self._draw_ev           = None
        self._groups_final      = []
        self._bracket_rounds    = {}
        self._player_matches    = []
        self._tournament_ev     = None
        self._minor_result_ev   = None
        self._player_in_minor   = False
        self._player_qualified  = True   # default: in main tournament

        player_teams = set()
        for ev in events:
            t = ev['type']
            if t == 'qualifier_summary':
                self._qualifier_ev = ev
                self._player_qualified = ev.get('player_qualified', True)
            elif t == 'qualifier_header':
                self._qualifier_header = ev
                player_teams = set(ev.get('player_teams', []))
            elif t == 'qualifier_done':
                self._player_qualified = ev.get('player_qualified', True)
            elif t == 'draw':
                self._draw_ev = ev
                if not self._qualifier_header:
                    player_teams = set(ev.get('player_teams', []))
            elif t == 'match_result':
                self._bracket_rounds.setdefault(ev['stage'], []).append(ev)
            elif t == 'groups_complete':
                self._groups_final = ev.get('group_standings', [])
            elif t == 'match_lineup':
                self._player_matches.append(ev)
            elif t == 'tournament_results':
                self._tournament_ev = ev
            elif t == 'minor_results':
                self._minor_result_ev = ev
            elif t == 'minor_header':
                self._player_in_minor = bool(
                    set(ev.get('teams', [])) & player_teams
                )
        self._player_teams = player_teams

    # ── UI builder ────────────────────────────────────────────

    def _build_ui(self, name):
        root = BoxLayout(orientation='vertical', spacing=4, padding=4)

        hdr = _BgBox(bg=_BG_PANEL, size_hint_y=None, height=42)
        hl  = Label(text=f'[b]{name}[/b]', markup=True, color=_ACCENT,
                    halign='center', valign='middle', font_size='15sp')
        hl.bind(size=hl.setter('text_size'))
        hdr.add_widget(hl)
        root.add_widget(hdr)

        body = BoxLayout(orientation='horizontal', size_hint=(1, 1), spacing=6)
        body.add_widget(self._make_left_panel())
        body.add_widget(self._make_right_panel())
        root.add_widget(body)

        close = Button(text='Закрыть', size_hint_y=None, height=48,
                       background_color=(0.65, 0.18, 0.18, 1), background_normal='')
        close.disabled = bool(self._player_matches)
        self._close_btn = close
        close.bind(on_press=self.dismiss)
        root.add_widget(close)

        self.content = root
        self.bind(on_dismiss=self._on_dismissed)
        Clock.schedule_once(self._start_feed, 0.4)

    # ── left: qualifier + groups + bracket ────────────────────

    def _make_left_panel(self):
        sv   = ScrollView(size_hint=(0.58, 1))
        grid = _auto_grid()
        pt   = self._player_teams

        self._left_grid           = grid
        self._pending_groups      = None   # set below if groups exist

        # Groups — built now but added to grid lazily (after qualifiers)
        self._group_tables = {}
        self._group_played = {}
        self._group_total  = {}
        if self._draw_ev:
            _groups = self._draw_ev.get('groups', [])
            _max_teams = max((len(g) for g in _groups), default=8)
            _row_h = 28 + 22 + (_max_teams * GroupTableWidget._ROW_H) + 26 + 6
            groups_row = BoxLayout(orientation='horizontal',
                                   size_hint_y=None, height=_row_h,
                                   spacing=6, padding=(2, 2))
            _ratings_map = {}
            try:
                import sqlite3 as _sq3
                _rc = _sq3.connect(self.db_name)
                for _rn, _rv in _rc.execute(
                    "SELECT name, COALESCE(rating,0) FROM teams"
                ).fetchall():
                    _ratings_map[_rn.strip()] = int(_rv)
                _rc.close()
            except Exception:
                pass
            for gi, group in enumerate(_groups):
                gtw = GroupTableWidget(gi, group, pt, logo_map=self._logo_map,
                                       ratings_map=_ratings_map)
                stage_key = f'Группа {gi + 1} (BO2)'
                self._group_tables[stage_key] = gtw
                self._group_played[stage_key] = 0
                self._group_total[stage_key]  = len(self._bracket_rounds.get(stage_key, []))
                groups_row.add_widget(gtw)

            # If no qualifiers, show groups immediately; else defer
            has_qualifiers = bool(self._qualifier_ev or self._qualifier_header)
            if has_qualifiers:
                self._pending_groups = [
                    _section_title('ГРУППОВОЙ ЭТАП', color=_ACCENT),
                    groups_row,
                ]
            else:
                grid.add_widget(_section_title('ГРУППОВОЙ ЭТАП', color=_ACCENT))
                grid.add_widget(groups_row)

        sv.add_widget(grid)
        return sv

    # ── right: live match feed ────────────────────────────────

    def _make_right_panel(self):
        outer = BoxLayout(orientation='vertical', size_hint=(0.42, 1), spacing=4)

        hl = Label(text='[b]Матчи турнира[/b]', markup=True,
                   size_hint_y=None, height=34,
                   color=_PLAYER, halign='center', valign='middle', font_size='14sp')
        hl.bind(size=hl.setter('text_size'))
        outer.add_widget(hl)

        sv = ScrollView(size_hint=(1, 1))
        self._feed_sv = sv
        grid = _auto_grid()
        self._feed_grid = grid
        sv.add_widget(grid)
        outer.add_widget(sv)
        return outer

    # ── feed sequence ─────────────────────────────────────────

    def _build_sequence(self):
        lineup_map = {}
        for pm in self._player_matches:
            lineup_map[(pm['stage'], pm['team1'], pm['team2'])] = pm

        seq = []

        # Qualifier stages first (always show to player)
        qual_stages = [s for s in self._bracket_rounds if 'Квалификац' in s]
        for stage in qual_stages:
            matches = self._bracket_rounds.get(stage, [])
            if not matches:
                continue
            seq.append(('header', stage, None, None))
            for m in matches:
                is_p   = m.get('is_player_match', False)
                lineup = lineup_map.get((stage, m['team1'], m['team2'])) if is_p else None
                seq.append(('player' if is_p else 'auto', stage, m, lineup))

        # If player not qualified → show minor matches; skip main tournament stages
        if not self._player_qualified and self._player_in_minor:
            minor_stages = [s for s in self._bracket_rounds if 'Малый' in s]
            for stage in minor_stages:
                matches = self._bracket_rounds.get(stage, [])
                if not matches:
                    continue
                seq.append(('header', stage, None, None))
                for m in matches:
                    is_p   = m.get('is_player_match', False)
                    lineup = lineup_map.get((stage, m['team1'], m['team2'])) if is_p else None
                    seq.append(('player' if is_p else 'auto', stage, m, lineup))
            return seq

        # Normal flow: groups + playoffs (filter out minor)
        group_stages  = sorted(s for s in self._bracket_rounds if 'Группа' in s)
        playoff_order = [s for s in _BRACKET_ORDER if s in self._bracket_rounds]
        rest = [s for s in self._bracket_rounds
                if 'Группа' not in s and s not in playoff_order
                and 'Квалификац' not in s]

        for stage in group_stages + playoff_order + rest:
            if 'Малый' in stage:
                continue
            matches = self._bracket_rounds.get(stage, [])
            if not matches:
                continue
            seq.append(('header', stage, None, None))
            for m in matches:
                is_p   = m.get('is_player_match', False)
                lineup = lineup_map.get((stage, m['team1'], m['team2'])) if is_p else None
                seq.append(('player' if is_p else 'auto', stage, m, lineup))

        return seq

    def _start_feed(self, *_):
        self._seq     = self._build_sequence()
        self._seq_idx = 0
        self._next_step()

    def _step_delay(self, stage):
        if 'Группа' in stage: return 0.35
        if 'Малый'  in stage: return 1.2
        return 2.0

    def _next_step(self, *_):
        self._clock_ev = None
        while self._seq_idx < len(self._seq):
            kind, stage, ev, lineup_ev = self._seq[self._seq_idx]

            if kind == 'header':
                self._feed_add_header(stage)
                self._seq_idx += 1
                continue

            if kind == 'auto':
                self._feed_add_result(ev)
                self._seq_idx += 1
                self._scroll_feed()
                self._clock_ev = Clock.schedule_once(
                    self._next_step, self._step_delay(stage))
                return

            if kind == 'player':
                self._feed_add_player_card(ev, lineup_ev)
                self._scroll_feed()
                return   # paused — buttons will call _next_step when done

        # Sequence finished
        if self._tournament_ev:
            self._persist_results(self._tournament_ev)
        if self._player_in_minor and self._minor_result_ev:
            self._persist_minor_results(self._minor_result_ev)
        if self._close_btn:
            self._close_btn.disabled = False

    # ── feed widget helpers ───────────────────────────────────

    @staticmethod
    def _fl(text, color=_WHITE, fs='11sp', bold=False, halign='left'):
        t = f'[b]{text}[/b]' if bold else text
        lbl = Label(text=t, markup=True, color=color,
                    size_hint_y=None, height=22,
                    halign=halign, valign='middle', font_size=fs)
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _feed_add_header(self, stage):
        is_minor = 'Малый' in stage
        is_group = 'Группа' in stage
        color = _YELLOW if is_minor else (_DIM if is_group else _ACCENT)
        h = _BgBox(bg=_BG_HEAD, size_hint_y=None, height=24)
        h.add_widget(self._fl(f'  {stage}', color=color,
                               fs='11sp', bold=True, halign='left'))
        self._feed_grid.add_widget(h)

        # Reveal group tables in left panel on first group stage header
        if is_group and getattr(self, '_pending_groups', None):
            for w in self._pending_groups:
                self._left_grid.add_widget(w)
            self._pending_groups = None

    def _feed_add_result(self, ev):
        t1, t2 = ev['team1'], ev['team2']
        winner = ev['winner']
        s1, s2 = ev.get('score_t1', 0), ev.get('score_t2', 0)

        def _tl(name, won):
            isp = name.strip() in self._player_teams
            c = _PLAYER if isp else (_WHITE if won else _DIM)
            lbl = Label(text=name, color=c, halign='left', valign='middle',
                        font_size='11sp')
            lbl.bind(size=lbl.setter('text_size'))
            return lbl

        row = _BgBox(bg=_BG_DARK, orientation='horizontal',
                     size_hint_y=None, height=26, padding=(4, 0), spacing=4)
        row.add_widget(_tl(t1, winner == t1))
        sc = Label(text=f'{s1}:{s2}', color=_YELLOW,
                   size_hint_x=None, width=34,
                   halign='center', valign='middle', font_size='11sp')
        sc.bind(size=sc.setter('text_size'))
        row.add_widget(sc)
        row.add_widget(_tl(t2, winner == t2))
        self._feed_grid.add_widget(row)

        stage = ev.get('stage', '')
        if 'Группа' in stage:
            gtw = self._group_tables.get(stage)
            if gtw:
                self._group_played[stage] = self._group_played.get(stage, 0) + 1
                gtw.update_standings(
                    ev.get('standings', {}),
                    last_match=(t1, t2, winner),
                )
                if self._group_played[stage] >= self._group_total.get(stage, 999):
                    gtw.finalize()

    def _feed_add_player_card(self, ev, lineup_ev):
        t1, t2 = ev['team1'], ev['team2']
        is_t1_p = t1.strip() in self._player_teams
        my_team = t1 if is_t1_p else t2
        opp     = t2 if is_t1_p else t1
        log_ev  = lineup_ev or ev
        bo      = log_ev.get('best_of') or _bo_from_stage(ev.get('stage', ''))

        # Show match card immediately — draft happens per-map inside MatchLogPopup
        card = _BgBox(bg=_BG_HEAD, orientation='vertical',
                      size_hint_y=None, height=96,
                      padding=(8, 6), spacing=4)
        card.add_widget(self._fl(
            f'{my_team}  vs  {opp}', _PLAYER, '14sp', bold=True, halign='center'))
        card.add_widget(self._fl(
            f'BO{bo}  —  выберите тактику и героев', _DIM, '12sp', halign='center'))

        btn_row = BoxLayout(size_hint_y=None, height=42, spacing=6)

        def _watch(_):
            self._feed_grid.remove_widget(card)
            pre_winner = ev.get('winner', t1)

            def _on_done():
                actual_winner = ev.get('winner', t1)
                if actual_winner != pre_winner:
                    self._apply_result_swap(self._seq_idx + 1, t1, t2)
                self._feed_add_result(ev)
                self._seq_idx += 1
                self._scroll_feed()
                Clock.schedule_once(self._next_step, 0.5)

            self._open_match_log(
                log_ev, on_close=_on_done,
                pre_match_team=my_team,
                on_result_update=lambda w, s1, s2: ev.update({
                    'winner': w, 'score_t1': s1, 'score_t2': s2,
                    'loser': (t2 if w == t1 else t1),
                }),
            )

        def _skip(_):
            self._feed_grid.remove_widget(card)
            self._feed_add_result(ev)
            self._seq_idx += 1
            self._scroll_feed()
            Clock.schedule_once(self._next_step, 0.5)

        watch_btn = Button(
            text='Начать матч',
            background_color=(0.18, 0.55, 0.20, 1),
            background_normal='', font_size='13sp',
        )
        skip_btn = Button(
            text='Пропустить',
            background_color=(0.35, 0.25, 0.10, 1),
            background_normal='', font_size='13sp',
        )
        watch_btn.bind(on_press=_watch)
        skip_btn.bind(on_press=_skip)
        btn_row.add_widget(watch_btn)
        btn_row.add_widget(skip_btn)
        card.add_widget(btn_row)
        self._feed_grid.add_widget(card)
        self._scroll_feed()

    def _scroll_feed(self):
        if self._feed_sv:
            Clock.schedule_once(
                lambda dt: setattr(self._feed_sv, 'scroll_y', 0), 0.05)

    def _apply_result_swap(self, from_idx, team_a, team_b):
        """Propagate a different-than-pre-calc result through subsequent bracket events.
        Swaps all occurrences of team_a and team_b in events at from_idx onwards.
        """
        def _sw(name):
            if name == team_a: return team_b
            if name == team_b: return team_a
            return name

        for i in range(from_idx, len(self._seq)):
            kind, stage, ev, lineup_ev = self._seq[i]
            if ev is None:
                continue
            ev['team1']  = _sw(ev.get('team1', ''))
            ev['team2']  = _sw(ev.get('team2', ''))
            ev['winner'] = _sw(ev.get('winner', ''))
            ev['loser']  = _sw(ev.get('loser', ''))
            if 'standings' in ev:
                ev['standings'] = {_sw(k): v for k, v in ev['standings'].items()}
            is_p = (ev['team1'] in self._player_teams or
                    ev['team2'] in self._player_teams)
            ev['is_player_match'] = is_p
            if lineup_ev:
                lineup_ev['team1']  = _sw(lineup_ev.get('team1', ''))
                lineup_ev['team2']  = _sw(lineup_ev.get('team2', ''))
                lineup_ev['winner'] = _sw(lineup_ev.get('winner', ''))
            new_kind = kind if kind == 'header' else ('player' if is_p else 'auto')
            self._seq[i] = (new_kind, stage, ev, lineup_ev)

        if self._tournament_ev:
            pl = self._tournament_ev.get('placements', {})
            self._tournament_ev['placements'] = {_sw(t): p for t, p in pl.items()}
            self._tournament_ev['champion'] = _sw(
                self._tournament_ev.get('champion', ''))
            ge = self._tournament_ev.get('group_eliminated', [])
            self._tournament_ev['group_eliminated'] = [(_sw(t), p) for t, p in ge]

    def _open_match_log(self, ev, on_close=None, pre_match_team=None,
                        on_result_update=None):
        """Open MatchLogPopup without dismissing TournamentPopup."""
        t1, t2 = ev['team1'], ev['team2']
        popup = MatchLogPopup(
            team1=t1, team2=t2,
            winner=ev.get('winner', t1),
            log_lines=ev.get('match_log', []),
            snapshots=ev.get('match_snaps', []),
            on_close=on_close or (lambda: None),
            t1_logo=self._logo_map.get(t1),
            t2_logo=self._logo_map.get(t2),
            best_of=ev.get('best_of') or _bo_from_stage(ev.get('stage', '')),
            final_score=(ev.get('score_t1', 0), ev.get('score_t2', 0)),
            match_stats=ev.get('match_stats', {}),
            pre_match_team=pre_match_team,
            db_name=self.db_name if pre_match_team else None,
            on_result_update=on_result_update,
        )
        popup.size_hint = (1.0, 1.0)
        popup.background = ''
        popup.background_color = (0, 0, 0, 0)
        popup.separator_color  = (0, 0, 0, 0)
        popup.title_bar_height = 0
        popup.open()

    def _watch(self, ev):
        self._open_match_log(ev)

    # ── on dismiss ────────────────────────────────────────────

    def _on_dismissed(self, _):
        if self._clock_ev:
            self._clock_ev.cancel()
            self._clock_ev = None
        if self._tournament_ev:
            self._persist_results(self._tournament_ev)
        if getattr(self, '_season_over', False):
            from ingame_interface.season_end import SeasonEndPopup
            SeasonEndPopup(
                self.db_name, self._season_year,
                on_confirmed=self._on_finish,
            ).open()
        elif self._on_finish:
            self._on_finish()

    # ── persistence ───────────────────────────────────────────


    def _persist_minor_results(self, event):
        places = event.get('placements', {})
        _MINOR_PRIZES = {1: 80_000, 2: 40_000, 3: 20_000, 4: 10_000}
        _MINOR_RATING = {1: 150, 2: 75, 3: 35, 4: 20}

        conn = sqlite3.connect(self.db_name)
        cur  = conn.cursor()
        my_team_name = (cur.execute("SELECT name FROM teams WHERE player='yes'").fetchone() or (None,))[0]
        if my_team_name:
            my_team_name = my_team_name.strip()
        player_prize = 0
        for team, place in places.items():
            prize  = _MINOR_PRIZES.get(place, 0)
            rating = _MINOR_RATING.get(place, 0)
            if prize:
                cur.execute("UPDATE teams SET budget=budget+? WHERE name=?", (prize, team))
                if my_team_name and team.strip() == my_team_name:
                    player_prize = prize
            if rating:
                cur.execute(
                    "UPDATE teams SET rating=COALESCE(rating,0)+? WHERE name=?",
                    (rating, team),
                )

        # Record history for all players in minor
        gd = cur.execute("SELECT date FROM save WHERE id=1").fetchone()
        season = int(gd[0][:4]) if gd else 0
        id_map = {r[0].strip(): r[1] for r in cur.execute("SELECT name, id FROM teams")}
        for team, place in places.items():
            tid = id_map.get(team)
            if not tid:
                continue
            pids_row = cur.execute(
                "SELECT carry, mid, offlane, partial_support, full_support FROM teams WHERE id=?",
                (tid,)
            ).fetchone()
            if not pids_row:
                continue
            for pid in [p for p in pids_row if p]:
                nick = (cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
                        .fetchone() or ('',))[0]
                try:
                    cur.execute(
                        "INSERT INTO player_history "
                        "(player_id, player_nick, season, tournament_name, place, team_name) "
                        "VALUES (?,?,?,?,?,?)",
                        (pid, nick, season, 'Малый турнир', place, team),
                    )
                except Exception:
                    pass

        conn.commit()
        conn.close()

        # earn_prize goal for player team
        if player_prize:
            try:
                from logic.goals import update_goal, year_from_date
                update_goal(self.db_name, year_from_date(gd[0] if gd else '2024'),
                            'earn_prize', player_prize)
            except Exception:
                pass

        # reputation for player if in minor
        player_t = event.get('player_teams', [])
        for pt in player_t:
            place = places.get(pt)
            if place:
                from ingame_interface.tournaments import _update_reputation
                rep = (3 if place == 1 else 2 if place <= 3 else 0)
                if rep:
                    _update_reputation(self.db_name, rep)

    def _render_results(self, ev):
        champion   = ev['champion']
        placements = ev['placements']
        eliminated = ev['group_eliminated']

        block = _auto_grid()
        block.add_widget(_section_title(
            f'ИТОГИ ТУРНИРА  —  ЧЕМПИОН: {champion}', color=_GOLD))

        medals = {1: '[1]', 2: '[2]', 3: '[3]', 4: ' 4.'}
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

    def _record_player_history(self, event):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT start_date FROM tournaments WHERE id=?",
                  (event.get('tournament_id', 0),))
        row = c.fetchone()
        season = int(row[0][:4]) if row else 0
        t_name = self.title

        all_places = dict(event.get('placements', {}))
        for i, (team, _) in enumerate(
            sorted(event.get('group_eliminated', []), key=lambda x: x[1], reverse=True)
        ):
            all_places[team] = 9 + i

        for team, place in all_places.items():
            c.execute("SELECT id, carry, mid, offlane, partial_support, full_support "
                      "FROM teams WHERE name=?", (team,))
            tr = c.fetchone()
            if not tr:
                continue
            pids = [p for p in tr[1:] if p]
            for pid in pids:
                nick = (c.execute("SELECT nickname FROM players WHERE id=?", (pid,))
                        .fetchone() or ('',))[0]
                c.execute(
                    "INSERT INTO player_history "
                    "(player_id, player_nick, season, tournament_name, place, team_name) "
                    "VALUES (?,?,?,?,?,?)",
                    (pid, nick, season, t_name, place, team),
                )
        conn.commit()
        conn.close()

    def _release_temp_players(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute("SELECT id FROM players WHERE is_temp=1 AND team_id!=0")
        for (pid,) in c.fetchall():
            for col in ('carry','mid','offlane','partial_support','full_support'):
                c.execute(f"UPDATE teams SET {col}=NULL WHERE {col}=?", (pid,))
            c.execute("UPDATE players SET team_id=0, is_temp=0, wage=0 WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    def _persist_results(self, event):
        # Guard: skip if results already saved (safe reopen)
        _tid = event.get('tournament_id')
        if _tid:
            _c = sqlite3.connect(self.db_name)
            _row = _c.execute("SELECT place1 FROM tournaments WHERE id=?", (_tid,)).fetchone()
            _c.close()
            if _row and _row[0] is not None:
                return
        self._release_temp_players()
        self._record_player_history(event)
        save_tournament_results(
            event['tournament_id'],
            event['placements'],
            event['group_eliminated'],
            self.db_name,
        )
        update_morale_after_tournament(
            self.db_name, event['placements'], event['group_eliminated'],
        )
        # Achievement check after tournament
        try:
            from logic.achievements import check_achievements
            _ctx = {
                'youth_win': event.get('youth_win', False),
            }
            _new = check_achievements(self.db_name, _game_date or '', _ctx)
            for _aname, _abonus in _new:
                _mc = sqlite3.connect(self.db_name)
                _mc.execute(
                    "INSERT INTO messages (text, date, author) VALUES (?,?,?)",
                    (f'🏆 Достижение разблокировано: «{_aname}»! Бонус: {_abonus}',
                     _game_date or '', 'Достижения')
                )
                _mc.commit(); _mc.close()
        except Exception:
            pass
        try:
            _gd = sqlite3.connect(self.db_name).execute(
                "SELECT date FROM save WHERE id=1"
            ).fetchone()
            _season = int(_gd[0][:4]) if _gd else 2024
            _game_date = _gd[0] if _gd else None
        except Exception:
            _season = 2024
            _game_date = None
        apply_training_from_games(
            self.db_name,
            event.get('games_played', {}),
            season=_season,
            placements=event.get('placements', {}),
            champion_name=event.get('champion'),
        )
        # Fatigue increment for player's team (Feature 3)
        try:
            from logic.tournaments.runner import increment_player_fatigue
            from logic.dota.match_data import get_teams_with_player_yes
            _ptms = get_teams_with_player_yes(self.db_name)
            _gp = event.get('games_played', {})
            for _pt in _ptms:
                _n = _gp.get(_pt, 0)
                if _n > 0:
                    increment_player_fatigue(self.db_name, _pt, amount=_n * 2)
        except Exception:
            pass
        update_form_after_tournament(
            self.db_name,
            event.get('placements', {}),
            event.get('group_eliminated', []),
        )
        if _is_transfer_window(_game_date or ''):
            ai_transfers(
                self.db_name,
                placements=event['placements'],
                group_eliminated=event['group_eliminated'],
            )

        # Season-end check
        self._season_over, self._season_year = self._check_season_over(
            event['tournament_id']
        )

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
                'Новости',
            )
            # Reputation update
            rep = (5 if place == 1 else
                   3 if place <= 3 else
                   1 if place <= 8 else -1)
            _update_reputation(self.db_name, rep)

            # Goals update
            from logic.goals import update_goal, year_from_date
            try:
                conn_g = sqlite3.connect(self.db_name)
                gd = conn_g.execute("SELECT date FROM save WHERE id=1").fetchone()
                conn_g.close()
                year = year_from_date(gd[0] if gd else '2024')
                update_goal(self.db_name, year, 'best_finish', place)
                if place == 1:
                    update_goal(self.db_name, year, 'win_tournament', 1)
                # estimate prize from tournament prizepool for place
                try:
                    from logic.tournaments.prizepool import get_prizepool_worldcup_system
                    prizes = get_prizepool_worldcup_system(
                        event.get('tournament_id', 0), self.db_name
                    )
                    prize = prizes.get(place, 0)
                    if prize:
                        update_goal(self.db_name, year, 'earn_prize', prize)
                except Exception:
                    pass
            except Exception:
                pass

        # Save player match logs to match_history
        if getattr(self, '_player_matches', None):
            import json as _json
            try:
                _conn = sqlite3.connect(self.db_name)
                _conn.execute("""
                    CREATE TABLE IF NOT EXISTS match_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        played_date TEXT, tournament TEXT, stage TEXT,
                        team1 TEXT, team2 TEXT, winner TEXT,
                        score_t1 INTEGER DEFAULT 0, score_t2 INTEGER DEFAULT 0,
                        best_of INTEGER DEFAULT 1, log_json TEXT
                    )
                """)
                for _ev in self._player_matches:
                    _conn.execute("""
                        INSERT INTO match_history
                        (played_date, tournament, stage, team1, team2, winner,
                         score_t1, score_t2, best_of, log_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        _game_date or '',
                        self.title,
                        _ev.get('stage', ''),
                        _ev.get('team1', ''), _ev.get('team2', ''),
                        _ev.get('winner', ''),
                        _ev.get('score_t1', 0), _ev.get('score_t2', 0),
                        _ev.get('best_of', 1),
                        _json.dumps(_ev.get('match_log', [])),
                    ))
                _conn.commit()
                _conn.close()
            except Exception:
                pass

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
            mark = ' *' if is_p else '  '
            rrow.add_widget(_lbl(f'  {rank+1:2}.{mark}  {name}',
                                 color=color, height=32))
            rrow.add_widget(_lbl(f'{int(rating):>5} pts  ',
                                 color=color, height=32, halign='right'))
            grid.add_widget(rrow)

        # Build team_id lookup for player result highlighting
        cur.execute("SELECT id FROM teams WHERE player='yes'")
        pt_row = cur.fetchone()
        player_team_id = pt_row[0] if pt_row else None

        cur.execute(
            """SELECT t.id, t.name, t.start_date, t.prizepool, t.ratingpool,
                      t.place1, tm.name
               FROM tournaments t
               LEFT JOIN teams tm ON t.place1=tm.id
               ORDER BY t.start_date"""
        )
        all_rows = cur.fetchall()
        done_rows     = [(r, True)  for r in all_rows if r[5]]
        upcoming_rows = [(r, False) for r in all_rows if not r[5]]

        if done_rows:
            grid.add_widget(_lbl('', height=10))
            grid.add_widget(_section_title('═══  ИСТОРИЯ ТУРНИРОВ  ═══'))
            for (tid, name, start, prize, rpool, place1, winner), _ in done_rows:
                trow = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                              size_hint_y=None, height=36, padding=(8, 0))
                trow.add_widget(_lbl(f'  {start}  ─  {name}',
                                     color=_GREEN, bold=True, height=36))
                grid.add_widget(trow)

                # Get full top-8
                places_row = cur.execute(
                    "SELECT place1,place2,place3,place4,place5,place6,place7,place8 "
                    "FROM tournaments WHERE id=?", (tid,)
                ).fetchone()
                player_place = None
                pnames = []
                if places_row:
                    for idx, team_id_slot in enumerate(places_row):
                        if not team_id_slot:
                            continue
                        n = cur.execute(
                            "SELECT name FROM teams WHERE id=?", (team_id_slot,)
                        ).fetchone()
                        tname = n[0].strip() if n else '?'
                        pnames.append((idx + 1, tname))
                        if team_id_slot == player_team_id:
                            player_place = idx + 1

                # Player result row (highlighted)
                if player_place is not None:
                    place_color = (
                        _GOLD   if player_place == 1 else
                        _SILVER if player_place == 2 else
                        _BRONZE if player_place == 3 else
                        _PLAYER if player_place <= 8 else
                        (0.8, 0.4, 0.4, 1)
                    )
                    place_bg = (0.10, 0.22, 0.10, 1) if player_place <= 4 else (0.12, 0.12, 0.18, 1)
                    pres = _BgBox(bg=place_bg, orientation='horizontal',
                                  size_hint_y=None, height=28, padding=(16, 0))
                    medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(player_place, f'#{player_place}')
                    pres.add_widget(_lbl(
                        f'  Ваш результат: {medal}  место  •  Чемпион: {winner.strip() if winner else "?"}',
                        color=place_color, height=28,
                    ))
                    grid.add_widget(pres)
                else:
                    irow = _BgBox(bg=(0.08, 0.10, 0.08, 1), orientation='horizontal',
                                  size_hint_y=None, height=28, padding=(16, 0))
                    irow.add_widget(_lbl(
                        f'  Не участвовали  •  Чемпион: {winner.strip() if winner else "?"}',
                        color=_DIM, height=28,
                    ))
                    grid.add_widget(irow)

                if pnames:
                    prow = _BgBox(bg=_BG_DARK, orientation='horizontal',
                                  size_hint_y=None, height=24, padding=(16, 0))
                    prow.add_widget(_lbl(
                        '  ' + '  '.join(f'{i}.{n}' for i, n in pnames),
                        color=(0.60, 0.80, 0.60, 1), height=24, font_size='11sp',
                    ))
                    grid.add_widget(prow)

        if upcoming_rows:
            grid.add_widget(_lbl('', height=10))
            grid.add_widget(_section_title('═══  РАСПИСАНИЕ ТУРНИРОВ  ═══'))
            for (tid, name, start, prize, rpool, place1, winner), _ in upcoming_rows:
                trow = _BgBox(bg=_BG_HEAD, orientation='horizontal',
                              size_hint_y=None, height=36, padding=(8, 0))
                trow.add_widget(_lbl(f'  {start}  ─  {name}',
                                     color=_YELLOW, bold=True, height=36))
                grid.add_widget(trow)

                irow = _BgBox(bg=(0.14, 0.14, 0.06, 1), orientation='horizontal',
                              size_hint_y=None, height=28, padding=(16, 0))
                irow.add_widget(_lbl(
                    f'  ${prize:,}  |  {rpool or 0} pts  |  → Предстоит',
                    color=_WHITE, height=28,
                ))
                grid.add_widget(irow)

        conn.close()
