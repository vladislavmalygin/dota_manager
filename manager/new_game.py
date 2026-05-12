import sqlite3
import shutil
import os
import random

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.clock import Clock

import ui_theme as T
from team_choice import TeamChoicePopup

_PORTRAITS = [
    'images/portrait4.png', 'images/portrait5.png', 'images/portrait6.png',
    'images/portrait7.png', 'images/portrait8.png', 'images/portrait9.png',
    'images/portrait10.png',
]


def _randomize_skill_caps(db_name):
    """Randomize skill_cap only for players that have the default/unset cap."""
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, micro_skills, macro_skills, soft_skills, skill_cap FROM players "
        "WHERE skill_cap IS NULL OR skill_cap = 200"
    )
    players = cur.fetchall()
    for pid, mi, ma, so, _ in players:
        mi = mi or 0; ma = ma or 0; so = so or 0
        current_total = mi + ma + so
        base = random.choices(
            [random.randint(150, 200),
             random.randint(180, 250),
             random.randint(220, 280),
             random.randint(260, 300)],
            weights=[30, 35, 25, 10],
            k=1
        )[0]
        cap = max(current_total + 10, base)
        cur.execute("UPDATE players SET skill_cap=? WHERE id=?", (cap, pid))
    conn.commit()
    conn.close()


class NewGamePopup(Popup):
    nickname = 'nickname'
    new_db_name = 'new_db_name'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (1, 1)
        self.selected_portrait = None

        root = BoxLayout(orientation='vertical', padding=14, spacing=8)

        # ── Step indicator ────────────────────────────────────
        root.add_widget(T.make_stepper(['Персонаж', 'Команда', 'Игра'], 0))

        # ── Main split ────────────────────────────────────────
        split = BoxLayout(orientation='horizontal', spacing=14)

        # LEFT: inputs + portrait grid
        left = BoxLayout(orientation='vertical', size_hint_x=0.55, spacing=8)

        self.name_input     = self._inp('Имя')
        self.surname_input  = self._inp('Фамилия')
        self.nickname_input = self._inp('Никнейм')
        for inp in (self.name_input, self.surname_input, self.nickname_input):
            inp.bind(text=self._update_preview)
            left.add_widget(inp)

        left.add_widget(Label(
            text='Выберите портрет:', color=T.TEXT_LABEL,
            size_hint_y=None, height=26, halign='left',
        ))

        portrait_grid = GridLayout(
            cols=4, size_hint_y=None, spacing=6, padding=(0, 2),
        )
        portrait_grid.bind(minimum_height=portrait_grid.setter('height'))
        for src in _PORTRAITS:
            img = Image(source=src, size_hint=(None, None), size=(80, 80))
            img.bind(on_touch_down=lambda inst, touch, p=img: self.select_portrait(p, touch))
            portrait_grid.add_widget(img)
        left.add_widget(portrait_grid)

        split.add_widget(left)

        # RIGHT: portrait preview + name preview
        right = BoxLayout(
            orientation='vertical', size_hint_x=0.45,
            spacing=8, padding=(8, 0, 0, 0),
        )

        preview_frame = BoxLayout(orientation='vertical')
        with preview_frame.canvas.before:
            Color(*T.BG_CARD)
            _bg = RoundedRectangle(radius=[8])
        preview_frame.bind(
            pos =lambda w, _: setattr(_bg, 'pos',  w.pos),
            size=lambda w, _: setattr(_bg, 'size', w.size),
        )
        self._preview_img = Image(
            source='', allow_stretch=True, keep_ratio=True,
            size_hint=(1, 1),
        )
        preview_frame.add_widget(self._preview_img)
        right.add_widget(preview_frame)

        self._preview_name = Label(
            text=f'[color={T.markup_color(T.TEXT_DIM)}]Выберите портрет[/color]',
            markup=True,
            font_size=T.FS_TITLE, color=T.TEXT_MAIN,
            size_hint_y=None, height=56,
            halign='center', valign='middle',
        )
        self._preview_name.bind(size=self._preview_name.setter('text_size'))
        right.add_widget(self._preview_name)

        split.add_widget(right)
        root.add_widget(split)

        # ── Bottom bar: error + create button ─────────────────
        bottom = BoxLayout(size_hint_y=None, height=48, spacing=8)
        self._error_lbl = Label(
            text='', color=T.NEGATIVE,
            halign='left', valign='middle',
        )
        self._error_lbl.bind(size=self._error_lbl.setter('text_size'))
        bottom.add_widget(self._error_lbl)
        bottom.add_widget(Button(
            text='Создать ►',
            size_hint=(None, 1), width=180,
            background_color=T.BTN_PRIMARY,
            background_normal='',
            on_press=self.create_character,
        ))
        root.add_widget(bottom)

        self.content = root

    def _inp(self, hint):
        return TextInput(
            hint_text=hint, multiline=False,
            size_hint_y=None, height=44,
            background_color=T.BG_CARD,
            foreground_color=T.TEXT_MAIN,
            hint_text_color=T.TEXT_DIM,
            cursor_color=T.ACCENT,
        )

    def _update_preview(self, *args):
        n = self.name_input.text.strip()
        s = self.surname_input.text.strip()
        k = self.nickname_input.text.strip()
        parts = []
        if n or s:
            parts.append(f'[b]{n} {s}'.strip() + '[/b]')
        if k:
            parts.append(f'[color={T.markup_color(T.ACCENT)}]{k}[/color]')
        if parts:
            self._preview_name.text = '\n'.join(parts)
        else:
            self._preview_name.text = (
                f'[color={T.markup_color(T.TEXT_DIM)}]Введите данные[/color]'
            )

    def select_portrait(self, instance, touch):
        if not instance.collide_point(touch.x, touch.y):
            return
        if self.selected_portrait and self.selected_portrait is not instance:
            self.selected_portrait.canvas.before.clear()
        self.selected_portrait = instance
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(1.0, 0.96, 0, 1)
            self._portrait_hl = RoundedRectangle(
                pos=(instance.x - 4, instance.y - 4),
                size=(instance.width + 8, instance.height + 8),
                radius=[4],
            )
        self._preview_img.source = instance.source
        self._preview_img.reload()

    def create_character(self, instance):
        name    = self.name_input.text.strip()
        surname = self.surname_input.text.strip()
        global nickname
        nickname = self.nickname_input.text.strip()

        if not name or not surname or not nickname:
            self._error_lbl.text = 'Заполните имя, фамилию и никнейм.'
            return
        if not self.selected_portrait:
            self._error_lbl.text = 'Выберите портрет.'
            return
        self._error_lbl.text = ''

        global new_db_name
        new_db_name = f"saves/{name}_{surname}.db"

        self._loading = Popup(
            title='', size_hint=(0.45, 0.20), auto_dismiss=False,
            content=Label(text='Создание игры...', color=T.TEXT_MAIN),
        )
        self._loading.open()
        Clock.schedule_once(lambda dt: self._do_create(name, surname, nickname), 0.15)

    def _do_create(self, name, surname, nick):
        global new_db_name

        if not os.path.exists('saves'):
            os.makedirs('saves')

        shutil.copy('start_database.db', new_db_name)

        from db_migrate2        import migrate as _m2
        from db_migrate3        import migrate as _m3
        from db_migrate4        import migrate as _m4
        from db_migrate5        import migrate as _m5
        from db_migrate6        import migrate as _m6
        from db_migrate7        import migrate as _m7
        from db_migrate8        import migrate as _m8
        from db_migrate9        import migrate as _m9
        from db_migrate10       import migrate as _m10
        from db_migrate11       import migrate as _m11
        from db_migrate12       import migrate as _m12
        from db_migrate13       import migrate as _m13
        from db_migrate14       import migrate as _m14
        from db_migrate15       import migrate as _m15
        from db_migrate16       import migrate as _m16
        from db_migrate17       import migrate as _m17
        from db_migrate18       import migrate as _m18
        from db_migrate18_fix   import migrate as _m18fix
        from db_migrate19       import migrate as _m19
        from db_migrate20       import migrate as _m20
        from db_migrate21       import migrate as _m21
        from db_fix_orphans     import fix as _fix
        from core               import _fix_contracts, _fix_team_regions
        from logic.sponsors     import ensure_sponsors_table

        _m2(new_db_name);  _m3(new_db_name);  _m4(new_db_name)
        _m5(new_db_name);  _m6(new_db_name);  _m7(new_db_name)
        _m8(new_db_name);  _m9(new_db_name);  _m10(new_db_name)
        _m11(new_db_name); _m12(new_db_name); _m13(new_db_name)
        _m14(new_db_name); _m15(new_db_name); _m16(new_db_name)
        _m17(new_db_name); _m18(new_db_name); _m18fix(new_db_name)
        _m19(new_db_name); _m20(new_db_name); _m21(new_db_name)
        _fix(new_db_name)
        _fix_contracts(new_db_name)
        _fix_team_regions(new_db_name)
        ensure_sponsors_table(new_db_name)
        _randomize_skill_caps(new_db_name)

        conn = sqlite3.connect(new_db_name)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS characters (
                         id INTEGER PRIMARY KEY,
                         name TEXT, surname TEXT,
                         nickname TEXT, portrait TEXT)''')
        cur.execute(
            "INSERT INTO characters (name, surname, nickname, portrait) VALUES (?,?,?,?)",
            (name, surname, nick, self.selected_portrait.source),
        )
        conn.commit()
        conn.close()

        self._loading.dismiss()
        self.dismiss()
        TeamChoicePopup().open()

    def get_db_name(self):
        global new_db_name
        return new_db_name

    def get_nickname(self):
        global nickname
        return nickname
