#!/usr/bin/env python3
"""
Детальная диагностика проблем с получением транскрипта
Логирует каждый шаг процесса для выявления точной причины проблемы
"""

import sys
import os
import logging
from datetime import datetime
import traceback

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.transcripts import get_transcript
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# Настройка детального логирования
log_filename = f"transcript_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_video_id_extraction(url):
    """Тестирует извлечение video_id из URL"""
    logger.info(f"=== ТЕСТ ИЗВЛЕЧЕНИЯ VIDEO_ID ===")
    logger.info(f"Входной URL: {url}")
    
    try:
        # Тестируем разные способы извлечения video_id
        
        # Способ 1: Простое извлечение из URL
        if 'v=' in url:
            video_id = url.split('v=')[1].split('&')[0]
            logger.info(f"Способ 1 (v=): video_id = {video_id}")
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
            logger.info(f"Способ 1 (youtu.be): video_id = {video_id}")
        else:
            logger.warning("Способ 1: Не удалось извлечь video_id")
            video_id = None
            
        # Способ 2: Через yt-dlp
        logger.info("Способ 2: Извлечение через yt-dlp")
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            ydl_video_id = info.get('id')
            logger.info(f"Способ 2 (yt-dlp): video_id = {ydl_video_id}")
            
        return video_id or ydl_video_id
        
    except Exception as e:
        logger.error(f"Ошибка при извлечении video_id: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def test_transcript_api_direct(video_id):
    """Тестирует прямое обращение к YouTube Transcript API"""
    logger.info(f"=== ТЕСТ ПРЯМОГО ОБРАЩЕНИЯ К TRANSCRIPT API ===")
    logger.info(f"Video ID: {video_id}")
    
    try:
        # Получаем список доступных языков
        logger.info("Получение списка доступных языков...")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        available_languages = []
        for transcript in transcript_list:
            lang_info = {
                'language': transcript.language,
                'language_code': transcript.language_code,
                'is_generated': transcript.is_generated,
                'is_translatable': transcript.is_translatable
            }
            available_languages.append(lang_info)
            logger.info(f"Доступный язык: {lang_info}")
            
        # Пробуем получить транскрипт на русском
        logger.info("Попытка получить транскрипт на русском...")
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru'])
            logger.info(f"Успешно получен русский транскрипт, длина: {len(transcript)} сегментов")
            if transcript:
                logger.info(f"Первый сегмент: {transcript[0]}")
            return transcript
        except Exception as e:
            logger.warning(f"Не удалось получить русский транскрипт: {e}")
            
        # Пробуем получить транскрипт на английском
        logger.info("Попытка получить транскрипт на английском...")
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            logger.info(f"Успешно получен английский транскрипт, длина: {len(transcript)} сегментов")
            if transcript:
                logger.info(f"Первый сегмент: {transcript[0]}")
            return transcript
        except Exception as e:
            logger.warning(f"Не удалось получить английский транскрипт: {e}")
            
        # Пробуем получить любой доступный транскрипт
        logger.info("Попытка получить любой доступный транскрипт...")
        if available_languages:
            first_lang = available_languages[0]['language_code']
            logger.info(f"Пробуем язык: {first_lang}")
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[first_lang])
            logger.info(f"Успешно получен транскрипт на {first_lang}, длина: {len(transcript)} сегментов")
            return transcript
            
    except Exception as e:
        logger.error(f"Ошибка при работе с Transcript API: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def test_our_transcript_function(url):
    """Тестирует нашу функцию get_transcript"""
    logger.info(f"=== ТЕСТ НАШЕЙ ФУНКЦИИ GET_TRANSCRIPT ===")
    logger.info(f"URL: {url}")
    
    try:
        transcript = get_transcript(url)
        if transcript:
            logger.info(f"Успешно получен транскрипт через нашу функцию, длина: {len(transcript)} символов")
            logger.info(f"Первые 200 символов: {transcript[:200]}...")
        else:
            logger.warning("Наша функция вернула пустой транскрипт")
        return transcript
    except Exception as e:
        logger.error(f"Ошибка в нашей функции get_transcript: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def test_yt_dlp_info(url):
    """Тестирует получение информации через yt-dlp"""
    logger.info(f"=== ТЕСТ YT-DLP INFO ===")
    logger.info(f"URL: {url}")
    
    try:
        # Тестируем разные конфигурации yt-dlp
        configs = [
            {"quiet": True, "no_warnings": True},
            {"quiet": False, "no_warnings": False},
            {"quiet": True, "no_warnings": True, "extract_flat": True},
            {}  # Пустая конфигурация
        ]
        
        for i, config in enumerate(configs):
            logger.info(f"Конфигурация {i+1}: {config}")
            try:
                with yt_dlp.YoutubeDL(config) as ydl:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Успешно получена информация:")
                    logger.info(f"  ID: {info.get('id')}")
                    logger.info(f"  Title: {info.get('title')}")
                    logger.info(f"  Duration: {info.get('duration')}")
                    logger.info(f"  Available subtitles: {list(info.get('subtitles', {}).keys())}")
                    logger.info(f"  Available automatic captions: {list(info.get('automatic_captions', {}).keys())}")
                    
            except Exception as e:
                logger.error(f"Ошибка с конфигурацией {i+1}: {e}")
                
    except Exception as e:
        logger.error(f"Общая ошибка при тестировании yt-dlp: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

def main():
    # Тестовые URL
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - известное видео
        "https://youtu.be/dQw4w9WgXcQ",  # Короткая форма
    ]
    
    # Если передан URL как аргумент, используем его
    if len(sys.argv) > 1:
        test_urls = [sys.argv[1]]
    
    logger.info(f"=== НАЧАЛО ДЕТАЛЬНОЙ ДИАГНОСТИКИ ТРАНСКРИПТОВ ===")
    logger.info(f"Время: {datetime.now()}")
    logger.info(f"Лог файл: {log_filename}")
    
    for url in test_urls:
        logger.info(f"\n{'='*60}")
        logger.info(f"ТЕСТИРОВАНИЕ URL: {url}")
        logger.info(f"{'='*60}")
        
        # Шаг 1: Извлечение video_id
        video_id = test_video_id_extraction(url)
        if not video_id:
            logger.error("Не удалось извлечь video_id, пропускаем URL")
            continue
            
        # Шаг 2: Тест yt-dlp
        test_yt_dlp_info(url)
        
        # Шаг 3: Прямой тест Transcript API
        test_transcript_api_direct(video_id)
        
        # Шаг 4: Тест нашей функции
        test_our_transcript_function(url)
        
    logger.info(f"\n=== ДИАГНОСТИКА ЗАВЕРШЕНА ===")
    logger.info(f"Подробный лог сохранен в файл: {log_filename}")
    print(f"\nПодробный лог сохранен в файл: {log_filename}")

if __name__ == "__main__":
    main()