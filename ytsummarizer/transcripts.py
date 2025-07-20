import os
import json
import time
import requests
import logging
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass

from .url_detector import URLDetector, URLType
from .youtube_blocking_detector import YouTubeBlockingDetector
from .error_handler import ErrorHandler
from .retry_logic import RetryManager, RetryConfig

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Вывод в консоль
    ]
)
logger = logging.getLogger("ytsummarizer.transcripts")

__all__ = [
    "get_transcript",
    "extract_video_id",
    "get_video_info",
    "clear_transcript_cache",
    "get_channel_info",
    "get_playlist_info", 
    "extract_video_list",
    "get_source_metadata",
    "SourceInfo",
    "VideoInfo"
]

# Создаем директорию для кэша, если её нет
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
TRANSCRIPT_CACHE_DIR = os.path.join(CACHE_DIR, "transcripts")
os.makedirs(TRANSCRIPT_CACHE_DIR, exist_ok=True)

# Время жизни кэша в секундах (7 дней)
CACHE_TTL = 7 * 24 * 60 * 60

# Global instances for blocking detection and error handling
_blocking_detector = None
_error_handler = None
_retry_manager = None

def get_blocking_detector() -> YouTubeBlockingDetector:
    """Get or create global blocking detector instance."""
    global _blocking_detector
    if _blocking_detector is None:
        _blocking_detector = YouTubeBlockingDetector()
    return _blocking_detector

def get_error_handler() -> ErrorHandler:
    """Get or create global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(get_blocking_detector())
    return _error_handler

def get_retry_manager() -> RetryManager:
    """Get or create global retry manager instance."""
    global _retry_manager
    if _retry_manager is None:
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=600.0,  # 10 minutes for YouTube operations
            exponential_base=2.0,
            jitter=True
        )
        _retry_manager = RetryManager(get_error_handler(), config)
    return _retry_manager

def youtube_api_call(func: Callable, operation_name: str, video_id: Optional[str] = None, **kwargs):
    """
    Wrapper for YouTube API calls with blocking detection and error handling.
    
    Args:
        func: Function to call
        operation_name: Name of the operation for logging
        video_id: Video ID if applicable
        **kwargs: Arguments to pass to the function
        
    Returns:
        Function result
        
    Raises:
        Exception: If operation fails after retries
    """
    context = {
        'operation': operation_name,
        'video_id': video_id,
        'timestamp': datetime.now().isoformat()
    }
    
    def wrapped_call():
        try:
            result = func(**kwargs)
            # Record success
            get_blocking_detector().record_success(operation_name, video_id)
            return result
        except Exception as e:
            # Let error handler and blocking detector process the error
            error_result = get_error_handler().handle_error(e, context)
            
            # If there's a blocking alert, log it
            if error_result.blocking_alert:
                logger.warning(f"YouTube blocking detected: {error_result.blocking_alert.message}")
            
            # Re-raise the exception to be handled by retry logic
            raise
    
    # Use retry manager for the operation
    return get_retry_manager().retry_with_backoff(
        wrapped_call,
        operation_id=f"{operation_name}_{video_id or 'unknown'}",
        context=context
    )


@dataclass
class SourceInfo:
    """Information about a YouTube source (channel or playlist)."""
    name: str
    type: URLType
    url: str
    total_videos: int
    description: Optional[str] = None
    channel_id: Optional[str] = None
    playlist_id: Optional[str] = None


@dataclass
class VideoInfo:
    """Information about a single YouTube video."""
    video_id: str
    title: str
    url: str
    duration: Optional[int] = None
    upload_date: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    description: Optional[str] = None

def get_video_info(video_id: str):
    """Возвращает информацию о видео, включая длительность."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "nocheckcertificate": True,
    }
    
    def _get_info():
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {"duration": info.get("duration"), "title": info.get("title")}
    
    try:
        return youtube_api_call(_get_info, "get_video_info", video_id)
    except Exception as e:
        logger.error(f"Error getting video info for {video_id}: {e}")
        return {"duration": None, "title": None}

def extract_video_id(url_or_id: str) -> str:
    """Возвращает идентификатор YouTube-ролика (11 символов)."""
    if not url_or_id.startswith(("http://", "https://")) and len(url_or_id) == 11:
        return url_or_id

    parsed = urlparse(url_or_id)
    if parsed.hostname and parsed.hostname.endswith("youtu.be"):
        return parsed.path.lstrip("/")[:11]

    if parsed.path == "/watch":
        vid = parse_qs(parsed.query).get("v")
        if vid:
            return vid[0][:11]

    for prefix in ("/embed/", "/v/"):
        if parsed.path.startswith(prefix):
            return parsed.path[len(prefix):len(prefix) + 11]

    return url_or_id


def clear_transcript_cache(video_id=None):
    """
    Очищает кэш транскриптов.
    
    Args:
        video_id: Если указан, очищает кэш только для этого видео.
                 Если None, очищает весь кэш.
    """
    if video_id:
        cache_file = os.path.join(TRANSCRIPT_CACHE_DIR, f"{video_id}.json")
        if os.path.exists(cache_file):
            os.remove(cache_file)
            return True
    else:
        for file in os.listdir(TRANSCRIPT_CACHE_DIR):
            if file.endswith(".json"):
                os.remove(os.path.join(TRANSCRIPT_CACHE_DIR, file))
        return True
    return False

def _get_transcript_with_blocking_detection(video_id: str, languages: list, cookies_param=None):
    """
    Получает транскрипт с интегрированным обнаружением блокировки.
    """
    def _get_transcript():
        # Check if cookies parameter is supported
        try:
            return YouTubeTranscriptApi.get_transcript(video_id, languages=languages, cookies=cookies_param)
        except TypeError as e:
            if "cookies" in str(e):
                # Fallback to version without cookies parameter
                return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            raise
    
    return youtube_api_call(_get_transcript, "get_transcript", video_id)


def get_transcript(url_or_id: str, lang_priority=("ru", "en"), use_cache=True):
    """
    Возвращает plain-text транскрипт (str). Бросает RuntimeError, если ничего не удалось.
    
    Args:
        url_or_id: URL видео на YouTube или ID видео (11 символов)
        lang_priority: Приоритет языков для транскрипта
        use_cache: Использовать ли кэширование (по умолчанию True)
    
    Returns:
        Кортеж (plain_text, processed_fragments, video_info)
    """
    # Извлекаем video_id из URL если передан URL
    video_id = extract_video_id(url_or_id)
    # Проверяем кэш, если разрешено использование кэша
    if use_cache:
        cache_file = os.path.join(TRANSCRIPT_CACHE_DIR, f"{video_id}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # Проверяем, не устарел ли кэш
                    if time.time() - cache_data.get('timestamp', 0) < CACHE_TTL:
                        return (
                            cache_data['plain_text'],
                            cache_data['fragments'],
                            cache_data['video_info']
                        )
            except (json.JSONDecodeError, KeyError):
                # Если с кэшем проблемы, игнорируем его
                pass

    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", "cookies.txt")
    cookies_param = cookies_file if os.path.exists(cookies_file) else None

    transcript = None
    used_lang = None

    # 1. youtube-transcript-api с приоритетами
    for lang in lang_priority:
        try:
            transcript = _get_transcript_with_blocking_detection(video_id, [lang], cookies_param)
            used_lang = lang
            break
        except Exception:
            transcript = None
    
    # 2. перебор всех доступных + переводимых
    if transcript is None:
        try:
            def _list_transcripts():
                try:
                    return YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies_param)
                except TypeError as e:
                    if "cookies" in str(e):
                        # Fallback to version without cookies parameter
                        return YouTubeTranscriptApi.list_transcripts(video_id)
                    raise
            
            lst = youtube_api_call(_list_transcripts, "list_transcripts", video_id)
            
            for tr in lst:
                try:
                    def _fetch_transcript():
                        return tr.fetch()
                    
                    transcript = youtube_api_call(_fetch_transcript, "fetch_transcript", video_id)
                    used_lang = tr.language_code
                    if transcript:
                        break
                except Exception:
                    pass
                
                if tr.is_translatable:
                    try:
                        target_lang = "ru" if "ru" in lang_priority else lang_priority[0]
                        
                        def _translate_transcript():
                            return tr.translate(target_lang).fetch()
                        
                        transcript = youtube_api_call(_translate_transcript, "translate_transcript", video_id)
                        used_lang = target_lang
                        if transcript:
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    # 3. fallback через yt-dlp
    if transcript is None:
        transcript, used_lang = _get_transcript_via_ytdlp(video_id, lang_priority)

    if not transcript:
        raise RuntimeError("Не удалось получить транскрипт")

    # сохранить фрагменты с таймкодами для последующего Q&A
    # Сначала получим информацию о видео, включая его длительность
    video_info = get_video_info(video_id)
    video_duration = video_info.get("duration")

    processed_fragments = []
    for i, entry in enumerate(transcript):
        start_time = entry["start"]
        # Длительность текущего фрагмента = время начала следующего - время начала текущего
        # Для последнего фрагмента: общая длительность видео - время начала последнего фрагмента
        if i < len(transcript) - 1:
            duration = transcript[i+1]["start"] - start_time
        elif video_duration is not None:
            duration = video_duration - start_time
        else:
            # Если общая длительность видео неизвестна, используем эвристику (например, 5 секунд)
            # или оставляем None, чтобы обработать это позже.
            # Для простоты пока оставим эвристическую длительность из оригинального API (поле duration в entry)
            duration = entry.get("duration", 5.0) # youtube_transcript_api добавляет поле duration

        processed_fragments.append({
            "start": start_time,
            "text": entry["text"],
            "duration": duration
        })

    plain_text = " ".join(entry["text"] for entry in processed_fragments)
    
    # Сохраняем результаты в кэш, если разрешено использование кэша
    if use_cache:
        cache_file = os.path.join(TRANSCRIPT_CACHE_DIR, f"{video_id}.json")
        try:
            cache_data = {
                'plain_text': plain_text,
                'fragments': processed_fragments,
                'video_info': video_info,
                'timestamp': time.time(),
                'language': used_lang
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении кэша: {e}")
    
    return plain_text, processed_fragments, video_info


# ---------- yt-dlp fallback ----------

def _get_transcript_via_ytdlp(video_id: str, lang_priorities):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": list(lang_priorities),
        "quiet": True,
        "nocheckcertificate": True,
    }
    
    def _extract_info():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    
    try:
        info = youtube_api_call(_extract_info, "ytdlp_extract_info", video_id)
    except Exception:
        return None, None

    for lang in lang_priorities:
        subs = None
        if info.get("subtitles") and lang in info["subtitles"]:
            subs = info["subtitles"][lang]
        elif info.get("automatic_captions") and lang in info["automatic_captions"]:
            subs = info["automatic_captions"][lang]
        if not subs:
            continue
        for track in subs:
            sub_url = track["url"]
            try:
                text = requests.get(sub_url, timeout=15).text
            except Exception:
                continue
            parsed = None
            if ".vtt" in sub_url or "format=vtt" in sub_url:
                parsed = _parse_vtt(text)
            else:
                parsed = _parse_xml_captions(text)
            if parsed:
                return parsed, lang
    return None, None


def _parse_vtt(vtt_text: str):
    import re
    pattern = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3}) --> .*")

    def ts_to_sec(ts):
        h, m, s = ts.split(":")
        sec, ms = s.split(".")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

    lines = vtt_text.splitlines()
    fragments = []
    i = 0
    while i < len(lines):
        match = pattern.match(lines[i])
        if match:
            start_ts = match.group(1)
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip() != "":
                text_lines.append(lines[i])
                i += 1
            fragments.append({"start": ts_to_sec(start_ts), "text": " ".join(text_lines)})
        i += 1
    return fragments if fragments else None


def _parse_xml_captions(xml_text: str):
    import re, html
    entries = []
    for m in re.finditer(r'<text start="(?P<start>[\d\.]+)"[^>]*?>(?P<text>.*?)</text>', xml_text, flags=re.DOTALL):
        start = float(m.group("start"))
        text = html.unescape(m.group("text").replace("\n", " ")).strip()
        if text:
            entries.append({"start": start, "text": text})
    return entries if entries else None


# ---------- Batch Processing Functions ----------

def get_channel_info(channel_url: str) -> Optional[SourceInfo]:
    """
    Get information about a YouTube channel.
    
    Args:
        channel_url: URL of the YouTube channel
        
    Returns:
        SourceInfo object with channel metadata or None if failed
    """
    detector = URLDetector()
    if detector.detect_url_type(channel_url) != URLType.CHANNEL:
        return None
    
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "nocheckcertificate": True,
        "extract_flat": True,  # Don't extract individual video info
    }
    
    def _extract_channel_info():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(channel_url, download=False)
    
    try:
        info = youtube_api_call(_extract_channel_info, "get_channel_info")
        
        # Sanitize channel name for folder creation
        channel_name = info.get("title", "Unknown Channel")
        safe_name = _sanitize_folder_name(channel_name)
        
        return SourceInfo(
            name=safe_name,
            type=URLType.CHANNEL,
            url=channel_url,
            total_videos=len(info.get("entries", [])),
            description=info.get("description"),
            channel_id=info.get("channel_id") or info.get("id")
        )
    except Exception as e:
        logger.error(f"Error getting channel info: {e}")
        return None


def get_playlist_info(playlist_url: str) -> Optional[SourceInfo]:
    """
    Get information about a YouTube playlist.
    
    Args:
        playlist_url: URL of the YouTube playlist
        
    Returns:
        SourceInfo object with playlist metadata or None if failed
    """
    detector = URLDetector()
    if detector.detect_url_type(playlist_url) != URLType.PLAYLIST:
        return None
    
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "nocheckcertificate": True,
        "extract_flat": True,  # Don't extract individual video info
    }
    
    def _extract_playlist_info():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(playlist_url, download=False)
    
    try:
        info = youtube_api_call(_extract_playlist_info, "get_playlist_info")
        
        # Sanitize playlist name for folder creation
        playlist_name = info.get("title", "Unknown Playlist")
        safe_name = _sanitize_folder_name(playlist_name)
        
        return SourceInfo(
            name=safe_name,
            type=URLType.PLAYLIST,
            url=playlist_url,
            total_videos=len(info.get("entries", [])),
            description=info.get("description"),
            playlist_id=info.get("id")
        )
    except Exception as e:
        logger.error(f"Error getting playlist info: {e}")
        return None


def extract_video_list(source_url: str, limit: Optional[int] = None) -> List[VideoInfo]:
    """
    Extract list of videos from a channel or playlist.
    
    Args:
        source_url: URL of the channel or playlist
        limit: Maximum number of videos to extract (None for all)
        
    Returns:
        List of VideoInfo objects
    """
    detector = URLDetector()
    url_type = detector.detect_url_type(source_url)
    
    if url_type not in [URLType.CHANNEL, URLType.PLAYLIST]:
        return []
    
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "nocheckcertificate": True,
        "extract_flat": False,  # Extract individual video info
        "ignoreerrors": True,   # Continue processing even if some videos fail
    }
    
    # Add playlist limit if specified
    if limit:
        ydl_opts["playlistend"] = limit
    
    def _extract_video_list():
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(source_url, download=False)
    
    try:
        info = youtube_api_call(_extract_video_list, "extract_video_list")
        
        videos = []
        entries = info.get("entries", [])
        
        for entry in entries:
            if not entry:  # Skip None entries (unavailable videos)
                continue
            
            video_id = entry.get("id")
            if not video_id:
                continue
            
            # Check for age restrictions or login requirements
            title = entry.get("title", "Unknown Title")
            if _is_video_restricted(entry):
                continue
            
            # Parse upload date
            upload_date = None
            if entry.get("upload_date"):
                try:
                    upload_date = datetime.strptime(entry["upload_date"], "%Y%m%d")
                except ValueError:
                    pass
            
            video_info = VideoInfo(
                video_id=video_id,
                title=title,
                url=f"https://www.youtube.com/watch?v={video_id}",
                duration=entry.get("duration"),
                upload_date=upload_date,
                thumbnail_url=entry.get("thumbnail"),
                view_count=entry.get("view_count"),
                description=entry.get("description")
            )
            videos.append(video_info)
        
        return videos
        
    except Exception as e:
        logger.error(f"Error extracting video list: {e}")
        return []


def _is_video_restricted(entry: dict) -> bool:
    """
    Check if a video has age restrictions or requires login.
    
    Args:
        entry: Video entry from yt-dlp
        
    Returns:
        True if video is restricted and should be skipped
    """
    # Check for age restriction indicators
    age_limit = entry.get("age_limit", 0)
    if age_limit and age_limit > 0:
        return True
    
    # Check for availability status
    availability = entry.get("availability")
    if availability in ["needs_auth", "premium_only", "subscriber_only"]:
        return True
    
    # Check for live streams (often problematic)
    if entry.get("is_live") or entry.get("was_live"):
        return True
    
    # Check title for common age restriction indicators
    title = entry.get("title", "").lower()
    restricted_keywords = ["age restricted", "sign in", "login required", "private video"]
    if any(keyword in title for keyword in restricted_keywords):
        return True
    
    return False


def get_source_metadata(source_url: str) -> Optional[SourceInfo]:
    """
    Get metadata about a YouTube source (channel or playlist).
    
    Args:
        source_url: URL of the source
        
    Returns:
        SourceInfo object or None if failed
    """
    detector = URLDetector()
    url_type = detector.detect_url_type(source_url)
    
    if url_type == URLType.CHANNEL:
        return get_channel_info(source_url)
    elif url_type == URLType.PLAYLIST:
        return get_playlist_info(source_url)
    else:
        return None


def _sanitize_folder_name(name: str, max_length: int = 50) -> str:
    """
    Sanitize a string to be safe for use as a folder name.
    
    Args:
        name: The original name
        max_length: Maximum length of the sanitized name
        
    Returns:
        Sanitized folder name
    """
    if not name:
        return "Unknown"
    
    # Replace invalid characters with underscores
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    
    # Replace multiple spaces with single spaces
    name = ' '.join(name.split())
    
    # Truncate if too long
    if len(name) > max_length:
        name = name[:max_length].rstrip()
    
    # Ensure it's not empty after sanitization
    if not name.strip():
        return "Unknown"
    
    return name.strip()


def get_youtube_blocking_status() -> Dict[str, Any]:
    """
    Get current YouTube blocking detection status.
    
    Returns:
        Dictionary with blocking status information
    """
    return get_blocking_detector().get_current_status()


def reset_blocking_detector():
    """Reset the YouTube blocking detector state."""
    get_blocking_detector().reset()


def is_youtube_blocked() -> bool:
    """
    Check if YouTube is currently blocking requests.
    
    Returns:
        True if likely blocked
    """
    return get_blocking_detector().is_likely_blocked()


def should_pause_youtube_requests() -> bool:
    """
    Check if YouTube requests should be paused due to blocking.
    
    Returns:
        True if requests should be paused
    """
    return get_blocking_detector().should_pause_requests()


def get_recommended_wait_time() -> int:
    """
    Get recommended wait time before retrying YouTube requests.
    
    Returns:
        Wait time in seconds
    """
    return get_blocking_detector().get_recommended_wait_time()