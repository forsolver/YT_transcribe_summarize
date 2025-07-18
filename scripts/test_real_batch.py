"""
Test script for real batch processing

This script tests batch processing with a real YouTube playlist
to identify where the process stops.
"""

import sys
import os
from threading import Event

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ytsummarizer.batch_processor import BatchProcessor, BatchOptions
from ytsummarizer.url_detector import URLDetector


def test_with_real_playlist():
    """Test batch processing with a real small playlist."""
    print("=== Testing Batch Processing with Real Playlist ===")
    
    # Use a known small playlist - you can replace this with any small public playlist
    # This is a small educational playlist that should be stable
    test_urls = [
        # Add a real small playlist URL here for testing
        # "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID",
        
        # For now, let's test with a single video to see if the basic flow works
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Famous Rick Roll video
    ]
    
    detector = URLDetector()
    
    def progress_callback(current, total, message):
        print(f"[PROGRESS] {current}/{total} - {message}")
    
    cancel_token = Event()
    processor = BatchProcessor(progress_callback, cancel_token)
    
    for test_url in test_urls:
        print(f"\nTesting with URL: {test_url}")
        url_type = detector.detect_url_type(test_url)
        print(f"URL type: {url_type}")
        
        if url_type.value in ['video', 'playlist', 'channel']:
            try:
                print("Starting batch processing...")
                options = BatchOptions(max_videos=2)  # Limit to 2 videos
                
                result = processor.process_source(test_url, options)
                
                print(f"\n=== RESULTS ===")
                print(f"Source: {result.source_info.name}")
                print(f"Total videos: {result.total_videos}")
                print(f"Processed: {result.processed_videos}")
                print(f"Successful: {result.successful_extractions}")
                print(f"Total tricks: {result.total_tricks}")
                print(f"Total segments: {result.total_segments}")
                print(f"Processing time: {result.processing_time:.1f}s")
                print(f"Cancelled: {result.cancelled}")
                
                if result.errors:
                    print(f"\nErrors ({len(result.errors)}):")
                    for error in result.errors:
                        print(f"  - {error.video_title}: {error.error_type} - {error.error_message}")
                
                if result.processed_videos > 0:
                    print("\n✓ Batch processing worked - at least one video was processed")
                else:
                    print("\n✗ Batch processing failed - no videos were processed")
                
            except Exception as e:
                print(f"✗ Exception during batch processing: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"Skipping invalid URL type: {url_type}")


def test_individual_components():
    """Test individual components to isolate issues."""
    print("\n=== Testing Individual Components ===")
    
    from ytsummarizer.transcripts import get_source_metadata, extract_video_list
    
    # Test with Rick Roll video as a "playlist" of 1 video
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"Testing URL: {test_url}")
    
    # Test URL detection
    detector = URLDetector()
    url_type = detector.detect_url_type(test_url)
    print(f"✓ URL type detected: {url_type}")
    
    # For single video, we can't test playlist extraction, but we can test the video processor
    if url_type.value == 'video':
        print("Testing single video processing...")
        
        from ytsummarizer.transcripts import get_transcript
        from ytsummarizer.video_processor import extract_trick_segments
        
        try:
            video_id = detector.extract_source_id(test_url)
            print(f"✓ Video ID extracted: {video_id}")
            
            print("Getting transcript...")
            plain_text, fragments, video_info = get_transcript(video_id)
            print(f"✓ Transcript obtained: {len(fragments)} fragments")
            
            print("Extracting trick segments...")
            trick_segments = extract_trick_segments(fragments)
            print(f"✓ Trick segments found: {len(trick_segments)}")
            
            if trick_segments:
                print("First trick segment:")
                seg = trick_segments[0]
                print(f"  Start: {seg['start']:.1f}s, End: {seg['end']:.1f}s, Duration: {seg['duration']:.1f}s")
            
        except Exception as e:
            print(f"✗ Error in single video processing: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Run the tests."""
    print("🧪 Real Batch Processing Test")
    print("=" * 50)
    
    print("This script will test batch processing with real YouTube content.")
    print("Make sure you have:")
    print("1. Internet connection")
    print("2. OPENAI_API_KEY set (for transcript processing)")
    print("3. ffmpeg installed and in PATH")
    print()
    
    try:
        test_individual_components()
        test_with_real_playlist()
        
        print("\n🎉 Test completed!")
        print("\nIf you see debug messages stopping at a specific point,")
        print("that's where the batch processing is failing.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()