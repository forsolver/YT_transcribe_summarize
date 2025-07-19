"""
Debug script to test URL detection for playlists
"""

import sys
import os

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ytsummarizer.url_detector import URLDetector, URLType

def test_url_detection():
    """Test URL detection with various playlist formats."""
    detector = URLDetector()
    
    # Test various playlist URL formats
    test_urls = [
        # Standard playlist URLs
        "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G",
        "https://youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G",
        
        # Playlist URLs with video parameter
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G",
        "https://www.youtube.com/watch?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G&v=dQw4w9WgXcQ",
        
        # Single video URLs
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        
        # Channel URLs
        "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
        "https://www.youtube.com/@channelname",
    ]
    
    print("🔍 URL Detection Test Results:")
    print("=" * 50)
    
    for url in test_urls:
        url_type = detector.detect_url_type(url)
        source_id = detector.extract_source_id(url)
        
        print(f"URL: {url}")
        print(f"  Type: {url_type}")
        print(f"  ID: {source_id}")
        print()
    
    # Test with user input
    print("🎯 Test with your playlist URL:")
    print("Please enter your playlist URL to test:")
    user_url = input("URL: ").strip()
    
    if user_url:
        url_type = detector.detect_url_type(user_url)
        source_id = detector.extract_source_id(user_url)
        
        print(f"\nYour URL: {user_url}")
        print(f"Detected Type: {url_type}")
        print(f"Extracted ID: {source_id}")
        
        if url_type == URLType.PLAYLIST:
            print("✅ URL correctly detected as PLAYLIST - batch processing should work")
        elif url_type == URLType.SINGLE_VIDEO:
            print("❌ URL detected as SINGLE_VIDEO - this is why batch processing doesn't start!")
        elif url_type == URLType.CHANNEL:
            print("✅ URL correctly detected as CHANNEL - batch processing should work")
        else:
            print("❌ URL detected as INVALID - this is why batch processing doesn't start!")

if __name__ == "__main__":
    test_url_detection()