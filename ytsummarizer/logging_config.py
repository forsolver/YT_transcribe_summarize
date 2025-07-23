"""
Centralized logging configuration for YouTube Summarizer application.

This module provides a unified logging setup that saves all logs to the 'logs' folder
with proper file rotation, formatting, and organization.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path


class LoggingConfig:
    """Centralized logging configuration manager."""
    
    def __init__(self, logs_dir: str = "logs"):
        """
        Initialize logging configuration.
        
        Args:
            logs_dir: Directory to store log files (relative to project root)
        """
        self.logs_dir = Path(logs_dir)
        self.setup_complete = False
        
        # Create logs directory if it doesn't exist
        self.logs_dir.mkdir(exist_ok=True)
        
        # Define log file paths
        self.main_log_file = self.logs_dir / "ytsummarizer.log"
        self.error_log_file = self.logs_dir / "errors.log"
        self.blocking_log_file = self.logs_dir / "blocking_events.log"
        self.performance_log_file = self.logs_dir / "performance.log"
        self.warp_log_file = self.logs_dir / "warp_logs.txt"  # Special log file for terminal output
    
    def setup_logging(self, log_level: str = "DEBUG"):
        """
        Set up comprehensive logging configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if self.setup_complete:
            return
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set root logger level
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 1. Console handler (for immediate feedback)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
        
        # 2. Main log file handler (rotating, all messages)
        main_file_handler = logging.handlers.RotatingFileHandler(
            self.main_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_file_handler.setLevel(logging.DEBUG)
        main_file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(main_file_handler)
        
        # 3. Error log file handler (errors and critical only)
        error_file_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_file_handler)
        
        # 4. Session-specific log file (current run only)
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_log_file = self.logs_dir / f"session_{session_timestamp}.log"
        session_file_handler = logging.FileHandler(
            session_log_file,
            encoding='utf-8'
        )
        session_file_handler.setLevel(logging.DEBUG)
        session_file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(session_file_handler)
        
        # 5. Special warp_logs.txt file for terminal output (always appends)
        warp_file_handler = logging.FileHandler(
            self.warp_log_file,
            encoding='utf-8',
            mode='a'  # Append mode to preserve previous logs
        )
        warp_file_handler.setLevel(logging.DEBUG)
        warp_file_handler.setFormatter(simple_formatter)
        root_logger.addHandler(warp_file_handler)
        
        # Set up specialized loggers
        self._setup_specialized_loggers()
        
        # Log the setup completion
        logging.info(f"Logging system initialized - logs saved to: {self.logs_dir.absolute()}")
        logging.info(f"Session log: {session_log_file}")
        logging.info(f"Main log: {self.main_log_file}")
        logging.info(f"Error log: {self.error_log_file}")
        
        self.setup_complete = True
    
    def _setup_specialized_loggers(self):
        """Set up specialized loggers for specific components."""
        
        # 1. Blocking events logger
        blocking_logger = logging.getLogger("ytsummarizer.blocking")
        blocking_handler = logging.handlers.RotatingFileHandler(
            self.blocking_log_file,
            maxBytes=2*1024*1024,  # 2MB
            backupCount=2,
            encoding='utf-8'
        )
        blocking_handler.setLevel(logging.INFO)
        blocking_formatter = logging.Formatter(
            '%(asctime)s - BLOCKING - %(levelname)s - %(message)s'
        )
        blocking_handler.setFormatter(blocking_formatter)
        blocking_logger.addHandler(blocking_handler)
        blocking_logger.setLevel(logging.INFO)
        
        # 2. Performance logger
        performance_logger = logging.getLogger("ytsummarizer.performance")
        performance_handler = logging.handlers.RotatingFileHandler(
            self.performance_log_file,
            maxBytes=2*1024*1024,  # 2MB
            backupCount=2,
            encoding='utf-8'
        )
        performance_handler.setLevel(logging.INFO)
        performance_formatter = logging.Formatter(
            '%(asctime)s - PERF - %(message)s'
        )
        performance_handler.setFormatter(performance_formatter)
        performance_logger.addHandler(performance_handler)
        performance_logger.setLevel(logging.INFO)
        
        # 3. Reduce noise from external libraries
        self._configure_external_loggers()
    
    def _configure_external_loggers(self):
        """Configure logging levels for external libraries to reduce noise."""
        external_loggers = [
            'urllib3.connectionpool',
            'requests.packages.urllib3',
            'yt_dlp',
            'youtube_transcript_api'
        ]
        
        for logger_name in external_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)
    
    def get_blocking_logger(self):
        """Get the specialized blocking events logger."""
        return logging.getLogger("ytsummarizer.blocking")
    
    def get_performance_logger(self):
        """Get the specialized performance logger."""
        return logging.getLogger("ytsummarizer.performance")
    
    def log_session_start(self):
        """Log session start information."""
        logger = logging.getLogger("ytsummarizer.session")
        logger.info("=" * 80)
        logger.info("NEW SESSION STARTED")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"Logs directory: {self.logs_dir.absolute()}")
        logger.info("=" * 80)
    
    def log_session_end(self):
        """Log session end information."""
        logger = logging.getLogger("ytsummarizer.session")
        logger.info("=" * 80)
        logger.info("SESSION ENDED")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 80)
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Clean up old log files.
        
        Args:
            days_to_keep: Number of days to keep log files
        """
        import time
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        for log_file in self.logs_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    logging.info(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    logging.warning(f"Failed to clean up log file {log_file}: {e}")


# Global logging configuration instance
_logging_config = None


def get_logging_config() -> LoggingConfig:
    """Get the global logging configuration instance."""
    global _logging_config
    if _logging_config is None:
        _logging_config = LoggingConfig()
    return _logging_config


def setup_application_logging(log_level: str = "DEBUG"):
    """
    Set up application-wide logging.
    
    Args:
        log_level: Logging level for the application
    """
    config = get_logging_config()
    config.setup_logging(log_level)
    config.log_session_start()
    
    # Clean up old logs on startup
    try:
        config.cleanup_old_logs()
    except Exception as e:
        logging.warning(f"Failed to clean up old logs: {e}")


def log_blocking_event(event_type: str, message: str, **kwargs):
    """
    Log a blocking event to the specialized blocking log.
    
    Args:
        event_type: Type of blocking event (IP_BLOCK, RATE_LIMIT, etc.)
        message: Event message
        **kwargs: Additional event data
    """
    blocking_logger = get_logging_config().get_blocking_logger()
    
    event_data = {
        'type': event_type,
        'message': message,
        **kwargs
    }
    
    blocking_logger.info(f"{event_type}: {message} | Data: {event_data}")


def log_performance_metric(metric_name: str, value: float, unit: str = "", **kwargs):
    """
    Log a performance metric.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        **kwargs: Additional metric data
    """
    performance_logger = get_logging_config().get_performance_logger()
    
    metric_data = {
        'metric': metric_name,
        'value': value,
        'unit': unit,
        **kwargs
    }
    
    performance_logger.info(f"{metric_name}: {value}{unit} | {metric_data}")


def shutdown_logging():
    """Shutdown logging system gracefully."""
    config = get_logging_config()
    config.log_session_end()
    
    # Shutdown all handlers
    logging.shutdown()