#!/usr/bin/env python3
"""
Тест нашей функции get_transcript после отката изменений.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from ytsummarizer.transcripts import get_transcript

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_our_get_transcript():
    """Тест нашей функции get_transcript."""
    
    # Тестовые видео
    test_videos = [
        ("dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),  # Популярное видео
        ("MYcIsqt_Tsg", "Why skateboarding is for EVERYONE"),     # Видео, которое работало раньше
        ("wj6yz01MBho", "SKATE and WILD GOAT in ( Morocco )"),    # Проблемное видео из логов
    ]
    
    print("=== ТЕСТ НАШЕЙ ФУНКЦИИ GET_TRANSCRIPT ===\n")
    
    for i, (video_id, title) in enumerate(test_videos, 1):
        print(f"{i}. Тестирование: {title}")
        print(f"   Video ID: {video_id}")
        
        try:
            # Используем нашу функцию get_transcript
            plain_text, fragments, video_info = get_transcript(video_id)
            
            print(f"   ✅ Транскрипт получен успешно!")
            print(f"   📝 Длина текста: {len(plain_text)} символов")
            print(f"   📋 Фрагментов: {len(fragments)}")
            print(f"   🎬 Название: {video_info.get('title', 'Неизвестно')}")
            print(f"   ⏱️ Длительность: {video_info.get('duration', 'Неизвестно')}с")
            
            if plain_text:
                print(f"   📄 Первые 100 символов: {plain_text[:100]}...")
            
            if fragments:
                print(f"   🎯 Первый фрагмент: start={fragments[0].get('start', 0):.1f}с, "
                      f"duration={fragments[0].get('duration', 0):.1f}с")
                print(f"   📝 Текст первого фрагмента: {fragments[0].get('text', '')[:50]}...")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            print(f"   🔍 Тип ошибки: {type(e).__name__}")
            
            # Подробная трассировка для отладки
            import traceback
            print(f"   📋 Трассировка:")
            traceback.print_exc()
        
        print()

def test_with_and_without_cache():
    """Тест с кэшем и без кэша."""
    
    print("=== ТЕСТ С КЭШЕМ И БЕЗ КЭША ===\n")
    
    video_id = "dQw4w9WgXcQ"  # Rick Roll
    
    print("1. Тест БЕЗ кэша:")
    try:
        plain_text, fragments, video_info = get_transcript(video_id, use_cache=False)
        print(f"   ✅ Без кэша: {len(plain_text)} символов, {len(fragments)} фрагментов")
    except Exception as e:
        print(f"   ❌ Ошибка без кэша: {e}")
    
    print("\n2. Тест С кэшем:")
    try:
        plain_text, fragments, video_info = get_transcript(video_id, use_cache=True)
        print(f"   ✅ С кэшем: {len(plain_text)} символов, {len(fragments)} фрагментов")
    except Exception as e:
        print(f"   ❌ Ошибка с кэшем: {e}")

if __name__ == "__main__":
    test_our_get_transcript()
    print()
    test_with_and_without_cache()