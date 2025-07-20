#!/usr/bin/env python3
"""
Детальная диагностика работы yt-dlp для получения субтитров
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yt_dlp
import requests
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def test_ytdlp_info():
    """Тест получения информации через yt-dlp"""
    video_id = "dQw4w9WgXcQ"
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    print(f"🔍 Тестирование yt-dlp для получения субтитров")
    print(f"   URL: {url}")
    
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["ru", "en"],
        "quiet": False,  # Включаем вывод для диагностики
        "nocheckcertificate": True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("📥 Получение информации о видео...")
            info = ydl.extract_info(url, download=False)
            
            print(f"✅ Информация получена:")
            print(f"   📺 Название: {info.get('title')}")
            print(f"   ⏱️ Длительность: {info.get('duration')} сек")
            
            # Проверяем доступные субтитры
            subtitles = info.get("subtitles", {})
            auto_captions = info.get("automatic_captions", {})
            
            print(f"   📝 Ручные субтитры: {list(subtitles.keys())}")
            print(f"   🤖 Автосубтитры: {list(auto_captions.keys())}")
            
            # Пробуем скачать субтитры
            for lang in ["ru", "en"]:
                print(f"\n🔍 Проверка субтитров на языке: {lang}")
                
                subs = None
                if lang in subtitles:
                    subs = subtitles[lang]
                    print(f"   ✅ Найдены ручные субтитры")
                elif lang in auto_captions:
                    subs = auto_captions[lang]
                    print(f"   ✅ Найдены автосубтитры")
                else:
                    print(f"   ❌ Субтитры не найдены")
                    continue
                
                if subs:
                    print(f"   📋 Доступные форматы: {len(subs)}")
                    for i, track in enumerate(subs):
                        print(f"      {i+1}. {track.get('ext', 'unknown')} - {track.get('url', 'no url')[:100]}...")
                        
                        # Пробуем скачать первый трек
                        if i == 0:
                            try:
                                print(f"   📥 Попытка скачать субтитры...")
                                response = requests.get(track["url"], timeout=15)
                                if response.status_code == 200:
                                    content = response.text
                                    print(f"   ✅ Субтитры скачаны: {len(content)} символов")
                                    print(f"   📄 Первые 300 символов:")
                                    print(f"      {content[:300]}...")
                                    return True
                                else:
                                    print(f"   ❌ Ошибка скачивания: {response.status_code}")
                            except Exception as e:
                                print(f"   ❌ Ошибка при скачивании: {e}")
            
            return False
            
    except Exception as e:
        print(f"❌ Ошибка yt-dlp: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Детальная диагностика yt-dlp для субтитров")
    print("=" * 60)
    
    success = test_ytdlp_info()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ yt-dlp может получать субтитры")
    else:
        print("❌ yt-dlp не может получить субтитры")

if __name__ == "__main__":
    main()