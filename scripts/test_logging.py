"""
Test script for logging configuration

This script tests if the logging system is properly configured
and working across all modules.
"""

import sys
import os
import logging

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure basic logging for this test script
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create a logger for this script
logger = logging.getLogger("test_logging")

def test_logging_system():
    """Test if the logging system is working."""
    logger.info("Testing logging system...")
    
    # Import modules that use logging
    from ytsummarizer.batch_processor import BatchProcessor
    from ytsummarizer.video_processor import extract_trick_segments
    from ytsummarizer.transcripts import get_transcript
    from ytsummarizer.url_detector import URLDetector
    
    # Test logging in each module
    logger.info("Testing logging in url_detector...")
    detector = URLDetector()
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    url_type = detector.detect_url_type(test_url)
    logger.info(f"URL type detected: {url_type}")
    
    # Test batch processor logging
    logger.info("Testing logging in batch_processor...")
    from threading import Event
    processor = BatchProcessor(progress_callback=None, cancel_token=Event())
    logger.info("BatchProcessor initialized")
    
    logger.info("All logging tests completed successfully!")

def main():
    """Run the logging tests."""
    print("🧪 Logging System Test")
    print("=" * 30)
    
    try:
        test_logging_system()
        print("\n✅ Logging system is working correctly!")
        print("Check the console output and ytsummarizer.log file for log messages.")
    except Exception as e:
        print(f"\n❌ Logging test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()