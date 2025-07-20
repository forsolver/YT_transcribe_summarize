"""
Менеджер состояния для управления прогрессом пакетной обработки
"""

import os
import json
import logging
import hashlib
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger("ytsummarizer.state_manager")

class StateManager:
    """Компонент для управления состоянием пакетной обработки"""
    
    # Директория для хранения файлов состояния
    STATE_DIR = ".state"
    
    @classmethod
    def get_state_dir(cls) -> str:
        """Возвращает путь к директории состояний"""
        state_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cls.STATE_DIR)
        os.makedirs(state_dir, exist_ok=True)
        return state_dir
    
    @classmethod
    def get_source_id(cls, source_url: str) -> str:
        """
        Генерирует уникальный идентификатор источника на основе URL
        
        Args:
            source_url: URL источника (канал или плейлист)
            
        Returns:
            Уникальный идентификатор источника
        """
        # Используем MD5 для генерации короткого идентификатора
        return hashlib.md5(source_url.encode('utf-8')).hexdigest()[:12]
    
    @classmethod
    def get_state_file_path(cls, source_id: str) -> str:
        """
        Возвращает путь к файлу состояния для указанного источника
        
        Args:
            source_id: Идентификатор источника
            
        Returns:
            Путь к файлу состояния
        """
        return os.path.join(cls.get_state_dir(), f"{source_id}_state.json")
    
    @classmethod
    def save_state(cls, source_url: str, state: dict) -> bool:
        """
        Сохраняет состояние обработки для указанного источника
        
        Args:
            source_url: URL источника
            state: Словарь с информацией о состоянии
            
        Returns:
            True если сохранение успешно, иначе False
        """
        source_id = cls.get_source_id(source_url)
        state_file = cls.get_state_file_path(source_id)
        
        # Добавляем метаданные
        state["source_id"] = source_id
        state["source_url"] = source_url
        state["timestamp"] = datetime.now().isoformat()
        
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            logger.debug(f"Состояние сохранено в {state_file}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении состояния: {e}")
            return False
    
    @classmethod
    def load_state(cls, source_url: str) -> Optional[dict]:
        """
        Загружает состояние обработки для указанного источника
        
        Args:
            source_url: URL источника
            
        Returns:
            Словарь с информацией о состоянии или None если состояние не найдено
        """
        source_id = cls.get_source_id(source_url)
        state_file = cls.get_state_file_path(source_id)
        
        if not os.path.exists(state_file):
            logger.debug(f"Файл состояния не найден: {state_file}")
            return None
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            logger.debug(f"Состояние загружено из {state_file}")
            return state
        except Exception as e:
            logger.error(f"Ошибка при загрузке состояния: {e}")
            return None
    
    @classmethod
    def delete_state(cls, source_url: str) -> bool:
        """
        Удаляет сохраненное состояние для указанного источника
        
        Args:
            source_url: URL источника
            
        Returns:
            True если удаление успешно, иначе False
        """
        source_id = cls.get_source_id(source_url)
        state_file = cls.get_state_file_path(source_id)
        
        if not os.path.exists(state_file):
            logger.debug(f"Файл состояния не найден для удаления: {state_file}")
            return True  # Считаем успешным, если файла нет
        
        try:
            os.remove(state_file)
            logger.debug(f"Файл состояния удален: {state_file}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении файла состояния: {e}")
            return False
    
    @classmethod
    def list_saved_states(cls) -> List[dict]:
        """
        Возвращает список всех сохраненных состояний с метаданными
        
        Returns:
            Список словарей с информацией о сохраненных состояниях
        """
        state_dir = cls.get_state_dir()
        result = []
        
        if not os.path.exists(state_dir):
            return []
        
        for filename in os.listdir(state_dir):
            if filename.endswith("_state.json"):
                try:
                    file_path = os.path.join(state_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    
                    # Извлекаем основную информацию
                    state_info = {
                        "source_id": state.get("source_id", ""),
                        "source_url": state.get("source_url", ""),
                        "source_name": state.get("source_name", "Неизвестный источник"),
                        "source_type": state.get("source_type", "UNKNOWN"),
                        "processed_videos": state.get("processed_videos", 0),
                        "total_videos": state.get("total_videos", 0),
                        "timestamp": state.get("timestamp", ""),
                        "file_path": file_path
                    }
                    
                    result.append(state_info)
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла состояния {filename}: {e}")
        
        # Сортируем по времени (новые сверху)
        result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return result
    
    @classmethod
    def format_timestamp(cls, timestamp_str: str) -> str:
        """
        Форматирует временную метку для отображения
        
        Args:
            timestamp_str: Строка с временной меткой в ISO формате
            
        Returns:
            Отформатированная строка с датой и временем
        """
        try:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime("%d.%m.%Y %H:%M")
        except (ValueError, TypeError):
            return "Неизвестная дата"
    
    @classmethod
    def is_state_valid(cls, state: dict, max_age_days: int = 7) -> bool:
        """
        Проверяет актуальность состояния
        
        Args:
            state: Словарь с информацией о состоянии
            max_age_days: Максимальный возраст состояния в днях
            
        Returns:
            True если состояние актуально, иначе False
        """
        if not state or not isinstance(state, dict):
            return False
        
        # Проверяем наличие обязательных полей
        required_fields = ["source_id", "source_url", "timestamp", 
                          "processed_videos", "processed_video_ids"]
        if not all(field in state for field in required_fields):
            return False
        
        # Проверяем возраст состояния
        try:
            timestamp = datetime.fromisoformat(state["timestamp"])
            age_days = (datetime.now() - timestamp).days
            if age_days > max_age_days:
                logger.debug(f"Состояние устарело: {age_days} дней")
                return False
        except (ValueError, TypeError):
            logger.debug("Некорректная временная метка в состоянии")
            return False
        
        return True