"""
Unit tests for enhanced transcripts with blocking detection
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.transcripts import (
    youtube_api_call, get_blocking_detector, get_error_handler, get_retry_manager,
    get_youtube_blocking_status, is_youtube_blocked, should_pause_youtube_requests,
    get_recommended_wait_time, reset_blocking_detector
)
from ytsummarizer.youtube_blocking_detector import YouTubeBlockingDetector
from ytsummarizer.error_handler import ErrorHandler
from ytsummarizer.retry_logic import RetryManager


class TestEnhancedTranscripts(unittest.TestCase):
    """Test cases for enhanced transcript functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset global instances
        import ytsummarizer.transcripts as transcripts_module
        transcripts_module._blocking_detector = None
        transcripts_module._error_handler = None
        transcripts_module._retry_manager = None
    
    def test_singleton_instances(self):
        """Test that singleton instances are created correctly."""
        # Test blocking detector
        detector1 = get_blocking_detector()
        detector2 = get_blocking_detector()
        self.assertIs(detector1, detector2)
        self.assertIsInstance(detector1, YouTubeBlockingDetector)
        
        # Test error handler
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        self.assertIs(handler1, handler2)
        self.assertIsInstance(handler1, ErrorHandler)
        
        # Test retry manager
        manager1 = get_retry_manager()
        manager2 = get_retry_manager()
        self.assertIs(manager1, manager2)
        self.assertIsInstance(manager1, RetryManager)
    
    def test_youtube_api_call_success(self):
        """Test successful YouTube API call."""
        mock_func = Mock(return_value="success")
        
        result = youtube_api_call(mock_func, "test_operation", "test_video")
        
        self.assertEqual(result, "success")
        mock_func.assert_called_once()
    
    def test_youtube_api_call_with_error(self):
        """Test YouTube API call with error handling."""
        # Mock function that fails once then succeeds
        mock_func = Mock(side_effect=[Exception("429 Too Many Requests"), "success"])
        
        # Mock the blocking detector to avoid actual blocking detection
        with patch.object(get_blocking_detector(), 'record_error') as mock_record_error, \
             patch.object(get_blocking_detector(), 'record_success') as mock_record_success:
            
            mock_record_error.return_value = None  # No blocking alert
            
            result = youtube_api_call(mock_func, "test_operation", "test_video")
            
            self.assertEqual(result, "success")
            self.assertEqual(mock_func.call_count, 2)
            mock_record_success.assert_called_once_with("test_operation", "test_video")
    
    def test_blocking_status_functions(self):
        """Test blocking status utility functions."""
        # Test status retrieval
        status = get_youtube_blocking_status()
        self.assertIsInstance(status, dict)
        self.assertIn("total_errors", status)
        self.assertIn("recent_errors", status)
        self.assertIn("is_likely_blocked", status)
        
        # Test blocking check
        blocked = is_youtube_blocked()
        self.assertIsInstance(blocked, bool)
        
        # Test pause recommendation
        should_pause = should_pause_youtube_requests()
        self.assertIsInstance(should_pause, bool)
        
        # Test wait time recommendation
        wait_time = get_recommended_wait_time()
        self.assertIsInstance(wait_time, int)
        self.assertGreaterEqual(wait_time, 0)
    
    def test_reset_blocking_detector(self):
        """Test blocking detector reset functionality."""
        # Add some errors to the detector
        detector = get_blocking_detector()
        detector.record_error(429, "Too Many Requests", "test_operation")
        
        # Verify errors are recorded
        status_before = detector.get_current_status()
        self.assertGreater(status_before["total_errors"], 0)
        
        # Reset detector
        reset_blocking_detector()
        
        # Verify reset worked
        status_after = detector.get_current_status()
        self.assertEqual(status_after["total_errors"], 0)
    
    @patch('ytsummarizer.transcripts.YouTubeTranscriptApi')
    def test_get_transcript_with_blocking_detection(self, mock_transcript_api):
        """Test transcript retrieval with blocking detection."""
        from ytsummarizer.transcripts import get_transcript
        
        # Mock successful transcript retrieval
        mock_transcript_api.get_transcript.return_value = [
            {"start": 0.0, "text": "Hello", "duration": 2.0},
            {"start": 2.0, "text": "World", "duration": 2.0}
        ]
        
        # Mock video info
        with patch('ytsummarizer.transcripts.get_video_info') as mock_video_info:
            mock_video_info.return_value = {"duration": 10, "title": "Test Video"}
            
            # Test transcript retrieval
            plain_text, fragments, video_info = get_transcript("test_video_id")
            
            self.assertIn("Hello", plain_text)
            self.assertIn("World", plain_text)
            self.assertEqual(len(fragments), 2)
            self.assertEqual(video_info["title"], "Test Video")
    
    @patch('ytsummarizer.transcripts.YoutubeDL')
    def test_get_video_info_with_blocking_detection(self, mock_ytdl):
        """Test video info retrieval with blocking detection."""
        from ytsummarizer.transcripts import get_video_info
        
        # Mock YoutubeDL
        mock_ydl_instance = Mock()
        mock_ydl_instance.extract_info.return_value = {
            "duration": 120,
            "title": "Test Video"
        }
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        
        result = get_video_info("test_video_id")
        
        self.assertEqual(result["duration"], 120)
        self.assertEqual(result["title"], "Test Video")
    
    @patch('ytsummarizer.transcripts.YoutubeDL')
    def test_extract_video_list_with_blocking_detection(self, mock_ytdl):
        """Test video list extraction with blocking detection."""
        from ytsummarizer.transcripts import extract_video_list
        
        # Mock YoutubeDL
        mock_ydl_instance = Mock()
        mock_ydl_instance.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Video 1",
                    "duration": 120,
                    "upload_date": "20240101"
                },
                {
                    "id": "video2",
                    "title": "Video 2",
                    "duration": 180,
                    "upload_date": "20240102"
                }
            ]
        }
        mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
        
        videos = extract_video_list("https://youtube.com/playlist?list=test")
        
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos[0].video_id, "video1")
        self.assertEqual(videos[0].title, "Video 1")
        self.assertEqual(videos[1].video_id, "video2")
        self.assertEqual(videos[1].title, "Video 2")
    
    def test_error_propagation(self):
        """Test that errors are properly propagated through the system."""
        mock_func = Mock(side_effect=Exception("Persistent error"))
        
        with self.assertRaises(Exception) as cm:
            youtube_api_call(mock_func, "test_operation", max_retries=2)
        
        self.assertEqual(str(cm.exception), "Persistent error")
    
    def test_context_information(self):
        """Test that context information is properly passed."""
        mock_func = Mock(side_effect=Exception("Test error"))
        
        with patch.object(get_error_handler(), 'handle_error') as mock_handle_error:
            mock_handle_error.return_value = Mock(
                action=Mock(value="abort"),
                blocking_alert=None
            )
            
            try:
                youtube_api_call(mock_func, "test_operation", "test_video")
            except:
                pass
            
            # Verify error handler was called with correct context
            mock_handle_error.assert_called()
            call_args = mock_handle_error.call_args
            context = call_args[0][1]  # Second argument is context
            
            self.assertEqual(context['operation'], "test_operation")
            self.assertEqual(context['video_id'], "test_video")
            self.assertIn('timestamp', context)


if __name__ == '__main__':
    unittest.main()