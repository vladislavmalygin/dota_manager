from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle

import ui_theme as T

_BG_DARK = T.BG_ROW_B
_BG_MED  = T.BG_ROW_A
_BG_ROW  = T.BG_ROW_B
_ACCENT  = T.ACCENT
_DIM     = T.TEXT_DIM
_WHITE   = T.TEXT_MAIN
_GOLD    = T.GOLD
_GREEN   = T.POSITIVE
_ORANGE  = (1.00, 0.60, 0.20, 1)
_BLUE    = (0.40, 0.70, 1.00, 1)
_PURPLE  = (0.80, 0.55, 1.00, 1)

_CATEGORIES = {
    'Все':        None,
    'Трансферы':  lambda a: 'Трансфер' in a or 'Цели' in a,
    'Контракты':  lambda a: 'Директор' in a or 'Контракт' in a,
    'Турниры':    lambda a: 'Турнир' in a or 'Система' in a or 'Результат' in a,
    'Академия':   lambda a: 'Скаутинг' in a or 'Академия' in a,
    'Спонсоры':   lambda a: 'Спонсор' in a or 'Организац' in a or 'Партнёр' in a,
    'Новости':    lambda a: 'Новости' in a or 'Отпуск' in a,
}

_CAT_COLOR = {
    'Все':        _WHITE,
    'Трансферы':  _GREEN,
    'Контракты':  _ORANGE,
    'Турниры':    _GOLD,
    'Академия':   _PURPLE,
    'Спонсоры':   _BLUE,
    'Новости':    (0.70, 0.70, 0.70, 1),
}

_AUTHOR_COLOR = {
    'Трансфер':            _GREEN,
    'Спортивный директор': _ORANGE,
    'Скаутинг':            _PURPLE,
    'Академия':            _PURPLE,
    'Спонсор':             _BLUE,
    'Организация':         _BLUE,
    'Партнёрский бонус':   _BLUE,
    'Система':             _DIM,
    'Новости':             (0.70, 0.70, 0.70, 1),
    'Отпуск':              (1.00, 0.80, 0.20, 1),
}


class MessagePopup(Popup):
    def __init__(self, messages, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.88, 0.90)
        self.background_color = (1, 1, 1, 0)
        self._messages   = messages
        self._active_cat = 'Все'
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=6, spacing=4)

        hdr = Label(
            text='[b]Входящие[/b]', markup=True,
            size_hint_y=None, height=36,
            color=_ACCENT, halign='center', valign='middle',
        )
        hdr.bind(size=hdr.setter('text_size'))
        root.add_widget(hdr)

        self._tab_bar  = BoxLayout(size_hint_y=None, height=36, spacing=3)
        self._tab_btns = {}
        for cat in _CATEGORIES:
            btn = Button(text=cat, background_normal='', font_size='14sp')
            btn.bind(on_press=lambda _, c=cat: self._set_cat(c))
            self._tab_bar.add_widget(btn)
            self._tab_btns[cat] = btn
        root.add_widget(self._tab_bar)
        self._highlight_tab()

        self._scroll = ScrollView(size_hint=(1, 1))
        self._grid   = GridLayout(cols=1, size_hint_y=None, spacing=2)
        self._grid.bind(minimum_height=self._grid.setter('height'))
        self._scroll.add_widget(self._grid)
        root.add_widget(self._scroll)

        close = Button(
            text='Закрыть', size_hint_y=None, height=46,
            background_color=(0.7, 0.2, 0.2, 0.9), background_normal='',
        )
        close.bind(on_press=self.dismiss)
        root.add_widget(close)
        self.content = root
        self._fill_messages()

    def _set_cat(self, cat):
        self._active_cat = cat
        self._highlight_tab()
        self._fill_messages()

    def _highlight_tab(self):
        for cat, btn in self._tab_btns.items():
            active = cat == self._active_cat
            c = _CAT_COLOR.get(cat, _WHITE)
            btn.background_color = (c[0], c[1], c[2], 1.0) if active else (0.20, 0.22, 0.28, 1)

    def _fill_messages(self):
        self._grid.clear_widgets()
        pred  = _CATEGORIES.get(self._active_cat)
        shown = [m for m in self._messages
                 if pred is None or pred(m.get('author', ''))]

        if not shown:
            lbl = Label(text='Нет сообщений.', color=_DIM,
                        size_hint_y=None, height=48,
                        halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            self._grid.add_widget(lbl)
            return

        for i, msg in enumerate(shown):
            author = msg.get('author', 'Система')
            text   = msg.get('text', '')
            d      = msg.get('date', '')
            color  = _AUTHOR_COLOR.get(
                next((k for k in _AUTHOR_COLOR if k in author), ''), _WHITE
            )
            bg = _BG_ROW if i % 2 == 0 else _BG_MED

            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None, height=52,
                padding=(8, 4), spacing=6,
            )
            with row.canvas.before:
                Color(*bg)
                rect = Rectangle(pos=row.pos, size=row.size)
            row.bind(
                pos =lambda inst, _, r=None: None,
                size=lambda inst, _, r=None: None,
            )
            # fix rect binding properly
            def _bind_rect(w, r):
                w.bind(
                    pos =lambda i, v, r=r: setattr(r, 'pos', i.pos),
                    size=lambda i, v, r=r: setattr(r, 'size', i.size),
                )
            _bind_rect(row, rect)

            meta = Label(
                text=f'[b]{author}[/b]\n{d}', markup=True,
                color=color, size_hint_x=0.22,
                halign='left', valign='middle', font_size='13sp',
            )
            meta.bind(size=meta.setter('text_size'))

            body = Label(
                text=text, color=_WHITE,
                size_hint_x=0.78,
                halign='left', valign='middle', font_size='14sp',
            )
            body.bind(size=body.setter('text_size'))

            row.add_widget(meta)
            row.add_widget(body)
            self._grid.add_widget(row)


def show_message(messages):
    MessagePopup(messages=messages).open()
