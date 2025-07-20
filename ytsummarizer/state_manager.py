"""
Enhanced State Manager for processing resumption and checkpoint management
"""

import os
import json
import logging
import hashlib
import time
import uuid
import shutil
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("ytsummarizer.state_manager")


class OperationType(Enum):
    """Types of processing operations."""
    BATCH = "batch_processing"
    SINGLE = "single_video"
    TRICKS_EXTRACTION = "tricks_extraction"


class ProcessingStatus(Enum):
    """Status of processing operations."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessingItem:
    """Represents a single item being processed."""
    video_id: str
    url: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    error: Optional[str] = None
    error_category: Optional[str] = None
    retry_count: int = 0
    tricks_found: int = 0
    output_files: List[str] = None
    progress: str = "pending"
    
    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []


@dataclass
class ProcessingState:
    """Enhanced processing state with comprehensive tracking."""
    session_id: str
    operation_type: str
    start_time: str
    total_items: int
    completed_items: List[ProcessingItem]
    failed_items: List[ProcessingItem]
    current_item: Optional[ProcessingItem]
    checkpoint_data: Dict[str, Any]
    resumable: bool
    status: str = ProcessingStatus.RUNNING.value
    last_checkpoint: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    
    def __post_init__(self):
        if self.completed_items is None:
            self.completed_items = []
        if self.failed_items is None:
            self.failed_items = []
        if self.checkpoint_data is None:
            self.checkpoint_data = {}
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 0.0
        completed = len(self.completed_items)
        return (completed / self.total_items) * 100.0
    
    @property
    def is_resumable(self) -> bool:
        """Check if session can be resumed."""
        return (self.resumable and 
                self.status in [ProcessingStatus.PAUSED.value, ProcessingStatus.FAILED.value, ProcessingStatus.RUNNING.value] and
                len(self.completed_items) + len(self.failed_items) < self.total_items)

class StateManager:
    """Enhanced state management with resumption capabilities."""
    
    # Directory for storing state files
    STATE_DIR = ".state"
    SESSIONS_DIR = "sessions"
    
    def __init__(self):
        """Initialize the StateManager."""
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure state directories exist."""
        state_dir = self.get_state_dir()
        sessions_dir = os.path.join(state_dir, self.SESSIONS_DIR)
        os.makedirs(sessions_dir, exist_ok=True)
    
    @classmethod
    def get_state_dir(cls) -> str:
        """Returns path to state directory."""
        state_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cls.STATE_DIR)
        os.makedirs(state_dir, exist_ok=True)
        return state_dir
    
    def get_sessions_dir(self) -> str:
        """Returns path to sessions directory."""
        return os.path.join(self.get_state_dir(), self.SESSIONS_DIR)
    
    def create_session(self, operation_type: OperationType, items: List[str], 
                      source_url: Optional[str] = None, source_name: Optional[str] = None,
                      processing_options: Optional[Dict] = None) -> str:
        """
        Create new processing session with unique ID.
        
        Args:
            operation_type: Type of operation (batch, single, tricks_extraction)
            items: List of items to process (URLs or video IDs)
            source_url: Source URL if applicable
            source_name: Human-readable source name
            processing_options: Additional processing options
            
        Returns:
            Unique session ID
        """
        session_id = f"{operation_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Create processing state
        state = ProcessingState(
            session_id=session_id,
            operation_type=operation_type.value,
            start_time=datetime.now().isoformat(),
            total_items=len(items),
            completed_items=[],
            failed_items=[],
            current_item=None,
            checkpoint_data={
                "items": items,
                "processing_options": processing_options or {},
                "last_checkpoint": datetime.now().isoformat()
            },
            resumable=True,
            status=ProcessingStatus.RUNNING.value,
            source_url=source_url,
            source_name=source_name
        )
        
        # Save initial state
        if self._save_session_state(state):
            logger.info(f"Created new session: {session_id}")
            return session_id
        else:
            raise RuntimeError(f"Failed to create session: {session_id}")
    
    def save_checkpoint(self, session_id: str, current_item: Optional[ProcessingItem] = None,
                       completed: Optional[List[ProcessingItem]] = None, 
                       failed: Optional[List[ProcessingItem]] = None,
                       additional_data: Optional[Dict] = None) -> bool:
        """
        Save processing checkpoint to persistent storage.
        
        Args:
            session_id: Session identifier
            current_item: Currently processing item
            completed: List of completed items
            failed: List of failed items
            additional_data: Additional checkpoint data
            
        Returns:
            True if checkpoint saved successfully
        """
        state = self.load_session(session_id)
        if not state:
            logger.error(f"Cannot save checkpoint: session {session_id} not found")
            return False
        
        # Update state
        if current_item:
            state.current_item = current_item
        if completed is not None:
            state.completed_items = completed
        if failed is not None:
            state.failed_items = failed
        if additional_data:
            state.checkpoint_data.update(additional_data)
        
        state.last_checkpoint = datetime.now().isoformat()
        
        success = self._save_session_state(state)
        if success:
            logger.debug(f"Checkpoint saved for session: {session_id}")
        else:
            logger.error(f"Failed to save checkpoint for session: {session_id}")
        
        return success
    
    def load_session(self, session_id: str) -> Optional[ProcessingState]:
        """
        Load existing processing session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ProcessingState object or None if not found
        """
        session_file = self._get_session_file_path(session_id)
        
        if not os.path.exists(session_file):
            logger.debug(f"Session file not found: {session_file}")
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert dict back to ProcessingState
            state = self._dict_to_processing_state(data)
            logger.debug(f"Session loaded: {session_id}")
            return state
            
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None
    
    def get_resumable_sessions(self) -> List[ProcessingState]:
        """
        Get all sessions that can be resumed.
        
        Returns:
            List of resumable ProcessingState objects
        """
        sessions = []
        sessions_dir = self.get_sessions_dir()
        
        if not os.path.exists(sessions_dir):
            return sessions
        
        for filename in os.listdir(sessions_dir):
            if filename.endswith('.json'):
                session_id = filename[:-5]  # Remove .json extension
                state = self.load_session(session_id)
                if state and state.is_resumable:
                    sessions.append(state)
        
        # Sort by last checkpoint time (newest first)
        sessions.sort(key=lambda x: x.last_checkpoint or x.start_time, reverse=True)
        return sessions
    
    def mark_session_complete(self, session_id: str) -> bool:
        """
        Mark session as completed and clean up.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if marked successfully
        """
        state = self.load_session(session_id)
        if not state:
            return False
        
        state.status = ProcessingStatus.COMPLETED.value
        state.resumable = False
        state.last_checkpoint = datetime.now().isoformat()
        
        return self._save_session_state(state)
    
    def mark_session_failed(self, session_id: str, error_message: str = "") -> bool:
        """
        Mark session as failed.
        
        Args:
            session_id: Session identifier
            error_message: Error description
            
        Returns:
            True if marked successfully
        """
        state = self.load_session(session_id)
        if not state:
            return False
        
        state.status = ProcessingStatus.FAILED.value
        state.last_checkpoint = datetime.now().isoformat()
        if error_message:
            state.checkpoint_data["failure_reason"] = error_message
        
        return self._save_session_state(state)
    
    def pause_session(self, session_id: str) -> bool:
        """
        Mark session as paused.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if paused successfully
        """
        state = self.load_session(session_id)
        if not state:
            return False
        
        state.status = ProcessingStatus.PAUSED.value
        state.last_checkpoint = datetime.now().isoformat()
        
        return self._save_session_state(state)
    
    def resume_session(self, session_id: str) -> bool:
        """
        Mark session as running (resumed).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if resumed successfully
        """
        state = self.load_session(session_id)
        if not state or not state.is_resumable:
            return False
        
        state.status = ProcessingStatus.RUNNING.value
        state.last_checkpoint = datetime.now().isoformat()
        
        return self._save_session_state(state)
    
    def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        Clean up old session data.
        
        Args:
            days: Maximum age in days for sessions to keep
            
        Returns:
            Number of sessions cleaned up
        """
        cleaned_count = 0
        sessions_dir = self.get_sessions_dir()
        
        if not os.path.exists(sessions_dir):
            return cleaned_count
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for filename in os.listdir(sessions_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(sessions_dir, filename)
                try:
                    # Check file modification time
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_date:
                        # Also check if session is completed
                        session_id = filename[:-5]
                        state = self.load_session(session_id)
                        if state and state.status == ProcessingStatus.COMPLETED.value:
                            os.remove(file_path)
                            cleaned_count += 1
                            logger.debug(f"Cleaned up old session: {session_id}")
                except Exception as e:
                    logger.error(f"Error cleaning up session file {filename}: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} old sessions")
        return cleaned_count
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully
        """
        session_file = self._get_session_file_path(session_id)
        
        if not os.path.exists(session_file):
            return True  # Already deleted
        
        try:
            os.remove(session_file)
            logger.debug(f"Session deleted: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def _get_session_file_path(self, session_id: str) -> str:
        """Get file path for session data."""
        return os.path.join(self.get_sessions_dir(), f"{session_id}.json")
    
    def _save_session_state(self, state: ProcessingState) -> bool:
        """Save ProcessingState to file."""
        session_file = self._get_session_file_path(state.session_id)
        
        try:
            # Convert ProcessingState to dict
            data = self._processing_state_to_dict(state)
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving session state: {e}")
            return False
    
    def _processing_state_to_dict(self, state: ProcessingState) -> Dict:
        """Convert ProcessingState to dictionary for JSON serialization."""
        data = asdict(state)
        
        # Convert ProcessingItem objects to dicts
        data['completed_items'] = [asdict(item) for item in state.completed_items]
        data['failed_items'] = [asdict(item) for item in state.failed_items]
        if state.current_item:
            data['current_item'] = asdict(state.current_item)
        
        return data
    
    def _dict_to_processing_state(self, data: Dict) -> ProcessingState:
        """Convert dictionary to ProcessingState object."""
        # Convert item dicts back to ProcessingItem objects
        completed_items = [ProcessingItem(**item) for item in data.get('completed_items', [])]
        failed_items = [ProcessingItem(**item) for item in data.get('failed_items', [])]
        current_item = None
        if data.get('current_item'):
            current_item = ProcessingItem(**data['current_item'])
        
        return ProcessingState(
            session_id=data['session_id'],
            operation_type=data['operation_type'],
            start_time=data['start_time'],
            total_items=data['total_items'],
            completed_items=completed_items,
            failed_items=failed_items,
            current_item=current_item,
            checkpoint_data=data.get('checkpoint_data', {}),
            resumable=data.get('resumable', True),
            status=data.get('status', ProcessingStatus.RUNNING.value),
            last_checkpoint=data.get('last_checkpoint'),
            source_url=data.get('source_url'),
            source_name=data.get('source_name')
        )
    
    def validate_checkpoint(self, session_id: str) -> bool:
        """
        Validate checkpoint data integrity.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if checkpoint is valid
        """
        try:
            state = self.load_session(session_id)
            if not state:
                return False
            
            # Basic validation checks
            required_fields = ['session_id', 'operation_type', 'start_time', 'total_items']
            for field in required_fields:
                if not hasattr(state, field) or getattr(state, field) is None:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Validate data consistency
            if state.total_items < 0:
                logger.error("Invalid total_items count")
                return False
            
            if len(state.completed_items) + len(state.failed_items) > state.total_items:
                logger.error("Processed items exceed total items")
                return False
            
            # Validate timestamps
            try:
                datetime.fromisoformat(state.start_time)
                if state.last_checkpoint:
                    datetime.fromisoformat(state.last_checkpoint)
            except ValueError:
                logger.error("Invalid timestamp format")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating checkpoint: {e}")
            return False
    
    def create_backup_checkpoint(self, session_id: str) -> bool:
        """
        Create a backup of the current checkpoint.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if backup created successfully
        """
        try:
            session_file = self._get_session_file_path(session_id)
            if not os.path.exists(session_file):
                return False
            
            backup_file = f"{session_file}.backup"
            shutil.copy2(session_file, backup_file)
            logger.debug(f"Backup checkpoint created: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup checkpoint: {e}")
            return False
    
    def restore_from_backup(self, session_id: str) -> bool:
        """
        Restore checkpoint from backup if main checkpoint is corrupted.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if restored successfully
        """
        try:
            session_file = self._get_session_file_path(session_id)
            backup_file = f"{session_file}.backup"
            
            if not os.path.exists(backup_file):
                logger.error(f"No backup found for session: {session_id}")
                return False
            
            # Validate backup before restoring
            temp_session_id = f"{session_id}_backup_test"
            shutil.copy2(backup_file, self._get_session_file_path(temp_session_id))
            
            if self.validate_checkpoint(temp_session_id):
                shutil.copy2(backup_file, session_file)
                os.remove(self._get_session_file_path(temp_session_id))
                logger.info(f"Checkpoint restored from backup: {session_id}")
                return True
            else:
                os.remove(self._get_session_file_path(temp_session_id))
                logger.error(f"Backup checkpoint is also corrupted: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False
    
    def auto_checkpoint(self, session_id: str, milestone: str, **kwargs) -> bool:
        """
        Automatically create checkpoint at processing milestones.
        
        Args:
            session_id: Session identifier
            milestone: Milestone name (e.g., 'video_completed', 'batch_started')
            **kwargs: Additional data to save in checkpoint
            
        Returns:
            True if checkpoint created successfully
        """
        try:
            # Create backup before updating
            self.create_backup_checkpoint(session_id)
            
            # Add milestone information
            additional_data = {
                'last_milestone': milestone,
                'milestone_timestamp': datetime.now().isoformat(),
                **kwargs
            }
            
            return self.save_checkpoint(session_id, additional_data=additional_data)
            
        except Exception as e:
            logger.error(f"Error creating auto checkpoint: {e}")
            return False
    
    def get_checkpoint_info(self, session_id: str) -> Optional[Dict]:
        """
        Get checkpoint information and statistics.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with checkpoint information
        """
        state = self.load_session(session_id)
        if not state:
            return None
        
        session_file = self._get_session_file_path(session_id)
        backup_file = f"{session_file}.backup"
        
        info = {
            'session_id': session_id,
            'operation_type': state.operation_type,
            'status': state.status,
            'progress_percentage': state.progress_percentage,
            'total_items': state.total_items,
            'completed_count': len(state.completed_items),
            'failed_count': len(state.failed_items),
            'start_time': state.start_time,
            'last_checkpoint': state.last_checkpoint,
            'is_resumable': state.is_resumable,
            'has_backup': os.path.exists(backup_file),
            'checkpoint_valid': self.validate_checkpoint(session_id)
        }
        
        # Add file information
        if os.path.exists(session_file):
            stat = os.stat(session_file)
            info['file_size'] = stat.st_size
            info['file_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return info

    # Legacy methods for backward compatibility
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