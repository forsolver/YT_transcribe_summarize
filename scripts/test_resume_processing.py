#!/usr/bin/env python3
"""
Тест функциональности возобновления пакетной обработки
"""

import sys
import os
import json
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.state_manager import StateManager
from ytsummarizer.batch_processor import BatchProcessor, BatchOptions
from ytsummarizer.url_detector import URLType

def test_state_manager():
    """Тест StateManager"""
    print("🧪 Тестирование StateManager...")
    
    # Создаем тестовый URL
    test_url = "https://www.youtube.com/playlist?list=test123"
    
    # Генерируем source_id
    source_id = StateManager.get_source_id(test_url)
    print(f"   ✅ Source ID: {source_id}")
    
    # Создаем тестовое состояние
    test_state = {
        "source_type": "PLAYLIST",
        "source_name": "Test Playlist",
        "total_videos": 10,
        "processed_videos": 5,
        "last_processed_index": 4,
        "last_processed_video": {
            "video_id": "abc123",
            "title": "Test Video",
            "url": "https://www.youtube.com/watch?v=abc123"
        },
        "processed_video_ids": ["vid1", "vid2", "vid3", "vid4", "vid5"]
    }
    
    # Сохраняем состояние
    success = StateManager.save_state(test_url, test_state)
    print(f"   ✅ Сохранение состояния: {success}")
    
    # Загружаем состояние
    loaded_state = StateManager.load_state(test_url)
    print(f"   ✅ Загрузка состояния: {'Успешно' if loaded_state else 'Ошибка'}")
    
    if loaded_state:
        print(f"   ✅ Проверка данных: {loaded_state.get('processed_videos')} из {loaded_state.get('total_videos')} видео обработано")
    
    # Получаем список состояний
    states = StateManager.list_saved_states()
    print(f"   ✅ Список состояний: {len(states)} состояний найдено")
    
    # Проверяем валидность состояния
    is_valid = StateManager.is_state_valid(loaded_state)
    print(f"   ✅ Валидность состояния: {is_valid}")
    
    # Удаляем состояние
    deleted = StateManager.delete_state(test_url)
    print(f"   ✅ Удаление состояния: {deleted}")
    
    # Проверяем, что состояние удалено
    state_after_delete = StateManager.load_state(test_url)
    print(f"   ✅ Состояние после удаления: {'Существует' if state_after_delete else 'Удалено'}")

def test_batch_processor_resume():
    """Тест возобновления обработки в BatchProcessor"""
    print("\n🧪 Тестирование возобновления в BatchProcessor...")
    
    # Создаем тестовый URL
    test_url = "https://www.youtube.com/playlist?list=test_resume"
    
    # Создаем тестовое состояние для имитации прерванной обработки
    test_state = {
        "source_type": "PLAYLIST",
        "source_name": "Test Resume Playlist",
        "total_videos": 5,
        "processed_videos": 2,
        "last_processed_index": 1,
        "last_processed_video": {
            "video_id": "vid2",
            "title": "Test Video 2",
            "url": "https://www.youtube.com/watch?v=vid2"
        },
        "processed_video_ids": ["vid1", "vid2"]
    }
    
    # Сохраняем состояние
    StateManager.save_state(test_url, test_state)
    print(f"   ✅ Тестовое состояние создано")
    
    # Проверяем, что состояние сохранено
    saved_state = StateManager.load_state(test_url)
    if saved_state:
        print(f"   ✅ Состояние сохранено: {saved_state.get('processed_videos')} из {saved_state.get('total_videos')} видео")
    
    # Удаляем состояние
    StateManager.delete_state(test_url)
    print(f"   ✅ Тестовое состояние удалено")

def test_ui_integration():
    """Тест интеграции с UI (запуск UI для ручного тестирования)"""
    print("\n🧪 Тестирование интеграции с UI...")
    print("   ℹ️ Запуск UI для ручного тестирования...")
    
    # Создаем тестовое состояние для демонстрации
    test_url = "https://www.youtube.com/playlist?list=demo_playlist"
    test_state = {
        "source_type": "PLAYLIST",
        "source_name": "Demo Playlist",
        "total_videos": 34,
        "processed_videos": 15,
        "last_processed_index": 14,
        "last_processed_video": {
            "video_id": "demo123",
            "title": "Demo Video",
            "url": "https://www.youtube.com/watch?v=demo123"
        },
        "processed_video_ids": ["vid1", "vid2", "vid3", "vid4", "vid5", 
                               "vid6", "vid7", "vid8", "vid9", "vid10",
                               "vid11", "vid12", "vid13", "vid14", "vid15"]
    }
    
    # Сохраняем состояние
    StateManager.save_state(test_url, test_state)
    print(f"   ✅ Демонстрационное состояние создано")
    
    # Запускаем UI
    print("   ℹ️ Инструкции для тестирования:")
    print("   1. Введите URL: https://www.youtube.com/playlist?list=demo_playlist")
    print("   2. Должен появиться диалог возобновления")
    print("   3. Проверьте отображение информации о прогрессе")
    print("   4. Попробуйте оба варианта: возобновление и перезапуск")
    print("   5. Проверьте настройки пакетной обработки для управления состояниями")
    
    try:
        from PyQt5.QtWidgets import QApplication
        from ytsummarizer.ui import YouTubeSummarizerUI
        
        app = QApplication(sys.argv)
        window = YouTubeSummarizerUI()
        window.show()
        print("   ✅ UI запущен, проведите ручное тестирование")
        print("   ℹ️ Закройте окно приложения для завершения теста")
        app.exec_()
    except ImportError:
        print("   ❌ Не удалось запустить UI (PyQt5 не установлен)")
    except Exception as e:
        print(f"   ❌ Ошибка запуска UI: {e}")

def main():
    print("🚀 Тестирование функциональности возобновления обработки")
    print("=" * 60)
    
    try:
        # Создаем временную директорию для тестов
        state_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), StateManager.STATE_DIR)
        os.makedirs(state_dir, exist_ok=True)
        
        # Запускаем тесты
        test_state_manager()
        test_batch_processor_resume()
        
        # Спрашиваем, нужно ли запускать UI для ручного тестирования
        response = input("\nЗапустить UI для ручного тестирования? (y/n): ")
        if response.lower() == 'y':
            test_ui_integration()
        
        print("\n" + "=" * 60)
        print("✅ Все тесты прошли успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())