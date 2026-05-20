"""Manager skill tree screen."""
import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

_BG     = (0.07, 0.09, 0.13, 1)
_BG_MED = (0.12, 0.15, 0.20, 1)
_BG_HDR = (0.10, 0.22, 0.32, 1)
_ACC    = (0.35, 0.85, 1.00, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)

_SKILLS = [
    ('negotiator',  'Переговорщик', '−15% агентский сбор при подписании', ''),
    ('tactician',   'Тактик',       '+5% к эффекту стратегий в матчах',   ''),
    ('scout',       'Скаут',        'Видит скилл FA без оплаты разведки',  '(ск)'),
    ('motivator',   'Мотиватор',    '+1 мораль игрокам ежемесячно',        ''),
    ('analyst',     'Аналитик',     '+10% к XP за тренировки',            ''),
    ('diplomat',    'Дипломат',     '−10% к зарплатным запросам при обмене', '[Дп]'),
]
_MAX_LEVEL = 3

_DDL = """
CREATE TABLE IF NOT EXISTS manager_skills (
    skill_key TEXT PRIMARY KEY,
    level     INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS manager_skill_points (
    id           INTEGER PRIMARY KEY,
    total_earned INTEGER DEFAULT 0,
    spent        INTEGER DEFAULT 0
);
"""


def ensure_skills_tables(db_name):
    conn = sqlite3.connect(db_name)
    for stmt in _DDL.strip().split(';'):
        s = stmt.strip()
        if s:
            try:
                conn.execute(s)
            except Exception:
                pass
    conn.execute(
        "INSERT OR IGNORE INTO manager_skill_points (id, total_earned, spent) VALUES (1,0,0)"
    )
    conn.commit()
    conn.close()


def award_skill_point(db_name, reason='турнир'):
    """Give player 1 skill point. Call after each tournament."""
    ensure_skills_tables(db_name)
    conn = sqlite3.connect(db_name)
    conn.execute(
        "UPDATE manager_skill_points SET total_earned=total_earned+1 WHERE id=1"
    )
    conn.execute(
        "INSERT INTO messages (text, date, author) VALUES (?,date('now'),?)",
        (f'Навык менеджера: получено 1 очко за {reason}. Потратьте в разделе Профиль → Навыки.',
         'Менеджмент'),
    )
    conn.commit()
    conn.close()


def get_skill_level(db_name, skill_key):
    ensure_skills_tables(db_name)
    conn = sqlite3.connect(db_name)
    row = conn.execute(
        "SELECT COALESCE(level,0) FROM manager_skills WHERE skill_key=?", (skill_key,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def get_available_points(db_name):
    ensure_skills_tables(db_name)
    conn = sqlite3.connect(db_name)
    row = conn.execute(
        "SELECT COALESCE(total_earned,0) - COALESCE(spent,0) FROM manager_skill_points WHERE id=1"
    ).fetchone()
    conn.close()
    return max(0, row[0] if row else 0)


class ManagerSkillsPopup(Popup):
    def __init__(self, db_name, **kw):
        super().__init__(**kw)
        self.title = ''
        self.size_hint = (0.70, 0.85)
        self._db = db_name
        ensure_skills_tables(db_name)
        self._build()

    def _build(self):
        avail = get_available_points(self._db)

        conn = sqlite3.connect(self._db)
        levels = {sk: (conn.execute(
            "SELECT COALESCE(level,0) FROM manager_skills WHERE skill_key=?", (sk,)
        ).fetchone() or (0,))[0] for sk, *_ in _SKILLS}
        conn.close()

        _BG2 = (0.07, 0.09, 0.13, 1)

        def _bg(widget, color):
            with widget.canvas.before:
                Color(*color)
                r = Rectangle()
            widget.bind(pos=lambda w, _: setattr(r, 'pos', w.pos),
                        size=lambda w, _: setattr(r, 'size', w.size))

        root = BoxLayout(orientation='vertical', padding=8, spacing=6)
        _bg(root, _BG2)

        hdr = Label(
            text=f'[b]НАВЫКИ МЕНЕДЖЕРА[/b]   Доступно очков: [b][color=ffd700]{avail}[/color][/b]',
            markup=True, color=_ACC, size_hint_y=None, height=44,
            halign='center', valign='middle', font_size='15sp',
        )
        hdr.bind(size=hdr.setter('text_size'))
        root.add_widget(hdr)

        sv = ScrollView(size_hint=(1, 1))
        gl = GridLayout(cols=1, size_hint_y=None, spacing=6, padding=4)
        gl.bind(minimum_height=gl.setter('height'))

        for sk_key, sk_name, sk_desc, sk_icon in _SKILLS:
            lvl = levels.get(sk_key, 0)
            can_upgrade = avail > 0 and lvl < _MAX_LEVEL

            card = BoxLayout(orientation='vertical', size_hint_y=None, height=80,
                             padding=(10, 4), spacing=3)
            _bg(card, _BG_MED)

            top_row = BoxLayout(size_hint_y=None, height=34)
            name_lbl = Label(
                text=f'[b]{sk_icon} {sk_name}[/b]  [color=888888]Ур. {lvl}/{_MAX_LEVEL}[/color]',
                markup=True, color=_GOLD if lvl > 0 else _WHITE,
                halign='left', valign='middle', font_size='14sp',
            )
            name_lbl.bind(size=name_lbl.setter('text_size'))
            top_row.add_widget(name_lbl)

            # Stars
            stars_lbl = Label(
                text='★' * lvl + '☆' * (_MAX_LEVEL - lvl),
                color=_GOLD, size_hint_x=None, width=80,
                halign='right', valign='middle', font_size='16sp',
            )
            top_row.add_widget(stars_lbl)

            up_btn = Button(
                text='↑ Прокачать',
                size_hint=(None, 1), width=110,
                background_color=(0.18, 0.50, 0.22, 1) if can_upgrade else (0.28, 0.28, 0.28, 1),
                background_normal='', font_size='12sp',
                disabled=not can_upgrade,
            )
            up_btn.bind(on_press=lambda _, k=sk_key: self._upgrade(k))
            top_row.add_widget(up_btn)

            card.add_widget(top_row)

            desc_lbl = Label(
                text=sk_desc, color=_DIM if lvl == 0 else _WHITE,
                size_hint_y=None, height=28,
                halign='left', valign='middle', font_size='12sp',
            )
            desc_lbl.bind(size=desc_lbl.setter('text_size'))
            card.add_widget(desc_lbl)

            gl.add_widget(card)

        sv.add_widget(gl)
        root.add_widget(sv)

        close = Button(text='Закрыть', size_hint_y=None, height=46,
                       background_color=(0.55, 0.18, 0.18, 1), background_normal='')
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root

    def _upgrade(self, skill_key):
        conn = sqlite3.connect(self._db)
        avail = (conn.execute(
            "SELECT COALESCE(total_earned,0)-COALESCE(spent,0) FROM manager_skill_points WHERE id=1"
        ).fetchone() or (0,))[0]
        cur_lvl = (conn.execute(
            "SELECT COALESCE(level,0) FROM manager_skills WHERE skill_key=?", (skill_key,)
        ).fetchone() or (0,))[0]
        if avail < 1 or cur_lvl >= _MAX_LEVEL:
            conn.close()
            return
        conn.execute("INSERT OR IGNORE INTO manager_skills (skill_key, level) VALUES (?,0)",
                     (skill_key,))
        conn.execute("UPDATE manager_skills SET level=level+1 WHERE skill_key=?", (skill_key,))
        conn.execute("UPDATE manager_skill_points SET spent=spent+1 WHERE id=1")
        conn.commit()
        conn.close()
        self.dismiss()
        ManagerSkillsPopup(db_name=self._db).open()


def show_skills_popup(db_name):
    ManagerSkillsPopup(db_name=db_name).open()
