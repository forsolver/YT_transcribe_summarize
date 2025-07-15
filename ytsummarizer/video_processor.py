import re
import os
import subprocess
from yt_dlp import YoutubeDL
from datetime import timedelta

DEFAULT_MIN_SILENCE_DURATION = 2.0  # Минимальная длительность "тихого" сегмента в секундах, чтобы считать его трюком
DEFAULT_MAX_WORDS_IN_TRICK_SEGMENT = 3 # Максимальное количество слов в сегменте, чтобы он считался "тихим"
MUSIC_TAG_PATTERN = re.compile(r"\[музыка\]", re.IGNORECASE)

def extract_trick_segments(
    fragments: list[dict],
    min_silence_duration: float = 10.0,  # Увеличиваем минимальную длительность до 10 секунд
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


def _find_nearest_keyframe(video_file: str, timestamp: float) -> float | None:
    """
    Находит ближайший ключевой кадр (I-frame) перед указанным тайм-кодом.
    Возвращает тайм-код ключевого кадра или None, если не найден.
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'frame=key_frame,pkt_pts_time',
        '-of', 'csv=p=0',
        video_file
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        keyframe_times = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(',')
            if len(parts) != 2:
                continue
            is_key, time_str = parts
            if is_key == '1' and time_str not in ('N/A', ''):
                try:
                    keyframe_times.append(float(time_str))
                except ValueError:
                    continue

        # Найти последний ключевой кадр, который меньше или равен timestamp
        valid_keyframes = [t for t in keyframe_times if t <= timestamp]
        if valid_keyframes:
            return max(valid_keyframes)
        return 0.0  # Если до тайм-кода нет ключей, начинаем с самого начала
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Если ffprobe не найден или выдал ошибку, возвращаем None, чтобы использовать перекодирование
        print("ffprobe не найден. Будет применено перекодирование для точной нарезки.")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка при работе с ffprobe: {e}")
        return None


def extract_video_segments(video_id: str, segments: list[dict], output_dir: str = "tricks", reencode_threshold: float = 0.5) -> list[str]:
    """
    Извлекает видео сегменты из YouTube видео в максимальном качестве,
    избегая черных экранов в начале.
    
    Args:
        video_id: ID YouTube видео
        segments: Список сегментов с полями 'start', 'end', 'duration'
        output_dir: Директория для сохранения сегментов
        
    Returns:
        Список путей к созданным видео файлам
    """
    if not segments:
        return []
    
    # Фильтруем сегменты - оставляем только те, что длиннее 10 секунд
    valid_segments = [seg for seg in segments if seg['duration'] >= 10.0]
    
    if not valid_segments:
        print("Нет сегментов длиннее 10 секунд")
        return []
    
    # Создаем директорию для сохранения
    os.makedirs(output_dir, exist_ok=True)
    
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Скачиваем видео в максимальном доступном качестве (отдельно видео+аудио, затем мерж)
    download_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',  # максимум 1080p
        'outtmpl': os.path.join(output_dir, f'{video_id}.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',  # объединяем в mp4
    }

    try:
        with YoutubeDL(download_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)

        # Ищем фактически скачанный файл (может быть с другим расширением)
        video_file_base = os.path.splitext(video_file)[0]
        possible_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov']
        actual_video_file = None
        
        for ext in possible_extensions:
            test_file = video_file_base + ext
            if os.path.exists(test_file):
                actual_video_file = test_file
                break
                
        if not actual_video_file:
            # Ищем любой файл с нужным video_id в папке
            for file in os.listdir(output_dir):
                if file.startswith(video_id):
                    actual_video_file = os.path.join(output_dir, file)
                    break
                    
        if not actual_video_file or not os.path.exists(actual_video_file):
            raise RuntimeError(f"Не удалось найти скачанный файл для {video_id}")
            
        video_file = actual_video_file
        print(f"Скачан файл: {os.path.basename(video_file)}")

        # Извлекаем сегменты с помощью ffmpeg
        segment_files = []
        for i, segment in enumerate(valid_segments):
            start_time = segment['start']
            duration = segment['duration']
            end_time = start_time + duration

            # Определяем стратегию нарезки
            nearest_keyframe_time = _find_nearest_keyframe(video_file, start_time)
            
            cmd = []
            segment_filename = ""

            # Если ffprobe не сработал или ключевой кадр слишком далеко -> перекодируем
            if nearest_keyframe_time is None or (start_time - nearest_keyframe_time > reencode_threshold):
                print(f"Сегмент {i+1}: Ключевой кадр далеко/не найден. Применяем точное перекодирование.")
                start_str = _seconds_to_ffmpeg_time(start_time)
                duration_str = _seconds_to_ffmpeg_time(duration)
                segment_filename = f"{video_id}_trick_{i+1}_{start_str.replace(':', '-')}_({duration:.1f}s)_re-encoded.mp4"
                segment_path = os.path.join(output_dir, segment_filename)
                cmd = [
                    'ffmpeg',
                    '-i', video_file,
                    '-ss', start_str,
                    '-t', duration_str,
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '18',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    segment_path,
                    '-y'
                ]
            else:
                # Иначе используем быструю нарезку, начиная с ближайшего ключевого кадра
                print(f"Сегмент {i+1}: Ключевой кадр близко. Применяем быструю нарезку.")
                start_str = _seconds_to_ffmpeg_time(nearest_keyframe_time)
                duration_str = _seconds_to_ffmpeg_time(duration)
                requested_start_str_for_fn = _seconds_to_ffmpeg_time(start_time).replace(':', '-')
                segment_filename = f"{video_id}_trick_{i+1}_{requested_start_str_for_fn}_({duration:.1f}s)_copied.mp4"
                segment_path = os.path.join(output_dir, segment_filename)
                cmd = [
                    'ffmpeg',
                    '-ss', start_str,  # быстрый seek к ключу
                    '-i', video_file,
                    '-t', duration_str,
                    '-c', 'copy',
                    '-map', '0',
                    '-avoid_negative_ts', 'make_zero',
                    segment_path,
                    '-y'
                ]

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                segment_files.append(segment_path)
                print(f"-> Создан сегмент: {segment_filename}")
            except subprocess.CalledProcessError as e:
                print(f"Ошибка при извлечении сегмента {i+1} ({segment_filename}):\n{e.stderr}")
                continue

        # Удаляем исходное видео после извлечения сегментов
        try:
            os.remove(video_file)
        except OSError:
            pass
            
        return segment_files

    except Exception as e:
        raise RuntimeError(f"Ошибка при извлечении видео сегментов: {e}")


def _seconds_to_ffmpeg_time(seconds: float) -> str:
    """Конвертирует секунды в формат времени ffmpeg (HH:MM:SS.mmm)"""
    if not isinstance(seconds, (int, float)):
        seconds = 0.0
    td = timedelta(seconds=seconds)
    return str(td)
