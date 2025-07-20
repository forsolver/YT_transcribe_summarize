# Исправление ошибки 'duration' в ручных транскриптах

## Проблема

При использовании функции ручного ввода транскрипта возникала ошибка:
```
Ошибка при анализе видео: 'duration'
```

## Причина

Метод `extract_trick_segments` в `video_processor.py` ожидает, что каждый фрагмент транскрипта содержит поле `'duration'`:

```python
duration = fragment.get("duration", 0.0)
```

Однако ручные транскрипты создавали фрагменты только с полями `'start'` и `'text'`, без поля `'duration'`.

## Решение

### 1. Добавлен метод `_calculate_fragment_durations()`

Новый метод в классе `ManualTranscriptDialog` вычисляет длительность для каждого фрагмента:

```python
def _calculate_fragment_durations(self, fragments):
    """Calculate duration for each fragment based on timestamps and text length."""
    for i, fragment in enumerate(fragments):
        if i < len(fragments) - 1:
            # Duration is the time until the next fragment starts
            next_start = fragments[i + 1]['start']
            fragment['duration'] = next_start - fragment['start']
        else:
            # For the last fragment, estimate duration based on text length
            text = fragment.get('text', '')
            estimated_duration = len(text.split()) * 0.5  # ~0.5 seconds per word
            # Minimum duration of 1 second, maximum of 30 seconds for estimation
            fragment['duration'] = max(1.0, min(30.0, estimated_duration))
```

### 2. Модифицирован метод `parse_manual_transcript()`

Добавлен вызов расчета длительности после создания фрагментов:

```python
# Calculate duration for each fragment
self._calculate_fragment_durations(fragments)
```

## Алгоритм расчета длительности

### Для фрагментов с временными метками:
- **Длительность = время_следующего_фрагмента - время_текущего_фрагмента**
- Пример: фрагмент с 0:15 до 0:30 имеет длительность 15 секунд

### Для последнего фрагмента:
- **Оценка на основе количества слов**: 0.5 секунды на слово
- **Ограничения**: минимум 1 секунда, максимум 30 секунд
- Пример: текст из 20 слов = 10 секунд длительности

## Результат

После исправления:
- ✅ Все фрагменты ручных транскриптов содержат поле `'duration'`
- ✅ Метод `extract_trick_segments` работает корректно
- ✅ Анализ трюков выполняется без ошибок
- ✅ Полная совместимость с автоматическими транскриптами

## Тестирование

Создан тестовый скрипт `scripts/test_duration_fix.py` для проверки исправления:
- Проверка наличия поля `'duration'` во всех фрагментах
- Тестирование анализа трюков с ручными транскриптами
- Валидация корректности вычисленных длительностей

## Совместимость

Исправление полностью обратно совместимо:
- Автоматические транскрипты продолжают работать как прежде
- Существующий код не требует изменений
- Новая функциональность прозрачна для пользователя