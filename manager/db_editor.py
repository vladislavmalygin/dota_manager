"""
Database editor — accessible from the main menu.
Reads from start_database.db; writes propagate to start_database.db + all saves/*.db
"""
import sqlite3
import os

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle

DB = 'start_database.db'

ROLES = ['carry', 'mid', 'offlane', 'partial_support', 'full_support']
ROLE_LABELS = {
    'carry': 'Carry', 'mid': 'Mid', 'offlane': 'Offlane',
    'partial_support': 'Sup 4', 'full_support': 'Sup 5',
}

_BG    = (0.10, 0.10, 0.13, 1)
_PANEL = (0.14, 0.14, 0.18, 1)
_SEL   = (0.10, 0.25, 0.38, 1)
_ACC   = (0.35, 0.85, 1.00, 1)
_GREEN = (0.20, 0.80, 0.35, 1)
_RED   = (0.85, 0.25, 0.20, 1)
_WHITE = (0.92, 0.92, 0.92, 1)
_DIM   = (0.55, 0.55, 0.55, 1)
_GOLD  = (1.00, 0.85, 0.25, 1)
_SAVE_CLR = (0.15, 0.55, 0.25, 1)


# ── multi-db helpers ──────────────────────────────────────────────────────────

def get_all_dbs():
    """Template DB + all valid save files."""
    dbs = [DB]
    saves_dir = 'saves'
    if os.path.exists(saves_dir):
        for f in sorted(os.listdir(saves_dir)):
            if not f.endswith('.db'):
                continue
            path = os.path.join(saves_dir, f)
            try:
                conn = sqlite3.connect(path)
                conn.execute("SELECT 1 FROM players LIMIT 1")
                conn.close()
                if path not in dbs:
                    dbs.append(path)
            except Exception:
                pass
    return dbs


def _exec_all(sql, params=()):
    """Run a write on every game database."""
    for db in get_all_dbs():
        try:
            conn = sqlite3.connect(db)
            conn.execute(sql, params)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f'[db_editor] {db}: {e}')


# ── widget helpers ────────────────────────────────────────────────────────────

class _Bg(BoxLayout):
    def __init__(self, color=_PANEL, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*color)
            self._r = Rectangle()
        self.bind(pos=self._u, size=self._u)

    def _u(self, *_):
        self._r.pos = self.pos
        self._r.size = self.size

    def set_color(self, c):
        self._c.rgba = c


def _lbl(text, height=28, color=_WHITE, bold=False, halign='left', font_size='13sp'):
    t = f'[b]{text}[/b]' if bold else text
    w = Label(text=t, markup=True, size_hint_y=None, height=height,
              color=color, halign=halign, valign='middle', font_size=font_size)
    w.bind(size=w.setter('text_size'))
    return w


def _btn(text, color=(0.20, 0.45, 0.65, 1), height=36, **kw):
    return Button(text=text, background_color=color, background_normal='',
                  size_hint_y=None, height=height, **kw)


def _inp(text='', hint='', height=34, **kw):
    ti = TextInput(text=str(text), hint_text=hint,
                   size_hint_y=None, height=height,
                   background_color=(0.18, 0.18, 0.22, 1),
                   foreground_color=_WHITE, cursor_color=_ACC,
                   multiline=False, **kw)
    return ti


def _scroll(child):
    sv = ScrollView(size_hint=(1, 1), bar_width=6)
    sv.add_widget(child)
    return sv


def _vgrid():
    g = GridLayout(cols=1, size_hint_y=None, spacing=2)
    g.bind(minimum_height=g.setter('height'))
    return g


# ── player picker popup ───────────────────────────────────────────────────────

class PlayerPickerPopup(Popup):
    def __init__(self, role, current_id, team_id, on_pick, **kw):
        super().__init__(**kw)
        self.title = f'Выбрать игрока — {ROLE_LABELS.get(role, role)}'
        self.size_hint = (0.55, 0.80)
        self.auto_dismiss = False
        self._on_pick = on_pick
        self._build(role, current_id, team_id)

    def _build(self, role, current_id, team_id):
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nickname,
                   COALESCE(micro_skills,0), COALESCE(macro_skills,0),
                   COALESCE(soft_skills,0), country
            FROM players
            WHERE (team_id=0 OR id=?) AND (role=? OR role IS NULL)
            ORDER BY COALESCE(micro_skills,0)+COALESCE(macro_skills,0)+COALESCE(soft_skills,0) DESC
        """, (current_id or -1, role))
        players = cur.fetchall()
        conn.close()

        root = BoxLayout(orientation='vertical', spacing=4, padding=6)
        grid = _vgrid()

        clear_btn = _btn('— Освободить слот —', color=(0.45, 0.15, 0.15, 1))
        clear_btn.bind(on_press=lambda _: self._pick(None))
        grid.add_widget(clear_btn)

        for pid, nick, micro, macro, soft, country in players:
            total = micro + macro + soft
            is_cur = (pid == current_id)
            row = _Bg(color=_SEL if is_cur else _PANEL,
                      orientation='horizontal', size_hint_y=None, height=40,
                      padding=(6, 2), spacing=6)
            row.add_widget(_lbl(
                f'{"★  " if is_cur else ""}{nick}  ({country})',
                color=_GOLD if is_cur else _WHITE, height=36,
            ))
            row.add_widget(_lbl(f'{total}', color=_ACC, height=36, halign='right'))
            row.bind(on_touch_down=lambda inst, t, pid=pid:
                     self._pick(pid) if inst.collide_point(*t.pos) else None)
            grid.add_widget(row)

        root.add_widget(_scroll(grid))
        close = _btn('Отмена', color=(0.45, 0.18, 0.18, 1))
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root

    def _pick(self, player_id):
        self.dismiss()
        if self._on_pick:
            self._on_pick(player_id)


# ── TEAM EDITOR ───────────────────────────────────────────────────────────────

class TeamEditorPanel(BoxLayout):
    def __init__(self, on_refresh, **kw):
        super().__init__(orientation='vertical', spacing=4, padding=6, **kw)
        self._on_refresh = on_refresh
        self._team_id = None
        self._staged = {}   # field: (text_value, cast_fn)
        self._slots = {}
        self._build_empty()

    def _build_empty(self):
        self.clear_widgets()
        self.add_widget(_lbl('Выберите команду слева', color=_DIM, halign='center', height=40))

    def flush(self):
        """Save all staged field changes to every DB."""
        if not self._team_id or not self._staged:
            return
        needs_refresh = False
        for field, (value, cast) in self._staged.items():
            try:
                v = cast(value)
                _exec_all(f"UPDATE teams SET {field}=? WHERE id=?", (v, self._team_id))
                if field == 'name':
                    needs_refresh = True
            except Exception:
                pass
        self._staged.clear()
        if needs_refresh:
            self._on_refresh()

    def load(self, team_id):
        self.flush()  # save pending changes before switching
        self._team_id = team_id
        self._staged = {}
        self.clear_widgets()
        self._slots = {}

        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT t.name, t.country, t.budget, COALESCE(t.rating,0),
                   t.carry, t.mid, t.offlane, t.partial_support, t.full_support,
                   COALESCE(t.cohesion, 0),
                   COALESCE(t.region, 'WEU'),
                   COALESCE(t.tactic, 'balanced')
            FROM teams t WHERE t.id=?
        """, (team_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        name, country, budget, rating, *rest = row
        slot_ids = rest[:5]
        cohesion = rest[5]
        region   = rest[6]
        tactic   = rest[7]

        self.add_widget(_lbl(name, bold=True, color=_GOLD, height=32, font_size='15sp'))

        fields_grid = GridLayout(cols=2, size_hint_y=None, spacing=4)
        fields_grid.bind(minimum_height=fields_grid.setter('height'))

        def _field(label, val, field, cast=str):
            fields_grid.add_widget(_lbl(label, height=32))
            ti = _inp(val, height=32)
            ti.bind(text=lambda inst, v, f=field, c=cast: self._stage(f, v, c))
            fields_grid.add_widget(ti)

        _field('Название', name,       'name')
        _field('Страна',   country or '', 'country')
        _field('Бюджет $', budget or 0,  'budget', int)
        _field('Рейтинг',  int(rating),  'rating', float)
        _field('Сыгранность', cohesion,  'cohesion', int)

        self.add_widget(fields_grid)

        # Region spinner
        from kivy.uix.spinner import Spinner
        regions = ['EEU', 'WEU', 'NA', 'SA', 'China', 'SEA', 'OPEN']
        tactics = ['balanced', 'aggressive', 'farming', 'teamplay']

        spin_row = GridLayout(cols=4, size_hint_y=None, height=36, spacing=4)
        spin_row.add_widget(_lbl('Регион', height=36))
        reg_spin = Spinner(text=region, values=regions,
                           size_hint_y=None, height=34,
                           background_color=(0.18, 0.35, 0.55, 1), background_normal='')
        reg_spin.bind(text=lambda inst, v: self._stage('region', v, str))
        spin_row.add_widget(reg_spin)

        spin_row.add_widget(_lbl('Тактика', height=36))
        tac_spin = Spinner(text=tactic, values=tactics,
                           size_hint_y=None, height=34,
                           background_color=(0.18, 0.35, 0.55, 1), background_normal='')
        tac_spin.bind(text=lambda inst, v: self._stage('tactic', v, str))
        spin_row.add_widget(tac_spin)
        self.add_widget(spin_row)

        save_btn = _btn('💾  Сохранить команду', color=_SAVE_CLR, height=38)
        save_btn.bind(on_press=lambda _: self.flush())
        self.add_widget(save_btn)

        self.add_widget(_lbl('─── Состав ───', color=_ACC, height=28, halign='center'))

        for role, pid in zip(ROLES, slot_ids):
            nick = self._player_nick(pid) if pid else '— свободно —'
            color = _WHITE if pid else _DIM
            row = _Bg(color=_PANEL, orientation='horizontal',
                      size_hint_y=None, height=42, padding=(4, 2), spacing=4)
            row.add_widget(_lbl(ROLE_LABELS[role], color=_ACC, height=38, font_size='12sp'))
            lbl = _lbl(nick, color=color, height=38)
            row.add_widget(lbl)
            pick_btn = _btn('Изменить', color=(0.15, 0.45, 0.65, 1), height=36,
                            size_hint_x=None, width=90)
            pid_ref = [pid]
            pick_btn.bind(on_press=lambda _, r=role, lb=lbl, pr=pid_ref:
                          self._open_picker(r, pr[0], lb, pr))
            row.add_widget(pick_btn)
            self.add_widget(row)
            self._slots[role] = (lbl, pid)

    def _stage(self, field, value, cast):
        self._staged[field] = (value, cast)

    def _player_nick(self, pid):
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT nickname FROM players WHERE id=?", (pid,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else str(pid)

    def _open_picker(self, role, current_pid, label_widget, pid_ref):
        def on_pick(new_pid):
            if current_pid:
                _exec_all(
                    "UPDATE players SET team_id=0, wage=0 WHERE id=? AND team_id=?",
                    (current_pid, self._team_id),
                )
                _exec_all(f"UPDATE teams SET {role}=NULL WHERE id=?", (self._team_id,))
            if new_pid:
                _exec_all("UPDATE players SET team_id=? WHERE id=?", (self._team_id, new_pid))
                _exec_all(f"UPDATE teams SET {role}=? WHERE id=?", (new_pid, self._team_id))
                conn = sqlite3.connect(DB)
                nr = conn.execute("SELECT nickname FROM players WHERE id=?", (new_pid,)).fetchone()
                conn.close()
                label_widget.text = nr[0] if nr else str(new_pid)
                label_widget.color = _WHITE
            else:
                label_widget.text = '— свободно —'
                label_widget.color = _DIM
            pid_ref[0] = new_pid

        PlayerPickerPopup(
            role=role, current_id=current_pid,
            team_id=self._team_id, on_pick=on_pick,
        ).open()


# ── PLAYER EDITOR ─────────────────────────────────────────────────────────────

class PlayerEditorPanel(BoxLayout):
    def __init__(self, on_refresh, **kw):
        super().__init__(orientation='vertical', spacing=4, padding=6, **kw)
        self._on_refresh = on_refresh
        self._pid = None
        self._staged = {}
        self._build_empty()

    def _build_empty(self):
        self.clear_widgets()
        self.add_widget(_lbl('Выберите игрока слева', color=_DIM, halign='center', height=40))

    def flush(self):
        """Save all staged field changes to every DB."""
        if not self._pid or not self._staged:
            return
        needs_refresh = False
        for field, (value, cast) in self._staged.items():
            try:
                v = cast(value)
                _exec_all(f"UPDATE players SET {field}=? WHERE id=?", (v, self._pid))
                if field == 'nickname':
                    needs_refresh = True
            except Exception:
                pass
        self._staged.clear()
        if needs_refresh:
            self._on_refresh()

    def load(self, player_id):
        self.flush()  # save pending changes before switching
        self._pid = player_id
        self._staged = {}
        self.clear_widgets()

        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT nickname, name, surname, country, role,
                   COALESCE(micro_skills,0), COALESCE(macro_skills,0),
                   COALESCE(soft_skills,0), COALESCE(skill_cap,300),
                   COALESCE(competence,5), COALESCE(morale,5),
                   COALESCE(wage,0), COALESCE(expected_wage,0),
                   team_id, COALESCE(age,22), contract_end,
                   secondary_role, COALESCE(secondary_comp,5),
                   COALESCE(stability,5), COALESCE(learning_rate,5)
            FROM players WHERE id=?
        """, (player_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        (nick, fname, lname, country, role, micro, macro, soft, cap, comp, morale,
         wage, exp_wage, team_id, age, contract_end, sec_role, sec_comp,
         stability, learning_rate) = row

        team_name = ''
        if team_id:
            r = cur.execute("SELECT name FROM teams WHERE id=?", (team_id,)).fetchone()
            team_name = r[0] if r else str(team_id)
        comp_exp = (cur.execute("SELECT COALESCE(comp_exp,0) FROM players WHERE id=?",
                               (player_id,)).fetchone() or (0,))[0]
        conn.close()

        self.add_widget(_lbl(f'id={player_id}  {nick}', bold=True, color=_GOLD,
                             height=30, font_size='14sp'))
        if team_name:
            self.add_widget(_lbl(f'Команда: {team_name}', color=_ACC, height=24))
        else:
            self.add_widget(_lbl('Свободный агент', color=_GREEN, height=24))

        sv = ScrollView(size_hint=(1, 1), bar_width=6)
        grid = GridLayout(cols=2, size_hint_y=None, spacing=3, padding=(0, 2))
        grid.bind(minimum_height=grid.setter('height'))

        def _row(label, val, field, cast=str, ro=False):
            grid.add_widget(_lbl(label, height=32))
            if ro:
                grid.add_widget(_lbl(str(val), color=_DIM, height=32))
                return
            ti = _inp(val, height=32)
            ti.bind(text=lambda inst, v, f=field, c=cast: self._stage(f, v, c))
            grid.add_widget(ti)

        _row('Никнейм',       nick,     'nickname')
        _row('Имя',           fname,    'name')
        _row('Фамилия',       lname,    'surname')
        _row('Страна',        country,  'country')

        grid.add_widget(_lbl('Роль', height=32))
        role_spin = Spinner(
            text=role or 'carry',
            values=ROLES,
            size_hint_y=None, height=32,
            background_color=(0.18, 0.35, 0.55, 1), background_normal='',
        )
        role_spin.bind(text=lambda inst, v: self._stage('role', v, str))
        grid.add_widget(role_spin)
        _row('Micro',         micro,    'micro_skills', int)
        _row('Macro',         macro,    'macro_skills', int)
        _row('Soft',          soft,     'soft_skills',  int)
        _row('Соревн. опыт',  comp_exp, 'comp_exp',     int)
        _row('Skill cap',     cap,      'skill_cap',    int)
        _row('Competence',    comp,     'competence',   int)
        _row('Morale',        morale,   'morale',       int)
        _row('Зарплата $',    wage,     'wage',         int)
        _row('Ожид. зарп. $', exp_wage, 'expected_wage',int)
        _row('Возраст',        age,               'age',          int)
        _row('Контракт до',   contract_end or '—', 'contract_end', ro=True)
        _row('Стабильность',   stability,     'stability',     int)
        _row('Скор. обучения', learning_rate, 'learning_rate', int)

        # Secondary role section
        from kivy.uix.spinner import Spinner as _Sp
        grid.add_widget(_lbl('Доп. роль', height=32))
        sec_vals = ['—'] + ROLES
        sec_spin = _Sp(
            text=sec_role or '—', values=sec_vals,
            size_hint_y=None, height=32,
            background_color=(0.18, 0.35, 0.55, 1), background_normal='',
        )
        sec_spin.bind(text=lambda inst, v: self._stage('secondary_role', None if v == '—' else v, str))
        grid.add_widget(sec_spin)

        _row('Компет. доп. роли', sec_comp, 'secondary_comp', int)

        sv.add_widget(grid)
        self.add_widget(sv)

        save_btn = _btn('💾  Сохранить игрока', color=_SAVE_CLR, height=38)
        save_btn.bind(on_press=lambda _: self.flush())
        self.add_widget(save_btn)

        del_btn = _btn('Удалить игрока', color=(0.55, 0.15, 0.15, 1), height=38)
        del_btn.bind(on_press=self._delete)
        self.add_widget(del_btn)

    def _stage(self, field, value, cast=str):
        self._staged[field] = (value, cast)

    def _delete(self, _):
        if not self._pid:
            return
        for col in ROLES:
            _exec_all(f"UPDATE teams SET {col}=NULL WHERE {col}=?", (self._pid,))
        _exec_all("DELETE FROM players WHERE id=?", (self._pid,))
        self._pid = None
        self._staged = {}
        self._build_empty()
        self._on_refresh()


# ── TEAMS TAB ─────────────────────────────────────────────────────────────────

class TeamsTab(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='horizontal', spacing=4, **kw)
        self._sel_btn = None
        self._editor = TeamEditorPanel(
            on_refresh=self._refresh_list,
            size_hint_x=0.60,
        )
        self._list_root = _Bg(color=_BG, orientation='vertical', size_hint_x=0.40)
        self._search = _inp('', hint='Поиск по названию...', height=34)
        self._search.bind(text=lambda inst, v: self._refresh_list(v))
        self._list_root.add_widget(self._search)

        self._list_grid = _vgrid()
        self._list_root.add_widget(_scroll(self._list_grid))

        add_btn = _btn('+ Новая команда', color=(0.15, 0.50, 0.25, 1), height=36)
        add_btn.bind(on_press=self._add_team)
        self._list_root.add_widget(add_btn)

        self.add_widget(self._list_root)
        self.add_widget(self._editor)
        self._refresh_list()

    def flush(self):
        self._editor.flush()

    def _refresh_list(self, query=''):
        if not isinstance(query, str):
            query = self._search.text
        self._list_grid.clear_widgets()
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.name, COALESCE(t.rating,0),
              COUNT(p1.id)+COUNT(p2.id)+COUNT(p3.id)+COUNT(p4.id)+COUNT(p5.id) as n
            FROM teams t
            LEFT JOIN players p1 ON t.carry=p1.id
            LEFT JOIN players p2 ON t.mid=p2.id
            LEFT JOIN players p3 ON t.offlane=p3.id
            LEFT JOIN players p4 ON t.partial_support=p4.id
            LEFT JOIN players p5 ON t.full_support=p5.id
            GROUP BY t.id
            ORDER BY t.rating DESC
        """)
        rows = cur.fetchall()
        conn.close()

        q = query.lower()
        for tid, name, rating, n in rows:
            if q and q not in name.lower():
                continue
            color_fill = (0.3, 1.0, 0.5, 1) if n == 5 else (_GOLD if n >= 3 else _DIM)
            btn = _btn(f'{name}  [{n}/5]  {int(rating)}', color=_SEL, height=36)
            btn.color = color_fill
            btn.bind(on_press=lambda _, tid=tid, b=btn: self._select(tid, b))
            self._list_grid.add_widget(btn)

    def _select(self, team_id, btn):
        if self._sel_btn:
            self._sel_btn.background_color = _SEL
        self._sel_btn = btn
        btn.background_color = (0.15, 0.45, 0.75, 1)
        self._editor.load(team_id)

    def _add_team(self, _):
        conn = sqlite3.connect(DB)
        conn.execute("""
            INSERT INTO teams (name, budget, player, rating, cohesion)
            VALUES ('Новая команда', 1000000, 'no', 0, 0)
        """)
        conn.commit()
        conn.close()
        self._refresh_list()


# ── PLAYERS TAB ───────────────────────────────────────────────────────────────

class PlayersTab(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='horizontal', spacing=4, **kw)
        self._sel_btn = None
        self._filter_role = 'все'
        self._filter_team = 'все'
        self._editor = PlayerEditorPanel(
            on_refresh=self._refresh_list,
            size_hint_x=0.55,
        )

        left = _Bg(color=_BG, orientation='vertical', size_hint_x=0.45, spacing=2)

        frow = BoxLayout(size_hint_y=None, height=34, spacing=4)
        self._search = _inp('', hint='Ник...', height=32)
        self._search.bind(text=lambda inst, v: self._refresh_list())

        role_vals = ['все'] + ROLES
        self._role_spin = Spinner(text='все', values=role_vals,
                                  size_hint_y=None, height=32,
                                  background_color=(0.18, 0.35, 0.55, 1),
                                  background_normal='')
        self._role_spin.bind(text=lambda inst, v: self._set_role(v))

        team_vals = self._get_team_values()
        self._team_spin = Spinner(text='все', values=team_vals,
                                  size_hint_y=None, height=32,
                                  background_color=(0.18, 0.35, 0.55, 1),
                                  background_normal='')
        self._team_spin.bind(text=lambda inst, v: self._set_team(v))

        frow.add_widget(self._search)
        frow.add_widget(self._role_spin)
        frow.add_widget(self._team_spin)
        left.add_widget(frow)

        self._list_grid = _vgrid()
        left.add_widget(_scroll(self._list_grid))

        add_btn = _btn('+ Новый игрок', color=(0.15, 0.50, 0.25, 1), height=36)
        add_btn.bind(on_press=self._add_player)
        left.add_widget(add_btn)

        self.add_widget(left)
        self.add_widget(self._editor)
        self._refresh_list()

    def flush(self):
        self._editor.flush()

    def _get_team_values(self):
        conn = sqlite3.connect(DB)
        rows = conn.execute("SELECT name FROM teams ORDER BY rating DESC").fetchall()
        conn.close()
        return ['все', 'свободные'] + [r[0] for r in rows]

    def _set_role(self, v):
        self._filter_role = v
        self._refresh_list()

    def _set_team(self, v):
        self._filter_team = v
        self._refresh_list()

    def _refresh_list(self):
        self._list_grid.clear_widgets()
        conn = sqlite3.connect(DB)
        cur = conn.cursor()

        where = []
        params = []
        q = self._search.text.lower()
        if q:
            where.append("LOWER(p.nickname) LIKE ?")
            params.append(f'%{q}%')
        if self._filter_role != 'все':
            where.append("p.role=?")
            params.append(self._filter_role)
        if self._filter_team == 'свободные':
            where.append("p.team_id=0")
        elif self._filter_team != 'все':
            where.append("t.name=?")
            params.append(self._filter_team)

        cond = ('WHERE ' + ' AND '.join(where)) if where else ''
        cur.execute(f"""
            SELECT p.id, p.nickname, p.role,
                   COALESCE(p.micro_skills,0)+COALESCE(p.macro_skills,0) as sk,
                   COALESCE(t.name, '—') as tname,
                   p.team_id
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            {cond}
            ORDER BY sk DESC, p.nickname
        """, params)
        rows = cur.fetchall()
        conn.close()

        for pid, nick, role, sk, tname, tid in rows:
            role_short = {'carry': 'C', 'mid': 'M', 'offlane': 'O',
                          'partial_support': 'S4', 'full_support': 'S5'}.get(role, '?')
            color = _WHITE if tid else _DIM
            text = f'[{role_short}] {nick}  {sk}'
            btn = _btn(text, color=_PANEL, height=34)
            btn._player_id = pid
            btn.color = color
            btn.bind(on_press=lambda _, pid=pid, b=btn: self._select(pid, b))
            self._list_grid.add_widget(btn)

    def _select(self, player_id, btn):
        if self._sel_btn:
            self._sel_btn.background_color = _PANEL
        self._sel_btn = btn
        btn.background_color = _SEL
        self._editor.load(player_id)

    def _add_player(self, _):
        conn = sqlite3.connect(DB)
        conn.execute("""
            INSERT INTO players
              (nickname, name, surname, country, role, team_id,
               micro_skills, macro_skills, soft_skills, skill_cap,
               competence, morale, wage, expected_wage, fame, character)
            VALUES ('Новый', 'Имя', 'Фамилия', 'Russia', 'carry', 0,
                    60, 60, 60, 200, 5, 5, 5000, 5000, 40, 'balanced')
        """)
        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()

        # Reset filters so the new player is visible, then auto-select it
        self._search.text = ''
        self._role_spin.text = 'все'
        self._team_spin.text = 'свободные'
        self._filter_role = 'все'
        self._filter_team = 'свободные'
        self._refresh_list()

        # Auto-open the new player in the editor
        for child in reversed(self._list_grid.children):
            if getattr(child, '_player_id', None) == new_id:
                self._select(new_id, child)
                return
        self._editor.load(new_id)


# ── MAIN POPUP ────────────────────────────────────────────────────────────────

class DBEditorPopup(Popup):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.title = 'Редактор базы данных'
        self.size_hint = (0.97, 0.95)
        self.auto_dismiss = False
        self._active_tab = None
        self._build()

    def _build(self):
        root = _Bg(color=_BG, orientation='vertical', spacing=0)

        tab_row = BoxLayout(size_hint_y=None, height=42, spacing=2)
        self._tab_btns = {}
        for name in ('Команды', 'Игроки'):
            b = _btn(name, color=(0.18, 0.35, 0.55, 1), height=40)
            b.bind(on_press=lambda _, n=name: self._switch(n))
            tab_row.add_widget(b)
            self._tab_btns[name] = b
        root.add_widget(tab_row)

        self._content = BoxLayout(size_hint=(1, 1))
        root.add_widget(self._content)

        btn_row = BoxLayout(size_hint_y=None, height=46, spacing=4)
        save_all_btn = _btn('💾  Сохранить все изменения', color=_SAVE_CLR, height=44)
        save_all_btn.bind(on_press=self._save_all)
        close = _btn('Закрыть', color=(0.50, 0.18, 0.18, 1), height=44)
        close.bind(on_press=self._save_all)
        close.bind(on_press=self.dismiss)
        btn_row.add_widget(save_all_btn)
        btn_row.add_widget(close)
        root.add_widget(btn_row)

        self.content = root
        self._switch('Команды')

    def _switch(self, name):
        for n, b in self._tab_btns.items():
            b.background_color = (0.25, 0.50, 0.75, 1) if n == name else (0.18, 0.35, 0.55, 1)
        self._content.clear_widgets()
        if name == 'Команды':
            tab = TeamsTab()
        else:
            tab = PlayersTab()
        self._active_tab = tab
        self._content.add_widget(tab)

    def _save_all(self, _):
        if self._active_tab:
            self._active_tab.flush()


def open_db_editor():
    DBEditorPopup().open()
