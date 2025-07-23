"""
Batch Processing Module for YouTube Tools

This module provides functionality for processing multiple YouTube videos
from channels and playlists in batch operations.
"""

import os
import time
import logging
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Event

# Настройка логирования
logger = logging.getLogger("ytsummarizer.batch_processor")

from .transcripts import (
    get_source_metadata, extract_video_list, get_transcript, 
    SourceInfo, VideoInfo
)
from .video_processor import extract_trick_segments, extract_video_segments
from .url_detector import URLDetector, URLType
from .state_manager import StateManager
from .settings_manager import SettingsManager
from .processing_controller import ProcessingController, BlockingStatus


@dataclass
class BatchOptions:
    """Configuration options for batch processing."""
    max_videos: int = 50
    skip_existing: bool = False
    min_video_duration: Optional[int] = None  # seconds
    max_video_duration: Optional[int] = None  # seconds
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    output_dir: str = "tricks"
    auto_resume: bool = True  # Автоматически возобновлять обработку без запроса


@dataclass
class ProcessingError:
    """Information about a processing error."""
    video_id: str
    video_title: str
    error_type: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class VideoProcessingResult:
    """Result of processing a single video."""
    video_info: VideoInfo
    tricks_found: int = 0
    segments_extracted: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    success: bool = False
    error: Optional[ProcessingError] = None


@dataclass
class BatchResult:
    """Result of a batch processing operation."""
    source_info: SourceInfo
    total_videos: int = 0
    processed_videos: int = 0
    successful_extractions: int = 0
    total_tricks: int = 0
    total_segments: int = 0
    errors: List[ProcessingError] = field(default_factory=list)
    processing_time: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    cancelled: bool = False
    halt_reason: Optional[Any] = None  # ProcessingHaltReason when halted due to blocking


class BatchProcessor:
    """
    Processes multiple YouTube videos from channels and playlists.
    
    Provides functionality for:
    - Extracting video lists from channels and playlists
    - Processing videos sequentially with progress reporting
    - Handling errors gracefully without stopping the batch
    - Supporting cancellation of long-running operations
    """
    
    def __init__(self, progress_callback: Optional[Callable] = None, 
                 cancel_token: Optional[Event] = None,
                 processing_controller: Optional[ProcessingController] = None):
        """
        Initialize the batch processor.
        
        Args:
            progress_callback: Function to call for progress updates
            cancel_token: Event object to check for cancellation requests
            processing_controller: Controller for handling YouTube blocking
        """
        self.progress_callback = progress_callback
        self.cancel_token = cancel_token
        self.processing_controller = processing_controller
        self.url_detector = URLDetector()
        self.logger = logging.getLogger(__name__)
    
    def process_source(self, source_url: str, options: BatchOptions, resume: bool = False) -> BatchResult:
        """
        Process all videos from a YouTube source (channel or playlist).
        
        Args:
            source_url: URL of the channel or playlist
            options: Processing options and filters
            resume: Whether to resume from previous state (if available)
            
        Returns:
            BatchResult with processing statistics and results
        """
        logger.debug(f"Starting process_source with URL: {source_url}")
        start_time = time.time()
        
        # Get source metadata
        logger.debug(f"Getting source metadata...")
        try:
            source_info = get_source_metadata(source_url)
            if not source_info:
                logger.debug(f"Failed to get source metadata")
                result = BatchResult(
                    source_info=SourceInfo("Unknown", URLType.INVALID, source_url, 0),
                    processing_time=time.time() - start_time
                )
                result.errors.append(ProcessingError(
                    video_id="",
                    video_title="",
                    error_type="SOURCE_ERROR",
                    error_message=f"Could not get information about source: {source_url}"
                ))
                return result
            else:
                logger.debug(f"Got source metadata: {source_info.name}, {source_info.total_videos} videos")
        except Exception as e:
            logger.exception(f"Exception getting source metadata: {e}")
            import traceback
            traceback.print_exc()
            result = BatchResult(
                source_info=SourceInfo("Unknown", URLType.INVALID, source_url, 0),
                processing_time=time.time() - start_time
            )
            result.errors.append(ProcessingError(
                video_id="",
                video_title="",
                error_type="SOURCE_ERROR",
                error_message=f"Exception getting source info: {str(e)}"
            ))
            return result
        
        # Extract video list
        logger.debug(f"Extracting video list (limit: {options.max_videos})...")
        try:
            videos = extract_video_list(source_url, limit=options.max_videos)
            if not videos:
                logger.warning(f"No videos found in source: {source_url}")
                result = BatchResult(
                    source_info=source_info,
                    processing_time=time.time() - start_time
                )
                
                # Provide more detailed error message
                error_msg = (
                    f"Не найдено доступных видео в источнике. "
                    f"Возможные причины:\n"
                    f"• Плейлист пустой или приватный\n"
                    f"• Все видео имеют возрастные ограничения\n"
                    f"• Видео требуют авторизации\n"
                    f"• Проблемы с доступом к YouTube API"
                )
                
                result.errors.append(ProcessingError(
                    video_id="",
                    video_title="",
                    error_type="VIDEO_LIST_ERROR",
                    error_message=error_msg
                ))
                
                # Удаляем сохраненное состояние, если оно есть
                StateManager.delete_state(source_url)
                
                return result
            else:
                logger.debug(f"Extracted {len(videos)} videos from source")
                for i, video in enumerate(videos[:3]):  # Show first 3 videos
                    logger.debug(f"  {i+1}. {video.title} ({video.video_id})")
                if len(videos) > 3:
                    logger.debug(f"  ... and {len(videos) - 3} more videos")
        except Exception as e:
            logger.exception(f"Exception extracting video list: {e}")
            import traceback
            traceback.print_exc()
            result = BatchResult(
                source_info=source_info,
                processing_time=time.time() - start_time
            )
            result.errors.append(ProcessingError(
                video_id="",
                video_title="",
                error_type="VIDEO_LIST_ERROR",
                error_message=f"Exception extracting video list: {str(e)}"
            ))
            return result
        
        # Apply filters
        logger.debug(f"Applying filters...")
        filtered_videos = self._apply_filters(videos, options)
        logger.debug(f"After filtering: {len(filtered_videos)} videos remain")
        
        # Check for saved state and resume if requested
        saved_state = None
        start_index = 0
        processed_video_ids = []
        
        if resume:
            saved_state = self._load_progress(source_url)
            if saved_state:
                logger.debug(f"Found saved state for {source_url}")
                
                # Check for changes in the source
                source_changed, change_message = self._check_source_changes(
                    source_url, filtered_videos, saved_state
                )
                
                if source_changed:
                    logger.warning(f"Source content changed: {change_message}")
                    # Continue with resume but log the changes
                
                # Get processed videos and start index
                processed_video_ids = saved_state.get("processed_video_ids", [])
                start_index = saved_state.get("last_processed_index", -1) + 1
                
                if start_index >= len(filtered_videos):
                    logger.debug(f"All videos already processed, starting from beginning")
                    start_index = 0
                    processed_video_ids = []
                else:
                    logger.debug(f"Resuming from video {start_index+1}/{len(filtered_videos)}")
        
        # Process videos
        logger.debug(f"Starting video processing from index {start_index}...")
        try:
            result = self.process_video_list(
                filtered_videos, 
                source_info, 
                options,
                start_index=start_index,
                processed_video_ids=processed_video_ids,
                source_url=source_url
            )
            result.processing_time = time.time() - start_time
            result.end_time = datetime.now()
            
            # If processing completed successfully, delete the state
            if not result.cancelled and result.processed_videos == len(filtered_videos):
                StateManager.delete_state(source_url)
                logger.debug(f"Processing completed, state deleted")
            
            logger.debug(f"process_source completed successfully")
            return result
        except Exception as e:
            logger.exception(f"Exception in process_video_list: {e}")
            import traceback
            traceback.print_exc()
            result = BatchResult(
                source_info=source_info,
                processing_time=time.time() - start_time
            )
            result.errors.append(ProcessingError(
                video_id="",
                video_title="",
                error_type="PROCESSING_ERROR",
                error_message=f"Exception in video processing: {str(e)}"
            ))
            return result
    
    def process_video_list(self, videos: List[VideoInfo], source_info: SourceInfo, 
                          options: BatchOptions, start_index: int = 0,
                          processed_video_ids: List[str] = None,
                          source_url: str = None) -> BatchResult:
        """
        Process a list of videos for trick extraction.
        
        Args:
            videos: List of VideoInfo objects to process
            source_info: Information about the source
            options: Processing options
            start_index: Index to start processing from (for resuming)
            processed_video_ids: List of already processed video IDs
            source_url: URL of the source (for saving state)
            
        Returns:
            BatchResult with processing statistics
        """
        if processed_video_ids is None:
            processed_video_ids = []
        result = BatchResult(
            source_info=source_info,
            total_videos=len(videos),
            processed_videos=len(processed_video_ids)  # Initialize with already processed count
        )
        
        logger.debug(f"Starting batch processing of {len(videos)} videos from {source_info.name}")
        if start_index > 0:
            self._report_progress(start_index, len(videos), f"Resuming from video {start_index+1}...")
        else:
            self._report_progress(0, len(videos), "Starting batch processing...")
        
        for i, video in enumerate(videos[start_index:], start=start_index):
            logger.debug(f"Processing video {i+1}/{len(videos)}: {video.title}")
            
            # Skip already processed videos
            if video.video_id in processed_video_ids:
                logger.debug(f"Skipping already processed video: {video.title}")
                continue
            
            # Check for cancellation
            if self.cancel_token and self.cancel_token.is_set():
                logger.debug(f"Batch processing cancelled at video {i+1}")
                result.cancelled = True
                self._report_progress(i, len(videos), "Processing cancelled")
                
                # Save progress for resuming later
                if source_url:
                    self._save_progress(source_url, source_info, videos, processed_video_ids, i, len(videos))
                
                break
            
            # Check for YouTube blocking
            if self.processing_controller and self.processing_controller.should_halt_processing():
                logger.critical(f"YouTube blocking detected - halting batch processing at video {i+1}")
                
                # Save progress before halting
                current_progress = {
                    "source_info": source_info.__dict__,
                    "videos": [v.__dict__ for v in videos],
                    "processed_video_ids": list(processed_video_ids),
                    "last_processed_index": i - 1,
                    "total_videos": len(videos),
                    "processed_count": len(processed_video_ids)
                }
                
                halt_reason = self.processing_controller.halt_processing(source_url, current_progress)
                result.cancelled = True
                result.halt_reason = halt_reason
                self._report_progress(i, len(videos), f"Processing halted: {halt_reason.message}")
                
                break
            
            # Report progress
            self._report_progress(i, len(videos), f"Processing: {video.title}")
            
            # Process individual video
            try:
                video_result = self._process_single_video(video, source_info, options)
                result.processed_videos += 1
                
                if video_result.success:
                    result.successful_extractions += 1
                    result.total_tricks += video_result.tricks_found
                    result.total_segments += len(video_result.segments_extracted)
                    logger.debug(f"Video {i+1} processed successfully: {video_result.tricks_found} tricks, {len(video_result.segments_extracted)} segments")
                    
                    # Add to processed videos
                    processed_video_ids.append(video.video_id)
                else:
                    if video_result.error:
                        result.errors.append(video_result.error)
                        logger.debug(f"Video {i+1} failed: {video_result.error.error_type} - {video_result.error.error_message}")
                
                # Save progress after each video
                if source_url:
                    self._save_progress(source_url, source_info, videos, processed_video_ids, i, len(videos))
                
            except Exception as e:
                logger.exception(f"Critical error processing video {i+1}: {str(e)}")
                import traceback
                traceback.print_exc()
                error = ProcessingError(
                    video_id=video.video_id,
                    video_title=video.title,
                    error_type="CRITICAL_ERROR",
                    error_message=f"Critical error in batch processing: {str(e)}"
                )
                result.errors.append(error)
                result.processed_videos += 1
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.5)
            logger.debug(f"Completed video {i+1}/{len(videos)}, continuing to next...")
        
        # Final progress report
        if not result.cancelled:
            logger.debug(f"Batch processing completed successfully")
            self._report_progress(len(videos), len(videos), "Batch processing complete")
            
            # Delete state file on successful completion
            if source_url:
                StateManager.delete_state(source_url)
                logger.debug(f"State file deleted after successful completion")
        
        logger.debug(f"Final stats: {result.processed_videos} processed, {result.successful_extractions} successful, {len(result.errors)} errors")
        
        return result
    
    def create_folder_structure(self, source_info: SourceInfo, video_info: VideoInfo, 
                              base_dir: str = "tricks") -> str:
        """
        Create nested folder structure for batch processing.
        
        Args:
            source_info: Information about the source
            video_info: Information about the video
            base_dir: Base directory for output
            
        Returns:
            Path to the created folder structure
        """
        # Create base directory
        os.makedirs(base_dir, exist_ok=True)
        
        # Create source folder
        source_folder = os.path.join(base_dir, source_info.name)
        os.makedirs(source_folder, exist_ok=True)
        
        # Create video folder
        video_folder_name = self._sanitize_folder_name(video_info.title)
        video_folder = os.path.join(source_folder, video_folder_name)
        os.makedirs(video_folder, exist_ok=True)
        
        return video_folder
    
    def _process_single_video(self, video_info: VideoInfo, source_info: SourceInfo, 
                             options: BatchOptions) -> VideoProcessingResult:
        """
        Process a single video for trick extraction.
        
        Args:
            video_info: Information about the video to process
            source_info: Information about the source
            options: Processing options
            
        Returns:
            VideoProcessingResult with processing details
        """
        start_time = time.time()
        result = VideoProcessingResult(video_info=video_info)
        
        logger.debug(f"Starting processing video: {video_info.title} (ID: {video_info.video_id})")
        
        try:
            # Check if we should skip existing
            if options.skip_existing:
                video_folder = self.create_folder_structure(source_info, video_info, options.output_dir)
                if os.path.exists(video_folder) and os.listdir(video_folder):
                    logger.debug(f"Skipping existing video: {video_info.title}")
                    result.success = True
                    result.processing_time = time.time() - start_time
                    return result
            
            logger.debug(f"Getting transcript for video: {video_info.video_id}")
            # Get transcript using settings-based language priority
            try:
                settings = SettingsManager.load_settings()
                lang_priority = tuple(settings.get("language_priority", ["en", "ru"]))
                
                plain_text, fragments, video_info_detailed = get_transcript(
                    video_info.video_id, 
                    lang_priority=lang_priority
                )
                logger.debug(f"Successfully got transcript with {len(fragments)} fragments")
            except Exception as e:
                logger.error(f"Failed to get transcript: {str(e)}")
                result.error = ProcessingError(
                    video_id=video_info.video_id,
                    video_title=video_info.title,
                    error_type="TRANSCRIPT_ERROR",
                    error_message=f"Failed to get transcript: {str(e)}"
                )
                result.processing_time = time.time() - start_time
                return result
            
            logger.debug(f"Extracting trick segments...")
            # Extract trick segments
            try:
                # Получаем настройки обнаружения трюков из settings.json
                settings = SettingsManager.load_settings()
                trick_settings = settings.get("trick_detection", {})
                
                # Используем настройки из settings.json или значения по умолчанию
                min_silence_duration = trick_settings.get("min_silence_duration", 5.0)
                max_words_in_segment = trick_settings.get("max_words_in_segment", 5)
                
                logger.debug(f"Using trick detection settings: min_silence={min_silence_duration}s, max_words={max_words_in_segment}")
                
                trick_segments = extract_trick_segments(
                    fragments, 
                    min_silence_duration=min_silence_duration,
                    max_words_in_segment=max_words_in_segment
                )
                result.tricks_found = len(trick_segments)
                logger.debug(f"Found {len(trick_segments)} trick segments")
                
                if trick_segments:
                    # Create folder structure
                    video_folder = self.create_folder_structure(source_info, video_info, options.output_dir)
                    logger.debug(f"Created folder: {video_folder}")
                    
                    # Extract video segments
                    logger.debug(f"Starting video segment extraction...")
                    logger.debug(f"Calling extract_video_segments with {len(trick_segments)} segments")
                    
                    extracted_files = extract_video_segments(
                        video_info.video_id, 
                        trick_segments, 
                        output_dir=video_folder,
                        video_info=video_info_detailed
                    )
                    
                    logger.debug(f"extract_video_segments returned successfully")
                    result.segments_extracted = extracted_files
                    logger.debug(f"Successfully extracted {len(extracted_files)} video segments")
                else:
                    logger.debug(f"No trick segments found for video: {video_info.title}")
                
                result.success = True
                logger.debug(f"Successfully completed processing video: {video_info.title}")
                
            except Exception as e:
                logger.exception(f"Error during trick extraction: {str(e)}")
                import traceback
                traceback.print_exc()
                result.error = ProcessingError(
                    video_id=video_info.video_id,
                    video_title=video_info.title,
                    error_type="EXTRACTION_ERROR",
                    error_message=f"Failed to extract tricks: {str(e)}"
                )
        
        except Exception as e:
            logger.exception(f"Unexpected error processing video {video_info.title}: {str(e)}")
            import traceback
            traceback.print_exc()
            result.error = ProcessingError(
                video_id=video_info.video_id,
                video_title=video_info.title,
                error_type="UNKNOWN_ERROR",
                error_message=f"Unexpected error: {str(e)}"
            )
        
        result.processing_time = time.time() - start_time
        logger.debug(f"Finished processing video: {video_info.title} (Success: {result.success}, Time: {result.processing_time:.1f}s)")
        return result
    
    def _apply_filters(self, videos: List[VideoInfo], options: BatchOptions) -> List[VideoInfo]:
        """
        Apply filtering options to the video list.
        
        Args:
            videos: List of videos to filter
            options: Filtering options
            
        Returns:
            Filtered list of videos
        """
        filtered = videos
        
        # Filter by duration
        if options.min_video_duration or options.max_video_duration:
            filtered = [
                v for v in filtered 
                if v.duration and (
                    (not options.min_video_duration or v.duration >= options.min_video_duration) and
                    (not options.max_video_duration or v.duration <= options.max_video_duration)
                )
            ]
        
        # Filter by date
        if options.date_from or options.date_to:
            filtered = [
                v for v in filtered
                if v.upload_date and (
                    (not options.date_from or v.upload_date >= options.date_from) and
                    (not options.date_to or v.upload_date <= options.date_to)
                )
            ]
        
        return filtered
    
    def _report_progress(self, current: int, total: int, message: str):
        """
        Report progress to the callback function.
        
        Args:
            current: Current progress value
            total: Total progress value
            message: Progress message
        """
        if self.progress_callback:
            try:
                self.progress_callback(current, total, message)
            except Exception as e:
                self.logger.warning(f"Progress callback error: {e}")
    
    def _sanitize_folder_name(self, name: str, max_length: int = 50) -> str:
        """
        Sanitize a string to be safe for use as a folder name.
        
        Args:
            name: The original name
            max_length: Maximum length of the sanitized name
            
        Returns:
            Sanitized folder name
        """
        if not name:
            return "Unknown_Video"
        
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Replace multiple spaces with single spaces
        name = ' '.join(name.split())
        
        # Truncate if too long
        if len(name) > max_length:
            name = name[:max_length].rstrip()
        
        # Ensure it's not empty after sanitization
        if not name.strip():
            return "Unknown_Video"
        
        return name.strip()
    
    def _load_progress(self, source_url: str) -> Optional[dict]:
        """
        Загружает прогресс обработки для источника
        
        Args:
            source_url: URL источника
            
        Returns:
            Словарь с информацией о прогрессе или None
        """
        try:
            state = StateManager.load_state(source_url)
            if not StateManager.is_state_valid(state):
                logger.debug(f"Saved state for {source_url} is invalid or expired")
                return None
            
            return state
        except Exception as e:
            logger.error(f"Error loading progress: {e}")
            return None
    
    def _save_progress(self, source_url: str, source_info: SourceInfo, 
                      videos: List[VideoInfo], processed_video_ids: List[str],
                      current_index: int, total_videos: int) -> None:
        """
        Сохраняет прогресс обработки
        
        Args:
            source_url: URL источника
            source_info: Информация об источнике
            videos: Список видео
            processed_video_ids: Список обработанных video_id
            current_index: Текущий индекс обработки
            total_videos: Общее количество видео
        """
        try:
            # Создаем информацию о последнем обработанном видео
            last_video = None
            if 0 <= current_index < len(videos):
                video = videos[current_index]
                last_video = {
                    "video_id": video.video_id,
                    "title": video.title,
                    "url": video.url
                }
            
            # Создаем состояние
            state = {
                "source_type": source_info.type.name,
                "source_name": source_info.name,
                "total_videos": total_videos,
                "processed_videos": len(processed_video_ids),
                "last_processed_index": current_index,
                "last_processed_video": last_video,
                "processed_video_ids": processed_video_ids
            }
            
            # Сохраняем состояние
            StateManager.save_state(source_url, state)
            logger.debug(f"Progress saved: {len(processed_video_ids)}/{total_videos} videos processed")
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
    
    def _check_source_changes(self, source_url: str, current_videos: List[VideoInfo], 
                             saved_state: dict) -> tuple[bool, str]:
        """
        Проверяет изменения в составе источника
        
        Args:
            source_url: URL источника
            current_videos: Текущий список видео
            saved_state: Сохраненное состояние
            
        Returns:
            (изменился_ли_источник, сообщение_об_изменениях)
        """
        try:
            # Получаем список video_id из текущего списка
            current_video_ids = [v.video_id for v in current_videos]
            
            # Получаем список video_id из сохраненного состояния
            saved_total = saved_state.get("total_videos", 0)
            
            # Если количество видео сильно изменилось, считаем что источник изменился
            if abs(len(current_videos) - saved_total) > 5:
                return True, f"Количество видео изменилось: было {saved_total}, стало {len(current_videos)}"
            
            # Проверяем наличие обработанных видео в текущем списке
            processed_ids = saved_state.get("processed_video_ids", [])
            missing_videos = [vid for vid in processed_ids if vid not in current_video_ids]
            
            if missing_videos:
                return True, f"Некоторые обработанные видео больше не доступны ({len(missing_videos)} шт.)"
            
            return False, "Источник не изменился"
        except Exception as e:
            logger.error(f"Error checking source changes: {e}")
            return False, f"Ошибка при проверке изменений: {e}"


# Convenience functions for easy usage
def process_source_batch(source_url: str, options: Optional[BatchOptions] = None, 
                        progress_callback: Optional[Callable] = None,
                        cancel_token: Optional[Event] = None) -> BatchResult:
    """
    Convenience function to process a source in batch mode.
    
    Args:
        source_url: URL of the channel or playlist
        options: Processing options (uses defaults if None)
        progress_callback: Function to call for progress updates
        cancel_token: Event object to check for cancellation
        
    Returns:
        BatchResult with processing statistics
    """
    if options is None:
        options = BatchOptions()
    
    processor = BatchProcessor(progress_callback, cancel_token)
    return processor.process_source(source_url, options)
