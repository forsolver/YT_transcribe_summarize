"""
Test the full batch processing chain with your specific playlist URL
"""

import sys
import os
import logging
from threading import Event

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

from ytsummarizer.url_detector import URLDetector, URLType
from ytsummarizer.batch_processor import BatchProcessor, BatchOptions
from ytsummarizer.transcripts import get_source_metadata, extract_video_list

def test_full_chain():
    """Test the complete batch processing chain."""
    # Your playlist URL
    playlist_url = "https://www.youtube.com/watch?v=Tvu4bWh_GLM&list=PLH2zHj82u-TEEialbg-4t9q7izl2ZD9uC"
    
    print("🧪 Testing Full Batch Processing Chain")
    print("=" * 50)
    
    # Step 1: URL Detection
    print("Step 1: URL Detection")
    detector = URLDetector()
    url_type = detector.detect_url_type(playlist_url)
    source_id = detector.extract_source_id(playlist_url)
    
    print(f"  URL: {playlist_url}")
    print(f"  Type: {url_type}")
    print(f"  ID: {source_id}")
    
    if url_type != URLType.PLAYLIST:
        print(f"❌ ERROR: URL should be detected as PLAYLIST, but got {url_type}")
        return
    else:
        print("✅ URL correctly detected as PLAYLIST")
    
    # Step 2: Source Metadata
    print("\nStep 2: Source Metadata")
    try:
        source_info = get_source_metadata(playlist_url)
        if source_info:
            print(f"✅ Source metadata retrieved:")
            print(f"  Name: {source_info.name}")
            print(f"  Total videos: {source_info.total_videos}")
        else:
            print("❌ Failed to get source metadata")
            return
    except Exception as e:
        print(f"❌ Exception getting source metadata: {e}")
        return
    
    # Step 3: Video List Extraction
    print("\nStep 3: Video List Extraction")
    try:
        videos = extract_video_list(playlist_url, limit=3)  # Limit to 3 for testing
        print(f"✅ Extracted {len(videos)} videos:")
        for i, video in enumerate(videos):
            print(f"  {i+1}. {video.title} ({video.video_id})")
    except Exception as e:
        print(f"❌ Exception extracting video list: {e}")
        return
    
    # Step 4: Batch Processor
    print("\nStep 4: Batch Processor Test")
    try:
        def progress_callback(current, total, message):
            print(f"  [PROGRESS] {current}/{total} - {message}")
        
        cancel_token = Event()
        processor = BatchProcessor(progress_callback, cancel_token)
        options = BatchOptions(max_videos=2)  # Process only 2 videos for testing
        
        print("Starting batch processing...")
        result = processor.process_source(playlist_url, options)
        
        print(f"✅ Batch processing completed:")
        print(f"  Total videos: {result.total_videos}")
        print(f"  Processed: {result.processed_videos}")
        print(f"  Successful: {result.successful_extractions}")
        print(f"  Errors: {len(result.errors)}")
        
        if result.errors:
            print("  Error details:")
            for error in result.errors:
                print(f"    - {error.video_title}: {error.error_message}")
        
    except Exception as e:
        print(f"❌ Exception in batch processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_chain()