"""
Unit tests for retry logic
"""

import unittest
import time
from unittest.mock import Mock, patch, call
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ytsummarizer.retry_logic import (
    RetryConfig, RetryManager, retry_on_error, 
    retry_youtube_operation, retry_network_operation
)
from ytsummarizer.error_handler import ErrorHandler, ErrorCategory, ActionType


class TestRetryConfig(unittest.TestCase):
    """Test cases for RetryConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.base_delay, 1.0)
        self.assertEqual(config.max_delay, 300.0)
        self.assertEqual(config.exponential_base, 2.0)
        self.assertTrue(config.jitter)
    
    def test_delay_calculation(self):
        """Test delay calculation with exponential backoff."""
        config = RetryConfig(base_delay=2.0, exponential_base=2.0, jitter=False)
        
        # Test exponential backoff
        delay1 = config.get_delay(1)
        delay2 = config.get_delay(2)
        delay3 = config.get_delay(3)
        
        self.assertEqual(delay1, 2.0)  # 2.0 * 2^0
        self.assertEqual(delay2, 4.0)  # 2.0 * 2^1
        self.assertEqual(delay3, 8.0)  # 2.0 * 2^2
    
    def test_max_delay_limit(self):
        """Test maximum delay limit."""
        config = RetryConfig(base_delay=100.0, max_delay=50.0, jitter=False)
        
        # Should be limited by max_delay
        delay = config.get_delay(5)  # Would be 100 * 2^4 = 1600 without limit
        self.assertEqual(delay, 50.0)
    
    def test_category_specific_delays(self):
        """Test category-specific base delays."""
        config = RetryConfig(jitter=False)
        
        # Rate limit should have longer delay
        rate_delay = config.get_delay(1, ErrorCategory.RATE_LIMIT)
        network_delay = config.get_delay(1, ErrorCategory.NETWORK_ERROR)
        
        self.assertGreater(rate_delay, network_delay)
    
    def test_jitter_application(self):
        """Test jitter application."""
        config = RetryConfig(base_delay=10.0, jitter=True, jitter_range=0.2)
        
        # With jitter, delays should vary
        delays = [config.get_delay(1) for _ in range(10)]
        
        # Should have some variation (not all identical)
        self.assertGreater(len(set(delays)), 1)
        
        # All delays should be positive
        self.assertTrue(all(d > 0 for d in delays))


class TestRetryManager(unittest.TestCase):
    """Test cases for RetryManager."""
    
    def setUp(self):
        """Set up test environment."""
        self.error_handler = Mock(spec=ErrorHandler)
        self.config = RetryConfig(max_retries=3, base_delay=0.1, jitter=False)
        self.retry_manager = RetryManager(self.error_handler, self.config)
    
    def test_successful_operation(self):
        """Test successful operation without retries."""
        mock_func = Mock(return_value="success")
        
        result = self.retry_manager.retry_with_backoff(mock_func, "arg1", kwarg1="value1")
        
        self.assertEqual(result, "success")
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        self.error_handler.handle_error.assert_not_called()
    
    def test_retry_on_failure(self):
        """Test retry behavior on failures."""
        # Mock function that fails twice then succeeds
        mock_func = Mock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])
        
        # Mock error handler to allow retries
        mock_error_result = Mock()
        mock_error_result.action = ActionType.RETRY
        mock_error_result.category = ErrorCategory.NETWORK_ERROR
        mock_error_result.retry_delay = 0.1
        self.error_handler.handle_error.return_value = mock_error_result
        
        result = self.retry_manager.retry_with_backoff(mock_func)
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(self.error_handler.handle_error.call_count, 2)
    
    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded."""
        mock_func = Mock(side_effect=Exception("persistent failure"))
        
        # Mock error handler to allow retries
        mock_error_result = Mock()
        mock_error_result.action = ActionType.RETRY
        mock_error_result.category = ErrorCategory.NETWORK_ERROR
        mock_error_result.retry_delay = 0.1
        self.error_handler.handle_error.return_value = mock_error_result
        
        with self.assertRaises(Exception) as cm:
            self.retry_manager.retry_with_backoff(mock_func, max_retries=2)
        
        self.assertEqual(str(cm.exception), "persistent failure")
        self.assertEqual(mock_func.call_count, 2)
    
    def test_non_retryable_error(self):
        """Test behavior with non-retryable errors."""
        mock_func = Mock(side_effect=Exception("non-retryable"))
        
        # Mock error handler to not allow retries
        mock_error_result = Mock()
        mock_error_result.action = ActionType.ABORT
        mock_error_result.category = ErrorCategory.PERMISSION_ERROR
        self.error_handler.handle_error.return_value = mock_error_result
        
        with self.assertRaises(Exception) as cm:
            self.retry_manager.retry_with_backoff(mock_func)
        
        self.assertEqual(str(cm.exception), "non-retryable")
        self.assertEqual(mock_func.call_count, 1)  # Should not retry
    
    def test_retry_callback(self):
        """Test retry callback functionality."""
        mock_func = Mock(side_effect=[Exception("fail"), "success"])
        mock_callback = Mock()
        
        # Mock error handler
        mock_error_result = Mock()
        mock_error_result.action = ActionType.RETRY
        mock_error_result.category = ErrorCategory.NETWORK_ERROR
        mock_error_result.retry_delay = 0.1
        self.error_handler.handle_error.return_value = mock_error_result
        
        result = self.retry_manager.retry_with_backoff(
            mock_func, 
            on_retry=mock_callback
        )
        
        self.assertEqual(result, "success")
        mock_callback.assert_called_once()
    
    def test_operation_tracking(self):
        """Test operation tracking functionality."""
        operation_id = "test_operation"
        
        # Initially no active retries
        self.assertEqual(self.retry_manager.get_retry_status(operation_id), None)
        
        # Mock function that fails once
        mock_func = Mock(side_effect=[Exception("fail"), "success"])
        
        # Mock error handler
        mock_error_result = Mock()
        mock_error_result.action = ActionType.RETRY
        mock_error_result.category = ErrorCategory.NETWORK_ERROR
        mock_error_result.retry_delay = 0.01  # Very short delay for testing
        self.error_handler.handle_error.return_value = mock_error_result
        
        # Start operation in a separate thread to test tracking
        import threading
        result_container = []
        
        def run_operation():
            result = self.retry_manager.retry_with_backoff(
                mock_func, 
                operation_id=operation_id
            )
            result_container.append(result)
        
        thread = threading.Thread(target=run_operation)
        thread.start()
        thread.join()
        
        # Should complete successfully
        self.assertEqual(result_container[0], "success")
        
        # Should no longer be tracked after completion
        self.assertEqual(self.retry_manager.get_retry_status(operation_id), None)
    
    def test_cancel_retries(self):
        """Test retry cancellation."""
        operation_id = "test_cancel"
        
        # Add to active retries
        self.retry_manager.active_retries[operation_id] = 2
        
        # Cancel should return True and remove from tracking
        self.assertTrue(self.retry_manager.cancel_retries(operation_id))
        self.assertNotIn(operation_id, self.retry_manager.active_retries)
        
        # Cancelling non-existent operation should return False
        self.assertFalse(self.retry_manager.cancel_retries("non_existent"))


class TestRetryDecorator(unittest.TestCase):
    """Test cases for retry decorator."""
    
    def test_decorator_success(self):
        """Test decorator with successful function."""
        @retry_on_error(max_retries=2, delay=0.1)
        def successful_func(x):
            return x * 2
        
        result = successful_func(5)
        self.assertEqual(result, 10)
    
    def test_decorator_with_retries(self):
        """Test decorator with failing then successful function."""
        call_count = 0
        
        @retry_on_error(max_retries=3, delay=0.1)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Failure {call_count}")
            return "success"
        
        result = flaky_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_decorator_max_retries(self):
        """Test decorator when max retries exceeded."""
        @retry_on_error(max_retries=2, delay=0.1)
        def always_fail():
            raise Exception("Always fails")
        
        with self.assertRaises(Exception) as cm:
            always_fail()
        
        self.assertEqual(str(cm.exception), "Always fails")


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions."""
    
    def test_retry_youtube_operation(self):
        """Test YouTube-specific retry function."""
        mock_func = Mock(return_value="youtube_success")
        error_handler = Mock(spec=ErrorHandler)
        
        result = retry_youtube_operation(mock_func, error_handler)
        
        self.assertEqual(result, "youtube_success")
        mock_func.assert_called_once()
    
    def test_retry_network_operation(self):
        """Test network-specific retry function."""
        mock_func = Mock(return_value="network_success")
        error_handler = Mock(spec=ErrorHandler)
        
        result = retry_network_operation(mock_func, error_handler)
        
        self.assertEqual(result, "network_success")
        mock_func.assert_called_once()
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_retry_with_different_configs(self, mock_sleep):
        """Test that different utility functions use different configs."""
        error_handler = Mock(spec=ErrorHandler)
        
        # Mock error result for retries
        mock_error_result = Mock()
        mock_error_result.action = ActionType.RETRY
        mock_error_result.category = ErrorCategory.NETWORK_ERROR
        mock_error_result.retry_delay = 1.0
        error_handler.handle_error.return_value = mock_error_result
        
        # Function that fails once then succeeds
        mock_func = Mock(side_effect=[Exception("fail"), "success"])
        
        # Test YouTube operation (should have longer delays)
        result = retry_youtube_operation(mock_func, error_handler, max_retries=2)
        self.assertEqual(result, "success")
        
        # Reset mock
        mock_func.reset_mock()
        mock_func.side_effect = [Exception("fail"), "success"]
        
        # Test network operation (should have shorter delays)
        result = retry_network_operation(mock_func, error_handler, max_retries=2)
        self.assertEqual(result, "success")


if __name__ == '__main__':
    unittest.main()