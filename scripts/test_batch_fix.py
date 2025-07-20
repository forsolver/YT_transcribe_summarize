#!/usr/bin/env python3
"""
Тест пакетной обработки после исправления.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.batch_processor import BatchProcessor, BatchOptions
from threading import Event

def test_batch_fix():
    """Тест пакетной обработки."""
    
    print("=== ТЕСТ ПАКЕТНОЙ ОБРАБОТКИ ПОСЛЕ ИСПРАВЛЕНИЯ ===\n")
    
    # Используем плейлист OCEANIA, который работал раньше
    test_url = "https://www.youtube.com/watch?v=Tvu4bWh_GLM&list=PLH2zHj82u-TEEialbg-4t9q7izl2ZD9uC"
    
    print(f"Тестирование URL: {test_url}")
    print("Ограничение: 2 видео для быстрого теста")
    
    try:
        # Создаем процессор
        cancel_token = Event()
        processor = BatchProcessor(cancel_token=cancel_token)
        
        # Настройки - только 2 видео для быстрого теста
        options = BatchOptions(max_videos=2)
        
        print("\nЗапуск пакетной обработки...")
        result = processor.process_source(test_url, options)
        
        print(f"\n=== РЕЗУЛЬТАТЫ ===")
        print(f"Источник: {result.source_info.name}")
        print(f"Всего видео: {result.total_videos}")
        print(f"Обработано: {result.processed_videos}")
        print(f"Успешно: {result.successful_extractions}")
        print(f"Найдено трюков: {result.total_tricks}")
        print(f"Создано сегментов: {result.total_segments}")
        print(f"Время обработки: {result.processing_time:.1f} сек")
        
        if result.errors:
            print(f"\nОшибки ({len(result.errors)}):")
            for error in result.errors:
                print(f"- {error.video_title}: {error.error_message}")
        
        # Оценка результата
        if result.successful_extractions > 0:
            print(f"\n🎉 ПАКЕТНАЯ ОБРАБОТКА РАБОТАЕТ!")
            print(f"Успешно обработано {result.successful_extractions} видео")
        elif result.processed_videos > 0:
            print(f"\n⚠️ Частичный успех - видео найдены, но могут быть ограничения")
        else:
            print(f"\n❌ Пакетная обработка не работает")
            
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print(f"🔍 Тип ошибки: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_batch_fix()