import sys
import logging
from PyQt5.QtWidgets import QApplication

from .ui import YouTubeSummarizerUI

# Настройка логирования для всего приложения
def setup_logging():
    """Настраивает логирование для всего приложения."""
    # Создаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Создаем форматтер для логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчик к корневому логгеру
    root_logger.addHandler(console_handler)
    
    # Создаем файловый обработчик для записи логов в файл
    file_handler = logging.FileHandler('ytsummarizer.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Логируем начало работы приложения
    logging.info("YouTube Tools application starting")


def main():
    # Настраиваем логирование
    setup_logging()
    
    # Запускаем приложение
    app = QApplication(sys.argv)
    window = YouTubeSummarizerUI()
    window.show()
    
    logging.info("Application UI displayed")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 