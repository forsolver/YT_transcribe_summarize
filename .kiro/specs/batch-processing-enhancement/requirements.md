# Requirements Document

## Introduction

This feature enhancement transforms the YouTube Tools application from processing single videos to supporting batch processing of entire channels and playlists. The enhancement maintains backward compatibility while adding powerful batch processing capabilities for extracting tricks from multiple videos in a structured manner.

## Requirements

### Requirement 1

**User Story:** As a user, I want to input a YouTube channel or playlist URL and have the application process all videos in that source, so that I can extract tricks from multiple videos efficiently without manual intervention.

#### Acceptance Criteria

1. WHEN a user enters a YouTube channel URL THEN the system SHALL detect it as a channel source and extract all available videos from that channel
2. WHEN a user enters a YouTube playlist URL THEN the system SHALL detect it as a playlist source and extract all videos from that playlist
3. WHEN a user enters a single video URL THEN the system SHALL continue to work as before (backward compatibility)
4. IF the channel or playlist contains more than 50 videos THEN the system SHALL process only the first 50 videos by default
5. WHEN processing multiple videos THEN the system SHALL create a nested folder structure: tricks/[source_name]/[video_name]/

### Requirement 2

**User Story:** As a user, I want to see the progress of batch processing operations, so that I can understand how much work remains and monitor the application's status.

#### Acceptance Criteria

1. WHEN batch processing starts THEN the system SHALL display an overall progress indicator showing X of Y videos processed
2. WHEN processing each individual video THEN the system SHALL display the current video being processed
3. WHEN processing is complete THEN the system SHALL display a summary of results including total videos processed, tricks found, and any errors
4. IF an error occurs with one video THEN the system SHALL continue processing remaining videos and report the error in the final summary
5. WHEN processing takes longer than 30 seconds THEN the system SHALL provide an estimated time remaining

### Requirement 3

**User Story:** As a user, I want to be able to cancel long-running batch operations, so that I can stop processing if needed without having to close the application.

#### Acceptance Criteria

1. WHEN batch processing is running THEN the system SHALL provide a "Cancel" button that is clearly visible
2. WHEN the user clicks "Cancel" THEN the system SHALL stop processing new videos within 5 seconds
3. WHEN cancellation occurs THEN the system SHALL complete processing of the current video before stopping
4. WHEN processing is cancelled THEN the system SHALL display a summary of videos processed before cancellation
5. WHEN processing is cancelled THEN all already extracted video segments SHALL remain saved

### Requirement 4

**User Story:** As a user, I want the application to handle errors gracefully during batch processing, so that one problematic video doesn't stop the entire batch operation.

#### Acceptance Criteria

1. WHEN a video in the batch cannot be processed THEN the system SHALL log the error and continue with the next video
2. WHEN transcript extraction fails for a video THEN the system SHALL skip that video and record the failure
3. WHEN video download fails for a video THEN the system SHALL skip that video and record the failure
4. WHEN processing completes THEN the system SHALL display a list of any videos that were skipped due to errors
5. IF more than 50% of videos fail to process THEN the system SHALL display a warning suggesting to check network connection or source accessibility

### Requirement 5

**User Story:** As a user, I want to configure batch processing settings, so that I can control how many videos are processed and optimize the operation for my needs.

#### Acceptance Criteria

1. WHEN starting batch processing THEN the system SHALL allow me to set a maximum number of videos to process
2. WHEN I set a video limit THEN the system SHALL process only that many videos from the source
3. WHEN I enable "skip existing" option THEN the system SHALL skip videos that already have extracted tricks
4. WHEN processing large sources THEN the system SHALL provide options to filter videos by upload date or duration
5. WHEN I save settings THEN the system SHALL remember my preferences for future batch operations

### Requirement 6

**User Story:** As a user, I want the batch processing to organize extracted tricks in a clear folder structure, so that I can easily find tricks from specific videos and sources.

#### Acceptance Criteria

1. WHEN processing a channel THEN the system SHALL create a folder named after the channel: tricks/[channel_name]/
2. WHEN processing a playlist THEN the system SHALL create a folder named after the playlist: tricks/[playlist_name]/
3. WHEN processing videos from a source THEN each video SHALL have its own subfolder: tricks/[source_name]/[video_name]/
4. WHEN creating folder names THEN the system SHALL sanitize names to be filesystem-compatible
5. WHEN folder names would be too long THEN the system SHALL truncate them to 50 characters maximum

### Requirement 7

**User Story:** As a user, I want the application to provide detailed feedback about the batch processing operation, so that I can understand what happened and troubleshoot any issues.

#### Acceptance Criteria

1. WHEN batch processing starts THEN the system SHALL display the source name and estimated number of videos
2. WHEN processing each video THEN the system SHALL show the current video title and progress
3. WHEN processing completes THEN the system SHALL show total processing time and summary statistics
4. WHEN errors occur THEN the system SHALL provide specific error messages for each failed video
5. WHEN processing completes THEN the system SHALL show the total number of trick segments extracted across all videos

### Requirement 8

**User Story:** As a user, I want the batch processing to work efficiently without overwhelming system resources, so that I can continue using my computer for other tasks during processing.

#### Acceptance Criteria

1. WHEN batch processing runs THEN the system SHALL process videos sequentially to avoid overwhelming network resources
2. WHEN downloading videos THEN the system SHALL limit concurrent downloads to prevent bandwidth saturation
3. WHEN processing videos THEN the system SHALL use existing caching mechanisms to avoid re-downloading transcripts
4. WHEN system resources are low THEN the system SHALL provide warnings about available disk space
5. WHEN processing large batches THEN the system SHALL provide options to pause and resume operations