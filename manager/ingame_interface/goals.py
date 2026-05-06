import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, RoundedRectangle

from logic.goals import get_goals, year_from_date

_ACCENT = (0.35, 0.85, 1.00, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_ORANGE = (1.00, 0.65, 0.20, 1)


class GoalsPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.72, 0.75)
        self.background_color = (1, 1, 1, 0)
        self._build(db_name)

    def _build(self, db_name):
        conn = sqlite3.connect(db_name)
        gd   = conn.execute("SELECT date FROM save WHERE id=1").fetchone()
        conn.close()
        year  = year_from_date(gd[0] if gd else '2024')
        goals = get_goals(db_name, year)

        root = BoxLayout(orientation='vertical', padding=10, spacing=8)

        hdr = Label(
            text=f'[b]Цели сезона {year}[/b]', markup=True,
            size_hint_y=None, height=40,
            color=_ACCENT, halign='center', valign='middle',
        )
        hdr.bind(size=hdr.setter('text_size'))
        root.add_widget(hdr)

        if not goals:
            root.add_widget(Label(
                text='Цели появятся в начале следующего сезона.',
                color=_DIM, halign='center',
            ))
        else:
            completed_n = sum(1 for *_, c, _, _ in goals if c)
            sub = Label(
                text=f'Выполнено: {completed_n}/{len(goals)}',
                size_hint_y=None, height=26, color=_GOLD,
                halign='center', valign='middle',
            )
            sub.bind(size=sub.setter('text_size'))
            root.add_widget(sub)

            for gtype, desc, target, current, completed, rep, money in goals:
                card = BoxLayout(orientation='vertical', size_hint_y=None,
                                 height=88, spacing=3, padding=(10, 6))
                bg = (0.07, 0.22, 0.10, 1) if completed else (0.12, 0.14, 0.20, 1)
                with card.canvas.before:
                    Color(*bg)
                    rr = RoundedRectangle(pos=card.pos, size=card.size, radius=[8])
                card.bind(
                    pos =lambda w, _, r=rr: setattr(r, 'pos',  w.pos),
                    size=lambda w, _, r=rr: setattr(r, 'size', w.size),
                )

                # display progress
                if gtype == 'best_finish':
                    prog_val = max(0, target - (current if current < 999 else target)) + (1 if completed else 0)
                    prog_max = 1
                    cur_disp = f'Лучшее место: {current}' if current < 999 else 'Нет'
                elif gtype in ('cohesion_target', 'sign_skill'):
                    prog_val = min(current, target)
                    prog_max = target
                    cur_disp = str(current)
                else:
                    prog_val = min(current, target)
                    prog_max = target
                    cur_disp = f'{current:,}' if gtype == 'earn_prize' else str(current)

                color = _GREEN if completed else _ORANGE
                status = '✓ Выполнено' if completed else cur_disp

                title_lbl = Label(
                    text=f'[b]{desc}[/b]',
                    markup=True, color=color,
                    size_hint_y=None, height=24,
                    halign='left', valign='middle',
                )
                title_lbl.bind(size=title_lbl.setter('text_size'))

                info_row = BoxLayout(size_hint_y=None, height=18)
                for txt, clr in [(f'Прогресс: {status}', _WHITE),
                                  (f'+{rep} репут.  +${money:,}', _GOLD)]:
                    lbl = Label(text=txt, color=clr, font_size='13sp',
                                halign='left', valign='middle')
                    lbl.bind(size=lbl.setter('text_size'))
                    info_row.add_widget(lbl)

                prog = ProgressBar(max=max(prog_max, 1), value=prog_val,
                                   size_hint_y=None, height=10)

                card.add_widget(title_lbl)
                card.add_widget(info_row)
                card.add_widget(prog)
                root.add_widget(card)

        close = Button(
            text='Закрыть', size_hint_y=None, height=46,
            background_color=(0.7, 0.2, 0.2, 0.9), background_normal='',
        )
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root


def show_goals_popup(db_name):
    GoalsPopup(db_name=db_name).open()
