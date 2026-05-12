from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle

import ui_theme as T
from create_team import CreateTeamPopup
from select_team import SelectTeamPopup


def _card(icon, title, desc, btn_color, handler):
    card = GridLayout(cols=1, size_hint=(1, 1), spacing=8, padding=16)
    with card.canvas.before:
        Color(*T.BG_CARD)
        _r = RoundedRectangle(radius=[10])
    card.bind(
        pos =lambda w, _: setattr(_r, 'pos',  w.pos),
        size=lambda w, _: setattr(_r, 'size', w.size),
    )

    icon_lbl = Label(
        text=icon, font_size='30sp', color=T.ACCENT,
        size_hint_y=None, height=46,
        halign='center', valign='middle',
    )
    icon_lbl.bind(size=icon_lbl.setter('text_size'))

    title_lbl = Label(
        text=f'[b]{title}[/b]', markup=True,
        font_size=T.FS_TITLE, color=T.TEXT_MAIN,
        size_hint_y=None, height=34,
        halign='center', valign='middle',
    )
    title_lbl.bind(size=title_lbl.setter('text_size'))

    desc_lbl = Label(
        text=desc, font_size=T.FS_SMALL, color=T.TEXT_DIM,
        size_hint_y=None, height=48,
        halign='center', valign='top',
    )
    desc_lbl.bind(size=desc_lbl.setter('text_size'))

    btn = Button(
        text='Выбрать',
        background_color=btn_color, background_normal='',
        size_hint_y=None, height=40,
        on_press=handler,
    )

    card.add_widget(icon_lbl)
    card.add_widget(title_lbl)
    card.add_widget(desc_lbl)
    card.add_widget(btn)
    return card


class TeamChoicePopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.72, 0.56)

        root = BoxLayout(orientation='vertical', padding=(16, 12), spacing=10)
        root.add_widget(T.make_stepper(['Персонаж', 'Команда', 'Игра'], 1))

        cards_row = BoxLayout(orientation='horizontal', spacing=12)
        cards_row.add_widget(_card(
            icon='►',
            title='Создать команду',
            desc='Своё название,\nлоготип и регион',
            btn_color=T.BTN_PRIMARY,
            handler=self.create_team,
        ))
        cards_row.add_widget(_card(
            icon='★',
            title='Выбрать команду',
            desc='Из 32 существующих\nпрофессиональных команд',
            btn_color=T.BTN_SUCCESS,
            handler=self.choose_existing,
        ))
        root.add_widget(cards_row)
        self.content = root

    def create_team(self, instance):
        self.dismiss()
        CreateTeamPopup().open()

    def choose_existing(self, instance):
        self.dismiss()
        SelectTeamPopup().open()
