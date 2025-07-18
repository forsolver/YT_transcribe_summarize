"""
Test script to check if file removal is causing the hang
"""

import os
import time
import tempfile
import subprocess

def test_file_removal_after_ffmpeg():
    """Test if file removal after ffmpeg causes issues."""
    print("=== Testing File Removal After ffmpeg ===")
    
    # Create a test video file
    test_video = "test_removal.mp4"
    create_cmd = [
        'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=320x240:rate=30',
        '-c:v', 'libx264', '-preset', 'ultrafast', test_video, '-y'
    ]
    
    try:
        print("Creating test video...")
        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"Failed to create test video: {result.stderr}")
            return
        
        print(f"✓ Created test video: {test_video}")
        
        # Test segment extraction
        segment_file = "test_segment_removal.mp4"
        extract_cmd = [
            'ffmpeg',
            '-ss', '1',
            '-i', test_video,
            '-t', '2',
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            segment_file,
            '-y'
        ]
        
        print("Extracting segment...")
        result = subprocess.run(extract_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to extract segment: {result.stderr}")
            return
        
        print("✓ Segment extracted successfully")
        
        # Test file removal with delay (like in our code)
        print("Testing file removal...")
        start_time = time.time()
        
        try:
            time.sleep(1)  # Same delay as in our code
            
            if os.path.exists(test_video):
                os.remove(test_video)
                print(f"✓ File removed successfully in {time.time() - start_time:.2f}s")
            else:
                print("File already removed or doesn't exist")
                
        except OSError as e:
            print(f"✗ File removal failed: {e}")
            elapsed = time.time() - start_time
            if elapsed > 5:
                print(f"WARNING: File removal took {elapsed:.2f}s - this could cause hangs!")
        
        # Clean up
        for file in [test_video, segment_file]:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except:
                pass
                
        print("✓ Test completed successfully")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")

def main():
    print("🧪 File Removal Test")
    print("=" * 30)
    
    test_file_removal_after_ffmpeg()

if __name__ == "__main__":
    main()