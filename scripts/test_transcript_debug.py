#!/usr/bin/env python3
"""
Отладочный скрипт для проверки получения транскрипта.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from ytsummarizer.transcripts import get_transcript, get_video_info

# Настройка подробного логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_single_transcript():
    """Тест получения транскрипта от одного видео."""
    
    # Тестовые видео из логов
    test_videos = [
        "wj6yz01MBho",  # SKATE and WILD GOAT in ( Morocco )
        "9UnlpIchBqY",  # SKATE in MOROCO for 24 h
        "MYcIsqt_Tsg",  # Why skateboarding is for EVERYONE (это видео работало раньше)
    ]
    
    print("=== ОТЛАДКА ПОЛУЧЕНИЯ ТРАНСКРИПТА ===\n")
    
    for i, video_id in enumerate(test_videos, 1):
        print(f"{i}. Тестирование видео ID: {video_id}")
        
        # Сначала проверим информацию о видео
        print(f"   Получение информации о видео...")
        try:
            video_info = get_video_info(video_id)
            print(f"   📹 Название: {video_info.get('title', 'Неизвестно')}")
            print(f"   ⏱️ Длительность: {video_info.get('duration', 'Неизвестно')}с")
            print(f"   🔞 Возрастное ограничение: {video_info.get('age_limit', 0)}")
            print(f"   🔒 Доступность: {video_info.get('availability', 'Неизвестно')}")
            
            if video_info.get('error'):
                print(f"   ❌ Ошибка в video_info: {video_info['error']}")
            else:
                print(f"   ✅ Информация о видео получена")
        except Exception as e:
            print(f"   ❌ Исключение при получении info: {e}")
        
        # Теперь попробуем получить транскрипт
        print(f"   Получение транскрипта...")
        try:
            plain_text, fragments, video_info = get_transcript(video_id)
            print(f"   ✅ Транскрипт получен успешно!")
            print(f"   📝 Длина текста: {len(plain_text)} символов")
            print(f"   📋 Фрагментов: {len(fragments)}")
            print(f"   🎬 Название из транскрипта: {video_info.get('title', 'Неизвестно')}")
            
            if plain_text:
                print(f"   📄 Первые 100 символов: {plain_text[:100]}...")
            
        except Exception as e:
            print(f"   ❌ Ошибка получения транскрипта: {e}")
            print(f"   🔍 Тип ошибки: {type(e).__name__}")
            
            # Попробуем получить более подробную информацию об ошибке
            import traceback
            print(f"   📋 Полная трассировка:")
            traceback.print_exc()
        
        print()

def test_cookies():
    """Проверка наличия и использования cookies."""
    print("=== ПРОВЕРКА COOKIES ===\n")
    
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", "cookies.txt")
    print(f"Путь к cookies: {cookies_file}")
    
    if os.path.exists(cookies_file):
        print(f"✅ Файл cookies найден")
        
        # Проверим размер файла
        file_size = os.path.getsize(cookies_file)
        print(f"📊 Размер файла: {file_size} байт")
        
        # Проверим дату модификации
        import datetime
        mod_time = os.path.getmtime(cookies_file)
        mod_date = datetime.datetime.fromtimestamp(mod_time)
        print(f"📅 Последнее изменение: {mod_date}")
        
        # Проверим первые несколько строк (без показа содержимого)
        try:
            with open(cookies_file, 'r') as f:
                lines = f.readlines()
                print(f"📄 Строк в файле: {len(lines)}")
                
                # Проверим, есть ли строки с youtube.com
                youtube_lines = [line for line in lines if 'youtube.com' in line.lower()]
                print(f"🎬 Строк с youtube.com: {len(youtube_lines)}")
        except Exception as e:
            print(f"❌ Ошибка чтения cookies: {e}")
    else:
        print(f"❌ Файл cookies не найден")
        print(f"💡 Создайте файл cookies.txt или установите переменную YOUTUBE_COOKIES_FILE")

if __name__ == "__main__":
    test_cookies()
    print()
    test_single_transcript()