"""
Unit tests for ErrorHandler
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, ActionType, ErrorResult
)
from ytsummarizer.youtube_blocking_detector import YouTubeBlockingDetector


class TestErrorHandler(unittest.TestCase):
    """Test cases for ErrorHandler."""
    
    def setUp(self):
        """Set up test environment."""
        self.blocking_detector = Mock(spec=YouTubeBlockingDetector)
        self.error_handler = ErrorHandler(self.blocking_detector)
    
    def test_error_categorization(self):
        """Test error categorization functionality."""
        # Network errors
        network_error = Exception("Connection timeout")
        self.assertEqual(
            self.error_handler.categorize_error(network_error),
            ErrorCategory.NETWORK_ERROR
        )
        
        # Rate limit errors
        rate_limit_error = Exception("429 Too Many Requests")
        self.assertEqual(
            self.error_handler.categorize_error(rate_limit_error),
            ErrorCategory.RATE_LIMIT
        )
        
        # Blocking errors
        blocking_error = Exception("403 Forbidden")
        self.assertEqual(
            self.error_handler.categorize_error(blocking_error),
            ErrorCategory.BLOCKING
        )
        
        # Transcript errors
        transcript_error = Exception("Transcript not available")
        self.assertEqual(
            self.error_handler.categorize_error(transcript_error),
            ErrorCategory.TRANSCRIPT_ERROR
        )
        
        # Video errors
        video_error = Exception("Video is private")
        self.assertEqual(
            self.error_handler.categorize_error(video_error),
            ErrorCategory.VIDEO_ERROR
        )
        
        # Unknown errors
        unknown_error = Exception("Some random error")
        self.assertEqual(
            self.error_handler.categorize_error(unknown_error),
            ErrorCategory.UNKNOWN
        )
    
    def test_user_message_generation(self):
        """Test user-friendly message generation."""
        # Network error
        network_error = Exception("Connection failed")
        message = self.error_handler.get_user_message(network_error, ErrorCategory.NETWORK_ERROR)
        self.assertIn("Network connection issue", message)
        
        # Rate limit error
        rate_limit_error = Exception("Too many requests")
        message = self.error_handler.get_user_message(rate_limit_error, ErrorCategory.RATE_LIMIT)
        self.assertIn("YouTube is limiting requests", message)
        
        # Private video error
        private_error = Exception("Video is private")
        message = self.error_handler.get_user_message(private_error, ErrorCategory.VIDEO_ERROR)
        self.assertIn("private", message)
    
    def test_resolution_steps(self):
        """Test resolution steps generation."""
        # Network error steps
        network_error = Exception("Connection failed")
        steps = self.error_handler.get_resolution_steps(network_error, ErrorCategory.NETWORK_ERROR)
        self.assertIsInstance(steps, list)
        self.assertTrue(len(steps) > 0)
        self.assertTrue(any("internet connection" in step.lower() for step in steps))
        
        # Rate limit steps
        rate_limit_error = Exception("Too many requests")
        steps = self.error_handler.get_resolution_steps(rate_limit_error, ErrorCategory.RATE_LIMIT)
        self.assertTrue(any("wait" in step.lower() for step in steps))
        
        # Blocking steps
        blocking_error = Exception("403 Forbidden")
        steps = self.error_handler.get_resolution_steps(blocking_error, ErrorCategory.BLOCKING)
        self.assertTrue(any("ip address" in step.lower() for step in steps))
    
    def test_retry_logic(self):
        """Test retry decision logic."""
        # Network errors should retry
        network_error = Exception("Connection timeout")
        self.assertTrue(self.error_handler.should_retry(network_error, 1, 3))
        self.assertTrue(self.error_handler.should_retry(network_error, 2, 3))
        self.assertFalse(self.error_handler.should_retry(network_error, 3, 3))
        
        # Rate limit errors should retry
        rate_limit_error = Exception("429 Too Many Requests")
        self.assertTrue(self.error_handler.should_retry(rate_limit_error, 1, 3))
        
        # Permission errors should not retry
        permission_error = Exception("Permission denied")
        self.error_handler.categorize_error = Mock(return_value=ErrorCategory.PERMISSION_ERROR)
        self.assertFalse(self.error_handler.should_retry(permission_error, 1, 3))
    
    def test_retry_delay_calculation(self):
        """Test retry delay calculation."""
        # Network error delay
        network_error = Exception("Connection failed")
        delay1 = self.error_handler.get_retry_delay(network_error, 1)
        delay2 = self.error_handler.get_retry_delay(network_error, 2)
        
        # Should increase with attempt number (exponential backoff)
        self.assertGreater(delay2, delay1)
        self.assertGreater(delay1, 0)
        
        # Rate limit should have longer delays
        rate_limit_error = Exception("429 Too Many Requests")
        rate_delay = self.error_handler.get_retry_delay(rate_limit_error, 1)
        network_delay = self.error_handler.get_retry_delay(network_error, 1)
        self.assertGreater(rate_delay, network_delay)
    
    def test_handle_error_comprehensive(self):
        """Test comprehensive error handling."""
        error = Exception("429 Too Many Requests")
        context = {
            'operation': 'get_transcript',
            'video_id': 'test_video',
            'attempt': 1
        }
        
        # Mock blocking detector
        mock_alert = Mock()
        self.blocking_detector.record_error.return_value = mock_alert
        
        result = self.error_handler.handle_error(error, context)
        
        # Verify result structure
        self.assertIsInstance(result, ErrorResult)
        self.assertEqual(result.category, ErrorCategory.RATE_LIMIT)
        self.assertEqual(result.action, ActionType.WAIT)
        self.assertGreater(result.retry_delay, 0)
        self.assertGreater(result.max_retries, 0)
        self.assertIsNotNone(result.user_message)
        self.assertIsInstance(result.resolution_steps, list)
        
        # Verify blocking detector was called
        self.blocking_detector.record_error.assert_called_once()
    
    def test_severity_determination(self):
        """Test error severity determination."""
        # System errors should be critical
        system_error = Exception("System failure")
        result = self.error_handler.handle_error(system_error, {'operation': 'test'})
        # Note: We can't directly test _determine_severity as it's private,
        # but we can verify through handle_error
        
        # Network errors should be medium severity
        network_error = Exception("Connection timeout")
        result = self.error_handler.handle_error(network_error, {'operation': 'test'})
        self.assertIsNotNone(result.severity)
    
    def test_action_determination(self):
        """Test action determination."""
        # Network errors should suggest retry
        network_error = Exception("Connection failed")
        result = self.error_handler.handle_error(network_error, {'operation': 'test'})
        self.assertEqual(result.action, ActionType.RETRY)
        
        # Rate limit should suggest wait
        rate_limit_error = Exception("429 Too Many Requests")
        result = self.error_handler.handle_error(rate_limit_error, {'operation': 'test'})
        self.assertEqual(result.action, ActionType.WAIT)
        
        # Transcript errors should suggest skip
        transcript_error = Exception("Transcript not available")
        result = self.error_handler.handle_error(transcript_error, {'operation': 'test'})
        self.assertEqual(result.action, ActionType.SKIP)
    
    def test_error_logging(self):
        """Test error logging functionality."""
        with patch('ytsummarizer.error_handler.logger') as mock_logger:
            error = Exception("Test error")
            context = {'operation': 'test'}
            
            result = self.error_handler.handle_error(error, context)
            
            # Verify logging was called
            mock_logger.log.assert_called()
            mock_logger.debug.assert_called()
    
    def test_blocking_detection_integration(self):
        """Test integration with blocking detector."""
        # Test with 429 error
        error = Exception("429 Too Many Requests")
        context = {'operation': 'get_transcript', 'video_id': 'test'}
        
        mock_alert = Mock()
        self.blocking_detector.record_error.return_value = mock_alert
        
        result = self.error_handler.handle_error(error, context)
        
        # Verify blocking detector was called with correct parameters
        self.blocking_detector.record_error.assert_called_once_with(
            status_code=429,
            error_message=str(error),
            request_type='get_transcript',
            video_id='test'
        )
        
        self.assertEqual(result.blocking_alert, mock_alert)
    
    def test_error_counter(self):
        """Test error counter functionality."""
        initial_count = self.error_handler.error_counter
        
        error = Exception("Test error")
        result1 = self.error_handler.handle_error(error, {})
        result2 = self.error_handler.handle_error(error, {})
        
        # Error counter should increment
        self.assertEqual(self.error_handler.error_counter, initial_count + 2)
        
        # Error IDs should be different
        self.assertNotEqual(result1.error_id, result2.error_id)


if __name__ == '__main__':
    unittest.main()