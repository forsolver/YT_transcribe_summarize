#!/usr/bin/env python3
"""
Тестовый скрипт для проверки извлечения видео из плейлистов с улучшенной обработкой ошибок.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.transcripts import extract_video_list, get_source_metadata
from ytsummarizer.url_detector import URLDetector, URLType

def test_playlist_extraction():
    """Тест извлечения видео из плейлиста."""
    
    # Тестовые URL плейлистов
    test_urls = [
        "https://www.youtube.com/playlist?list=PLH2zHj82u-TGLmVvSP2xbVrsRAdDxAYRl",  # SKATE MORROCO 2022
        "https://www.youtube.com/playlist?list=PLH2zHj82u-TH8uhGEqP1xJIa89Henwvsw",  # EAST ASIA
        "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy8VkXKhp4XZYGKzJd7QvvQ",  # Популярный плейлист (если доступен)
    ]
    
    print("=== ТЕСТ ИЗВЛЕЧЕНИЯ ВИДЕО ИЗ ПЛЕЙЛИСТОВ ===\n")
    
    detector = URLDetector()
    
    for i, url in enumerate(test_urls, 1):
        print(f"{i}. Тестирование плейлиста: {url}")
        
        # Проверяем тип URL
        url_type = detector.detect_url_type(url)
        print(f"   Тип URL: {url_type}")
        
        if url_type != URLType.PLAYLIST:
            print(f"   ❌ Неподдерживаемый тип URL")
            continue
        
        # Получаем метаданные источника
        print(f"   Получение метаданных...")
        try:
            source_info = get_source_metadata(url)
            if source_info:
                print(f"   📋 Название: {source_info.name}")
                print(f"   📊 Всего видео: {source_info.total_videos}")
            else:
                print(f"   ❌ Не удалось получить метаданные")
                continue
        except Exception as e:
            print(f"   ❌ Ошибка получения метаданных: {e}")
            continue
        
        # Извлекаем список видео
        print(f"   Извлечение списка видео (лимит: 10)...")
        try:
            videos = extract_video_list(url, limit=10)
            print(f"   ✅ Извлечено видео: {len(videos)}")
            
            if videos:
                print(f"   📹 Первые видео:")
                for j, video in enumerate(videos[:3], 1):
                    duration_str = f"{video.duration}s" if video.duration else "неизвестно"
                    print(f"      {j}. {video.title} ({duration_str})")
                
                if len(videos) > 3:
                    print(f"      ... и еще {len(videos) - 3} видео")
            else:
                print(f"   ⚠️ Видео не найдены")
                
        except Exception as e:
            print(f"   ❌ Ошибка извлечения видео: {e}")
        
        print()
    
    print("=== ТЕСТ ЗАВЕРШЕН ===")

def test_single_video_info():
    """Тест получения информации об отдельном видео."""
    from ytsummarizer.transcripts import get_video_info
    
    print("\n=== ТЕСТ ИНФОРМАЦИИ О ВИДЕО ===\n")
    
    # Тестовые видео
    test_videos = [
        "MYcIsqt_Tsg",  # Обычное видео
        "dQw4w9WgXcQ",  # Rick Roll (популярное видео)
        "invalid_id",   # Несуществующий ID
    ]
    
    for i, video_id in enumerate(test_videos, 1):
        print(f"{i}. Тестирование видео ID: {video_id}")
        
        try:
            info = get_video_info(video_id)
            print(f"   📹 Название: {info.get('title', 'Неизвестно')}")
            print(f"   ⏱️ Длительность: {info.get('duration', 'Неизвестно')}с")
            print(f"   🔞 Возрастное ограничение: {info.get('age_limit', 0)}")
            print(f"   🔒 Доступность: {info.get('availability', 'Неизвестно')}")
            
            if info.get('error'):
                print(f"   ❌ Ошибка: {info['error']}")
            else:
                print(f"   ✅ Информация получена успешно")
                
        except Exception as e:
            print(f"   ❌ Исключение: {e}")
        
        print()

if __name__ == "__main__":
    test_playlist_extraction()
    test_single_video_info()