#!/usr/bin/env python3
"""
Тест исправленной функции get_transcript
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.transcripts import get_transcript
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_transcript_with_url():
    """Тест с полным URL"""
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ"
    ]
    
    for url in test_urls:
        print(f"\n🔍 Тестирование URL: {url}")
        try:
            result = get_transcript(url)
            if isinstance(result, tuple) and len(result) == 3:
                plain_text, fragments, video_info = result
                print(f"✅ Успех! Получен транскрипт:")
                print(f"   📝 Длина текста: {len(plain_text)} символов")
                print(f"   🎬 Фрагментов: {len(fragments)}")
                print(f"   ℹ️ Название: {video_info.get('title', 'Неизвестно')}")
                print(f"   ⏱️ Длительность: {video_info.get('duration', 'Неизвестно')} сек")
                print(f"   📄 Первые 200 символов: {plain_text[:200]}...")
            else:
                print(f"⚠️ Неожиданный формат результата: {type(result)}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

def test_transcript_with_id():
    """Тест с video_id"""
    video_id = "dQw4w9WgXcQ"
    
    print(f"\n🔍 Тестирование video_id: {video_id}")
    try:
        result = get_transcript(video_id)
        if isinstance(result, tuple) and len(result) == 3:
            plain_text, fragments, video_info = result
            print(f"✅ Успех! Получен транскрипт:")
            print(f"   📝 Длина текста: {len(plain_text)} символов")
            print(f"   🎬 Фрагментов: {len(fragments)}")
            print(f"   ℹ️ Название: {video_info.get('title', 'Неизвестно')}")
            print(f"   ⏱️ Длительность: {video_info.get('duration', 'Неизвестно')} сек")
        else:
            print(f"⚠️ Неожиданный формат результата: {type(result)}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    print("🚀 Тестирование исправленной функции get_transcript")
    print("=" * 60)
    
    # Тест с URL
    test_transcript_with_url()
    
    # Тест с video_id
    test_transcript_with_id()
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")

if __name__ == "__main__":
    main()