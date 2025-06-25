import os
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL

__all__ = [
    "get_transcript",
    "extract_video_id"
]

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


def get_transcript(video_id: str, lang_priority=("ru", "en")):
    """Возвращает plain-text транскрипт (str). Бросает RuntimeError, если ничего не удалось."""
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", "cookies.txt")
    cookies_param = cookies_file if os.path.exists(cookies_file) else None

    transcript = None

    # 1. youtube-transcript-api с приоритетами
    for lang in lang_priority:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang], cookies=cookies_param)
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
                    if transcript:
                        break
                except Exception:
                    pass
                if tr.is_translatable:
                    try:
                        transcript = tr.translate("ru" if "ru" in lang_priority else lang_priority[0]).fetch()
                        if transcript:
                            break
                    except Exception:
                        pass
        except Exception:
            pass

    # 3. fallback через yt-dlp
    if transcript is None:
        transcript = _get_transcript_via_ytdlp(video_id, lang_priority)

    if not transcript:
        raise RuntimeError("Не удалось получить транскрипт")

    # сохранить фрагменты с таймкодами для последующего Q&A
    fragments = [{"start": entry["start"], "text": entry["text"]} for entry in transcript]
    plain = " ".join(entry["text"] for entry in transcript)
    return plain, fragments


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
        return None

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
                return parsed
    return None


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