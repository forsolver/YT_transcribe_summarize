# Анализ корневой причины проблем с транскриптом

## Дата: 19 июля 2025, 20:41

## Выявленные проблемы

### 1. 429 Client Error: Too Many Requests
**Причина**: YouTube блокирует слишком частые запросы к Transcript API
**Детали**:
- Ошибка: `429 Client Error: Too Many Requests for url: https://www.youtube.com/api/timedtext?v=...`
- Происходит при попытке получить транскрипт через `YouTubeTranscriptApi.get_transcript()`
- YouTube ограничивает количество запросов к API транскриптов

### 2. Неправильное использование функции get_transcript()
**Причина**: Функция `get_transcript()` ожидает `video_id`, но иногда получает полный URL
**Детали**:
- В `quick_transcript_test.py` и `transcript_detailed_debug.py` функция вызывается с URL
- Функция `get_transcript(video_id: str, ...)` ожидает только ID видео (11 символов)
- Это приводит к ошибке: `ERROR: Unsupported URL: https://www.youtube.com/watch?v=https://youtu.be/dQw4w9WgXcQ`

### 3. Дублирование URL в yt-dlp
**Причина**: Неправильная обработка URL приводит к дублированию в запросе к yt-dlp
**Детали**:
- Видно в логе: `https://www.youtube.com/watch?v=https://youtu.be/dQw4w9WgXcQ`
- URL дублируется, что делает его недействительным

## Решения

### 1. Добавить задержки между запросами к Transcript API
```python
import time
import random

# Добавить случайную задержку между запросами
time.sleep(random.uniform(1, 3))
```

### 2. Исправить функцию get_transcript для работы с URL
```python
def get_transcript(url_or_id: str, lang_priority=("ru", "en"), use_cache=True):
    # Извлечь video_id из URL если передан URL
    video_id = extract_video_id(url_or_id)
    # Остальная логика...
```

### 3. Добавить обработку ошибок 429
```python
def get_transcript_with_retry(video_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            return get_transcript(video_id)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            raise
```

## Рекомендации

1. **Немедленно**: Исправить функцию `get_transcript()` для работы с URL
2. **Краткосрочно**: Добавить обработку ошибок 429 с повторными попытками
3. **Долгосрочно**: Реализовать более умное кэширование и ограничение частоты запросов

## Статус
- ✅ Проблема идентифицирована
- 🔄 Исправления в процессе
- ❌ Тестирование не завершено