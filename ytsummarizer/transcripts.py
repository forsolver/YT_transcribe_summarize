import os
import json
import time
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from .url_detector import URLDetector, URLType

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
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {"duration": info.get("duration"), "title": info.get("title")}
    except Exception as e:
        # print(f"Error getting video info: {e}")
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

def get_transcript(video_id: str, lang_priority=("ru", "en"), use_cache=True):
    """
    Возвращает plain-text транскрипт (str). Бросает RuntimeError, если ничего не удалось.
    
    Args:
        video_id: ID видео на YouTube
        lang_priority: Приоритет языков для транскрипта
        use_cache: Использовать ли кэширование (по умолчанию True)
    
    Returns:
        Кортеж (plain_text, processed_fragments, video_info)
    """
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
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang], cookies=cookies_param)
            used_lang = lang
            break
        except Exception:
            transcript = None
    
    # 2. перебор всех доступных + переводимых
    if transcript is None:
        try:
            lst = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies_param)
            for tr in lst:
                try:
                    transcript = tr.fetch()
                    used_lang = tr.language_code
                    if transcript:
                        break
                except Exception:
                    pass
                if tr.is_translatable:
                    try:
                        target_lang = "ru" if "ru" in lang_priority else lang_priority[0]
                        transcript = tr.translate(target_lang).fetch()
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
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
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
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
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
        print(f"Error getting channel info: {e}")
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
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            
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
        print(f"Error getting playlist info: {e}")
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
    }
    
    # Add playlist limit if specified
    if limit:
        ydl_opts["playlistend"] = limit
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source_url, download=False)
            
            videos = []
            entries = info.get("entries", [])
            
            for entry in entries:
                if not entry:  # Skip None entries (unavailable videos)
                    continue
                
                video_id = entry.get("id")
                if not video_id:
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
                    title=entry.get("title", "Unknown Title"),
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
        print(f"Error extracting video list: {e}")
        return []


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