"""
Advanced retry logic with exponential backoff and jitter
"""

import time
import random
import logging
import functools
from typing import Callable, Any, Optional, Dict, List, Type
from dataclasses import dataclass
from enum import Enum

from .error_handler import ErrorHandler, ErrorCategory, ActionType
from .youtube_blocking_detector import YouTubeBlockingDetector

logger = logging.getLogger("ytsummarizer.retry_logic")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 300.0  # 5 minutes
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.2  # ±20% jitter
    
    def get_delay(self, attempt: int, error_category: Optional[ErrorCategory] = None) -> float:
        """
        Calculate delay with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (1-based)
            error_category: Category of error for specialized delays
            
        Returns:
            Delay in seconds
        """
        # Category-specific base delays
        category_delays = {
            ErrorCategory.NETWORK_ERROR: 2.0,
            ErrorCategory.RATE_LIMIT: 60.0,
            ErrorCategory.BLOCKING: 300.0,  # 5 minutes
            ErrorCategory.TRANSCRIPT_ERROR: 5.0,
            ErrorCategory.VIDEO_ERROR: 10.0,
            ErrorCategory.SYSTEM_ERROR: 30.0,
        }
        
        base = category_delays.get(error_category, self.base_delay)
        
        # Exponential backoff
        delay = min(base * (self.exponential_base ** (attempt - 1)), self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay + jitter)  # Minimum 0.1 second delay
        
        return delay
    
    def should_retry_with_blocking_check(self, error: Exception, operation_type: str = "unknown") -> bool:
        """
        Check if operation should be retried considering blocking status.
        
        Args:
            error: Exception that occurred
            operation_type: Type of operation (transcript, video_info, etc.)
            
        Returns:
            True if should retry, False if blocked or non-retryable
        """
        # Check if operation is blocked due to YouTube blocking
        if self.is_operation_blocked(operation_type):
            logger.info(f"Operation {operation_type} is blocked - not retrying")
            return False
        
        # Check if blocking detector indicates we should halt
        if self.blocking_detector and self.blocking_detector.should_halt_processing():
            logger.warning(f"YouTube blocking detected - marking {operation_type} as blocked")
            self.blocked_operations.add(operation_type)
            return False
        
        # Use normal error handling logic
        error_result = self.error_handler.handle_error(error, {"operation_type": operation_type})
        return error_result.action == ActionType.RETRY
    
    def is_operation_blocked(self, operation_type: str) -> bool:
        """Check if a specific operation type is blocked due to YouTube blocking."""
        return operation_type in self.blocked_operations
    
    def get_blocking_aware_delay(self, attempt: int, error_category: Optional[ErrorCategory] = None) -> float:
        """
        Calculate delay considering blocking status.
        
        Args:
            attempt: Current attempt number
            error_category: Category of error
            
        Returns:
            Delay in seconds, or -1 if should not retry due to blocking
        """
        # Check if we're in a blocking state
        if self.blocking_detector and self.blocking_detector.should_halt_processing():
            logger.warning("Blocking detected - returning no-retry signal")
            return -1  # Signal that retry should not happen
        
        # Use normal delay calculation
        return self.config.get_delay(attempt, error_category)
    
    def clear_blocked_operations(self):
        """Clear all blocked operations (call when blocking is resolved)."""
        if self.blocked_operations:
            logger.info(f"Clearing {len(self.blocked_operations)} blocked operations")
            self.blocked_operations.clear()
    
    def mark_operation_as_blocked(self, operation_type: str):
        """Manually mark an operation as blocked."""
        self.blocked_operations.add(operation_type)
        logger.info(f"Operation {operation_type} marked as blocked")
    
    def unblock_operation(self, operation_type: str):
        """Unblock a specific operation type."""
        self.blocked_operations.discard(operation_type)
        logger.info(f"Operation {operation_type} unblocked")


class RetryResult(Enum):
    """Result of retry operation."""
    SUCCESS = "success"
    FAILED_MAX_RETRIES = "failed_max_retries"
    FAILED_NON_RETRYABLE = "failed_non_retryable"
    FAILED_USER_ABORT = "failed_user_abort"


class RetryManager:
    """Advanced retry manager with error handling integration."""
    
    def __init__(self, error_handler: ErrorHandler, config: Optional[RetryConfig] = None,
                 blocking_detector: Optional[YouTubeBlockingDetector] = None):
        """
        Initialize RetryManager.
        
        Args:
            error_handler: ErrorHandler instance for error processing
            config: Retry configuration
            blocking_detector: YouTube blocking detector for blocking-aware retries
        """
        self.error_handler = error_handler
        self.config = config or RetryConfig()
        self.blocking_detector = blocking_detector
        self.active_retries: Dict[str, int] = {}  # Track retry counts by operation
        self.blocked_operations: set[str] = set()  # Track operations blocked due to YouTube blocking
    
    def retry_with_backoff(self, 
                          func: Callable,
                          *args,
                          operation_id: Optional[str] = None,
                          context: Optional[Dict] = None,
                          max_retries: Optional[int] = None,
                          on_retry: Optional[Callable] = None,
                          **kwargs) -> Any:
        """
        Execute function with retry logic and exponential backoff.
        
        Args:
            func: Function to execute
            *args: Function arguments
            operation_id: Unique identifier for this operation
            context: Context information for error handling
            max_retries: Override default max retries
            on_retry: Callback function called before each retry
            **kwargs: Function keyword arguments
            
        Returns:
            Function result if successful
            
        Raises:
            Last exception if all retries failed
        """
        operation_id = operation_id or f"retry_{id(func)}_{time.time()}"
        context = context or {}
        max_retries = max_retries or self.config.max_retries
        
        last_exception = None
        
        for attempt in range(1, max_retries + 1):
            try:
                # Track attempt in context
                context['attempt'] = attempt
                context['max_attempts'] = max_retries
                context['operation_id'] = operation_id
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Success - clean up tracking
                if operation_id in self.active_retries:
                    del self.active_retries[operation_id]
                
                logger.debug(f"Operation {operation_id} succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                
                # Process error through error handler
                error_result = self.error_handler.handle_error(e, context)
                
                # Check if we should retry
                if attempt >= max_retries:
                    logger.error(f"Operation {operation_id} failed after {max_retries} attempts")
                    break
                
                if error_result.action not in [ActionType.RETRY, ActionType.WAIT]:
                    logger.info(f"Operation {operation_id} not retryable: {error_result.action}")
                    break
                
                # Check for blocking before retrying
                operation_type = context.get('operation_type', 'unknown')
                if not self.should_retry_with_blocking_check(e, operation_type):
                    logger.warning(f"Operation {operation_id} blocked due to YouTube blocking - stopping retries")
                    break
                
                # Calculate delay with blocking awareness
                delay = self.get_blocking_aware_delay(attempt, error_result.category)
                if delay < 0:  # Blocking detected
                    logger.warning(f"Operation {operation_id} halted due to blocking")
                    break
                
                # Use error handler's delay if it's longer
                if error_result.retry_delay > delay:
                    delay = error_result.retry_delay
                
                # Track retry
                self.active_retries[operation_id] = attempt
                
                logger.warning(
                    f"Operation {operation_id} failed on attempt {attempt}/{max_retries}: "
                    f"{error_result.category.value} - {str(e)[:100]}. "
                    f"Retrying in {delay:.1f} seconds..."
                )
                
                # Call retry callback if provided
                if on_retry:
                    try:
                        on_retry(attempt, error_result, delay)
                    except Exception as callback_error:
                        logger.error(f"Retry callback failed: {callback_error}")
                
                # Wait before retry
                time.sleep(delay)
        
        # All retries failed
        if operation_id in self.active_retries:
            del self.active_retries[operation_id]
        
        raise last_exception
    
    def get_retry_status(self, operation_id: str) -> Optional[int]:
        """
        Get current retry count for an operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            Current retry count or None if not found
        """
        return self.active_retries.get(operation_id)
    
    def cancel_retries(self, operation_id: str) -> bool:
        """
        Cancel ongoing retries for an operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            True if cancelled, False if not found
        """
        if operation_id in self.active_retries:
            del self.active_retries[operation_id]
            logger.info(f"Cancelled retries for operation: {operation_id}")
            return True
        return False
    
    def get_active_retries(self) -> Dict[str, int]:
        """Get all active retry operations."""
        return self.active_retries.copy()


def retry_on_error(max_retries: int = 3,
                  delay: float = 1.0,
                  exponential_base: float = 2.0,
                  max_delay: float = 300.0,
                  exceptions: Optional[List[Type[Exception]]] = None,
                  error_handler: Optional[ErrorHandler] = None):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Base delay between retries
        exponential_base: Base for exponential backoff
        max_delay: Maximum delay between retries
        exceptions: List of exception types to retry on (None = all exceptions)
        error_handler: ErrorHandler instance for advanced error processing
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay=delay,
                exponential_base=exponential_base,
                max_delay=max_delay
            )
            
            # Use provided error handler or create a basic one
            handler = error_handler or ErrorHandler()
            retry_manager = RetryManager(handler, config)
            
            # Create context from function info
            context = {
                'function': func.__name__,
                'module': func.__module__,
            }
            
            return retry_manager.retry_with_backoff(
                func, *args, 
                context=context,
                **kwargs
            )
        
        return wrapper
    return decorator


class AsyncRetryManager:
    """Async version of RetryManager for future async operations."""
    
    def __init__(self, error_handler: ErrorHandler, config: Optional[RetryConfig] = None):
        self.error_handler = error_handler
        self.config = config or RetryConfig()
        self.active_retries: Dict[str, int] = {}
    
    async def retry_with_backoff_async(self,
                                     func: Callable,
                                     *args,
                                     operation_id: Optional[str] = None,
                                     context: Optional[Dict] = None,
                                     max_retries: Optional[int] = None,
                                     on_retry: Optional[Callable] = None,
                                     **kwargs) -> Any:
        """
        Async version of retry_with_backoff.
        
        Note: This is a placeholder for future async implementation.
        Currently not used but prepared for async operations.
        """
        # This would be implemented when async operations are needed
        # For now, we'll use the synchronous version
        pass


# Utility functions for common retry patterns

def retry_youtube_operation(func: Callable, 
                          error_handler: ErrorHandler,
                          max_retries: int = 5,
                          context: Optional[Dict] = None) -> Any:
    """
    Retry YouTube-specific operations with appropriate delays.
    
    Args:
        func: Function to retry
        error_handler: ErrorHandler instance
        max_retries: Maximum retry attempts
        context: Operation context
        
    Returns:
        Function result
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=2.0,
        max_delay=600.0,  # 10 minutes for YouTube operations
        exponential_base=2.0,
        jitter=True
    )
    
    retry_manager = RetryManager(error_handler, config)
    return retry_manager.retry_with_backoff(func, context=context)


def retry_network_operation(func: Callable,
                          error_handler: ErrorHandler,
                          max_retries: int = 3,
                          context: Optional[Dict] = None) -> Any:
    """
    Retry network operations with shorter delays.
    
    Args:
        func: Function to retry
        error_handler: ErrorHandler instance
        max_retries: Maximum retry attempts
        context: Operation context
        
    Returns:
        Function result
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=1.0,
        max_delay=60.0,  # 1 minute max for network operations
        exponential_base=2.0,
        jitter=True
    )
    
    retry_manager = RetryManager(error_handler, config)
    return retry_manager.retry_with_backoff(func, context=context)