"""
Менеджер настроек для YouTube Инструментов
"""

import os
import json
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger("ytsummarizer.settings_manager")

class SettingsManager:
    """Класс для управления настройками приложения"""
    
    SETTINGS_FILE = "settings.json"
    DEFAULT_OUTPUT_FOLDER = "tricks"
    
    @classmethod
    def get_settings_path(cls) -> str:
        """Возвращает путь к файлу настроек"""
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cls.SETTINGS_FILE)
    
    @classmethod
    def load_settings(cls) -> dict:
        """Загружает настройки из файла"""
        settings_path = cls.get_settings_path()
        
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    logger.debug(f"Настройки загружены из {settings_path}")
                    return settings
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Ошибка при загрузке настроек: {e}. Используем настройки по умолчанию.")
        
        # Возвращаем настройки по умолчанию
        return {
            "output_folder": cls.DEFAULT_OUTPUT_FOLDER
        }
    
    @classmethod
    def save_settings(cls, settings: dict) -> bool:
        """Сохраняет настройки в файл"""
        settings_path = cls.get_settings_path()
        
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                logger.debug(f"Настройки сохранены в {settings_path}")
                return True
        except IOError as e:
            logger.error(f"Ошибка при сохранении настроек: {e}")
            return False
    
    @classmethod
    def save_output_folder(cls, folder_path: str) -> bool:
        """Сохраняет путь к папке вывода в настройки"""
        settings = cls.load_settings()
        settings["output_folder"] = folder_path
        return cls.save_settings(settings)
    
    @classmethod
    def load_output_folder(cls) -> str:
        """Загружает путь к папке вывода из настроек"""
        settings = cls.load_settings()
        folder_path = settings.get("output_folder", cls.DEFAULT_OUTPUT_FOLDER)
        
        # Проверяем, что папка существует и доступна
        if cls.validate_folder(folder_path):
            return folder_path
        else:
            logger.warning(f"Сохраненная папка '{folder_path}' недоступна. Используем папку по умолчанию.")
            return cls.DEFAULT_OUTPUT_FOLDER
    
    @classmethod
    def validate_folder(cls, folder_path: str) -> bool:
        """Проверяет доступность папки для записи"""
        if not folder_path:
            return False
        
        try:
            # Создаем папку если она не существует
            os.makedirs(folder_path, exist_ok=True)
            
            # Проверяем права на запись
            test_file = os.path.join(folder_path, ".test_write_access")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                return True
            except (IOError, OSError):
                return False
                
        except (OSError, IOError) as e:
            logger.debug(f"Папка '{folder_path}' недоступна: {e}")
            return False
    
    @classmethod
    def get_folder_display_name(cls, folder_path: str, max_length: int = 50) -> str:
        """Возвращает сокращенное имя папки для отображения"""
        if not folder_path:
            return ""
        
        if len(folder_path) <= max_length:
            return folder_path
        
        # Сокращаем путь с многоточием в середине
        start_length = max_length // 2 - 2
        end_length = max_length - start_length - 3
        
        return f"{folder_path[:start_length]}...{folder_path[-end_length:]}"
    
    @classmethod
    def reset_to_defaults(cls) -> bool:
        """Сбрасывает настройки к значениям по умолчанию"""
        default_settings = {
            "output_folder": cls.DEFAULT_OUTPUT_FOLDER
        }
        return cls.save_settings(default_settings)