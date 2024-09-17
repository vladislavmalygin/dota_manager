from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle
from kivy.uix.image import Image

# Создаем постоянный интерфейс
class MainWindow(BoxLayout):
    def __init__(self, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.orientation = 'vertical'

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
        buttons = ['Входящие', 'Состав', 'Организация', 'Турниры', 'Трансферы', 'Настройки', 'Мой профиль', 'Главное меню']
        for btn_text in buttons:
            button = Button(text=btn_text, background_color=(0.4, 0.4, 0.8, 0.8))
            left_layout.add_widget(button)

        # Создаем основной область экрана для переменного контента
        self.main_area = BoxLayout(size_hint_x=0.8)

        # Добавляем левую часть и основную область к главному окну
        main_layout = BoxLayout(orientation='horizontal')
        main_layout.add_widget(left_layout)
        main_layout.add_widget(self.main_area)

        self.add_widget(main_layout)

    def _update_rect(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_next(self, instance):
        # Логика для кнопки "Далее" будет здесь
        print('Переход к следующему шагу')

    # Обработчик для нажатия кнопки
    def on_press(self, instance):
        print(f'Нажата кнопка: {instance.text}')

# Создаем приложение
class DotaManagerApp(App):
    def build(self):
        return MainWindow()

# Запуск приложения
if __name__ == '__main__':
    DotaManagerApp().run()