"""
YouTube Blocking Detection System

This module provides functionality for detecting YouTube API limitations,
rate limiting, and IP blocks that may occur during video processing.
"""

import time
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# Configure logging
logger = logging.getLogger("ytsummarizer.youtube_blocking_detector")


class BlockType(Enum):
    """Types of YouTube blocks/restrictions."""
    RATE_LIMIT = "rate_limit"  # HTTP 429 - Too Many Requests
    FORBIDDEN = "forbidden"    # HTTP 403 - Forbidden
    SERVER_ERROR = "server_error"  # HTTP 503 - Service Unavailable
    IP_BLOCK = "ip_block"      # Consistent 403s suggest IP block
    CLOUD_IP_BLOCK = "cloud_ip_block"  # Cloud provider IP blocking
    UNKNOWN = "unknown"        # Other blocking patterns


@dataclass
class ErrorEvent:
    """Represents a single error event from YouTube."""
    timestamp: datetime
    status_code: int
    error_message: str
    request_type: str = "unknown"  # video, playlist, transcript, etc.
    video_id: Optional[str] = None


@dataclass
class BlockingAlert:
    """Alert generated when blocking is detected."""
    block_type: BlockType
    severity: str  # "warning", "critical"
    message: str
    recommendation: str
    error_count: int
    time_window: timedelta
    first_error: datetime
    last_error: datetime


class YouTubeBlockingDetector:
    """
    Advanced YouTube blocking detection system.
    
    Monitors HTTP requests and responses to detect various types of
    YouTube restrictions and provides recommendations for handling them.
    """
    
    def __init__(self, 
                 max_errors_threshold: int = 5,
                 time_window_minutes: int = 10,
                 consecutive_403_threshold: int = 3):
        """
        Initialize the blocking detector.
        
        Args:
            max_errors_threshold: Maximum errors before considering blocked
            time_window_minutes: Time window for error rate analysis
            consecutive_403_threshold: Consecutive 403s to trigger IP block alert
        """
        self.max_errors_threshold = max_errors_threshold
        self.time_window = timedelta(minutes=time_window_minutes)
        self.consecutive_403_threshold = consecutive_403_threshold
        
        self.error_events: List[ErrorEvent] = []
        self.current_alert: Optional[BlockingAlert] = None
        self.last_reset_time = datetime.now()
        self.processing_halted = False
        
        # IP blocking message patterns
        self.ip_block_patterns = [
            "YouTube is blocking requests from your IP",
            "requests from your IP",
            "cloud provider",
            "AWS, Google Cloud Platform, Azure",
            "IP has been blocked by YouTube",
            "too many requests and your IP has been blocked"
        ]
        
        logger.info(f"YouTubeBlockingDetector initialized with thresholds: "
                   f"max_errors={max_errors_threshold}, time_window={time_window_minutes}min, "
                   f"consecutive_403s={consecutive_403_threshold}")
    
    def record_error(self, status_code: int, error_message: str, 
                    request_type: str = "unknown", video_id: Optional[str] = None) -> Optional[BlockingAlert]:
        """
        Record an error event and analyze for blocking patterns.
        
        Args:
            status_code: HTTP status code
            error_message: Error message from the response
            request_type: Type of request (video, playlist, transcript, etc.)
            video_id: Video ID if applicable
            
        Returns:
            BlockingAlert if blocking is detected, None otherwise
        """
        now = datetime.now()
        
        # Record the error event
        error_event = ErrorEvent(
            timestamp=now,
            status_code=status_code,
            error_message=error_message,
            request_type=request_type,
            video_id=video_id
        )
        self.error_events.append(error_event)
        
        logger.debug(f"Recorded error: {status_code} - {error_message} "
                    f"({request_type}, video_id={video_id})")
        
        # Clean old events outside time window
        self._clean_old_events(now)
        
        # Analyze for blocking patterns
        return self._analyze_blocking_patterns()
    
    def record_success(self, request_type: str = "unknown", video_id: Optional[str] = None):
        """
        Record a successful request.
        
        Args:
            request_type: Type of successful request
            video_id: Video ID if applicable
        """
        logger.debug(f"Recorded success: {request_type}, video_id={video_id}")
        
        # If we had an alert and now have success, consider reducing severity
        if self.current_alert and self.current_alert.severity == "critical":
            # Check if recent errors are decreasing
            recent_errors = self._get_recent_errors(timedelta(minutes=2))
            if len(recent_errors) == 0:
                logger.info("Successful request after critical alert - reducing alert severity")
                if self.current_alert:
                    self.current_alert.severity = "warning"
    
    def _clean_old_events(self, current_time: datetime):
        """Remove error events outside the time window."""
        cutoff_time = current_time - self.time_window
        initial_count = len(self.error_events)
        self.error_events = [event for event in self.error_events 
                           if event.timestamp > cutoff_time]
        
        removed_count = initial_count - len(self.error_events)
        if removed_count > 0:
            logger.debug(f"Cleaned {removed_count} old error events")
    
    def _get_recent_errors(self, time_window: Optional[timedelta] = None) -> List[ErrorEvent]:
        """Get error events within the specified time window."""
        if time_window is None:
            time_window = self.time_window
            
        cutoff_time = datetime.now() - time_window
        return [event for event in self.error_events if event.timestamp > cutoff_time]
    
    def _analyze_blocking_patterns(self) -> Optional[BlockingAlert]:
        """Analyze error patterns to detect blocking."""
        recent_errors = self._get_recent_errors()
        
        if len(recent_errors) == 0:
            self.current_alert = None
            return None
        
        # Check for IP blocking message patterns (highest priority)
        for error in recent_errors:
            if self._contains_ip_block_pattern(error.error_message):
                block_type = BlockType.CLOUD_IP_BLOCK if "cloud provider" in error.error_message.lower() else BlockType.IP_BLOCK
                alert = self._create_alert(
                    block_type,
                    "critical",
                    f"IP blocking detected: {error.error_message[:100]}...",
                    "Change your IP address immediately. Cloud provider IPs are blocked by YouTube.",
                    recent_errors
                )
                self.halt_processing()  # Immediately halt processing
                return alert
        
        # Check for rate limiting (HTTP 429)
        rate_limit_errors = [e for e in recent_errors if e.status_code == 429]
        if len(rate_limit_errors) >= 2:
            alert = self._create_alert(
                BlockType.RATE_LIMIT,
                "critical",
                f"Rate limiting detected: {len(rate_limit_errors)} HTTP 429 errors",
                "Wait 10-30 minutes before retrying. Consider reducing request frequency.",
                recent_errors
            )
            self.halt_processing()  # Halt processing for rate limiting
            return alert
        
        # Check for consecutive 403 errors (potential IP block)
        if len(recent_errors) >= self.consecutive_403_threshold:
            recent_403s = [e for e in recent_errors[-self.consecutive_403_threshold:] 
                          if e.status_code == 403]
            if len(recent_403s) == self.consecutive_403_threshold:
                alert = self._create_alert(
                    BlockType.IP_BLOCK,
                    "critical",
                    f"Potential IP block: {len(recent_403s)} consecutive 403 errors",
                    "Change your IP address (restart router, use VPN, or wait 1-24 hours).",
                    recent_errors
                )
                self.halt_processing()  # Halt processing for IP block
                return alert
        
        # Check for general error threshold
        if len(recent_errors) >= self.max_errors_threshold:
            forbidden_count = len([e for e in recent_errors if e.status_code == 403])
            server_error_count = len([e for e in recent_errors if e.status_code in [503, 500]])
            
            if forbidden_count > server_error_count:
                return self._create_alert(
                    BlockType.FORBIDDEN,
                    "warning",
                    f"Multiple access errors: {forbidden_count} forbidden errors",
                    "Check if videos are private/restricted. Consider changing IP if errors persist.",
                    recent_errors
                )
            else:
                return self._create_alert(
                    BlockType.SERVER_ERROR,
                    "warning",
                    f"YouTube server issues: {len(recent_errors)} errors in {self.time_window}",
                    "YouTube may be experiencing issues. Wait and retry later.",
                    recent_errors
                )
        
        return None
    
    def _contains_ip_block_pattern(self, error_message: str) -> bool:
        """Check if error message contains IP blocking patterns."""
        if not error_message:
            return False
        
        error_lower = error_message.lower()
        return any(pattern.lower() in error_lower for pattern in self.ip_block_patterns)
    
    def _create_alert(self, block_type: BlockType, severity: str, 
                     message: str, recommendation: str, 
                     error_events: List[ErrorEvent]) -> BlockingAlert:
        """Create a blocking alert."""
        alert = BlockingAlert(
            block_type=block_type,
            severity=severity,
            message=message,
            recommendation=recommendation,
            error_count=len(error_events),
            time_window=self.time_window,
            first_error=min(event.timestamp for event in error_events),
            last_error=max(event.timestamp for event in error_events)
        )
        
        self.current_alert = alert
        logger.warning(f"Blocking alert created: {alert.block_type.value} - {alert.message}")
        
        return alert
    
    def get_current_status(self) -> dict:
        """Get current blocking detection status."""
        recent_errors = self._get_recent_errors()
        
        return {
            "total_errors": len(self.error_events),
            "recent_errors": len(recent_errors),
            "time_window_minutes": self.time_window.total_seconds() / 60,
            "current_alert": self.current_alert,
            "is_likely_blocked": self.is_likely_blocked(),
            "last_reset": self.last_reset_time,
            "error_breakdown": self._get_error_breakdown(recent_errors)
        }
    
    def _get_error_breakdown(self, errors: List[ErrorEvent]) -> dict:
        """Get breakdown of error types."""
        breakdown = {}
        for error in errors:
            status_code = error.status_code
            breakdown[status_code] = breakdown.get(status_code, 0) + 1
        return breakdown
    
    def is_likely_blocked(self) -> bool:
        """Check if we're likely being blocked by YouTube."""
        return (self.current_alert is not None and 
                self.current_alert.severity == "critical")
    
    def should_pause_requests(self) -> bool:
        """Determine if requests should be paused due to blocking."""
        if not self.current_alert:
            return False
            
        # Always pause for rate limiting and IP blocks
        if self.current_alert.block_type in [BlockType.RATE_LIMIT, BlockType.IP_BLOCK]:
            return True
            
        # Pause for critical severity
        return self.current_alert.severity == "critical"
    
    def get_recommended_wait_time(self) -> int:
        """Get recommended wait time in seconds before retrying."""
        if not self.current_alert:
            return 0
            
        if self.current_alert.block_type == BlockType.RATE_LIMIT:
            return 600  # 10 minutes
        elif self.current_alert.block_type == BlockType.IP_BLOCK:
            return 3600  # 1 hour (recommend IP change instead)
        elif self.current_alert.severity == "critical":
            return 300   # 5 minutes
        else:
            return 60    # 1 minute
    
    def reset(self):
        """Reset the detector state."""
        self.error_events.clear()
        self.current_alert = None
        self.last_reset_time = datetime.now()
        logger.info("YouTubeBlockingDetector reset")
    
    def force_clear_alert(self):
        """Manually clear current alert (user acknowledges the issue)."""
        if self.current_alert:
            logger.info(f"Manually clearing alert: {self.current_alert.block_type.value}")
            self.current_alert = None
            self.processing_halted = False
    
    def should_halt_processing(self) -> bool:
        """Check if processing should be immediately halted due to blocking."""
        if not self.current_alert:
            return False
        
        # Always halt for critical IP blocks and rate limiting
        if self.current_alert.block_type in [BlockType.IP_BLOCK, BlockType.CLOUD_IP_BLOCK]:
            return True
        
        if self.current_alert.block_type == BlockType.RATE_LIMIT and self.current_alert.severity == "critical":
            return True
        
        # Halt for any critical severity blocking
        return self.current_alert.severity == "critical"
    
    def get_halt_reason(self) -> str:
        """Get the reason why processing should be halted."""
        if not self.current_alert:
            return ""
        
        if self.current_alert.block_type == BlockType.IP_BLOCK:
            return "YouTube has blocked your IP address. Processing halted to prevent further blocking."
        elif self.current_alert.block_type == BlockType.CLOUD_IP_BLOCK:
            return "YouTube is blocking cloud provider IPs. Processing halted."
        elif self.current_alert.block_type == BlockType.RATE_LIMIT:
            return "YouTube rate limiting detected. Processing halted to respect limits."
        else:
            return f"YouTube blocking detected ({self.current_alert.block_type.value}). Processing halted."
    
    def is_blocking_cleared(self) -> bool:
        """Check if blocking has been cleared and processing can resume."""
        # If no current alert, blocking is cleared
        if not self.current_alert:
            return True
        
        # Check if alert severity has been reduced
        if self.current_alert.severity != "critical":
            return True
        
        # For IP blocks, require manual clearance
        if self.current_alert.block_type in [BlockType.IP_BLOCK, BlockType.CLOUD_IP_BLOCK]:
            return False
        
        # For rate limits, check if enough time has passed
        if self.current_alert.block_type == BlockType.RATE_LIMIT:
            time_since_last_error = datetime.now() - self.current_alert.last_error
            return time_since_last_error > timedelta(minutes=10)
        
        return False
    
    def get_user_action_options(self) -> List[str]:
        """Get available user action options based on current blocking type."""
        if not self.current_alert:
            return ["resume"]
        
        options = []
        
        if self.current_alert.block_type == BlockType.IP_BLOCK:
            options.extend(["change_ip", "wait_24h", "stop_processing"])
        elif self.current_alert.block_type == BlockType.CLOUD_IP_BLOCK:
            options.extend(["change_to_residential_ip", "stop_processing"])
        elif self.current_alert.block_type == BlockType.RATE_LIMIT:
            options.extend(["wait_and_retry", "stop_processing"])
        else:
            options.extend(["wait_and_retry", "stop_processing"])
        
        return options
    
    def halt_processing(self):
        """Mark processing as halted due to blocking."""
        self.processing_halted = True
        logger.critical("Processing halted due to YouTube blocking")
    
    def resume_processing(self):
        """Resume processing after blocking is resolved."""
        if self.is_blocking_cleared():
            self.processing_halted = False
            logger.info("Processing resumed - blocking cleared")
            return True
        else:
            logger.warning("Cannot resume processing - blocking still active")
            return False
