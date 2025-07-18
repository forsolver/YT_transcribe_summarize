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

from .transcripts import (
    get_source_metadata, extract_video_list, get_transcript, 
    SourceInfo, VideoInfo
)
from .video_processor import extract_trick_segments, extract_video_segments
from .url_detector import URLDetector, URLType


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
                 cancel_token: Optional[Event] = None):
        """
        Initialize the batch processor.
        
        Args:
            progress_callback: Function to call for progress updates
            cancel_token: Event object to check for cancellation requests
        """
        self.progress_callback = progress_callback
        self.cancel_token = cancel_token
        self.url_detector = URLDetector()
        self.logger = logging.getLogger(__name__)
    
    def process_source(self, source_url: str, options: BatchOptions) -> BatchResult:
        """
        Process all videos from a YouTube source (channel or playlist).
        
        Args:
            source_url: URL of the channel or playlist
            options: Processing options and filters
            
        Returns:
            BatchResult with processing statistics and results
        """
        print(f"[DEBUG] Starting process_source with URL: {source_url}")
        start_time = time.time()
        
        # Get source metadata
        print(f"[DEBUG] Getting source metadata...")
        try:
            source_info = get_source_metadata(source_url)
            if not source_info:
                print(f"[DEBUG] Failed to get source metadata")
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
                print(f"[DEBUG] Got source metadata: {source_info.name}, {source_info.total_videos} videos")
        except Exception as e:
            print(f"[DEBUG] Exception getting source metadata: {e}")
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
        print(f"[DEBUG] Extracting video list (limit: {options.max_videos})...")
        try:
            videos = extract_video_list(source_url, limit=options.max_videos)
            if not videos:
                print(f"[DEBUG] No videos found in source")
                result = BatchResult(
                    source_info=source_info,
                    processing_time=time.time() - start_time
                )
                result.errors.append(ProcessingError(
                    video_id="",
                    video_title="",
                    error_type="VIDEO_LIST_ERROR",
                    error_message="No videos found in source or failed to extract video list"
                ))
                return result
            else:
                print(f"[DEBUG] Extracted {len(videos)} videos from source")
                for i, video in enumerate(videos[:3]):  # Show first 3 videos
                    print(f"[DEBUG]   {i+1}. {video.title} ({video.video_id})")
                if len(videos) > 3:
                    print(f"[DEBUG]   ... and {len(videos) - 3} more videos")
        except Exception as e:
            print(f"[DEBUG] Exception extracting video list: {e}")
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
        print(f"[DEBUG] Applying filters...")
        filtered_videos = self._apply_filters(videos, options)
        print(f"[DEBUG] After filtering: {len(filtered_videos)} videos remain")
        
        # Process videos
        print(f"[DEBUG] Starting video processing...")
        try:
            result = self.process_video_list(filtered_videos, source_info, options)
            result.processing_time = time.time() - start_time
            result.end_time = datetime.now()
            print(f"[DEBUG] process_source completed successfully")
            return result
        except Exception as e:
            print(f"[DEBUG] Exception in process_video_list: {e}")
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
                          options: BatchOptions) -> BatchResult:
        """
        Process a list of videos for trick extraction.
        
        Args:
            videos: List of VideoInfo objects to process
            source_info: Information about the source
            options: Processing options
            
        Returns:
            BatchResult with processing statistics
        """
        result = BatchResult(
            source_info=source_info,
            total_videos=len(videos)
        )
        
        print(f"[DEBUG] Starting batch processing of {len(videos)} videos from {source_info.name}")
        self._report_progress(0, len(videos), "Starting batch processing...")
        
        for i, video in enumerate(videos):
            print(f"[DEBUG] Processing video {i+1}/{len(videos)}: {video.title}")
            
            # Check for cancellation
            if self.cancel_token and self.cancel_token.is_set():
                print(f"[DEBUG] Batch processing cancelled at video {i+1}")
                result.cancelled = True
                self._report_progress(i, len(videos), "Processing cancelled")
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
                    print(f"[DEBUG] Video {i+1} processed successfully: {video_result.tricks_found} tricks, {len(video_result.segments_extracted)} segments")
                else:
                    if video_result.error:
                        result.errors.append(video_result.error)
                        print(f"[DEBUG] Video {i+1} failed: {video_result.error.error_type} - {video_result.error.error_message}")
                
            except Exception as e:
                print(f"[DEBUG] Critical error processing video {i+1}: {str(e)}")
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
            print(f"[DEBUG] Completed video {i+1}/{len(videos)}, continuing to next...")
        
        # Final progress report
        if not result.cancelled:
            print(f"[DEBUG] Batch processing completed successfully")
            self._report_progress(len(videos), len(videos), "Batch processing complete")
        
        print(f"[DEBUG] Final stats: {result.processed_videos} processed, {result.successful_extractions} successful, {len(result.errors)} errors")
        
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
        
        print(f"[DEBUG] Starting processing video: {video_info.title} (ID: {video_info.video_id})")
        
        try:
            # Check if we should skip existing
            if options.skip_existing:
                video_folder = self.create_folder_structure(source_info, video_info, options.output_dir)
                if os.path.exists(video_folder) and os.listdir(video_folder):
                    print(f"[DEBUG] Skipping existing video: {video_info.title}")
                    result.success = True
                    result.processing_time = time.time() - start_time
                    return result
            
            print(f"[DEBUG] Getting transcript for video: {video_info.video_id}")
            # Get transcript
            try:
                plain_text, fragments, video_info_detailed = get_transcript(video_info.video_id)
                print(f"[DEBUG] Successfully got transcript with {len(fragments)} fragments")
            except Exception as e:
                print(f"[DEBUG] Failed to get transcript: {str(e)}")
                result.error = ProcessingError(
                    video_id=video_info.video_id,
                    video_title=video_info.title,
                    error_type="TRANSCRIPT_ERROR",
                    error_message=f"Failed to get transcript: {str(e)}"
                )
                result.processing_time = time.time() - start_time
                return result
            
            print(f"[DEBUG] Extracting trick segments...")
            # Extract trick segments
            try:
                trick_segments = extract_trick_segments(fragments)
                result.tricks_found = len(trick_segments)
                print(f"[DEBUG] Found {len(trick_segments)} trick segments")
                
                if trick_segments:
                    # Create folder structure
                    video_folder = self.create_folder_structure(source_info, video_info, options.output_dir)
                    print(f"[DEBUG] Created folder: {video_folder}")
                    
                    # Extract video segments
                    print(f"[DEBUG] Starting video segment extraction...")
                    print(f"[DEBUG] Calling extract_video_segments with {len(trick_segments)} segments")
                    
                    extracted_files = extract_video_segments(
                        video_info.video_id, 
                        trick_segments, 
                        output_dir=video_folder,
                        video_info=video_info_detailed
                    )
                    
                    print(f"[DEBUG] extract_video_segments returned successfully")
                    result.segments_extracted = extracted_files
                    print(f"[DEBUG] Successfully extracted {len(extracted_files)} video segments")
                else:
                    print(f"[DEBUG] No trick segments found for video: {video_info.title}")
                
                result.success = True
                print(f"[DEBUG] Successfully completed processing video: {video_info.title}")
                
            except Exception as e:
                print(f"[DEBUG] Error during trick extraction: {str(e)}")
                import traceback
                traceback.print_exc()
                result.error = ProcessingError(
                    video_id=video_info.video_id,
                    video_title=video_info.title,
                    error_type="EXTRACTION_ERROR",
                    error_message=f"Failed to extract tricks: {str(e)}"
                )
        
        except Exception as e:
            print(f"[DEBUG] Unexpected error processing video {video_info.title}: {str(e)}")
            import traceback
            traceback.print_exc()
            result.error = ProcessingError(
                video_id=video_info.video_id,
                video_title=video_info.title,
                error_type="UNKNOWN_ERROR",
                error_message=f"Unexpected error: {str(e)}"
            )
        
        result.processing_time = time.time() - start_time
        print(f"[DEBUG] Finished processing video: {video_info.title} (Success: {result.success}, Time: {result.processing_time:.1f}s)")
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