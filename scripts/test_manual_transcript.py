#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности ручного ввода транскрипта.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt5.QtWidgets import QApplication
from ytsummarizer.ui import YouTubeSummarizerUI, ManualTranscriptDialog

def test_manual_transcript_dialog():
    """Тест диалога ручного ввода транскрипта."""
    app = QApplication(sys.argv)
    
    # Создаем диалог
    dialog = ManualTranscriptDialog(None, "https://youtu.be/test_video")
    
    print("Диалог создан успешно!")
    print("Запуск диалога...")
    
    # Показываем диалог
    result = dialog.exec_()
    
    if result == dialog.Accepted:
        fragments, video_info = dialog.get_transcript_data()
        print(f"\nПолучены данные:")
        print(f"Название видео: {video_info.get('title')}")
        print(f"Длительность: {video_info.get('duration')} сек")
        print(f"Количество фрагментов: {len(fragments)}")
        
        if fragments:
            print("\nПервые 3 фрагмента:")
            for i, fragment in enumerate(fragments[:3]):
                print(f"  {i+1}. Время: {fragment.get('start')}с")
                print(f"     Текст: {fragment.get('text')[:100]}...")
    else:
        print("Диалог отменен пользователем")

def test_transcript_parsing():
    """Тест парсинга транскрипта."""
    app = QApplication([])  # Минимальное приложение для тестирования
    
    dialog = ManualTranscriptDialog()
    
    # Тестовый транскрипт
    test_transcript = """0:00
привет всем сегодня я покажу вам новый трюк
0:15
сначала нужно взять доску и поставить ее вот так
0:30
теперь делаем олли и сразу же поворачиваем доску
1:00
вот так получается kickflip
1:15
попробуйте сами и увидите как это работает"""
    
    fragments = dialog.parse_manual_transcript(test_transcript)
    
    print("Тест парсинга транскрипта:")
    print(f"Количество фрагментов: {len(fragments)}")
    
    for i, fragment in enumerate(fragments):
        print(f"  {i+1}. Время: {fragment.get('start')}с")
        print(f"     Текст: {fragment.get('text')}")
    
    # Тест оценки длительности
    duration = dialog.estimate_duration_from_fragments(fragments)
    print(f"\nОценочная длительность: {duration:.1f} сек")

if __name__ == "__main__":
    print("=== Тест парсинга транскрипта ===")
    test_transcript_parsing()
    
    print("\n=== Тест диалога (интерактивный) ===")
    print("Запуск интерактивного теста диалога...")
    print("Введите тестовый транскрипт и нажмите OK для проверки")
    test_manual_transcript_dialog()