"""
Test UI logging to see if it works
"""

import sys
import os
import logging

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging like in the app
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
    logging.info("Test logging setup complete")

def test_ui_logging():
    """Test if UI logging works."""
    setup_logging()
    
    # Create UI logger like in the actual UI
    logger = logging.getLogger("ytsummarizer.ui")
    
    print("Testing UI logging...")
    
    # Test various log levels
    logger.debug("This is a DEBUG message from UI")
    logger.info("This is an INFO message from UI")
    logger.warning("This is a WARNING message from UI")
    logger.error("This is an ERROR message from UI")
    
    # Test URL detection simulation
    test_url = "https://www.youtube.com/watch?v=Tvu4bWh_GLM&list=PLH2zHj82u-TEEialbg-4t9q7izl2ZD9uC"
    logger.info(f"Processing URL: {test_url}")
    
    from ytsummarizer.url_detector import URLDetector, URLType
    detector = URLDetector()
    url_type = detector.detect_url_type(test_url)
    logger.info(f"Detected URL type: {url_type}")
    
    if url_type == URLType.PLAYLIST:
        logger.info("Using batch processing")
    else:
        logger.info("Using single video processing")
    
    print("✅ UI logging test completed!")
    print("Check ytsummarizer.log file for the log entries.")

if __name__ == "__main__":
    test_ui_logging()