"""
Unit tests for enhanced StateManager
"""

import os
import json
import tempfile
import shutil
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.state_manager import (
    StateManager, ProcessingState, ProcessingItem, 
    OperationType, ProcessingStatus
)


class TestStateManager(unittest.TestCase):
    """Test cases for enhanced StateManager."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_state_dir = StateManager.STATE_DIR
        StateManager.STATE_DIR = os.path.join(self.temp_dir, ".state")
        self.state_manager = StateManager()
    
    def tearDown(self):
        """Clean up test environment."""
        StateManager.STATE_DIR = self.original_state_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_session(self):
        """Test session creation."""
        items = ["https://youtu.be/video1", "https://youtu.be/video2"]
        session_id = self.state_manager.create_session(
            OperationType.BATCH,
            items,
            source_url="https://youtube.com/playlist?list=test",
            source_name="Test Playlist"
        )
        
        self.assertIsNotNone(session_id)
        self.assertTrue(session_id.startswith("batch_processing_"))
        
        # Verify session was saved
        state = self.state_manager.load_session(session_id)
        self.assertIsNotNone(state)
        self.assertEqual(state.operation_type, OperationType.BATCH.value)
        self.assertEqual(state.total_items, 2)
        self.assertEqual(state.status, ProcessingStatus.RUNNING.value)
        self.assertTrue(state.resumable)
    
    def test_save_and_load_checkpoint(self):
        """Test checkpoint saving and loading."""
        # Create session
        items = ["video1", "video2", "video3"]
        session_id = self.state_manager.create_session(OperationType.TRICKS_EXTRACTION, items)
        
        # Create test items
        completed_item = ProcessingItem(
            video_id="video1",
            url="https://youtu.be/video1",
            completed_at=datetime.now().isoformat(),
            tricks_found=2,
            output_files=["trick1.mp4", "trick2.mp4"]
        )
        
        current_item = ProcessingItem(
            video_id="video2",
            url="https://youtu.be/video2",
            started_at=datetime.now().isoformat(),
            progress="extracting_tricks"
        )
        
        # Save checkpoint
        success = self.state_manager.save_checkpoint(
            session_id,
            current_item=current_item,
            completed=[completed_item],
            failed=[],
            additional_data={"custom_data": "test_value"}
        )
        
        self.assertTrue(success)
        
        # Load and verify
        state = self.state_manager.load_session(session_id)
        self.assertIsNotNone(state)
        self.assertEqual(len(state.completed_items), 1)
        self.assertEqual(state.completed_items[0].video_id, "video1")
        self.assertEqual(state.completed_items[0].tricks_found, 2)
        self.assertEqual(state.current_item.video_id, "video2")
        self.assertEqual(state.checkpoint_data["custom_data"], "test_value")
    
    def test_session_status_management(self):
        """Test session status changes."""
        session_id = self.state_manager.create_session(OperationType.SINGLE, ["video1"])
        
        # Test pause
        self.assertTrue(self.state_manager.pause_session(session_id))
        state = self.state_manager.load_session(session_id)
        self.assertEqual(state.status, ProcessingStatus.PAUSED.value)
        
        # Test resume
        self.assertTrue(self.state_manager.resume_session(session_id))
        state = self.state_manager.load_session(session_id)
        self.assertEqual(state.status, ProcessingStatus.RUNNING.value)
        
        # Test completion
        self.assertTrue(self.state_manager.mark_session_complete(session_id))
        state = self.state_manager.load_session(session_id)
        self.assertEqual(state.status, ProcessingStatus.COMPLETED.value)
        self.assertFalse(state.resumable)
    
    def test_resumable_sessions(self):
        """Test getting resumable sessions."""
        # Create multiple sessions with different statuses
        session1 = self.state_manager.create_session(OperationType.BATCH, ["v1", "v2"])
        session2 = self.state_manager.create_session(OperationType.TRICKS_EXTRACTION, ["v3"])
        session3 = self.state_manager.create_session(OperationType.SINGLE, ["v4"])
        
        # Pause one, complete another
        self.state_manager.pause_session(session1)
        self.state_manager.mark_session_complete(session2)
        
        # Get resumable sessions
        resumable = self.state_manager.get_resumable_sessions()
        
        # Should have session1 (paused) and session3 (running), but not session2 (completed)
        resumable_ids = [s.session_id for s in resumable]
        self.assertIn(session1, resumable_ids)
        self.assertIn(session3, resumable_ids)
        self.assertNotIn(session2, resumable_ids)
        
        # Verify we have exactly 2 resumable sessions
        self.assertEqual(len(resumable), 2)
    
    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        items = ["v1", "v2", "v3", "v4"]
        session_id = self.state_manager.create_session(OperationType.BATCH, items)
        
        # Complete 2 out of 4 items
        completed = [
            ProcessingItem("v1", "url1", completed_at=datetime.now().isoformat()),
            ProcessingItem("v2", "url2", completed_at=datetime.now().isoformat())
        ]
        
        self.state_manager.save_checkpoint(session_id, completed=completed)
        state = self.state_manager.load_session(session_id)
        
        self.assertEqual(state.progress_percentage, 50.0)
    
    def test_cleanup_old_sessions(self):
        """Test cleanup of old completed sessions."""
        # Create sessions
        session1 = self.state_manager.create_session(OperationType.BATCH, ["v1"])
        session2 = self.state_manager.create_session(OperationType.SINGLE, ["v2"])
        
        # Mark one as completed
        self.state_manager.mark_session_complete(session1)
        
        # Mock file modification time to be old
        session1_file = self.state_manager._get_session_file_path(session1)
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(session1_file, (old_time, old_time))
        
        # Cleanup sessions older than 7 days
        cleaned = self.state_manager.cleanup_old_sessions(days=7)
        
        # Should clean up the completed old session
        self.assertEqual(cleaned, 1)
        self.assertIsNone(self.state_manager.load_session(session1))
        self.assertIsNotNone(self.state_manager.load_session(session2))
    
    def test_error_handling(self):
        """Test error handling in state operations."""
        # Test loading non-existent session
        state = self.state_manager.load_session("non_existent_session")
        self.assertIsNone(state)
        
        # Test saving checkpoint for non-existent session
        success = self.state_manager.save_checkpoint("non_existent_session")
        self.assertFalse(success)
        
        # Test operations on non-existent session
        self.assertFalse(self.state_manager.pause_session("non_existent_session"))
        self.assertFalse(self.state_manager.resume_session("non_existent_session"))
        self.assertFalse(self.state_manager.mark_session_complete("non_existent_session"))
    
    def test_processing_item_functionality(self):
        """Test ProcessingItem data class functionality."""
        item = ProcessingItem(
            video_id="test_video",
            url="https://youtu.be/test_video",
            started_at=datetime.now().isoformat()
        )
        
        self.assertEqual(item.video_id, "test_video")
        self.assertEqual(item.retry_count, 0)
        self.assertEqual(item.tricks_found, 0)
        self.assertEqual(item.output_files, [])
        self.assertEqual(item.progress, "pending")
    
    def test_checkpoint_validation(self):
        """Test checkpoint validation functionality."""
        # Create valid session
        session_id = self.state_manager.create_session(OperationType.BATCH, ["v1", "v2"])
        
        # Should be valid
        self.assertTrue(self.state_manager.validate_checkpoint(session_id))
        
        # Test invalid session
        self.assertFalse(self.state_manager.validate_checkpoint("invalid_session"))
    
    def test_backup_and_restore(self):
        """Test checkpoint backup and restore functionality."""
        # Create session and save some data
        session_id = self.state_manager.create_session(OperationType.BATCH, ["v1", "v2"])
        completed_item = ProcessingItem("v1", "url1", completed_at=datetime.now().isoformat())
        self.state_manager.save_checkpoint(session_id, completed=[completed_item])
        
        # Create backup
        self.assertTrue(self.state_manager.create_backup_checkpoint(session_id))
        
        # Verify backup exists
        session_file = self.state_manager._get_session_file_path(session_id)
        backup_file = f"{session_file}.backup"
        self.assertTrue(os.path.exists(backup_file))
        
        # Modify original (simulate corruption)
        with open(session_file, 'w') as f:
            f.write("corrupted data")
        
        # Restore from backup
        self.assertTrue(self.state_manager.restore_from_backup(session_id))
        
        # Verify restoration worked
        state = self.state_manager.load_session(session_id)
        self.assertIsNotNone(state)
        self.assertEqual(len(state.completed_items), 1)
    
    def test_auto_checkpoint(self):
        """Test automatic checkpoint creation."""
        session_id = self.state_manager.create_session(OperationType.TRICKS_EXTRACTION, ["v1"])
        
        # Create auto checkpoint
        success = self.state_manager.auto_checkpoint(
            session_id, 
            "video_started",
            current_video="v1",
            custom_data="test"
        )
        
        self.assertTrue(success)
        
        # Verify milestone data was saved
        state = self.state_manager.load_session(session_id)
        self.assertEqual(state.checkpoint_data["last_milestone"], "video_started")
        self.assertEqual(state.checkpoint_data["current_video"], "v1")
        self.assertEqual(state.checkpoint_data["custom_data"], "test")
    
    def test_checkpoint_info(self):
        """Test checkpoint information retrieval."""
        session_id = self.state_manager.create_session(OperationType.BATCH, ["v1", "v2", "v3"])
        
        # Add some completed items
        completed = [ProcessingItem("v1", "url1", completed_at=datetime.now().isoformat())]
        self.state_manager.save_checkpoint(session_id, completed=completed)
        
        # Get checkpoint info
        info = self.state_manager.get_checkpoint_info(session_id)
        
        self.assertIsNotNone(info)
        self.assertEqual(info["session_id"], session_id)
        self.assertEqual(info["total_items"], 3)
        self.assertEqual(info["completed_count"], 1)
        self.assertEqual(info["failed_count"], 0)
        self.assertAlmostEqual(info["progress_percentage"], 33.33, places=1)
        self.assertTrue(info["checkpoint_valid"])
        self.assertTrue(info["is_resumable"])
    
    def test_backward_compatibility(self):
        """Test that legacy methods still work."""
        # Test legacy source ID generation
        source_url = "https://youtube.com/playlist?list=test"
        source_id = StateManager.get_source_id(source_url)
        self.assertIsNotNone(source_id)
        self.assertEqual(len(source_id), 12)
        
        # Test legacy state file path
        state_file = StateManager.get_state_file_path(source_id)
        self.assertTrue(state_file.endswith("_state.json"))


if __name__ == '__main__':
    unittest.main()