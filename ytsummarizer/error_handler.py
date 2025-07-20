"""
Unified error handling system with categorization and retry logic
"""

import logging
import traceback
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .youtube_blocking_detector import YouTubeBlockingDetector, BlockingAlert

logger = logging.getLogger("ytsummarizer.error_handler")


class ErrorCategory(Enum):
    """Categories of errors for appropriate handling."""
    NETWORK_ERROR = "network"
    RATE_LIMIT = "rate_limit"
    BLOCKING = "blocking"
    TRANSCRIPT_ERROR = "transcript"
    VIDEO_ERROR = "video"
    SYSTEM_ERROR = "system"
    AUTHENTICATION_ERROR = "authentication"
    PERMISSION_ERROR = "permission"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(Enum):
    """Recommended actions for error handling."""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    WAIT = "wait"
    USER_ACTION = "user_action"
    IGNORE = "ignore"


@dataclass
class ErrorResult:
    """Result of error processing with recommended actions."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    action: ActionType
    message: str
    user_message: str
    resolution_steps: List[str]
    retry_delay: int = 0
    max_retries: int = 0
    context: Dict[str, Any] = None
    blocking_alert: Optional[BlockingAlert] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class ErrorHandler:
    """Unified error handling with retry logic and user guidance."""
    
    def __init__(self, blocking_detector: Optional[YouTubeBlockingDetector] = None):
        """
        Initialize ErrorHandler.
        
        Args:
            blocking_detector: YouTube blocking detector instance
        """
        self.blocking_detector = blocking_detector or YouTubeBlockingDetector()
        self.error_patterns = self._initialize_error_patterns()
        self.error_counter = 0
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> ErrorResult:
        """
        Process error and determine appropriate action.
        
        Args:
            error: Exception that occurred
            context: Context information (operation, video_id, etc.)
            
        Returns:
            ErrorResult with categorization and recommended actions
        """
        self.error_counter += 1
        error_id = f"err_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.error_counter:03d}"
        
        # Categorize the error
        category = self.categorize_error(error)
        severity = self._determine_severity(error, category, context)
        
        # Check for blocking if it's a network-related error
        blocking_alert = None
        if category in [ErrorCategory.RATE_LIMIT, ErrorCategory.BLOCKING, ErrorCategory.NETWORK_ERROR]:
            blocking_alert = self._check_blocking(error, context)
        
        # Determine recommended action
        action = self._determine_action(error, category, context)
        
        # Generate messages
        message = str(error)
        user_message = self.get_user_message(error, category)
        resolution_steps = self.get_resolution_steps(error, category)
        
        # Calculate retry parameters
        retry_delay = self.get_retry_delay(error, context.get('attempt', 1))
        max_retries = self._get_max_retries(category)
        
        result = ErrorResult(
            error_id=error_id,
            category=category,
            severity=severity,
            action=action,
            message=message,
            user_message=user_message,
            resolution_steps=resolution_steps,
            retry_delay=retry_delay,
            max_retries=max_retries,
            context=context,
            blocking_alert=blocking_alert
        )
        
        # Log the error
        self._log_error(result, error)
        
        return result
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize error based on type and message.
        
        Args:
            error: Exception to categorize
            
        Returns:
            ErrorCategory enum value
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Check specific error patterns
        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_str, re.IGNORECASE) or pattern in error_type.lower():
                    return category
        
        # Check by exception type
        if 'http' in error_type.lower():
            if '429' in error_str or 'too many requests' in error_str:
                return ErrorCategory.RATE_LIMIT
            elif '403' in error_str or 'forbidden' in error_str:
                return ErrorCategory.BLOCKING
            elif '401' in error_str or 'unauthorized' in error_str:
                return ErrorCategory.AUTHENTICATION_ERROR
            else:
                return ErrorCategory.NETWORK_ERROR
        
        if 'permission' in error_type.lower() or 'access' in error_str:
            return ErrorCategory.PERMISSION_ERROR
        
        if 'transcript' in error_str or 'subtitle' in error_str:
            return ErrorCategory.TRANSCRIPT_ERROR
        
        if 'video' in error_str or 'download' in error_str:
            return ErrorCategory.VIDEO_ERROR
        
        return ErrorCategory.UNKNOWN
    
    def get_user_message(self, error: Exception, category: ErrorCategory) -> str:
        """
        Generate user-friendly error message.
        
        Args:
            error: Exception that occurred
            category: Error category
            
        Returns:
            User-friendly error message
        """
        messages = {
            ErrorCategory.NETWORK_ERROR: "Network connection issue. Please check your internet connection.",
            ErrorCategory.RATE_LIMIT: "YouTube is limiting requests. The application will wait before retrying.",
            ErrorCategory.BLOCKING: "YouTube may be blocking requests from your IP address.",
            ErrorCategory.TRANSCRIPT_ERROR: "Unable to retrieve video transcript. The video may not have subtitles available.",
            ErrorCategory.VIDEO_ERROR: "Unable to process the video. It may be private, deleted, or restricted.",
            ErrorCategory.SYSTEM_ERROR: "A system error occurred. Please try again.",
            ErrorCategory.AUTHENTICATION_ERROR: "Authentication failed. Please check your credentials or cookies.",
            ErrorCategory.PERMISSION_ERROR: "Permission denied. Please check file/folder permissions.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred."
        }
        
        base_message = messages.get(category, messages[ErrorCategory.UNKNOWN])
        
        # Add specific details for certain errors
        if "private" in str(error).lower():
            base_message += " The video appears to be private."
        elif "age" in str(error).lower():
            base_message += " The video may have age restrictions."
        elif "region" in str(error).lower():
            base_message += " The video may be region-blocked."
        
        return base_message
    
    def get_resolution_steps(self, error: Exception, category: ErrorCategory) -> List[str]:
        """
        Get recommended steps to resolve the error.
        
        Args:
            error: Exception that occurred
            category: Error category
            
        Returns:
            List of resolution steps
        """
        steps = {
            ErrorCategory.NETWORK_ERROR: [
                "Check your internet connection",
                "Try again in a few minutes",
                "Consider using a VPN if the issue persists"
            ],
            ErrorCategory.RATE_LIMIT: [
                "Wait for the automatic retry",
                "Reduce the number of concurrent operations",
                "Try again later when rate limits reset"
            ],
            ErrorCategory.BLOCKING: [
                "Wait 1-24 hours before trying again",
                "Change your IP address (restart router or use VPN)",
                "Try using different YouTube cookies",
                "Reduce request frequency"
            ],
            ErrorCategory.TRANSCRIPT_ERROR: [
                "Check if the video has subtitles available",
                "Try a different video from the same channel",
                "Use manual transcript input if available"
            ],
            ErrorCategory.VIDEO_ERROR: [
                "Verify the video URL is correct and accessible",
                "Check if the video is public and not age-restricted",
                "Try updating your YouTube cookies",
                "Skip this video and continue with others"
            ],
            ErrorCategory.AUTHENTICATION_ERROR: [
                "Update your YouTube cookies",
                "Check if your YouTube account is still valid",
                "Try logging out and back into YouTube in your browser"
            ],
            ErrorCategory.PERMISSION_ERROR: [
                "Check file and folder permissions",
                "Run the application as administrator if needed",
                "Ensure the output directory is writable"
            ],
            ErrorCategory.SYSTEM_ERROR: [
                "Restart the application",
                "Check available disk space",
                "Close other applications to free up memory"
            ],
            ErrorCategory.UNKNOWN: [
                "Try the operation again",
                "Restart the application if the problem persists",
                "Check the application logs for more details"
            ]
        }
        
        return steps.get(category, steps[ErrorCategory.UNKNOWN])
    
    def should_retry(self, error: Exception, attempt: int, max_retries: int = 3) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            error: Exception that occurred
            attempt: Current attempt number (1-based)
            max_retries: Maximum number of retries allowed
            
        Returns:
            True if should retry
        """
        if attempt >= max_retries:
            return False
        
        category = self.categorize_error(error)
        
        # Always retry for transient errors
        if category in [ErrorCategory.NETWORK_ERROR, ErrorCategory.RATE_LIMIT]:
            return True
        
        # Sometimes retry for blocking (with longer delays)
        if category == ErrorCategory.BLOCKING and attempt <= 2:
            return True
        
        # Don't retry for permanent errors
        if category in [ErrorCategory.AUTHENTICATION_ERROR, ErrorCategory.PERMISSION_ERROR]:
            return False
        
        # Retry once for unknown errors
        if category == ErrorCategory.UNKNOWN and attempt == 1:
            return True
        
        return False
    
    def get_retry_delay(self, error: Exception, attempt: int) -> int:
        """
        Calculate delay before retry in seconds.
        
        Args:
            error: Exception that occurred
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        category = self.categorize_error(error)
        
        base_delays = {
            ErrorCategory.NETWORK_ERROR: 5,
            ErrorCategory.RATE_LIMIT: 60,
            ErrorCategory.BLOCKING: 300,  # 5 minutes
            ErrorCategory.TRANSCRIPT_ERROR: 10,
            ErrorCategory.VIDEO_ERROR: 15,
            ErrorCategory.SYSTEM_ERROR: 30,
            ErrorCategory.UNKNOWN: 10
        }
        
        base_delay = base_delays.get(category, 10)
        
        # Exponential backoff with jitter
        import random
        delay = min(base_delay * (2 ** (attempt - 1)), 600)  # Max 10 minutes
        jitter = random.uniform(0.8, 1.2)
        
        return int(delay * jitter)
    
    def _initialize_error_patterns(self) -> Dict[ErrorCategory, List[str]]:
        """Initialize regex patterns for error categorization."""
        return {
            ErrorCategory.NETWORK_ERROR: [
                r'connection.*error',
                r'timeout',
                r'network.*unreachable',
                r'dns.*resolution.*failed',
                r'socket.*error',
                r'connection.*refused',
                r'connection.*reset'
            ],
            ErrorCategory.RATE_LIMIT: [
                r'429',
                r'too many requests',
                r'rate.*limit',
                r'quota.*exceeded',
                r'request.*limit'
            ],
            ErrorCategory.BLOCKING: [
                r'403.*forbidden',
                r'access.*denied',
                r'ip.*blocked',
                r'region.*blocked',
                r'country.*blocked'
            ],
            ErrorCategory.TRANSCRIPT_ERROR: [
                r'transcript.*not.*available',
                r'no.*transcript.*found',
                r'subtitle.*not.*found',
                r'captions.*disabled',
                r'transcript.*api.*error'
            ],
            ErrorCategory.VIDEO_ERROR: [
                r'video.*not.*available',
                r'video.*private',
                r'video.*deleted',
                r'age.*restricted',
                r'video.*unavailable',
                r'invalid.*video.*id'
            ],
            ErrorCategory.AUTHENTICATION_ERROR: [
                r'401.*unauthorized',
                r'authentication.*failed',
                r'invalid.*credentials',
                r'login.*required',
                r'cookie.*expired'
            ],
            ErrorCategory.PERMISSION_ERROR: [
                r'permission.*denied',
                r'access.*is.*denied',
                r'insufficient.*privileges',
                r'file.*permission',
                r'directory.*permission'
            ]
        }
    
    def _determine_severity(self, error: Exception, category: ErrorCategory, context: Dict) -> ErrorSeverity:
        """Determine error severity based on category and context."""
        # Critical errors that stop processing
        if category in [ErrorCategory.SYSTEM_ERROR, ErrorCategory.PERMISSION_ERROR]:
            return ErrorSeverity.CRITICAL
        
        # High severity for blocking issues
        if category in [ErrorCategory.BLOCKING, ErrorCategory.AUTHENTICATION_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium for rate limiting and network issues
        if category in [ErrorCategory.RATE_LIMIT, ErrorCategory.NETWORK_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Low for individual video/transcript issues
        return ErrorSeverity.LOW
    
    def _determine_action(self, error: Exception, category: ErrorCategory, context: Dict) -> ActionType:
        """Determine recommended action based on error category."""
        action_map = {
            ErrorCategory.NETWORK_ERROR: ActionType.RETRY,
            ErrorCategory.RATE_LIMIT: ActionType.WAIT,
            ErrorCategory.BLOCKING: ActionType.USER_ACTION,
            ErrorCategory.TRANSCRIPT_ERROR: ActionType.SKIP,
            ErrorCategory.VIDEO_ERROR: ActionType.SKIP,
            ErrorCategory.AUTHENTICATION_ERROR: ActionType.USER_ACTION,
            ErrorCategory.PERMISSION_ERROR: ActionType.USER_ACTION,
            ErrorCategory.SYSTEM_ERROR: ActionType.ABORT,
            ErrorCategory.UNKNOWN: ActionType.RETRY
        }
        
        return action_map.get(category, ActionType.RETRY)
    
    def _get_max_retries(self, category: ErrorCategory) -> int:
        """Get maximum retry count for error category."""
        retry_limits = {
            ErrorCategory.NETWORK_ERROR: 3,
            ErrorCategory.RATE_LIMIT: 5,
            ErrorCategory.BLOCKING: 2,
            ErrorCategory.TRANSCRIPT_ERROR: 2,
            ErrorCategory.VIDEO_ERROR: 2,
            ErrorCategory.AUTHENTICATION_ERROR: 1,
            ErrorCategory.PERMISSION_ERROR: 0,
            ErrorCategory.SYSTEM_ERROR: 1,
            ErrorCategory.UNKNOWN: 2
        }
        
        return retry_limits.get(category, 2)
    
    def _check_blocking(self, error: Exception, context: Dict) -> Optional[BlockingAlert]:
        """Check if error indicates YouTube blocking."""
        if not self.blocking_detector:
            return None
        
        # Extract status code from error
        status_code = 0
        error_str = str(error)
        
        if '429' in error_str:
            status_code = 429
        elif '403' in error_str:
            status_code = 403
        elif '503' in error_str:
            status_code = 503
        
        if status_code > 0:
            return self.blocking_detector.record_error(
                status_code=status_code,
                error_message=error_str,
                request_type=context.get('operation', 'unknown'),
                video_id=context.get('video_id')
            )
        
        return None
    
    def _log_error(self, result: ErrorResult, error: Exception):
        """Log error with full context."""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(result.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"Error {result.error_id}: {result.category.value} - {result.message}"
        )
        
        # Log full traceback for critical errors
        if result.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Full traceback for {result.error_id}:\n{traceback.format_exc()}")
        
        # Log context information
        if result.context:
            logger.debug(f"Error context for {result.error_id}: {result.context}")