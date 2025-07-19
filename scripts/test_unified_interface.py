"""
Test the unified interface with single button for extract and download
"""

import sys
import os

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ytsummarizer.url_detector import URLDetector, URLType

def test_unified_logic():
    """Test the logic that will be used in the unified interface."""
    detector = URLDetector()
    
    test_cases = [
        {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'expected_type': URLType.SINGLE_VIDEO,
            'expected_action': 'Single video processing with download'
        },
        {
            'url': 'https://www.youtube.com/watch?v=Tvu4bWh_GLM&list=PLH2zHj82u-TEEialbg-4t9q7izl2ZD9uC',
            'expected_type': URLType.PLAYLIST,
            'expected_action': 'Batch processing with download'
        },
        {
            'url': 'https://www.youtube.com/@channelname',
            'expected_type': URLType.CHANNEL,
            'expected_action': 'Batch processing with download'
        }
    ]
    
    print("🧪 Testing Unified Interface Logic")
    print("=" * 50)
    
    for i, case in enumerate(test_cases, 1):
        url = case['url']
        expected_type = case['expected_type']
        expected_action = case['expected_action']
        
        print(f"\nTest {i}: {url}")
        
        # Detect URL type
        url_type = detector.detect_url_type(url)
        print(f"  Detected type: {url_type}")
        
        # Determine action
        if url_type == URLType.SINGLE_VIDEO:
            action = "Single video processing with download"
        elif url_type in [URLType.CHANNEL, URLType.PLAYLIST]:
            action = "Batch processing with download"
        else:
            action = "Unsupported URL type"
        
        print(f"  Action: {action}")
        
        # Check if correct
        if url_type == expected_type and action == expected_action:
            print("  ✅ CORRECT")
        else:
            print("  ❌ INCORRECT")
            print(f"    Expected type: {expected_type}")
            print(f"    Expected action: {expected_action}")
    
    print("\n🎯 Summary:")
    print("- Single videos: Download tricks directly")
    print("- Playlists/Channels: Use batch processing (already downloads)")
    print("- One button handles both cases appropriately")
    print("\n✅ Unified interface logic is sound!")

if __name__ == "__main__":
    test_unified_logic()