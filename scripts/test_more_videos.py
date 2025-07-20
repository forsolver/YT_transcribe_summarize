#!/usr/bin/env python3
"""
Тест дополнительных видео для подтверждения исправления.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.transcripts import get_transcript

def test_more_videos():
    """Тест дополнительных видео."""
    
    # Тестовые видео - используем разные, чтобы избежать 429 ошибок
    test_videos = [
        ("dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),  # Популярное видео
        ("9bZkp7q19f0", "PSY - GANGNAM STYLE"),  # Еще одно популярное
        ("kJQP7kiw5Fk", "Luis Fonsi - Despacito"),  # И еще одно
    ]
    
    print("=== ТЕСТ ДОПОЛНИТЕЛЬНЫХ ВИДЕО ===\n")
    
    success_count = 0
    
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
            
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
            print(f"   🔍 Тип ошибки: {type(e).__name__}")
        
        print()
    
    print(f"=== РЕЗУЛЬТАТ: {success_count}/{len(test_videos)} видео успешно ===")
    
    if success_count >= 2:
        print("🎉 ИСПРАВЛЕНИЕ РАБОТАЕТ! Основная функциональность восстановлена.")
    elif success_count >= 1:
        print("⚠️ Частичный успех. Некоторые видео могут иметь ограничения.")
    else:
        print("❌ Проблема не решена полностью.")

if __name__ == "__main__":
    test_more_videos()