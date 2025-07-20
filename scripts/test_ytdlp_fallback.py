#!/usr/bin/env python3
"""
Тест fallback метода получения транскрипта через yt-dlp
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.transcripts import _get_transcript_via_ytdlp
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_ytdlp_fallback():
    """Тест fallback метода через yt-dlp"""
    video_id = "dQw4w9WgXcQ"
    lang_priorities = ("ru", "en")
    
    print(f"🔍 Тестирование fallback через yt-dlp")
    print(f"   Video ID: {video_id}")
    print(f"   Языки: {lang_priorities}")
    
    try:
        transcript, used_lang = _get_transcript_via_ytdlp(video_id, lang_priorities)
        
        if transcript:
            print(f"✅ Успех! Получен транскрипт через yt-dlp:")
            print(f"   🌐 Язык: {used_lang}")
            print(f"   🎬 Фрагментов: {len(transcript)}")
            print(f"   📄 Первые 3 фрагмента:")
            for i, fragment in enumerate(transcript[:3]):
                print(f"      {i+1}. [{fragment['start']:.1f}s] {fragment['text'][:100]}...")
        else:
            print(f"❌ Fallback через yt-dlp не сработал")
            
    except Exception as e:
        print(f"❌ Ошибка в fallback методе: {e}")
        import traceback
        traceback.print_exc()

def test_different_video():
    """Тест с менее популярным видео"""
    # Попробуем с менее популярным видео
    video_id = "9bZkp7q19f0"  # PSY - GANGNAM STYLE
    lang_priorities = ("en", "ru")
    
    print(f"\n🔍 Тестирование с другим видео")
    print(f"   Video ID: {video_id}")
    print(f"   Языки: {lang_priorities}")
    
    try:
        transcript, used_lang = _get_transcript_via_ytdlp(video_id, lang_priorities)
        
        if transcript:
            print(f"✅ Успех! Получен транскрипт:")
            print(f"   🌐 Язык: {used_lang}")
            print(f"   🎬 Фрагментов: {len(transcript)}")
            print(f"   📄 Первые 3 фрагмента:")
            for i, fragment in enumerate(transcript[:3]):
                print(f"      {i+1}. [{fragment['start']:.1f}s] {fragment['text'][:100]}...")
        else:
            print(f"❌ Не удалось получить транскрипт")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🚀 Тестирование fallback методов получения транскрипта")
    print("=" * 60)
    
    # Тест основного fallback
    test_ytdlp_fallback()
    
    # Тест с другим видео
    test_different_video()
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено")

if __name__ == "__main__":
    main()