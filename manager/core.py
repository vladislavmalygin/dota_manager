import sqlite3
from datetime import date, timedelta

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle

from settings import SettingsPopup
from ingame_interface.inbox import show_message
from ingame_interface.mixin import show_custom_popup
from ingame_interface.squad import show_squad_popup
from ingame_interface.tournaments import TournamentPopup


class MainWindow(BoxLayout):
    def __init__(self, db_name, popup, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.db_name = db_name
        self.popup = popup

        self.date_object = self.get_date_from_db(1)

        self.today_date_button = Button(text=f'{self.date_object}', background_color=(0.5, 0.5, 0.2, 1),
                                        on_press=self.on_press)

        # Установка фона с изображением
        with self.canvas.before:
            Color(1, 1, 1, 0.5)  # Белый цвет фона
            self.rect = Rectangle(source='images/core1.png', pos=self.pos, size=self.size)

        # Обновление размера прямоугольника при изменении размера окна
        self.bind(size=self._update_rect, pos=self._update_rect)

        # Верхняя часть интерфейса
        top_layout = GridLayout(cols=5, size_hint_y=0.1)

        team_name = self.get_team_name()
        tournament_name = self.get_next_tournament()

        # Добавляем кнопки в верхнюю часть с цветами
        top_layout.add_widget(Button(text='Dota Manager', background_color=(0.2, 0.6, 0.8, 1), on_press=self.on_press))
        top_layout.add_widget(Button(text=team_name, background_color=(0.2, 0.8, 0.2, 1), on_press=self.on_press))
        top_layout.add_widget(Button(text=tournament_name, background_color=(0.8, 0.2, 0.2, 1), on_press=self.on_press))
        top_layout.add_widget(self.today_date_button)
        top_layout.add_widget(Button(text='Далее', background_color=(0.8, 0.8, 0.2, 1), on_press=self.on_next))

        # Добавляем верхнюю часть в основной макет
        self.add_widget(top_layout)

        # Создаем основной макет для левой и правой части интерфейса
        main_layout = BoxLayout(orientation='horizontal')

        # Левая часть
        left_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 1))

        # Заполняем левую часть кнопками с цветами
        buttons = {
            'Входящие': self.on_incoming,
            'Состав': self.on_roster,
            'Организация': self.on_organization,
            'Турниры': self.on_tournaments,
            'Трансферы': self.on_transfers,
            'Настройки': self.on_settings,
            'Мой профиль': self.on_profile,
            'Главное меню': self.on_main_menu,
        }

        for btn_text, action in buttons.items():
            button = Button(text=btn_text, background_color=(0.4, 0.4, 0.8, 0.8))
            button.bind(on_press=action)  # Привязываем отдельный обработчик к кнопке
            left_layout.add_widget(button)

        # Создаем основной область экрана для переменного контента
        self.main_area = BoxLayout(size_hint_x=0.8)

        # Создаем полупрозрачный белый фон для основной области контента
        with self.main_area.canvas.before:
            Color(0.4, 0.4, 0.4, 0.2)  # Полупрозрачный белый цвет фона
            self.rect_main_area = Rectangle(pos=self.main_area.pos, size=self.main_area.size)

        # Обновление размера прямоугольника основной области при изменении размера окна
        self.main_area.bind(size=self._update_main_area_rect)

        # Добавляем левую часть и основную область к главному окну
        main_layout.add_widget(left_layout)
        main_layout.add_widget(self.main_area)

        self.add_widget(main_layout)

    def get_date_from_db(self, record_id):
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT date FROM save WHERE id = ?", (record_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                # Предполагаем, что дата хранится в формате 'YYYY-MM-DD'
                return date.fromisoformat(result[0])
            else:
                raise ValueError("No record found with the given ID.")
        except Exception as e:
            print(f"Error retrieving date from database: {e}")
            return date.today()

    def _update_rect(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _update_main_area_rect(self, instance, value):
        self.rect_main_area.pos = self.main_area.pos
        self.rect_main_area.size = self.main_area.size

    def get_next_tournament_date(self):
        # Получаем дату из базы данных
        date_object = self.get_date_from_db(1)

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        query = '''
            SELECT start_date FROM tournaments
            WHERE start_date >= ?
            ORDER BY start_date ASC
            LIMIT 1
        '''

        cursor.execute(query, (date_object,))
        result = cursor.fetchone()

        conn.close()

        if result:
            return result[0]  # Возвращаем дату следующего турнира
        return None

    def on_next(self, instance):
        self.date_object += timedelta(days=1)
        database = self.db_name
        conn = None
        try:
            conn = sqlite3.connect(database)
            cursor = conn.cursor()

            cursor.execute("UPDATE save SET date = ? WHERE id = 1", (str(self.date_object),))

            # Сохраняем изменения
            conn.commit()
            print(f"Дата успешно обновлена на {self.date_object} в базе данных")

            cursor.execute("SELECT date FROM save WHERE id = 1")
            updated_date = cursor.fetchone()

            if updated_date:
                updated_date_value = updated_date[0]  # Получаем обновленную дату

                # Получаем следующую дату турнира
                next_tournament_date = self.get_next_tournament_date()

                # Проверяем совпадение дат
                if next_tournament_date and updated_date_value == next_tournament_date:
                    # Если даты совпадают, запускаем TournamentPopup
                    self.show_tournament_popup()

                self.today_date_button.text = updated_date_value
        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")
        finally:
            if conn:
                conn.close()



    def on_press(self, instance):
        print(f'Нажата кнопка: {instance.text}')

    def on_incoming(self, instance):
        messages = [
            {'date': '2023-09-20', 'author': 'Владелец команды', 'text': 'Добро пожаловать!'},
            {'date': '2023-09-20', 'author': 'Владелец команды', 'text': f'Рады приветстовать вас на посту менеджера'
                                                                         f' команды {self.get_team_name()}! '},
            {'date': '2023-09-20', 'author': 'Владелец команды', 'text': f'Впереди турнир {self.get_next_tournament()} '
                                                                         f'Желаем удачи! '},
        ]
        show_message(messages)

    def on_roster(self, instance):
        show_squad_popup(self.db_name)

    def on_organization(self, instance):
        show_custom_popup()

    def on_tournaments(self, instance):
        show_custom_popup()

    def on_transfers(self, instance):
        show_custom_popup()

    def on_settings(self, instance):
        SettingsPopup().open()

    def on_profile(self, instance):
        show_custom_popup()

    def on_main_menu(self, instance):
        content = BoxLayout(orientation='vertical')

        label = Button(text='Хотите ли вы выйти в главное меню?', size_hint_y=None, height=44)

        yes_button = Button(text='Да', size_hint_y=None, height=44)
        yes_button.bind(on_press=self.exit_to_main_menu)

        no_button = Button(text='Нет', size_hint_y=None, height=44)
        no_button.bind(on_press=self.close_popup)

        content.add_widget(label)
        content.add_widget(yes_button)
        content.add_widget(no_button)

        self.popup_confirm = Popup(title='Подтверждение', content=content, size_hint=(0.6, 0.4))
        self.popup_confirm.open()

    def exit_to_main_menu(self, instance):
        self.popup_confirm.dismiss()
        self.popup.dismiss()

    def close_popup(self, instance):
        self.popup_confirm.dismiss()

    def get_team_name(self):
        try:
            # Подключение к базе данных
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Выполнение запроса для получения имени команды
            cursor.execute("SELECT name FROM teams WHERE player = 'yes'")
            result = cursor.fetchone()

            # Закрытие соединения
            conn.close()

            return result[0] if result else None

        except sqlite3.Error as e:
            print(f"Ошибка при работе с базой данных: {e}")
            return None

    def get_next_tournament(self):
        # Получаем дату из базы данных
        date_object = self.get_date_from_db(1)

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        query = '''
            SELECT name FROM tournaments
            WHERE start_date >= ?
            ORDER BY start_date ASC
            LIMIT 1
        '''

        cursor.execute(query, (date_object,))
        result = cursor.fetchone()

        conn.close()

        if result:
            return result[0]
        return None

    def show_tournament_popup(self):
        popup = TournamentPopup(self.db_name)
        popup.open()




class DotaPopup(Popup):
    def __init__(self, db_name, **kwargs):
        super(DotaPopup, self).__init__(**kwargs)
        self.title = ""
        self.content = MainWindow(db_name,self)
        self.size_hint = (1, 1)
        self.auto_dismiss = False

    def open_popup(self, db_name):
        DotaPopup(db_name).open()