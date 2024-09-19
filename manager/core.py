from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle

from manager.settings import SettingsPopup

class MainWindow(BoxLayout):
    def __init__(self, db_name=None, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.db_name = db_name

        # Установка фона с изображением
        with self.canvas.before:
            Color(1, 1, 1, 0.5)  # Белый цвет фона
            self.rect = Rectangle(source='images/core1.png', pos=self.pos, size=self.size)

        # Обновление размера прямоугольника при изменении размера окна
        self.bind(size=self._update_rect, pos=self._update_rect)

        # Верхняя часть интерфейса
        top_layout = GridLayout(cols=5, size_hint_y=0.1)

        # Добавляем кнопки в верхнюю часть с цветами
        top_layout.add_widget(Button(text='Dota Manager', background_color=(0.2, 0.6, 0.8, 1), on_press=self.on_press))
        top_layout.add_widget(Button(text='Team Name', background_color=(0.2, 0.8, 0.2, 1), on_press=self.on_press))
        top_layout.add_widget(Button(text='Next Tournament', background_color=(0.8, 0.2, 0.2, 1), on_press=self.on_press))
        top_layout.add_widget(Button(text='Дата: 1.01.2024', background_color=(0.5, 0.5, 0.2, 1), on_press=self.on_press))
        top_layout.add_widget(Button(text='Далее', background_color=(0.8, 0.8, 0.2, 1), on_press=self.on_next))

        # Добавляем верхнюю часть в основной макет
        self.add_widget(top_layout)

        # Основное содержание графического интерфейса
        main_content = BoxLayout()
        self.add_widget(main_content)

        # Левая часть
        left_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 2))

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

        # Добавляем левую часть и основную область к главному окну
        main_layout = BoxLayout(orientation='horizontal')
        main_layout.add_widget(left_layout)
        main_layout.add_widget(self.main_area)

        self.add_widget(main_layout)

        if self.db_name:
            print(f'Используется база данных: {self.db_name}')

    def _update_rect(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_next(self, instance):
        print('Переход к следующему шагу')

    def on_press(self, instance):
        print(f'Нажата кнопка: {instance.text}')

    def on_incoming(self, instance):
        print('Открытие входящих сообщений')

    def on_roster(self, instance):
        print('Показ состава команды')

    def on_organization(self, instance):
        print('Информация об организации')

    def on_tournaments(self, instance):
        print('Список турниров')

    def on_transfers(self, instance):
        print('Информация о трансферах')

    def on_settings(self, instance):
        SettingsPopup().open()

    def on_profile(self, instance):
        print('Мой профиль')

    def on_main_menu(self, instance):
        print('Возврат в главное меню')


class DotaPopup(Popup):
    def __init__(self, db_name=None, **kwargs):
        super(DotaPopup, self).__init__(**kwargs)
        self.title = ""  # Убираем заголовок
        self.content = MainWindow(db_name=db_name)
        self.size_hint = (1, 1)  # Занимает всё пространство
        self.auto_dismiss = True


class DotaApp(App):
    def build(self):
        # Создаем кнопку для открытия всплывающего окна
        button = Button(text="Открыть Dota Manager", on_press=lambda x: self.open_popup("my_database.db"))
        return button

    def open_popup(self, db_name):
        DotaPopup(db_name=db_name).open()


# Запуск приложения
if __name__ == '__main__':
    DotaApp().run()