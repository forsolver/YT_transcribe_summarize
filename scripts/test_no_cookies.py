#!/usr/bin/env python3
"""
Тест получения транскрипта без использования cookies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from youtube_transcript_api import YouTubeTranscriptApi

def test_without_cookies():
    """Тест получения транскрипта без cookies."""
    
    # Тестовые видео - используем популярные видео, которые точно имеют транскрипты
    test_videos = [
        ("dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),  # Rick Roll
        ("9bZkp7q19f0", "PSY - GANGNAM STYLE"),  # Gangnam Style
        ("kJQP7kiw5Fk", "Luis Fonsi - Despacito"),  # Despacito
    ]
    
    print("=== ТЕСТ БЕЗ COOKIES ===\n")
    
    for i, (video_id, title) in enumerate(test_videos, 1):
        print(f"{i}. Тестирование: {title}")
        print(f"   Video ID: {video_id}")
        
        try:
            # Попробуем получить английский транскрипт без cookies
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            print(f"   ✅ Транскрипт получен: {len(transcript)} фрагментов")
            
            if transcript:
                print(f"   📄 Первый фрагмент: {transcript[0].get('text', '')[:50]}...")
                print(f"   ⏱️ Время первого фрагмента: {transcript[0].get('start', 0):.1f}с")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            print(f"   🔍 Тип ошибки: {type(e).__name__}")
        
        print()

def test_moroccan_videos_no_cookies():
    """Тест марокканских видео без cookies."""
    
    # Видео из логов, которые не работают
    test_videos = [
        ("wj6yz01MBho", "SKATE and WILD GOAT in ( Morocco )"),
        ("9UnlpIchBqY", "SKATE in MOROCO for 24 h"),
        ("MYcIsqt_Tsg", "Why skateboarding is for EVERYONE"),
    ]
    
    print("=== ТЕСТ МАРОККАНСКИХ ВИДЕО БЕЗ COOKIES ===\n")
    
    for i, (video_id, title) in enumerate(test_videos, 1):
        print(f"{i}. Тестирование: {title}")
        print(f"   Video ID: {video_id}")
        
        # Сначала попробуем получить список доступных транскриптов
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            print(f"   ✅ Список транскриптов получен")
            
            available_langs = []
            for transcript in transcript_list:
                available_langs.append(f"{transcript.language_code} ({'auto' if transcript.is_generated else 'manual'})")
            print(f"   🌐 Доступные языки: {', '.join(available_langs)}")
            
            # Попробуем получить любой доступный транскрипт
            for transcript_info in transcript_list:
                try:
                    transcript = transcript_info.fetch()
                    print(f"   ✅ Транскрипт на {transcript_info.language_code} получен: {len(transcript)} фрагментов")
                    
                    if transcript:
                        print(f"   📄 Первый фрагмент: {transcript[0].get('text', '')[:50]}...")
                    break
                except Exception as fetch_e:
                    print(f"   ⚠️ Не удалось получить {transcript_info.language_code}: {fetch_e}")
                    continue
            else:
                print(f"   ❌ Ни один транскрипт не удалось получить")
                
        except Exception as e:
            print(f"   ❌ Ошибка получения списка транскриптов: {e}")
            print(f"   🔍 Тип ошибки: {type(e).__name__}")
        
        print()

if __name__ == "__main__":
    test_without_cookies()
    test_moroccan_videos_no_cookies()