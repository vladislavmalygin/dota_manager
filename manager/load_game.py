import os
import sqlite3

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.image import Image

from core import DotaPopup


class LoadSavePopup(Popup):
    def __init__(self, **kwargs):
        super(LoadSavePopup, self).__init__(**kwargs)
        self.title = "Выберите сейв"
        self.size_hint = (0.82, 0.85)
        self.selected_save = None
        self._build()

    def _build(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', spacing=4, padding=6)
        self._grid = GridLayout(cols=1, spacing=6, size_hint_y=None)
        self._grid.bind(minimum_height=self._grid.setter('height'))

        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(self._grid)
        layout.add_widget(scroll_view)

        btn_row = BoxLayout(size_hint_y=None, height=46, spacing=6)
        continue_btn = Button(text='Продолжить', background_normal='',
                              background_color=(0.15, 0.55, 0.25, 1))
        continue_btn.bind(on_press=self.continue_with_save)

        delete_btn = Button(text='🗑 Удалить', background_normal='',
                            background_color=(0.60, 0.15, 0.15, 1))
        delete_btn.bind(on_press=self._confirm_delete)

        btn_row.add_widget(continue_btn)
        btn_row.add_widget(delete_btn)
        layout.add_widget(btn_row)
        self.add_widget(layout)
        self._populate()

    def _populate(self):
        self._grid.clear_widgets()
        self.selected_save = None

        if not os.path.exists('saves'):
            return
        save_files = sorted(f for f in os.listdir('saves') if f.endswith('.db'))

        for save_file in save_files:
            path = os.path.join('saves', save_file)
            try:
                conn = sqlite3.connect(path)
                row = conn.execute(
                    "SELECT logo, name, COALESCE(rating,0), COALESCE(budget,0) "
                    "FROM teams WHERE player='yes'"
                ).fetchone()
                date_row = conn.execute("SELECT date FROM save WHERE id=1").fetchone()
                conn.close()
            except Exception:
                continue
            if not row:
                continue
            logo, name, rating, budget = row
            game_date = date_row[0] if date_row else '—'

            box = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, spacing=6)
            logo_path = os.path.join('images', logo) if logo else ''
            if logo_path and os.path.isfile(logo_path):
                box.add_widget(Image(source=logo_path, size_hint_x=None, width=80))
            else:
                box.add_widget(Label(text='?', size_hint_x=None, width=80))

            btn = ToggleButton(
                text=f'[b]{name}[/b]\nДата: {game_date}  |  Рейтинг: {int(rating)}  |  Бюджет: ${budget:,}',
                markup=True, group='saves', halign='left', valign='middle',
                size_hint=(1, None), height=86,
            )
            btn.save_file = save_file
            btn.bind(on_press=self.select_save)
            box.add_widget(btn)
            self._grid.add_widget(box)

    def select_save(self, instance):
        self.selected_save = instance

    def continue_with_save(self, _):
        if not self.selected_save:
            return
        db_name = f'saves/{self.selected_save.save_file}'
        self.dismiss()
        DotaPopup(db_name).open_popup(db_name)

    def _confirm_delete(self, _):
        if not self.selected_save:
            return
        save_file = self.selected_save.save_file
        content = BoxLayout(orientation='vertical', padding=10, spacing=8)
        content.add_widget(Label(
            text=f'Удалить [b]{save_file}[/b]?\nОтменить невозможно.',
            markup=True, halign='center',
        ))
        btn_row = BoxLayout(size_hint_y=None, height=44, spacing=6)
        yes = Button(text='Удалить', background_color=(0.7, 0.15, 0.15, 1),
                     background_normal='')
        no  = Button(text='Отмена',  background_color=(0.2, 0.4, 0.6, 1),
                     background_normal='')
        btn_row.add_widget(yes)
        btn_row.add_widget(no)
        content.add_widget(btn_row)
        confirm = Popup(content=content, title='', size_hint=(0.50, 0.30),
                        auto_dismiss=False)
        yes.bind(on_press=lambda _: self._do_delete(save_file, confirm))
        no.bind(on_press=confirm.dismiss)
        confirm.open()

    def _do_delete(self, save_file, confirm_popup):
        confirm_popup.dismiss()
        path = os.path.join('saves', save_file)
        try:
            os.remove(path)
        except Exception:
            pass
        self._populate()

    def open_popup(self, instance):
        LoadSavePopup().open()


