import os
import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle, Rectangle

import ui_theme as T
from core import DotaPopup


def _lbl(text, height=30, color=None, bold=False, halign='left', font_size=None):
    color = color or T.TEXT_MAIN
    font_size = font_size or T.FS_BODY
    t = f'[b]{text}[/b]' if bold else text
    lbl = Label(
        text=t, markup=bold,
        size_hint_y=None, height=height,
        color=color, font_size=font_size,
        halign=halign, valign='middle',
    )
    lbl.bind(size=lbl.setter('text_size'))
    return lbl


class ContinueLastSavePopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.54, 0.62)

        root = BoxLayout(orientation='vertical', padding=16, spacing=10)

        if not os.path.exists('saves'):
            root.add_widget(_lbl('Нет сохранений', color=T.TEXT_DIM,
                                 halign='center', height=60))
            self.content = root
            return

        save_files = [f for f in os.listdir('saves') if f.endswith('.db')]
        if not save_files:
            root.add_widget(_lbl('Нет сохранений', color=T.TEXT_DIM,
                                 halign='center', height=60))
            self.content = root
            return

        global latest_save
        latest_save = max(
            save_files,
            key=lambda f: os.path.getmtime(os.path.join('saves', f)),
        )

        db_path = os.path.join('saves', latest_save)
        try:
            conn = sqlite3.connect(db_path)
            team = conn.execute(
                "SELECT logo, name, manager, COALESCE(rating,0), COALESCE(budget,0) "
                "FROM teams WHERE player='yes'"
            ).fetchone()
            date_row = conn.execute("SELECT date FROM save WHERE id=1").fetchone()
            conn.close()
        except Exception:
            team = None
            date_row = None

        if not team:
            root.add_widget(_lbl('Данные повреждены', color=T.NEGATIVE,
                                 halign='center', height=60))
            self.content = root
            return

        logo, name, manager, rating, budget = team
        game_date = date_row[0] if date_row else '—'

        # ── Header card: logo + team info ─────────────────────
        header = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=110,
            spacing=12, padding=12,
        )
        with header.canvas.before:
            Color(*T.BG_CARD)
            _hr = RoundedRectangle(radius=[8])
        header.bind(
            pos =lambda w, _: setattr(_hr, 'pos',  w.pos),
            size=lambda w, _: setattr(_hr, 'size', w.size),
        )

        logo_path = os.path.join('images', logo) if logo else ''
        if logo_path and os.path.isfile(logo_path):
            header.add_widget(Image(
                source=logo_path,
                size_hint=(None, None), size=(86, 86),
                allow_stretch=True, keep_ratio=True,
            ))

        info = BoxLayout(orientation='vertical', spacing=2)
        info.add_widget(_lbl(name, height=34, color=T.ACCENT, bold=True, font_size=T.FS_TITLE))
        info.add_widget(_lbl(f'Менеджер: {manager or "—"}', height=24, color=T.TEXT_DIM))
        info.add_widget(_lbl(f'Дата: {game_date}', height=24, color=T.TEXT_DIM))
        header.add_widget(info)
        root.add_widget(header)

        # ── Stats row ─────────────────────────────────────────
        stats = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=52,
            spacing=8,
        )

        for label, value, color in [
            ('Рейтинг', f'{int(rating):,}', T.GOLD),
            ('Бюджет',  f'${int(budget):,}', T.budget_color(budget)),
        ]:
            card = GridLayout(cols=1, size_hint=(1, 1), padding=8)
            with card.canvas.before:
                Color(*T.BG_CARD_B)
                _cr = RoundedRectangle(radius=[6])
            card.bind(
                pos =lambda w, _: setattr(_cr, 'pos',  w.pos),
                size=lambda w, _: setattr(_cr, 'size', w.size),
            )
            card.add_widget(_lbl(label, height=16, color=T.TEXT_DIM,
                                 halign='center', font_size=T.FS_TINY))
            card.add_widget(_lbl(value, height=24, color=color,
                                 bold=True, halign='center', font_size=T.FS_BODY))
            stats.add_widget(card)

        root.add_widget(stats)

        # ── Continue button ───────────────────────────────────
        root.add_widget(Button(
            text='► Продолжить',
            size_hint_y=None, height=48,
            background_color=T.BTN_SUCCESS, background_normal='',
            on_press=self.confirm_continue,
        ))

        self.content = root

    def confirm_continue(self, instance):
        self.dismiss()
        db_name = f'saves/{latest_save}'
        DotaPopup(db_name).open_popup(db_name)
