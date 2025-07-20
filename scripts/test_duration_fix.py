#!/usr/bin/env python3
"""
Тест исправления проблемы с duration в ручных транскриптах.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt5.QtWidgets import QApplication
from ytsummarizer.ui import ManualTranscriptDialog
from ytsummarizer import video_processor as vp

def test_duration_fix():
    """Тест исправления проблемы с duration."""
    app = QApplication([])
    
    dialog = ManualTranscriptDialog()
    
    # Тестовый транскрипт с временными метками
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
    
    print("=== ТЕСТ ИСПРАВЛЕНИЯ DURATION ===\n")
    
    # Парсим транскрипт
    fragments = dialog.parse_manual_transcript(test_transcript)
    
    print("1. Проверка фрагментов с duration:")
    for i, fragment in enumerate(fragments):
        print(f"   {i+1}. Время: {fragment['start']}с, Длительность: {fragment.get('duration', 'НЕТ')}с")
        print(f"      Текст: {fragment['text'][:50]}...")
    
    # Проверяем, что все фрагменты имеют поле duration
    all_have_duration = all('duration' in f for f in fragments)
    print(f"\n2. Все фрагменты имеют поле 'duration': {all_have_duration}")
    
    # Тестируем анализ трюков
    print("\n3. Тестирование анализа трюков...")
    try:
        trick_segments = vp.extract_trick_segments(fragments)
        print(f"   ✅ Анализ трюков прошел успешно!")
        print(f"   Найдено трюков: {len(trick_segments)}")
        
        for i, seg in enumerate(trick_segments, 1):
            print(f"   Трюк {i}: {seg['start']:.1f}с - {seg['end']:.1f}с (длительность: {seg['duration']:.1f}с)")
            
    except Exception as e:
        print(f"   ❌ Ошибка при анализе трюков: {e}")
        return False
    
    print("\n=== ТЕСТ ЗАВЕРШЕН УСПЕШНО ===")
    return True

if __name__ == "__main__":
    success = test_duration_fix()
    if success:
        print("\n✅ Исправление работает корректно!")
    else:
        print("\n❌ Исправление требует доработки!")