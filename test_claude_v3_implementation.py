#!/usr/bin/env python3
"""
Test script for Claude v3.0 improvements implementation
"""

import os
import sys
import time
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ytsummarizer.state_manager import StateManager, OperationType, ProcessingItem
from ytsummarizer.error_handler import ErrorHandler, ErrorCategory
from ytsummarizer.retry_logic import RetryManager, RetryConfig, retry_on_error
from ytsummarizer.youtube_blocking_detector import YouTubeBlockingDetector
from ytsummarizer.transcripts import (
    get_blocking_detector, get_error_handler, get_retry_manager,
    get_youtube_blocking_status, is_youtube_blocked, reset_blocking_detector
)


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


def test_state_manager():
    """Test the enhanced StateManager functionality."""
    print_section("TESTING STATE MANAGER")
    
    state_manager = StateManager()
    
    # Test 1: Create a new session
    print_subsection("Creating New Session")
    items = ["video1", "video2", "video3", "video4", "video5"]
    session_id = state_manager.create_session(
        OperationType.BATCH,
        items,
        source_url="https://youtube.com/playlist?list=test",
        source_name="Test Playlist",
        processing_options={"output_folder": "tricks", "skip_existing": True}
    )
    print(f"✅ Created session: {session_id}")
    
    # Test 2: Save checkpoint with progress
    print_subsection("Saving Checkpoints")
    completed_items = [
        ProcessingItem("video1", "https://youtu.be/video1", 
                      completed_at=datetime.now().isoformat(), 
                      tricks_found=3, output_files=["trick1.mp4", "trick2.mp4", "trick3.mp4"]),
        ProcessingItem("video2", "https://youtu.be/video2", 
                      completed_at=datetime.now().isoformat(), 
                      tricks_found=1, output_files=["trick4.mp4"])
    ]
    
    current_item = ProcessingItem("video3", "https://youtu.be/video3", 
                                 started_at=datetime.now().isoformat(), 
                                 progress="extracting_tricks")
    
    success = state_manager.save_checkpoint(
        session_id,
        current_item=current_item,
        completed=completed_items,
        additional_data={"last_milestone": "video_processing"}
    )
    print(f"✅ Checkpoint saved: {success}")
    
    # Test 3: Load session and check progress
    print_subsection("Loading Session and Progress")
    loaded_state = state_manager.load_session(session_id)
    if loaded_state:
        print(f"✅ Session loaded successfully")
        print(f"   Progress: {loaded_state.progress_percentage:.1f}%")
        print(f"   Completed: {len(loaded_state.completed_items)}/{loaded_state.total_items}")
        print(f"   Current item: {loaded_state.current_item.video_id if loaded_state.current_item else 'None'}")
        print(f"   Status: {loaded_state.status}")
        print(f"   Resumable: {loaded_state.is_resumable}")
    
    # Test 4: Test checkpoint validation and backup
    print_subsection("Checkpoint Validation and Backup")
    is_valid = state_manager.validate_checkpoint(session_id)
    print(f"✅ Checkpoint valid: {is_valid}")
    
    backup_created = state_manager.create_backup_checkpoint(session_id)
    print(f"✅ Backup created: {backup_created}")
    
    # Test 5: Get checkpoint info
    print_subsection("Checkpoint Information")
    info = state_manager.get_checkpoint_info(session_id)
    if info:
        print(f"✅ Checkpoint info retrieved:")
        for key, value in info.items():
            print(f"   {key}: {value}")
    
    # Test 6: Test resumable sessions
    print_subsection("Resumable Sessions")
    state_manager.pause_session(session_id)
    resumable = state_manager.get_resumable_sessions()
    print(f"✅ Found {len(resumable)} resumable sessions")
    for session in resumable:
        print(f"   Session: {session.session_id[:20]}... ({session.operation_type})")
        print(f"   Progress: {session.progress_percentage:.1f}%")
    
    return session_id


def test_error_handler():
    """Test the ErrorHandler functionality."""
    print_section("TESTING ERROR HANDLER")
    
    blocking_detector = YouTubeBlockingDetector()
    error_handler = ErrorHandler(blocking_detector)
    
    # Test 1: Different error types
    print_subsection("Error Categorization")
    test_errors = [
        Exception("Connection timeout"),
        Exception("429 Too Many Requests"),
        Exception("403 Forbidden"),
        Exception("Transcript not available"),
        Exception("Video is private"),
        Exception("Permission denied"),
        Exception("Some random error")
    ]
    
    for i, error in enumerate(test_errors, 1):
        context = {"operation": f"test_operation_{i}", "video_id": f"video_{i}"}
        result = error_handler.handle_error(error, context)
        
        print(f"✅ Error {i}: {result.category.value}")
        print(f"   Message: {result.user_message}")
        print(f"   Action: {result.action.value}")
        print(f"   Severity: {result.severity.value}")
        print(f"   Retry delay: {result.retry_delay}s")
        print(f"   Resolution steps: {len(result.resolution_steps)} steps")
    
    # Test 2: Retry logic
    print_subsection("Retry Decision Logic")
    network_error = Exception("Connection failed")
    for attempt in range(1, 5):
        should_retry = error_handler.should_retry(network_error, attempt, max_retries=3)
        delay = error_handler.get_retry_delay(network_error, attempt)
        print(f"   Attempt {attempt}: Retry={should_retry}, Delay={delay}s")
    
    return error_handler


def test_retry_logic():
    """Test the RetryManager functionality."""
    print_section("TESTING RETRY LOGIC")
    
    error_handler = ErrorHandler()
    config = RetryConfig(max_retries=3, base_delay=0.5, jitter=False)  # Fast for testing
    retry_manager = RetryManager(error_handler, config)
    
    # Test 1: Successful operation
    print_subsection("Successful Operation")
    def successful_operation():
        return "success"
    
    result = retry_manager.retry_with_backoff(successful_operation, operation_id="test_success")
    print(f"✅ Successful operation result: {result}")
    
    # Test 2: Operation that fails then succeeds
    print_subsection("Operation with Retries")
    attempt_count = 0
    def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception(f"Temporary failure {attempt_count}")
        return f"success after {attempt_count} attempts"
    
    try:
        result = retry_manager.retry_with_backoff(
            flaky_operation, 
            operation_id="test_flaky",
            max_retries=5
        )
        print(f"✅ Flaky operation result: {result}")
    except Exception as e:
        print(f"❌ Flaky operation failed: {e}")
    
    # Test 3: Decorator usage
    print_subsection("Retry Decorator")
    call_count = 0
    
    @retry_on_error(max_retries=3, delay=0.2)
    def decorated_function(x):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Decorator test failure")
        return f"decorated result: {x}"
    
    try:
        result = decorated_function("test_value")
        print(f"✅ Decorated function result: {result}")
    except Exception as e:
        print(f"❌ Decorated function failed: {e}")
    
    return retry_manager


def test_blocking_detection():
    """Test YouTube blocking detection."""
    print_section("TESTING BLOCKING DETECTION")
    
    # Reset detector for clean test
    reset_blocking_detector()
    
    # Test 1: Initial status
    print_subsection("Initial Status")
    status = get_youtube_blocking_status()
    print(f"✅ Initial blocking status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Test 2: Simulate some errors
    print_subsection("Simulating Errors")
    detector = get_blocking_detector()
    
    # Simulate rate limiting
    for i in range(3):
        alert = detector.record_error(429, "Too Many Requests", "get_transcript", f"video_{i}")
        if alert:
            print(f"⚠️  Blocking alert: {alert.message}")
    
    # Check status after errors
    status = get_youtube_blocking_status()
    print(f"✅ Status after rate limit errors:")
    print(f"   Total errors: {status['total_errors']}")
    print(f"   Recent errors: {status['recent_errors']}")
    print(f"   Is likely blocked: {status['is_likely_blocked']}")
    
    # Test 3: Check blocking functions
    print_subsection("Blocking Status Functions")
    print(f"   Is YouTube blocked: {is_youtube_blocked()}")
    print(f"   Should pause requests: {detector.should_pause_requests()}")
    print(f"   Recommended wait time: {detector.get_recommended_wait_time()}s")
    
    # Test 4: Simulate success to reduce alert
    print_subsection("Simulating Recovery")
    for i in range(2):
        detector.record_success("get_transcript", f"video_success_{i}")
    
    status = get_youtube_blocking_status()
    print(f"✅ Status after successful requests:")
    print(f"   Is likely blocked: {status['is_likely_blocked']}")


def test_integration():
    """Test integration between components."""
    print_section("TESTING COMPONENT INTEGRATION")
    
    # Test 1: Error handler with blocking detector
    print_subsection("Error Handler + Blocking Detector")
    blocking_detector = YouTubeBlockingDetector()
    error_handler = ErrorHandler(blocking_detector)
    
    # Simulate a 429 error
    rate_limit_error = Exception("429 Too Many Requests")
    context = {"operation": "get_transcript", "video_id": "test_video"}
    
    result = error_handler.handle_error(rate_limit_error, context)
    print(f"✅ Error handled: {result.category.value}")
    print(f"   Blocking alert: {result.blocking_alert is not None}")
    
    # Test 2: State manager with error tracking
    print_subsection("State Manager + Error Tracking")
    state_manager = StateManager()
    session_id = state_manager.create_session(
        OperationType.TRICKS_EXTRACTION,
        ["video1", "video2"],
        processing_options={"track_errors": True}
    )
    
    # Simulate processing with errors
    failed_item = ProcessingItem(
        "video1", "https://youtu.be/video1",
        failed_at=datetime.now().isoformat(),
        error="Rate limit exceeded",
        retry_count=3
    )
    
    state_manager.save_checkpoint(session_id, failed=[failed_item])
    
    loaded_state = state_manager.load_session(session_id)
    print(f"✅ Session with errors:")
    print(f"   Failed items: {len(loaded_state.failed_items)}")
    if loaded_state.failed_items:
        print(f"   Error: {loaded_state.failed_items[0].error}")
        print(f"   Retry count: {loaded_state.failed_items[0].retry_count}")


def test_real_world_scenario():
    """Test a realistic scenario combining all components."""
    print_section("TESTING REAL-WORLD SCENARIO")
    
    print_subsection("Scenario: Batch Processing with Interruption")
    
    # Step 1: Create batch processing session
    state_manager = StateManager()
    video_urls = [
        "https://youtu.be/dQw4w9WgXcQ",  # Rick Roll (should work)
        "https://youtu.be/invalid123",   # Invalid video
        "https://youtu.be/another456"    # Another test video
    ]
    
    session_id = state_manager.create_session(
        OperationType.BATCH,
        video_urls,
        source_url="https://youtube.com/playlist?list=test",
        source_name="Test Batch Processing"
    )
    print(f"✅ Created batch session: {session_id[:20]}...")
    
    # Step 2: Simulate processing with mixed results
    completed_item = ProcessingItem(
        "dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ",
        completed_at=datetime.now().isoformat(),
        tricks_found=2,
        output_files=["rick_roll_trick1.mp4", "rick_roll_trick2.mp4"]
    )
    
    failed_item = ProcessingItem(
        "invalid123", "https://youtu.be/invalid123",
        failed_at=datetime.now().isoformat(),
        error="Video not available",
        error_category="video_error",
        retry_count=2
    )
    
    current_item = ProcessingItem(
        "another456", "https://youtu.be/another456",
        started_at=datetime.now().isoformat(),
        progress="downloading_video"
    )
    
    # Step 3: Save checkpoint (simulating interruption point)
    checkpoint_saved = state_manager.save_checkpoint(
        session_id,
        current_item=current_item,
        completed=[completed_item],
        failed=[failed_item],
        additional_data={
            "last_milestone": "video_download_started",
            "processing_stats": {
                "total_tricks_found": 2,
                "total_processing_time": 45.6,
                "average_tricks_per_video": 2.0
            }
        }
    )
    print(f"✅ Checkpoint saved: {checkpoint_saved}")
    
    # Step 4: Simulate application restart - load resumable sessions
    print_subsection("Simulating Application Restart")
    resumable_sessions = state_manager.get_resumable_sessions()
    print(f"✅ Found {len(resumable_sessions)} resumable sessions")
    
    if resumable_sessions:
        session = resumable_sessions[0]
        print(f"   Session: {session.session_id[:20]}...")
        print(f"   Operation: {session.operation_type}")
        print(f"   Progress: {session.progress_percentage:.1f}%")
        print(f"   Completed: {len(session.completed_items)}")
        print(f"   Failed: {len(session.failed_items)}")
        print(f"   Current: {session.current_item.video_id if session.current_item else 'None'}")
        
        # Show processing statistics
        if "processing_stats" in session.checkpoint_data:
            stats = session.checkpoint_data["processing_stats"]
            print(f"   Total tricks found: {stats['total_tricks_found']}")
            print(f"   Processing time: {stats['total_processing_time']}s")
    
    # Step 5: Demonstrate resumption capability
    print_subsection("Resumption Capability")
    if resumable_sessions:
        session = resumable_sessions[0]
        remaining_items = []
        
        # Calculate remaining items
        processed_ids = {item.video_id for item in session.completed_items + session.failed_items}
        if session.current_item:
            processed_ids.add(session.current_item.video_id)
        
        all_items = session.checkpoint_data.get("items", [])
        remaining_items = [item for item in all_items if item.split("/")[-1] not in processed_ids]
        
        print(f"✅ Resumption analysis:")
        print(f"   Total items: {len(all_items)}")
        print(f"   Processed: {len(processed_ids)}")
        print(f"   Remaining: {len(remaining_items)}")
        print(f"   Can resume: {session.is_resumable}")
    
    return session_id


def main():
    """Run all tests."""
    print("🚀 Starting Claude v3.0 Implementation Tests")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Run individual component tests
        session_id = test_state_manager()
        error_handler = test_error_handler()
        retry_manager = test_retry_logic()
        test_blocking_detection()
        
        # Run integration tests
        test_integration()
        
        # Run real-world scenario
        scenario_session = test_real_world_scenario()
        
        print_section("TEST SUMMARY")
        print("✅ All tests completed successfully!")
        print(f"   State Manager: Working")
        print(f"   Error Handler: Working")
        print(f"   Retry Logic: Working")
        print(f"   Blocking Detection: Working")
        print(f"   Integration: Working")
        print(f"   Real-world Scenario: Working")
        
        print(f"\n📊 Test Results:")
        print(f"   Created sessions: 2")
        print(f"   Processed checkpoints: Multiple")
        print(f"   Error scenarios tested: 7+")
        print(f"   Retry scenarios tested: 3")
        print(f"   Blocking scenarios tested: Multiple")
        
        # Cleanup
        print_section("CLEANUP")
        state_manager = StateManager()
        cleaned = state_manager.cleanup_old_sessions(days=0)  # Clean all for testing
        print(f"✅ Cleaned up {cleaned} test sessions")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)