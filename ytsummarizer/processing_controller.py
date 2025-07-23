"""
Processing Controller for YouTube Blocking Management

This module provides centralized control for halting and resuming processing
based on YouTube blocking status.
"""

import logging
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass

from .youtube_blocking_detector import YouTubeBlockingDetector, BlockingAlert, BlockType
from .state_manager import StateManager
from .logging_config import log_blocking_event, log_performance_metric

logger = logging.getLogger("ytsummarizer.processing_controller")


class BlockingStatus(Enum):
    """Current blocking status of the system."""
    CLEAR = "clear"
    WARNING = "warning"
    CRITICAL_RATE_LIMIT = "critical_rate_limit"
    CRITICAL_IP_BLOCK = "critical_ip_block"
    HALTED = "halted"


@dataclass
class ProcessingHaltReason:
    """Information about why processing was halted."""
    reason_type: BlockingStatus
    message: str
    recommended_action: str
    estimated_wait_time: Optional[int]
    can_resume: bool


class ProcessingController:
    """
    Central controller for managing processing state based on YouTube blocking.
    
    Coordinates between blocking detection, batch processing, and user interface
    to provide seamless halt/resume functionality.
    """
    
    def __init__(self, blocking_detector: YouTubeBlockingDetector, 
                 state_manager: Optional[StateManager] = None):
        """
        Initialize the processing controller.
        
        Args:
            blocking_detector: YouTube blocking detector instance
            state_manager: State manager for saving progress during halts
        """
        self.blocking_detector = blocking_detector
        self.state_manager = state_manager
        self.halt_callbacks: list[Callable] = []
        self.resume_callbacks: list[Callable] = []
        self.current_halt_reason: Optional[ProcessingHaltReason] = None
        
        logger.info("ProcessingController initialized")
    
    def register_halt_callback(self, callback: Callable):
        """Register a callback to be called when processing is halted."""
        self.halt_callbacks.append(callback)
    
    def register_resume_callback(self, callback: Callable):
        """Register a callback to be called when processing is resumed."""
        self.resume_callbacks.append(callback)
    
    def check_blocking_status(self) -> BlockingStatus:
        """Check current blocking status and return appropriate enum."""
        if self.blocking_detector.processing_halted:
            return BlockingStatus.HALTED
        
        if not self.blocking_detector.current_alert:
            return BlockingStatus.CLEAR
        
        alert = self.blocking_detector.current_alert
        
        if alert.severity == "critical":
            if alert.block_type in [BlockType.IP_BLOCK, BlockType.CLOUD_IP_BLOCK]:
                return BlockingStatus.CRITICAL_IP_BLOCK
            elif alert.block_type == BlockType.RATE_LIMIT:
                return BlockingStatus.CRITICAL_RATE_LIMIT
            else:
                return BlockingStatus.HALTED
        
        return BlockingStatus.WARNING
    
    def should_halt_processing(self) -> bool:
        """Check if processing should be halted based on current blocking status."""
        return self.blocking_detector.should_halt_processing()
    
    def halt_processing(self, source_url: Optional[str] = None, 
                       current_progress: Optional[dict] = None) -> ProcessingHaltReason:
        """
        Halt processing due to blocking and save state.
        
        Args:
            source_url: URL being processed (for state saving)
            current_progress: Current processing progress to save
            
        Returns:
            ProcessingHaltReason with details about the halt
        """
        if not self.blocking_detector.current_alert:
            logger.warning("halt_processing called but no blocking alert active")
            return None
        
        alert = self.blocking_detector.current_alert
        
        # Create halt reason
        halt_reason = self._create_halt_reason(alert)
        self.current_halt_reason = halt_reason
        
        # Save state if possible
        if source_url and current_progress and self.state_manager:
            try:
                self.state_manager.save_state(source_url, current_progress)
                logger.info(f"State saved during halt for {source_url}")
            except Exception as e:
                logger.error(f"Failed to save state during halt: {e}")
        
        # Mark as halted in blocking detector
        self.blocking_detector.halt_processing()
        
        # Call halt callbacks
        for callback in self.halt_callbacks:
            try:
                callback(halt_reason)
            except Exception as e:
                logger.error(f"Error in halt callback: {e}")
        
        logger.critical(f"Processing halted: {halt_reason.message}")
        
        # Log to specialized blocking events log
        log_blocking_event(
            event_type="PROCESSING_CONTROLLER_HALT",
            message=halt_reason.message,
            reason_type=halt_reason.reason_type.value,
            recommended_action=halt_reason.recommended_action,
            can_resume=halt_reason.can_resume,
            source_url=source_url
        )
        return halt_reason
    
    def can_resume_processing(self) -> bool:
        """Check if processing can be resumed."""
        return self.blocking_detector.is_blocking_cleared()
    
    def resume_processing(self) -> bool:
        """
        Resume processing if blocking is cleared.
        
        Returns:
            True if processing was resumed, False if still blocked
        """
        if not self.can_resume_processing():
            logger.warning("Cannot resume processing - blocking still active")
            return False
        
        # Resume in blocking detector
        if not self.blocking_detector.resume_processing():
            return False
        
        # Clear halt reason
        self.current_halt_reason = None
        
        # Call resume callbacks
        for callback in self.resume_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in resume callback: {e}")
        
        logger.info("Processing resumed successfully")
        return True
    
    def get_halt_reason(self) -> Optional[ProcessingHaltReason]:
        """Get the current halt reason if processing is halted."""
        return self.current_halt_reason
    
    def get_user_action_options(self) -> list[str]:
        """Get available user action options for current blocking situation."""
        return self.blocking_detector.get_user_action_options()
    
    def handle_user_action(self, action: str) -> bool:
        """
        Handle user action in response to blocking.
        
        Args:
            action: User selected action
            
        Returns:
            True if action was handled successfully
        """
        logger.info(f"Handling user action: {action}")
        
        if action == "resume":
            return self.resume_processing()
        elif action == "stop_processing":
            logger.info("User chose to stop processing")
            return True
        elif action == "wait_and_retry":
            # For now, just try to resume - in future could implement wait timer
            return self.resume_processing()
        elif action in ["change_ip", "change_to_residential_ip"]:
            # Clear the alert to allow user to try with new IP
            self.blocking_detector.force_clear_alert()
            logger.info("IP change action - blocking alert cleared")
            return True
        elif action == "wait_24h":
            logger.info("User chose to wait 24 hours - processing remains halted")
            return True
        else:
            logger.warning(f"Unknown user action: {action}")
            return False
    
    def _create_halt_reason(self, alert: BlockingAlert) -> ProcessingHaltReason:
        """Create a ProcessingHaltReason from a BlockingAlert."""
        if alert.block_type == BlockType.IP_BLOCK:
            return ProcessingHaltReason(
                reason_type=BlockingStatus.CRITICAL_IP_BLOCK,
                message="YouTube has blocked your IP address",
                recommended_action="Change your IP address (restart router, use VPN, or wait 1-24 hours)",
                estimated_wait_time=3600,  # 1 hour minimum
                can_resume=False  # Requires manual action
            )
        elif alert.block_type == BlockType.CLOUD_IP_BLOCK:
            return ProcessingHaltReason(
                reason_type=BlockingStatus.CRITICAL_IP_BLOCK,
                message="YouTube is blocking cloud provider IP addresses",
                recommended_action="Switch to a residential IP address (not from AWS, Google Cloud, Azure, etc.)",
                estimated_wait_time=None,  # Requires IP change
                can_resume=False
            )
        elif alert.block_type == BlockType.RATE_LIMIT:
            return ProcessingHaltReason(
                reason_type=BlockingStatus.CRITICAL_RATE_LIMIT,
                message="YouTube rate limiting is active",
                recommended_action="Wait 10-30 minutes before retrying",
                estimated_wait_time=600,  # 10 minutes
                can_resume=True
            )
        else:
            return ProcessingHaltReason(
                reason_type=BlockingStatus.HALTED,
                message=f"YouTube blocking detected: {alert.block_type.value}",
                recommended_action=alert.recommendation,
                estimated_wait_time=300,  # 5 minutes default
                can_resume=True
            )
    
    def get_status_summary(self) -> dict:
        """Get a summary of current processing controller status."""
        return {
            "blocking_status": self.check_blocking_status().value,
            "processing_halted": self.blocking_detector.processing_halted,
            "can_resume": self.can_resume_processing(),
            "halt_reason": self.current_halt_reason,
            "user_actions": self.get_user_action_options(),
            "blocking_detector_status": self.blocking_detector.get_status()
        }