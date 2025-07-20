#!/usr/bin/env python3
"""
Демонстрационный скрипт для показа функциональности ручного ввода транскрипта.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.ui import ManualTranscriptDialog
from ytsummarizer import video_processor as vp

def demo_manual_transcript():
    """Демонстрация обработки ручного транскрипта."""
    
    # Пример транскрипта скейт-видео
    sample_transcript = """0:00
привет всем меня зовут Макс и сегодня я покажу вам как делать kickflip
0:10
сначала нужно правильно поставить ноги на доску
0:20
передняя нога должна быть примерно в середине доски
0:30
а задняя нога на тейле вот так
0:45
теперь самое главное это движение
1:00
делаем олли и одновременно поворачиваем доску пальцем передней ноги
1:30
вот смотрите как это выглядит
2:00
попробуйте сами несколько раз
2:15
не расстраивайтесь если не получается с первого раза
2:30
это нормально для такого сложного трюка
2:45
продолжайте тренироваться и у вас обязательно получится
3:00
увидимся в следующем видео удачи"""

    print("=== ДЕМОНСТРАЦИЯ РУЧНОГО ВВОДА ТРАНСКРИПТА ===\n")
    
    # Создаем диалог (без GUI для демонстрации)
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    
    dialog = ManualTranscriptDialog()
    
    # Парсим тестовый транскрипт
    print("1. Парсинг транскрипта...")
    fragments = dialog.parse_manual_transcript(sample_transcript)
    print(f"   Найдено фрагментов: {len(fragments)}")
    
    # Показываем первые несколько фрагментов
    print("\n2. Первые 5 фрагментов:")
    for i, fragment in enumerate(fragments[:5]):
        print(f"   {i+1}. {fragment['start']}с: {fragment['text'][:50]}...")
    
    # Оценка длительности
    duration = dialog.estimate_duration_from_fragments(fragments)
    print(f"\n3. Оценочная длительность: {duration:.1f} секунд")
    
    # Создаем информацию о видео
    video_info = {
        'title': 'Как делать Kickflip - Урок скейтбординга',
        'duration': duration
    }
    
    print(f"\n4. Информация о видео:")
    print(f"   Название: {video_info['title']}")
    print(f"   Длительность: {video_info['duration']:.1f}с")
    
    # Анализ трюков
    print("\n5. Анализ трюков...")
    try:
        trick_segments = vp.extract_trick_segments(fragments)
        print(f"   Найдено трюков: {len(trick_segments)}")
        
        if trick_segments:
            print("\n6. Детали найденных трюков:")
            for i, seg in enumerate(trick_segments, 1):
                start_min = int(seg['start'] // 60)
                start_sec = int(seg['start'] % 60)
                end_min = int(seg['end'] // 60)
                end_sec = int(seg['end'] % 60)
                duration_sec = int(seg['duration'])
                
                print(f"   Трюк {i}: {start_min}:{start_sec:02d} - {end_min}:{end_sec:02d} (длительность: {duration_sec}с)")
        else:
            print("   Трюки не найдены (возможно, слишком много речи)")
            
    except Exception as e:
        print(f"   Ошибка при анализе трюков: {e}")
    
    print("\n=== ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА ===")
    print("\nВ реальном приложении:")
    print("- Пользователь вводит транскрипт через GUI диалог")
    print("- Все функции (саммари, анализ, скачивание) работают с ручными транскриптами")
    print("- Поддерживаются различные форматы транскриптов")

if __name__ == "__main__":
    demo_manual_transcript()