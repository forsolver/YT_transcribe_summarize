# Design Document

## Overview

Добавление функциональности возобновления пакетной обработки плейлистов и каналов после прерывания. Система будет сохранять прогресс обработки, позволяя пользователям продолжить с того места, где процесс был прерван из-за внешних факторов.

## Architecture

### Компоненты системы

1. **StateManager** - компонент для управления состоянием обработки
   - Сохранение/загрузка состояния обработки
   - Отслеживание прогресса
   - Управление файлами состояния

2. **BatchProcessor** - существующий компонент пакетной обработки
   - Интеграция с StateManager для сохранения прогресса
   - Поддержка возобновления обработки с определенной позиции

3. **UI Components** - компоненты пользовательского интерфейса
   - Диалог возобновления обработки
   - Отображение информации о прогрессе
   - Управление сохраненными состояниями

### Хранение данных

1. **Файлы состояния** - JSON файлы с информацией о прогрессе
   - Хранятся в директории `.state` в корне проекта
   - Именование: `{source_id}_state.json`
   - Содержат информацию о прогрессе, метаданные и список обработанных видео

2. **Интеграция с настройками** - использование существующего SettingsManager
   - Добавление настроек для управления возобновлением
   - Сохранение пользовательских предпочтений

## Components and Interfaces

### StateManager

```python
class StateManager:
    """Компонент для управления состоянием пакетной обработки"""
    
    @staticmethod
    def save_state(source_id: str, state: dict) -> bool:
        """Сохраняет состояние обработки для указанного источника"""
        
    @staticmethod
    def load_state(source_id: str) -> Optional[dict]:
        """Загружает состояние обработки для указанного источника"""
        
    @staticmethod
    def delete_state(source_id: str) -> bool:
        """Удаляет сохраненное состояние для указанного источника"""
        
    @staticmethod
    def list_saved_states() -> List[dict]:
        """Возвращает список всех сохраненных состояний с метаданными"""
        
    @staticmethod
    def get_state_file_path(source_id: str) -> str:
        """Возвращает путь к файлу состояния для указанного источника"""
```

### BatchProcessor Updates

```python
class BatchProcessor:
    """Обновленный компонент пакетной обработки с поддержкой возобновления"""
    
    def process_source(self, source_url: str, options: BatchOptions, 
                      resume: bool = False) -> BatchResult:
        """Обрабатывает источник с возможностью возобновления"""
        
    def _load_progress(self, source_id: str) -> Optional[dict]:
        """Загружает прогресс обработки для источника"""
        
    def _save_progress(self, source_id: str, processed_videos: List[str], 
                      current_index: int, total_videos: int) -> None:
        """Сохраняет прогресс обработки"""
        
    def _check_source_changes(self, source_id: str, current_videos: List[VideoInfo], 
                             saved_state: dict) -> Tuple[bool, str]:
        """Проверяет изменения в составе источника"""
```

### UI Components

#### ResumeDialog

```python
class ResumeDialog(QDialog):
    """Диалог для возобновления обработки"""
    
    def __init__(self, parent, source_url: str, state_info: dict):
        """Инициализирует диалог с информацией о сохраненном состоянии"""
        
    def get_resume_choice(self) -> bool:
        """Возвращает выбор пользователя (возобновить или начать заново)"""
```

#### BatchSettingsDialog Updates

```python
class BatchSettingsDialog(QDialog):
    """Обновленный диалог настроек пакетной обработки"""
    
    def __init__(self, parent=None):
        """Инициализирует диалог с дополнительными настройками возобновления"""
        
    def _create_saved_states_section(self) -> QWidget:
        """Создает секцию для управления сохраненными состояниями"""
        
    def _delete_selected_state(self) -> None:
        """Удаляет выбранное сохраненное состояние"""
```

## Data Models

### State File Structure

```json
{
  "source_id": "UC...",
  "source_url": "https://www.youtube.com/channel/UC...",
  "source_type": "CHANNEL",
  "source_name": "Channel Name",
  "total_videos": 34,
  "processed_videos": 15,
  "last_processed_index": 14,
  "last_processed_video": {
    "video_id": "abc123",
    "title": "Video Title",
    "url": "https://www.youtube.com/watch?v=abc123"
  },
  "processed_video_ids": ["vid1", "vid2", "..."],
  "timestamp": "2025-07-20T21:30:00Z",
  "options": {
    "max_videos": 50,
    "skip_existing": true,
    "output_dir": "tricks"
  }
}
```

### BatchOptions Updates

```python
@dataclass
class BatchOptions:
    """Расширенные опции пакетной обработки"""
    max_videos: int = 50
    skip_existing: bool = True
    output_dir: str = "tricks"
    auto_resume: bool = True  # Автоматически возобновлять обработку без запроса
```

## Error Handling

### Обработка ошибок при возобновлении

1. **Несовместимость состояния**
   - Проверка версии формата состояния
   - Предупреждение при значительных изменениях в источнике
   - Опция сброса состояния при несовместимости

2. **Недоступность файла состояния**
   - Корректная обработка отсутствующих или поврежденных файлов
   - Автоматическое создание новых файлов состояния

3. **Изменения в структуре источника**
   - Обнаружение добавленных/удаленных видео
   - Корректировка индексов и счетчиков

## UI Layout Design

### Диалог возобновления обработки

```
+------------------------------------------+
|    Возобновление пакетной обработки      |
+------------------------------------------+
| Обнаружен сохраненный прогресс для:      |
| Channel Name                             |
|                                          |
| Обработано: 15 из 34 видео (44%)         |
|                                          |
| Последнее обработанное видео:            |
| "Video Title"                            |
|                                          |
| [x] Запомнить выбор                      |
|                                          |
| [Возобновить]  [Начать заново]  [Отмена] |
+------------------------------------------+
```

### Секция управления состояниями в настройках

```
+------------------------------------------+
|    Сохраненные состояния обработки       |
+------------------------------------------+
| Channel Name (15/34) - 20.07.2025        |
| Playlist Name (7/12) - 19.07.2025        |
|                                          |
| [Удалить выбранное]                      |
|                                          |
| [x] Автоматически возобновлять обработку |
+------------------------------------------+
```

## Implementation Priority

1. **High Priority**: Базовое сохранение и загрузка состояния
2. **High Priority**: Диалог возобновления обработки
3. **Medium Priority**: Интеграция с BatchProcessor
4. **Medium Priority**: Обработка изменений в источнике
5. **Low Priority**: Управление сохраненными состояниями в настройках