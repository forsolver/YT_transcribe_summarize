"""
Diagnostic script for YouTube Tools batch processing issues

This script helps diagnose:
1. Why batch processing stops after first video
2. Why video files don't play in media players
3. Threading and UI integration issues
"""

import sys
import os
import subprocess
import tempfile
from threading import Event

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ytsummarizer.batch_processor import BatchProcessor, BatchOptions
from ytsummarizer.transcripts import get_source_metadata, extract_video_list
from ytsummarizer.url_detector import URLDetector, URLType


def test_ffmpeg_command():
    """Test if ffmpeg command produces playable files."""
    print("=== Testing ffmpeg Command ===")
    
    # Test with a simple command that should work
    test_commands = [
        # Simple copy command
        ['ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=320x240:rate=1', '-c:v', 'libx264', '-t', '2', 'test_simple.mp4', '-y'],
        
        # Our current command structure (simulated)
        ['ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=320x240:rate=1', '-ss', '1', '-t', '2', '-c', 'copy', '-avoid_negative_ts', 'make_zero', 'test_complex.mp4', '-y']
    ]
    
    for i, cmd in enumerate(test_commands):
        try:
            print(f"Testing command {i+1}: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                output_file = cmd[-2]  # Second to last argument is output file
                if os.path.exists(output_file):
                    size = os.path.getsize(output_file)
                    print(f"✓ Command {i+1} succeeded, file size: {size} bytes")
                    
                    # Test if file is playable with ffprobe
                    probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', output_file]
                    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                    if probe_result.returncode == 0:
                        print(f"✓ File {output_file} is valid and playable")
                    else:
                        print(f"✗ File {output_file} is corrupted or unplayable")
                        print(f"  ffprobe error: {probe_result.stderr}")
                    
                    # Clean up
                    try:
                        os.remove(output_file)
                    except:
                        pass
                else:
                    print(f"✗ Command {i+1} succeeded but no output file created")
            else:
                print(f"✗ Command {i+1} failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"✗ Command {i+1} timed out")
        except Exception as e:
            print(f"✗ Command {i+1} error: {e}")
    
    print()


def test_url_detection_and_extraction():
    """Test URL detection and video list extraction."""
    print("=== Testing URL Detection and Video List Extraction ===")
    
    detector = URLDetector()
    
    # Test URLs (using safe, known URLs)
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Single video
        "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G",  # Small playlist
    ]
    
    for url in test_urls:
        print(f"Testing URL: {url}")
        url_type = detector.detect_url_type(url)
        print(f"  Detected type: {url_type}")
        
        if url_type == URLType.PLAYLIST:
            try:
                print("  Getting source metadata...")
                source_info = get_source_metadata(url)
                if source_info:
                    print(f"  ✓ Source: {source_info.name}, Total videos: {source_info.total_videos}")
                    
                    print("  Extracting video list (limit 2)...")
                    videos = extract_video_list(url, limit=2)
                    print(f"  ✓ Extracted {len(videos)} videos")
                    for i, video in enumerate(videos):
                        print(f"    {i+1}. {video.title} ({video.video_id})")
                else:
                    print("  ✗ Failed to get source metadata")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                import traceback
                traceback.print_exc()
        
        print()


def test_batch_processor_logic():
    """Test batch processor with mock data."""
    print("=== Testing Batch Processor Logic ===")
    
    def progress_callback(current, total, message):
        print(f"  [PROGRESS] {current}/{total} - {message}")
    
    cancel_token = Event()
    processor = BatchProcessor(progress_callback, cancel_token)
    
    print("✓ BatchProcessor initialized")
    
    # Test with a real small playlist if available
    test_playlist_url = "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G"
    
    try:
        print(f"Testing with playlist: {test_playlist_url}")
        options = BatchOptions(max_videos=2)  # Limit to 2 videos for testing
        
        print("Starting batch processing test...")
        result = processor.process_source(test_playlist_url, options)
        
        print(f"✓ Batch processing completed")
        print(f"  Total videos: {result.total_videos}")
        print(f"  Processed: {result.processed_videos}")
        print(f"  Successful: {result.successful_extractions}")
        print(f"  Errors: {len(result.errors)}")
        
        if result.errors:
            print("  Error details:")
            for error in result.errors:
                print(f"    - {error.video_title}: {error.error_message}")
        
    except Exception as e:
        print(f"✗ Batch processing test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_video_file_creation():
    """Test creating a simple video file with our ffmpeg parameters."""
    print("=== Testing Video File Creation ===")
    
    # Create a test video file first
    print("Creating test video file...")
    test_video = "test_source.mp4"
    create_cmd = [
        'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=10:size=640x480:rate=30',
        '-c:v', 'libx264', '-preset', 'ultrafast', test_video, '-y'
    ]
    
    try:
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"✗ Failed to create test video: {result.stderr}")
            return
        
        print(f"✓ Created test video: {test_video}")
        
        # Test our extraction command
        print("Testing video segment extraction...")
        segment_file = "test_segment.mp4"
        
        # Our current command structure
        extract_cmd = [
            'ffmpeg',
            '-ss', '2',  # Start at 2 seconds
            '-i', test_video,
            '-t', '3',   # Duration 3 seconds
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            segment_file,
            '-y'
        ]
        
        result = subprocess.run(extract_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            if os.path.exists(segment_file):
                size = os.path.getsize(segment_file)
                print(f"✓ Segment created successfully, size: {size} bytes")
                
                # Test playability
                probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', segment_file]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                if probe_result.returncode == 0:
                    print("✓ Segment is valid and should be playable")
                else:
                    print("✗ Segment appears to be corrupted")
                    print(f"  ffprobe error: {probe_result.stderr}")
            else:
                print("✗ Segment file was not created")
        else:
            print(f"✗ Segment extraction failed: {result.stderr}")
        
        # Clean up
        for file in [test_video, segment_file]:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        print("✗ Test video creation timed out")
    except Exception as e:
        print(f"✗ Error in video file test: {e}")
    
    print()


def main():
    """Run all diagnostic tests."""
    print("🔍 YouTube Tools Diagnostic Script")
    print("=" * 50)
    
    # Check if ffmpeg is available
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ ffmpeg is available")
        else:
            print("✗ ffmpeg is not working properly")
            return
    except FileNotFoundError:
        print("✗ ffmpeg is not installed or not in PATH")
        return
    
    print()
    
    try:
        test_ffmpeg_command()
        test_video_file_creation()
        test_url_detection_and_extraction()
        # test_batch_processor_logic()  # Comment out for now as it requires real YouTube access
        
        print("🎉 Diagnostic tests completed!")
        print("\nRecommendations:")
        print("1. If ffmpeg tests pass but video files don't play, the issue is likely in the specific parameters")
        print("2. If URL detection works but batch processing fails, check the threading implementation")
        print("3. Run the application with console output visible to see debug messages")
        print("4. Test with a very small playlist (2-3 videos) first")
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()