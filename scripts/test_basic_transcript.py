#!/usr/bin/env python3
"""
Базовый тест получения транскрипта без сложной логики.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from youtube_transcript_api import YouTubeTranscriptApi

def test_basic_transcript():
    """Тест базового получения транскрипта через youtube-transcript-api."""
    
    # Тестовые видео
    test_videos = [
        "wj6yz01MBho",  # SKATE and WILD GOAT in ( Morocco )
        "MYcIsqt_Tsg",  # Why skateboarding is for EVERYONE
        "dQw4w9WgXcQ",  # Rick Roll (популярное видео)
    ]
    
    print("=== БАЗОВЫЙ ТЕСТ ПОЛУЧЕНИЯ ТРАНСКРИПТА ===\n")
    
    # Проверим cookies
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", "cookies.txt")
    cookies_param = cookies_file if os.path.exists(cookies_file) else None
    
    print(f"Cookies файл: {cookies_file}")
    print(f"Cookies найден: {'Да' if cookies_param else 'Нет'}")
    print()
    
    for i, video_id in enumerate(test_videos, 1):
        print(f"{i}. Тестирование видео ID: {video_id}")
        
        # Тест 1: Получение списка доступных транскриптов
        print(f"   Получение списка транскриптов...")
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies_param)
            print(f"   ✅ Список транскриптов получен")
            
            # Покажем доступные языки
            available_langs = []
            for transcript in transcript_list:
                available_langs.append(transcript.language_code)
            print(f"   🌐 Доступные языки: {', '.join(available_langs)}")
            
        except Exception as e:
            print(f"   ❌ Ошибка получения списка: {e}")
            print(f"   🔍 Тип ошибки: {type(e).__name__}")
            continue
        
        # Тест 2: Попытка получить русский транскрипт
        print(f"   Попытка получить русский транскрипт...")
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru'], cookies=cookies_param)
            print(f"   ✅ Русский транскрипт получен: {len(transcript)} фрагментов")
            
            if transcript:
                print(f"   📄 Первый фрагмент: {transcript[0].get('text', '')[:50]}...")
            
        except Exception as e:
            print(f"   ⚠️ Русский транскрипт недоступен: {e}")
            
            # Тест 3: Попытка получить английский транскрипт
            print(f"   Попытка получить английский транскрипт...")
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'], cookies=cookies_param)
                print(f"   ✅ Английский транскрипт получен: {len(transcript)} фрагментов")
                
                if transcript:
                    print(f"   📄 Первый фрагмент: {transcript[0].get('text', '')[:50]}...")
                
            except Exception as e:
                print(f"   ❌ Английский транскрипт тоже недоступен: {e}")
                
                # Тест 4: Попытка получить любой доступный транскрипт
                print(f"   Попытка получить любой доступный транскрипт...")
                try:
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
                    print(f"   ❌ Ошибка при переборе транскриптов: {e}")
        
        print()

if __name__ == "__main__":
    test_basic_transcript()