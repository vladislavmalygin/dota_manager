import sqlite3
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView

_ACCENT  = (0.35, 0.85, 1.00, 1)
_GOLD    = (1.00, 0.85, 0.25, 1)
_GREEN   = (0.25, 0.90, 0.40, 1)
_DIM     = (0.45, 0.45, 0.50, 1)
_WHITE   = (0.90, 0.90, 0.90, 1)
_LOCKED  = (0.28, 0.28, 0.32, 1)

_BG = (0.07, 0.09, 0.13, 1)


class AchievementsPopup(Popup):
    def __init__(self, db_name, **kw):
        super().__init__(**kw)
        self.title = ''
        self.size_hint = (0.82, 0.90)
        self.background_color = (1, 1, 1, 0)
        self._build(db_name)

    def _build(self, db_name):
        conn = sqlite3.connect(db_name)
        rows = conn.execute(
            "SELECT achievement_key, name, description, unlocked_date, bonus_desc "
            "FROM achievements ORDER BY unlocked_date DESC NULLS LAST, id"
        ).fetchall()
        conn.close()

        root = BoxLayout(orientation='vertical', padding=8, spacing=6)

        # Header
        hdr = Label(
            text='[b]ДОСТИЖЕНИЯ[/b]', markup=True,
            color=_ACCENT, size_hint_y=None, height=38,
            font_size='17sp', halign='center', valign='middle',
        )
        hdr.bind(size=hdr.setter('text_size'))
        root.add_widget(hdr)

        unlocked = sum(1 for r in rows if r[3])
        total = len(rows)
        prog = Label(
            text=f'Открыто: {unlocked}/{total}',
            color=_GOLD, size_hint_y=None, height=24,
            font_size='13sp', halign='center', valign='middle',
        )
        prog.bind(size=prog.setter('text_size'))
        root.add_widget(prog)

        sv = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=4, padding=(4, 4))
        grid.bind(minimum_height=grid.setter('height'))

        for key, name, desc, date, bonus in rows:
            is_done = bool(date)
            card = BoxLayout(
                orientation='horizontal',
                size_hint_y=None, height=64,
                padding=(10, 6), spacing=8,
            )
            from kivy.graphics import Color, RoundedRectangle
            bg_col = (0.10, 0.22, 0.14, 1) if is_done else (0.12, 0.12, 0.16, 1)
            with card.canvas.before:
                Color(*bg_col)
                card._bg_rect = RoundedRectangle(radius=[6])
            card.bind(
                pos=lambda w, _: setattr(w._bg_rect, 'pos', w.pos),
                size=lambda w, _: setattr(w._bg_rect, 'size', w.size),
            )

            icon = Label(
                text='✓' if is_done else '○',
                color=_GREEN if is_done else _LOCKED,
                size_hint=(None, 1), width=30,
                font_size='20sp', halign='center', valign='middle',
            )

            info = BoxLayout(orientation='vertical', size_hint=(1, 1), spacing=2)
            title_lbl = Label(
                text=f'[b]{name}[/b]', markup=True,
                color=_GOLD if is_done else _WHITE,
                size_hint_y=None, height=24,
                font_size='13sp', halign='left', valign='middle',
            )
            title_lbl.bind(size=title_lbl.setter('text_size'))
            desc_lbl = Label(
                text=desc or '',
                color=_DIM if not is_done else (0.75, 0.85, 0.75, 1),
                size_hint_y=None, height=18,
                font_size='11sp', halign='left', valign='middle',
            )
            desc_lbl.bind(size=desc_lbl.setter('text_size'))
            bonus_lbl = Label(
                text=f'Бонус: {bonus}' if bonus else '',
                color=_GOLD if is_done else _LOCKED,
                size_hint_y=None, height=16,
                font_size='10sp', halign='left', valign='middle',
            )
            bonus_lbl.bind(size=bonus_lbl.setter('text_size'))
            info.add_widget(title_lbl)
            info.add_widget(desc_lbl)
            info.add_widget(bonus_lbl)

            date_lbl = Label(
                text=date[:7] if date else '',
                color=_DIM, size_hint=(None, 1), width=55,
                font_size='10sp', halign='right', valign='middle',
            )
            date_lbl.bind(size=date_lbl.setter('text_size'))

            card.add_widget(icon)
            card.add_widget(info)
            card.add_widget(date_lbl)
            grid.add_widget(card)

        sv.add_widget(grid)
        root.add_widget(sv)

        close = Button(
            text='Закрыть', size_hint_y=None, height=44,
            background_color=(0.55, 0.18, 0.18, 1), background_normal='',
        )
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root


def show_achievements_popup(db_name):
    AchievementsPopup(db_name=db_name).open()
