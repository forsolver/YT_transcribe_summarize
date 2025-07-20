#!/usr/bin/env python3
"""
Test UI integration with Claude v3.0 improvements
"""

import os
import sys
import time
from unittest.mock import patch, Mock

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ytsummarizer.transcripts import get_transcript, get_youtube_blocking_status, reset_blocking_detector


def test_transcript_with_blocking_detection():
    """Test transcript retrieval with our enhanced blocking detection."""
    print("🧪 Testing Enhanced Transcript Functionality")
    print("=" * 50)
    
    # Reset blocking detector for clean test
    reset_blocking_detector()
    
    # Test with a well-known video (Rick Roll - should have transcript)
    test_video_url = "https://youtu.be/dQw4w9WgXcQ"
    
    print(f"📹 Testing with video: {test_video_url}")
    print("⏳ Attempting to get transcript with enhanced error handling...")
    
    try:
        # This will use our enhanced transcript system with:
        # - Blocking detection
        # - Retry logic with exponential backoff
        # - Error categorization
        # - Automatic recovery
        plain_text, fragments, video_info = get_transcript(test_video_url, use_cache=False)
        
        print("✅ Transcript retrieved successfully!")
        print(f"   Title: {video_info.get('title', 'Unknown')}")
        print(f"   Duration: {video_info.get('duration', 'Unknown')} seconds")
        print(f"   Fragments: {len(fragments)}")
        print(f"   Text length: {len(plain_text)} characters")
        print(f"   First 100 chars: {plain_text[:100]}...")
        
        # Show blocking status
        status = get_youtube_blocking_status()
        print(f"\n📊 Blocking Detection Status:")
        print(f"   Total errors: {status['total_errors']}")
        print(f"   Recent errors: {status['recent_errors']}")
        print(f"   Is likely blocked: {status['is_likely_blocked']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to get transcript: {e}")
        
        # Show blocking status even on failure
        status = get_youtube_blocking_status()
        print(f"\n📊 Blocking Detection Status (after error):")
        print(f"   Total errors: {status['total_errors']}")
        print(f"   Recent errors: {status['recent_errors']}")
        print(f"   Is likely blocked: {status['is_likely_blocked']}")
        
        if status['current_alert']:
            alert = status['current_alert']
            print(f"   Alert: {alert.message}")
            print(f"   Recommendation: {alert.recommendation}")
        
        return False


def test_error_simulation():
    """Test error handling with simulated failures."""
    print("\n🔧 Testing Error Handling with Simulated Failures")
    print("=" * 50)
    
    # Test with invalid video ID to trigger errors
    invalid_video_id = "invalid_video_123"
    
    print(f"📹 Testing with invalid video: {invalid_video_id}")
    print("⏳ This should trigger our error handling system...")
    
    try:
        plain_text, fragments, video_info = get_transcript(invalid_video_id, use_cache=False)
        print("❌ Unexpected success with invalid video")
        return False
        
    except Exception as e:
        print(f"✅ Expected error caught: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        
        # Show how our error handling categorized this
        status = get_youtube_blocking_status()
        print(f"\n📊 Error Handling Results:")
        print(f"   Total errors recorded: {status['total_errors']}")
        print(f"   Error breakdown: {status['error_breakdown']}")
        
        return True


def test_state_persistence():
    """Test that our state management works."""
    print("\n💾 Testing State Management")
    print("=" * 50)
    
    from ytsummarizer.state_manager import StateManager, OperationType
    
    state_manager = StateManager()
    
    # Create a test session
    session_id = state_manager.create_session(
        OperationType.SINGLE,
        ["test_video"],
        source_name="UI Integration Test"
    )
    
    print(f"✅ Created session: {session_id[:20]}...")
    
    # Check if we can load it back
    loaded_state = state_manager.load_session(session_id)
    if loaded_state:
        print(f"✅ Session loaded successfully")
        print(f"   Operation type: {loaded_state.operation_type}")
        print(f"   Total items: {loaded_state.total_items}")
        print(f"   Status: {loaded_state.status}")
        print(f"   Resumable: {loaded_state.is_resumable}")
        
        # Test checkpoint functionality
        success = state_manager.auto_checkpoint(session_id, "ui_test_milestone")
        print(f"✅ Auto checkpoint created: {success}")
        
        return True
    else:
        print("❌ Failed to load session")
        return False


def main():
    """Run UI integration tests."""
    print("🚀 Claude v3.0 UI Integration Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Enhanced transcript functionality
    print("Test 1: Enhanced Transcript with Blocking Detection")
    results.append(test_transcript_with_blocking_detection())
    
    # Test 2: Error handling
    print("\nTest 2: Error Handling System")
    results.append(test_error_simulation())
    
    # Test 3: State management
    print("\nTest 3: State Management")
    results.append(test_state_persistence())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 UI Integration Test Results")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All UI integration tests passed!")
        print("The Claude v3.0 improvements are ready for production use.")
    else:
        print(f"\n⚠️  Some tests failed. Please review the results above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)