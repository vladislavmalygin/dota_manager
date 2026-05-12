import subprocess
import logging

# Настраиваем логирование
logging.basicConfig(filename='output.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Путь к вашему файлу formats.py
script_path = 'formats.py'

# Выполняем скрипт 1000 раз
for i in range(1000):
    try:
        # Запускаем скрипт и захватываем вывод
        result = subprocess.run(['python', script_path], capture_output=True, text=True)

        # Логируем вывод скрипта
        logging.info(result.stdout.strip())

        # Логируем ошибки, если они есть
        if result.stderr:
            logging.error(result.stderr.strip())

    except Exception as e:
        logging.error(f'Ошибка при выполнении скрипта: {e}')
