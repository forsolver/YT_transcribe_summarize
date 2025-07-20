#!/usr/bin/env python3
"""
Тест UI с функциональностью выбора папки
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt5.QtWidgets import QApplication
from ytsummarizer.ui import YouTubeSummarizerUI

def main():
    print("🚀 Запуск UI с функциональностью выбора папки")
    print("=" * 60)
    print("Инструкции для тестирования:")
    print("1. Проверьте, что отображается текущая папка сохранения")
    print("2. Нажмите 'Выбрать папку' и выберите другую папку")
    print("3. Убедитесь, что путь обновился в интерфейсе")
    print("4. Попробуйте обработать видео - файлы должны сохраниться в выбранной папке")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # Создаем главное окно
    window = YouTubeSummarizerUI()
    window.show()
    
    # Выводим информацию о текущей папке
    current_folder = window.get_output_folder()
    print(f"📁 Текущая папка сохранения: {current_folder}")
    
    # Запускаем приложение
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())