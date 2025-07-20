#!/usr/bin/env python3
"""
Быстрый тест исправления проблемы с транскриптами.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.transcripts import get_transcript

def test_quick_fix():
    """Быстрый тест исправления."""
    
    # Тестовые видео - используем те, которые работали раньше
    test_videos = [
        ("Tvu4bWh_GLM", "Australian Skater Mia Kretzer is Incredible 🇦🇺"),  # Это работало в 12:30
        ("MYcIsqt_Tsg", "Why skateboarding is for EVERYONE"),  # Это тоже работало
    ]
    
    print("=== БЫСТРЫЙ ТЕСТ ИСПРАВЛЕНИЯ ===\n")
    
    for i, (video_id, title) in enumerate(test_videos, 1):
        print(f"{i}. Тестирование: {title}")
        print(f"   Video ID: {video_id}")
        
        try:
            # Пробуем получить транскрипт
            plain_text, fragments, video_info = get_transcript(video_id)
            
            print(f"   ✅ УСПЕХ! Транскрипт получен")
            print(f"   📝 Длина текста: {len(plain_text)} символов")
            print(f"   📋 Фрагментов: {len(fragments)}")
            print(f"   🎬 Название: {video_info.get('title', 'Неизвестно')}")
            
            if plain_text:
                print(f"   📄 Первые 50 символов: {plain_text[:50]}...")
            
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
            print(f"   🔍 Тип ошибки: {type(e).__name__}")
        
        print()

if __name__ == "__main__":
    test_quick_fix()