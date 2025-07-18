"""
URL Detection Module for YouTube Tools

This module provides functionality to detect and classify YouTube URLs,
determining whether they point to single videos, channels, or playlists.
"""

import re
from enum import Enum
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any


class URLType(Enum):
    """Enumeration of supported YouTube URL types."""
    SINGLE_VIDEO = "video"
    CHANNEL = "channel"
    PLAYLIST = "playlist"
    INVALID = "invalid"


class URLDetector:
    """
    Detects and classifies YouTube URLs.
    
    Supports detection of:
    - Single video URLs (youtube.com/watch?v=..., youtu.be/...)
    - Channel URLs (youtube.com/channel/..., youtube.com/@username, youtube.com/c/...)
    - Playlist URLs (youtube.com/playlist?list=...)
    """
    
    # Regex patterns for different URL types
    VIDEO_PATTERNS = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
    ]
    
    CHANNEL_PATTERNS = [
        r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        r'youtube\.com/@([a-zA-Z0-9_.-]+)',
        r'youtube\.com/c/([a-zA-Z0-9_.-]+)',
        r'youtube\.com/user/([a-zA-Z0-9_.-]+)',
    ]
    
    PLAYLIST_PATTERNS = [
        r'youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
        r'youtube\.com/watch\?.*list=([a-zA-Z0-9_-]+)',
    ]
    
    def __init__(self):
        """Initialize the URL detector with compiled regex patterns."""
        self.video_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.VIDEO_PATTERNS]
        self.channel_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.CHANNEL_PATTERNS]
        self.playlist_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.PLAYLIST_PATTERNS]
    
    def detect_url_type(self, url: str) -> URLType:
        """
        Detect the type of YouTube URL.
        
        Args:
            url: The URL to analyze
            
        Returns:
            URLType enum indicating the type of URL
        """
        if not url or not isinstance(url, str):
            return URLType.INVALID
        
        url = url.strip()
        
        # Handle case where user provides just a video ID (11 characters)
        if len(url) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return URLType.SINGLE_VIDEO
        
        # Check if it's a valid URL
        if not self._is_valid_url(url):
            return URLType.INVALID
        
        # Check for playlist URLs first (they can contain video IDs too)
        for regex in self.playlist_regexes:
            if regex.search(url):
                return URLType.PLAYLIST
        
        # Check for video URLs
        for regex in self.video_regexes:
            if regex.search(url):
                return URLType.SINGLE_VIDEO
        
        # Check for channel URLs
        for regex in self.channel_regexes:
            if regex.search(url):
                return URLType.CHANNEL
        
        return URLType.INVALID
    
    def extract_source_id(self, url: str) -> Optional[str]:
        """
        Extract the relevant ID from a YouTube URL.
        
        Args:
            url: The URL to extract ID from
            
        Returns:
            The extracted ID (video ID, channel ID, playlist ID) or None if not found
        """
        if not url or not isinstance(url, str):
            return None
        
        url = url.strip()
        
        # Handle case where user provides just a video ID
        if len(url) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        
        url_type = self.detect_url_type(url)
        
        if url_type == URLType.SINGLE_VIDEO:
            for regex in self.video_regexes:
                match = regex.search(url)
                if match:
                    return match.group(1)
        
        elif url_type == URLType.CHANNEL:
            for regex in self.channel_regexes:
                match = regex.search(url)
                if match:
                    return match.group(1)
        
        elif url_type == URLType.PLAYLIST:
            for regex in self.playlist_regexes:
                match = regex.search(url)
                if match:
                    return match.group(1)
        
        return None
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if the URL is a supported YouTube URL.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if the URL is valid and supported, False otherwise
        """
        return self.detect_url_type(url) != URLType.INVALID
    
    def get_url_info(self, url: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a YouTube URL.
        
        Args:
            url: The URL to analyze
            
        Returns:
            Dictionary containing URL type, extracted ID, and other metadata
        """
        url_type = self.detect_url_type(url)
        source_id = self.extract_source_id(url)
        
        info = {
            'url': url,
            'type': url_type,
            'source_id': source_id,
            'is_valid': url_type != URLType.INVALID,
        }
        
        # Add type-specific information
        if url_type == URLType.SINGLE_VIDEO:
            info['video_url'] = f"https://www.youtube.com/watch?v={source_id}" if source_id else None
        elif url_type == URLType.CHANNEL:
            info['channel_url'] = self._normalize_channel_url(url, source_id)
        elif url_type == URLType.PLAYLIST:
            info['playlist_url'] = f"https://www.youtube.com/playlist?list={source_id}" if source_id else None
        
        return info
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Check if the string is a valid URL format.
        
        Args:
            url: The string to check
            
        Returns:
            True if it's a valid URL format, False otherwise
        """
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme)
        except Exception:
            return False
    
    def _normalize_channel_url(self, original_url: str, channel_id: str) -> Optional[str]:
        """
        Normalize channel URL to a standard format.
        
        Args:
            original_url: The original channel URL
            channel_id: The extracted channel ID
            
        Returns:
            Normalized channel URL or None if normalization fails
        """
        if not channel_id:
            return None
        
        # If it's already a channel ID format, use it directly
        if '/channel/' in original_url:
            return f"https://www.youtube.com/channel/{channel_id}"
        
        # For @username, /c/, or /user/ formats, preserve the original format
        # as they might be more user-friendly
        if original_url.startswith('http'):
            return original_url
        else:
            return f"https://www.youtube.com/{original_url}"


# Convenience functions for backward compatibility and ease of use
def detect_url_type(url: str) -> URLType:
    """Convenience function to detect URL type."""
    detector = URLDetector()
    return detector.detect_url_type(url)


def extract_source_id(url: str) -> Optional[str]:
    """Convenience function to extract source ID."""
    detector = URLDetector()
    return detector.extract_source_id(url)


def validate_url(url: str) -> bool:
    """Convenience function to validate URL."""
    detector = URLDetector()
    return detector.validate_url(url)


def get_url_info(url: str) -> Dict[str, Any]:
    """Convenience function to get URL info."""
    detector = URLDetector()
    return detector.get_url_info(url)