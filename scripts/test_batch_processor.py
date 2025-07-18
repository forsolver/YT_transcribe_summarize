"""
Tests for Batch Processing Module

This module contains tests for the BatchProcessor class and related functionality.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from threading import Event

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ytsummarizer.batch_processor import (
    BatchProcessor, BatchOptions, BatchResult, ProcessingError, 
    VideoProcessingResult, process_source_batch
)
from ytsummarizer.transcripts import SourceInfo, VideoInfo
from ytsummarizer.url_detector import URLType
from datetime import datetime


class TestBatchProcessor(unittest.TestCase):
    """Test cases for BatchProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.progress_callback = Mock()
        self.cancel_token = Event()
        self.processor = BatchProcessor(self.progress_callback, self.cancel_token)
    
    def test_batch_options_defaults(self):
        """Test BatchOptions default values."""
        options = BatchOptions()
        self.assertEqual(options.max_videos, 50)
        self.assertFalse(options.skip_existing)
        self.assertEqual(options.output_dir, "tricks")
    
    def test_batch_options_custom(self):
        """Test BatchOptions with custom values."""
        options = BatchOptions(
            max_videos=100,
            skip_existing=True,
            output_dir="custom_tricks"
        )
        self.assertEqual(options.max_videos, 100)
        self.assertTrue(options.skip_existing)
        self.assertEqual(options.output_dir, "custom_tricks")
    
    def test_processing_error_creation(self):
        """Test ProcessingError data class."""
        error = ProcessingError(
            video_id="test123",
            video_title="Test Video",
            error_type="TRANSCRIPT_ERROR",
            error_message="Failed to get transcript"
        )
        self.assertEqual(error.video_id, "test123")
        self.assertEqual(error.video_title, "Test Video")
        self.assertEqual(error.error_type, "TRANSCRIPT_ERROR")
        self.assertEqual(error.error_message, "Failed to get transcript")
        self.assertIsInstance(error.timestamp, datetime)
    
    def test_video_processing_result_defaults(self):
        """Test VideoProcessingResult default values."""
        video_info = VideoInfo(
            video_id="test123",
            title="Test Video",
            url="https://youtube.com/watch?v=test123"
        )
        result = VideoProcessingResult(video_info=video_info)
        self.assertEqual(result.video_info, video_info)
        self.assertEqual(result.tricks_found, 0)
        self.assertEqual(result.segments_extracted, [])
        self.assertEqual(result.processing_time, 0.0)
        self.assertFalse(result.success)
        self.assertIsNone(result.error)
    
    def test_batch_result_defaults(self):
        """Test BatchResult default values."""
        source_info = SourceInfo(
            name="Test Channel",
            type=URLType.CHANNEL,
            url="https://youtube.com/channel/test",
            total_videos=10
        )
        result = BatchResult(source_info=source_info)
        self.assertEqual(result.source_info, source_info)
        self.assertEqual(result.total_videos, 0)
        self.assertEqual(result.processed_videos, 0)
        self.assertEqual(result.successful_extractions, 0)
        self.assertEqual(result.total_tricks, 0)
        self.assertEqual(result.total_segments, 0)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.processing_time, 0.0)
        self.assertIsInstance(result.start_time, datetime)
        self.assertIsNone(result.end_time)
        self.assertFalse(result.cancelled)
    
    def test_sanitize_folder_name(self):
        """Test folder name sanitization."""
        # Test normal name
        result = self.processor._sanitize_folder_name("Normal Video Title")
        self.assertEqual(result, "Normal Video Title")
        
        # Test name with invalid characters
        result = self.processor._sanitize_folder_name("Video<>:\"/\\|?*Title")
        self.assertEqual(result, "Video_________Title")
        
        # Test empty name
        result = self.processor._sanitize_folder_name("")
        self.assertEqual(result, "Unknown_Video")
        
        # Test None
        result = self.processor._sanitize_folder_name(None)
        self.assertEqual(result, "Unknown_Video")
        
        # Test long name
        long_name = "A" * 100
        result = self.processor._sanitize_folder_name(long_name)
        self.assertEqual(len(result), 50)
    
    @patch('ytsummarizer.batch_processor.get_source_metadata')
    def test_process_source_invalid_source(self, mock_get_metadata):
        """Test processing with invalid source."""
        mock_get_metadata.return_value = None
        
        options = BatchOptions()
        result = self.processor.process_source("invalid_url", options)
        
        self.assertIsInstance(result, BatchResult)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].error_type, "SOURCE_ERROR")
    
    @patch('ytsummarizer.batch_processor.extract_video_list')
    @patch('ytsummarizer.batch_processor.get_source_metadata')
    def test_process_source_no_videos(self, mock_get_metadata, mock_extract_videos):
        """Test processing with no videos found."""
        mock_source_info = SourceInfo(
            name="Test Channel",
            type=URLType.CHANNEL,
            url="https://youtube.com/channel/test",
            total_videos=0
        )
        mock_get_metadata.return_value = mock_source_info
        mock_extract_videos.return_value = []
        
        options = BatchOptions()
        result = self.processor.process_source("https://youtube.com/channel/test", options)
        
        self.assertIsInstance(result, BatchResult)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].error_type, "VIDEO_LIST_ERROR")
    
    def test_apply_filters_duration(self):
        """Test video filtering by duration."""
        videos = [
            VideoInfo("id1", "Video 1", "url1", duration=30),
            VideoInfo("id2", "Video 2", "url2", duration=120),
            VideoInfo("id3", "Video 3", "url3", duration=300),
            VideoInfo("id4", "Video 4", "url4", duration=None),
        ]
        
        # Filter by minimum duration
        options = BatchOptions(min_video_duration=60)
        filtered = self.processor._apply_filters(videos, options)
        self.assertEqual(len(filtered), 2)  # Videos 2 and 3
        
        # Filter by maximum duration
        options = BatchOptions(max_video_duration=200)
        filtered = self.processor._apply_filters(videos, options)
        self.assertEqual(len(filtered), 2)  # Videos 1 and 2
        
        # Filter by range
        options = BatchOptions(min_video_duration=60, max_video_duration=200)
        filtered = self.processor._apply_filters(videos, options)
        self.assertEqual(len(filtered), 1)  # Only Video 2
    
    def test_apply_filters_date(self):
        """Test video filtering by date."""
        videos = [
            VideoInfo("id1", "Video 1", "url1", upload_date=datetime(2023, 1, 1)),
            VideoInfo("id2", "Video 2", "url2", upload_date=datetime(2023, 6, 1)),
            VideoInfo("id3", "Video 3", "url3", upload_date=datetime(2023, 12, 1)),
            VideoInfo("id4", "Video 4", "url4", upload_date=None),
        ]
        
        # Filter by date from
        options = BatchOptions(date_from=datetime(2023, 6, 1))
        filtered = self.processor._apply_filters(videos, options)
        self.assertEqual(len(filtered), 2)  # Videos 2 and 3
        
        # Filter by date to
        options = BatchOptions(date_to=datetime(2023, 6, 1))
        filtered = self.processor._apply_filters(videos, options)
        self.assertEqual(len(filtered), 2)  # Videos 1 and 2
    
    def test_progress_callback(self):
        """Test progress reporting."""
        self.processor._report_progress(5, 10, "Test message")
        self.progress_callback.assert_called_once_with(5, 10, "Test message")
    
    def test_progress_callback_exception(self):
        """Test progress callback with exception."""
        self.progress_callback.side_effect = Exception("Callback error")
        # Should not raise exception
        self.processor._report_progress(5, 10, "Test message")
    
    def test_create_folder_structure(self):
        """Test folder structure creation."""
        source_info = SourceInfo(
            name="Test Channel",
            type=URLType.CHANNEL,
            url="https://youtube.com/channel/test",
            total_videos=10
        )
        video_info = VideoInfo(
            video_id="test123",
            title="Test Video",
            url="https://youtube.com/watch?v=test123"
        )
        
        with patch('os.makedirs') as mock_makedirs:
            result = self.processor.create_folder_structure(source_info, video_info, "test_tricks")
            
            # Should create base dir, source dir, and video dir
            self.assertEqual(mock_makedirs.call_count, 3)
            self.assertTrue(result.endswith("Test Video"))
    
    def test_convenience_function(self):
        """Test convenience function."""
        with patch.object(BatchProcessor, 'process_source') as mock_process:
            mock_result = BatchResult(
                source_info=SourceInfo("Test", URLType.CHANNEL, "url", 0)
            )
            mock_process.return_value = mock_result
            
            result = process_source_batch("test_url")
            
            self.assertEqual(result, mock_result)
            mock_process.assert_called_once()


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)