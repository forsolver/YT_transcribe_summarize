# Design Document

## Overview

Добавление функциональности выбора папки для сохранения нарезанных трюков в пользовательский интерфейс YouTube Инструментов. Функция будет интегрирована в основное окно приложения и будет сохранять настройки между сессиями.

## Architecture

### UI Components
- **Folder Selection Widget**: Группа элементов для выбора и отображения папки
- **Settings Manager**: Компонент для сохранения и загрузки настроек
- **Path Validator**: Компонент для проверки доступности выбранной папки

### Integration Points
- **BatchProcessor**: Передача выбранной папки в BatchOptions
- **Video Processor**: Использование выбранной папки для одиночной обработки
- **UI Main Window**: Интеграция элементов выбора папки

## Components and Interfaces

### 1. UI Components

#### FolderSelectionWidget
```python
class FolderSelectionWidget(QWidget):
    folder_changed = pyqtSignal(str)  # Сигнал при изменении папки
    
    def __init__(self, default_folder: str = "tricks"):
        # Инициализация с папкой по умолчанию
        
    def get_selected_folder(self) -> str:
        # Возвращает текущую выбранную папку
        
    def set_folder(self, folder_path: str):
        # Устанавливает папку программно
        
    def select_folder(self):
        # Открывает диалог выбора папки
```

#### Элементы интерфейса:
- `QLabel` для отображения текущей папки
- `QPushButton` для открытия диалога выбора
- `QHBoxLayout` для размещения элементов

### 2. Settings Manager

```python
class SettingsManager:
    SETTINGS_FILE = "settings.json"
    DEFAULT_OUTPUT_FOLDER = "tricks"
    
    @staticmethod
    def save_output_folder(folder_path: str):
        # Сохраняет путь к папке в настройки
        
    @staticmethod
    def load_output_folder() -> str:
        # Загружает путь к папке из настроек
        
    @staticmethod
    def validate_folder(folder_path: str) -> bool:
        # Проверяет доступность папки
```

### 3. Integration Changes

#### YouTubeSummarizerUI Updates
```python
class YouTubeSummarizerUI(QMainWindow):
    def __init__(self):
        # Добавить folder_selection_widget
        self.folder_selection_widget = FolderSelectionWidget()
        
    def get_output_folder(self) -> str:
        # Возвращает выбранную папку для использования в обработке
```

## Data Models

### Settings Structure
```json
{
    "output_folder": "/path/to/selected/folder",
    "last_updated": "2025-07-19T20:50:00Z"
}
```

### Folder Validation Result
```python
@dataclass
class FolderValidationResult:
    is_valid: bool
    error_message: Optional[str] = None
    suggested_folder: Optional[str] = None
```

## Error Handling

### Folder Access Errors
- **Недоступная папка**: Показать предупреждение и предложить выбрать другую
- **Нет прав записи**: Показать ошибку с объяснением и предложить другую папку
- **Папка не существует**: Предложить создать папку или выбрать существующую

### Settings Errors
- **Поврежденный файл настроек**: Использовать настройки по умолчанию
- **Недоступный файл настроек**: Создать новый файл настроек

## Testing Strategy

### Unit Tests
- Тестирование FolderSelectionWidget
- Тестирование SettingsManager
- Тестирование валидации папок

### Integration Tests
- Тестирование интеграции с BatchProcessor
- Тестирование сохранения/загрузки настроек
- Тестирование UI взаимодействий

### User Acceptance Tests
- Выбор папки через диалог
- Сохранение настроек между сессиями
- Обработка ошибок доступа к папкам
- Отображение длинных путей

## UI Layout Design

### Размещение в основном окне
```
[URL Input Field                                    ]
[Summarize] [Check Video] [Extract Tricks] [Settings]

Output Folder: [/path/to/folder...] [Choose Folder]

[Progress Indicators]
[Output Text Area]
```

### Альтернативное размещение в настройках
- Добавить в диалог "Настройки пакетной обработки"
- Создать отдельную секцию "Папка сохранения"

## Implementation Priority

1. **High Priority**: Базовая функциональность выбора папки
2. **Medium Priority**: Сохранение настроек между сессиями
3. **Low Priority**: Продвинутая валидация и обработка ошибок