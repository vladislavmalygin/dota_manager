import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from logic.sponsors import (
    get_active_sponsor, get_available_offers,
    sign_sponsor, drop_sponsor, condition_label,
)

_ACCENT = (0.35, 0.85, 1.00, 1)
_GOLD   = (1.00, 0.85, 0.25, 1)
_GREEN  = (0.20, 0.88, 0.35, 1)
_WHITE  = (0.92, 0.92, 0.92, 1)
_DIM    = (0.55, 0.55, 0.55, 1)
_RED    = (0.90, 0.28, 0.20, 1)

_BG_DARK  = (0.10, 0.10, 0.12, 1)
_BG_MED   = (0.15, 0.15, 0.18, 1)
_BG_PANEL = (0.12, 0.18, 0.22, 1)
_BG_HEAD  = (0.10, 0.22, 0.32, 1)
_BG_ACTIVE = (0.08, 0.22, 0.10, 1)


def _lbl(text, height=34, color=_WHITE, bold=False, halign='left'):
    t = f'[b]{text}[/b]' if bold else text
    lbl = Label(
        text=t, markup=True,
        size_hint_y=None, height=height,
        color=color, halign=halign, valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


class _BgBox(BoxLayout):
    def __init__(self, bg=_BG_MED, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*bg)
            self._rect = Rectangle()
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class SponsorsPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super().__init__(**kwargs)
        self.db_name = db_name
        self.title = 'Спонсоры'
        self.size_hint = (0.80, 0.88)
        self.auto_dismiss = True
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=6, padding=6)

        active = get_active_sponsor(self.db_name)
        if active:
            root.add_widget(self._active_panel(active))
        else:
            root.add_widget(_lbl(
                '  Нет активного спонсора. Выберите предложение ниже.',
                height=36, color=_DIM,
            ))

        root.add_widget(_lbl('  Доступные предложения', height=38, color=_ACCENT, bold=True))

        offers = get_available_offers(self.db_name)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=4)
        grid.bind(minimum_height=grid.setter('height'))

        if not offers:
            grid.add_widget(_lbl('  Предложений нет.', color=_DIM))
        else:
            for offer in offers:
                grid.add_widget(self._offer_row(offer, bool(active)))

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)
        root.add_widget(scroll)

        close_btn = Button(
            text='Закрыть', size_hint_y=None, height=46,
            background_color=(0.55, 0.18, 0.18, 1), background_normal='',
        )
        close_btn.bind(on_press=self.dismiss)
        root.add_widget(close_btn)

        self.content = root

    def _active_panel(self, active):
        sid, name, desc, income, cond, bonus, penalty, signed = active

        panel = _BgBox(bg=_BG_ACTIVE, orientation='vertical',
                       size_hint_y=None, height=190, padding=(10, 8), spacing=4)

        panel.add_widget(_lbl(f'  Активный спонсор: {name}', height=36, color=_GREEN, bold=True))
        panel.add_widget(_lbl(f'  {desc}', height=30, color=_WHITE))
        panel.add_widget(_lbl(f'  Ежемесячный доход: ${income:,}', height=28, color=_GOLD))

        cond_str = condition_label(cond)
        if bonus:
            cond_str += f'  → бонус +${bonus:,}'
        if penalty:
            cond_str += f'  / штраф −${penalty:,}'
        panel.add_widget(_lbl(f'  Условие сезона: {cond_str}', height=28, color=_WHITE))

        if signed:
            panel.add_widget(_lbl(f'  Подписан: {signed}', height=26, color=_DIM))

        drop_btn = Button(
            text='Отказаться от спонсора', size_hint_y=None, height=38,
            background_color=(0.7, 0.25, 0.15, 1), background_normal='',
        )
        drop_btn.bind(on_press=self._drop)
        panel.add_widget(drop_btn)

        return panel

    def _offer_row(self, offer, has_active):
        oid, name, desc, income, cond, bonus, penalty = offer

        row = _BgBox(bg=_BG_PANEL, orientation='vertical',
                     size_hint_y=None, height=130, padding=(10, 6), spacing=3)

        row.add_widget(_lbl(f'  {name}', height=34, color=_ACCENT, bold=True))
        row.add_widget(_lbl(f'  {desc}', height=26, color=_WHITE))
        row.add_widget(_lbl(f'  Доход: ${income:,}/мес', height=26, color=_GOLD))

        cond_str = condition_label(cond)
        extras = []
        if bonus:
            extras.append(f'бонус +${bonus:,}')
        if penalty:
            extras.append(f'штраф −${penalty:,}')
        if extras:
            cond_str += '  → ' + ',  '.join(extras)
        row.add_widget(_lbl(f'  Условие: {cond_str}', height=24, color=_DIM))

        sign_btn = Button(
            text='Подписать контракт',
            size_hint_y=None, height=34,
            background_color=(0.15, 0.55, 0.25, 1) if not has_active else (0.28, 0.28, 0.28, 1),
            background_normal='',
            disabled=has_active,
        )
        sign_btn.bind(on_press=lambda _, o=oid: self._sign(o))
        row.add_widget(sign_btn)

        return row

    def _sign(self, offer_id):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT date FROM save WHERE id=1")
        row = cur.fetchone()
        conn.close()
        game_date = row[0] if row else '2024-01-01'

        sign_sponsor(self.db_name, offer_id, game_date)

        cur2 = sqlite3.connect(self.db_name)
        cur2.execute(
            "INSERT INTO messages (text, date, author) VALUES (?, date('now'), ?)",
            ('Подписан новый спонсорский контракт.', 'Организация'),
        )
        cur2.commit()
        cur2.close()

        self.dismiss()
        SponsorsPopup(self.db_name).open()

    def _drop(self, _):
        drop_sponsor(self.db_name)
        self.dismiss()
        SponsorsPopup(self.db_name).open()


def show_sponsors_popup(db_name):
    SponsorsPopup(db_name=db_name).open()
