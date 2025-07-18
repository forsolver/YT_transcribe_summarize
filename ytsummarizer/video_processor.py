import re
import os
import subprocess
from yt_dlp import YoutubeDL

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

def extract_video_segments(video_id: str, segments: list[dict], output_dir: str = "tricks", video_info: dict = None) -> list[str]:
    """
    Извлекает видео сегменты из YouTube видео в максимальном качестве.
    
    Args:
        video_id: ID YouTube видео
        segments: Список сегментов с полями 'start', 'end', 'duration'
        output_dir: Директория для сохранения сегментов (может быть уже подготовленной для batch processing)
        video_info: Информация о видео (title, duration)
        
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
    
    # Определяем выходную директорию
    # Если output_dir уже содержит полный путь (для batch processing), используем его как есть
    # Иначе создаем структуру как раньше (для backward compatibility)
    if os.path.basename(output_dir) != "tricks" and os.path.exists(output_dir):
        # Batch processing mode - output_dir уже подготовлен
        video_output_dir = output_dir
    else:
        # Single video mode - создаем структуру как раньше
        os.makedirs(output_dir, exist_ok=True)
        
        # Получаем название видео и создаем подпапку
        video_title = "Unnamed_Video"
        if video_info and video_info.get("title"):
            video_title = video_info.get("title")
        
        # Создаем безопасное имя папки из названия видео
        safe_folder_name = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in video_title])
        safe_folder_name = safe_folder_name.strip()[:50]  # Ограничиваем длину
        if not safe_folder_name:  # Если после очистки имя пустое
            safe_folder_name = f"video_{video_id}"
        
        # Создаем подпапку для этого видео
        video_output_dir = os.path.join(output_dir, safe_folder_name)
        os.makedirs(video_output_dir, exist_ok=True)
    
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Скачиваем видео в качестве до 1080p для оптимизации скорости и размера
    download_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',  # ограничиваем качество до 1080p
        'outtmpl': os.path.join(video_output_dir, f'{video_id}.%(ext)s'),
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
            for file in os.listdir(video_output_dir):
                if file.startswith(video_id):
                    actual_video_file = os.path.join(video_output_dir, file)
                    break
                    
        if not actual_video_file or not os.path.exists(actual_video_file):
            raise RuntimeError(f"Не удалось найти скачанный файл для {video_id}")
            
        video_file = actual_video_file
        print(f"Скачан файл: {os.path.basename(video_file)}")
            
        # Извлекаем сегменты с помощью ffmpeg
        print(f"[DEBUG] Starting extraction of {len(valid_segments)} video segments")
        segment_files = []
        for i, segment in enumerate(valid_segments):
            print(f"[DEBUG] Processing segment {i+1}/{len(valid_segments)}")
            # Корректируем время начала, чтобы избежать черного экрана в начале
            # Вычитаем 2 секунды, но не уходим в отрицательное время
            start_time = max(0, segment['start'] - 2.0)
            
            # Корректируем длительность, чтобы компенсировать смещение начала
            # Если мы сместили начало на 2 секунды, добавляем 2 секунды к длительности
            duration_adjustment = segment['start'] - start_time
            duration = segment['duration'] + duration_adjustment
            
            # Форматируем время для ffmpeg
            start_str = _seconds_to_ffmpeg_time(start_time)
            duration_str = _seconds_to_ffmpeg_time(duration)
            
            # Имя файла сегмента
            segment_filename = f"trick_{i+1}_{start_str.replace(':', '-')}_({duration:.1f}s).mp4"
            segment_path = os.path.join(video_output_dir, segment_filename)
            
            # Команда ffmpeg для извлечения сегмента - с fallback на перекодирование
            cmd_copy = [
                'ffmpeg',
                '-ss', start_str,  # Точное позиционирование перед входным файлом
                '-i', video_file,
                '-t', duration_str,
                '-c', 'copy',  # Копируем без перекодирования
                '-avoid_negative_ts', 'make_zero',  # Исправляем отрицательные временные метки
                segment_path,
                '-y'  # Перезаписываем файл если существует
            ]
            
            # Fallback команда с перекодированием для проблемных файлов
            cmd_reencode = [
                'ffmpeg',
                '-ss', start_str,
                '-i', video_file,
                '-t', duration_str,
                '-c:v', 'libx264',  # Перекодируем видео
                '-c:a', 'aac',      # Перекодируем аудио
                '-preset', 'fast',   # Быстрое кодирование
                '-crf', '23',        # Хорошее качество
                segment_path,
                '-y'
            ]
            
            success = False
            
            # Сначала пробуем копирование (быстрее)
            try:
                print(f"[DEBUG] Trying copy mode for segment {i+1}...")
                result = subprocess.run(cmd_copy, check=True, capture_output=True, text=True)
                
                # Проверяем, что файл создался и не пустой
                if os.path.exists(segment_path) and os.path.getsize(segment_path) > 1000:
                    segment_files.append(segment_path)
                    print(f"Создан сегмент {i+1} (copy mode): {segment_filename}")
                    success = True
                else:
                    print(f"[DEBUG] Copy mode created empty/small file for segment {i+1}")
                    if os.path.exists(segment_path):
                        os.remove(segment_path)
                    
            except subprocess.CalledProcessError as e:
                print(f"[DEBUG] Copy mode failed for segment {i+1}: {e.stderr}")
            
            # Если копирование не сработало, пробуем перекодирование
            if not success:
                try:
                    print(f"[DEBUG] Trying re-encode mode for segment {i+1}...")
                    result = subprocess.run(cmd_reencode, check=True, capture_output=True, text=True)
                    
                    if os.path.exists(segment_path) and os.path.getsize(segment_path) > 1000:
                        segment_files.append(segment_path)
                        print(f"Создан сегмент {i+1} (re-encode mode): {segment_filename}")
                        success = True
                    else:
                        print(f"[DEBUG] Re-encode mode created empty/small file for segment {i+1}")
                        
                except subprocess.CalledProcessError as e:
                    print(f"Ошибка при извлечении сегмента {i+1} (re-encode): {e.stderr}")
            
            if not success:
                print(f"[ERROR] Failed to create segment {i+1} with both copy and re-encode modes")
                continue
        
        # Удаляем исходное видео после извлечения сегментов
        print(f"[DEBUG] Attempting to remove source video file: {os.path.basename(video_file)}")
        try:
            # На Windows файл может быть заблокирован, добавляем небольшую задержку
            import time
            time.sleep(1)
            
            if os.path.exists(video_file):
                os.remove(video_file)
                print(f"[DEBUG] Successfully removed source video file")
            else:
                print(f"[DEBUG] Source video file already removed or doesn't exist")
        except OSError as e:
            print(f"[DEBUG] Could not remove source video file: {e} (this is not critical)")
            pass
        
        print(f"[DEBUG] extract_video_segments completed successfully, returning {len(segment_files)} files")
        return segment_files

    except Exception as e:
        raise RuntimeError(f"Ошибка при извлечении видео сегментов: {e}")

def _seconds_to_ffmpeg_time(seconds: float) -> str:
    """Конвертирует секунды в формат времени ffmpeg (HH:MM:SS)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
