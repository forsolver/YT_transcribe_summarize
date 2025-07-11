import re

DEFAULT_MIN_SILENCE_DURATION = 2.0  # Минимальная длительность "тихого" сегмента в секундах, чтобы считать его трюком
DEFAULT_MAX_WORDS_IN_TRICK_SEGMENT = 3 # Максимальное количество слов в сегменте, чтобы он считался "тихим"
MUSIC_TAG_PATTERN = re.compile(r"\[музыка\]", re.IGNORECASE)

def extract_trick_segments(
    fragments: list[dict],
    min_silence_duration: float = DEFAULT_MIN_SILENCE_DURATION,
    max_words_in_segment: int = DEFAULT_MAX_WORDS_IN_TRICK_SEGMENT
) -> list[dict]:
    """
    Извлекает из списка фрагментов транскрипта временные интервалы,
    предположительно содержащие трюки.

    Трюками считаются сегменты с минимальным количеством текста и достаточной длительностью.

    Args:
        fragments: Список словарей, где каждый словарь содержит:
            'start': время начала фрагмента (float, секунды)
            'text': текст фрагмента (str)
            'duration': длительность фрагмента (float, секунды)
        min_silence_duration: Минимальная общая длительность последовательных
                              "тихих" фрагментов, чтобы считать их за один трюковой сегмент.
        max_words_in_segment: Максимальное количество слов в тексте фрагмента,
                               чтобы он считался "тихим". Фрагменты, содержащие
                               только '[музыка]' также считаются тихими.

    Returns:
        Список словарей, где каждый словарь представляет трюковый сегмент:
            'start': время начала трюка (float, секунды)
            'end': время окончания трюка (float, секунды)
            'duration': длительность трюка (float, секунды)
    """
    trick_segments = []
    current_trick_start_time = None
    current_trick_accumulated_duration = 0.0
    last_fragment_end_time = 0.0

    if not fragments:
        return []

    for i, fragment in enumerate(fragments):
        text = fragment.get("text", "").strip()
        duration = fragment.get("duration", 0.0)
        start_time = fragment.get("start", 0.0)

        # Рассчитываем конец текущего фрагмента для корректного определения конца трюка
        # Если это не последний фрагмент, и следующий фрагмент существует
        if i + 1 < len(fragments):
            actual_end_time = fragments[i+1]["start"]
        else: # для последнего фрагмента
            actual_end_time = start_time + duration

        # Обновляем время окончания предыдущего фрагмента
        # Это нужно, чтобы правильно установить начало первого "тихого" фрагмента в серии
        if i > 0:
            last_fragment_end_time = fragments[i-1]["start"] + fragments[i-1]["duration"]
        else: # для самого первого фрагмента
             last_fragment_end_time = 0.0


        words = text.split()
        is_silent_text = (
            len(words) <= max_words_in_segment and not (len(words) > 0 and MUSIC_TAG_PATTERN.fullmatch(words[0]) is None and len(words[0]) > 1)
        ) or MUSIC_TAG_PATTERN.search(text) is not None


        if is_silent_text:
            if current_trick_start_time is None:
                # Начало нового потенциального трюка.
                # Если предыдущий фрагмент был текстовым, трюк начинается с текущего start_time.
                # Если это первый фрагмент или предыдущий тоже был "тихим" (что покрывается логикой объединения),
                # используем start_time текущего фрагмента.
                current_trick_start_time = start_time

            current_trick_accumulated_duration += duration
        else:
            # Сегмент с текстом, проверяем, был ли накоплен трюк
            if current_trick_start_time is not None and current_trick_accumulated_duration >= min_silence_duration:
                trick_end_time = start_time # Трюк заканчивается там, где начался текстовый сегмент
                trick_segments.append({
                    "start": current_trick_start_time,
                    "end": trick_end_time,
                    "duration": trick_end_time - current_trick_start_time
                })
            # Сбрасываем текущий трюк
            current_trick_start_time = None
            current_trick_accumulated_duration = 0.0

        last_fragment_end_time = actual_end_time


    # Проверка после цикла, если последний сегмент был частью трюка
    if current_trick_start_time is not None and current_trick_accumulated_duration >= min_silence_duration:
        # Конец последнего трюка - это конец последнего "тихого" фрагмента
        # Используем actual_end_time последнего обработанного фрагмента, если он был тихим
        # или start_time последнего + его duration
        final_trick_end_time = last_fragment_end_time # Это будет время конца последнего фрагмента в "тихой" серии

        trick_segments.append({
            "start": current_trick_start_time,
            "end": final_trick_end_time,
            "duration": final_trick_end_time - current_trick_start_time
        })

    return trick_segments
