import sys
import logging
import os
from PyQt5.QtWidgets import QApplication

from .ui import YouTubeSummarizerUI
from .logging_config import setup_application_logging

# Настройка логирования для всего приложения
def setup_logging():
    """Настраивает логирование для всего приложения."""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Use the comprehensive logging configuration
    setup_application_logging(log_level="DEBUG")
    
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