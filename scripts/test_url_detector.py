"""
Tests for URL Detection Module

This module contains comprehensive tests for the URLDetector class,
testing various YouTube URL formats and edge cases.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import ytsummarizer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ytsummarizer.url_detector import URLDetector, URLType, detect_url_type, extract_source_id, validate_url


class TestURLDetector(unittest.TestCase):
    """Test cases for URLDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = URLDetector()
    
    def test_single_video_urls(self):
        """Test detection of single video URLs."""
        video_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=TestChannel",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?t=30",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/v/dQw4w9WgXcQ",
            "dQw4w9WgXcQ",  # Just the video ID
        ]
        
        for url in video_urls:
            with self.subTest(url=url):
                self.assertEqual(self.detector.detect_url_type(url), URLType.SINGLE_VIDEO)
                self.assertEqual(self.detector.extract_source_id(url), "dQw4w9WgXcQ")
    
    def test_channel_urls(self):
        """Test detection of channel URLs."""
        channel_test_cases = [
            ("https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw", "UCuAXFkgsw1L7xaCfnd5JJOw"),
            ("https://youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw", "UCuAXFkgsw1L7xaCfnd5JJOw"),
            ("https://www.youtube.com/@testchannel", "testchannel"),
            ("https://www.youtube.com/@test.channel", "test.channel"),
            ("https://www.youtube.com/@test_channel", "test_channel"),
            ("https://www.youtube.com/c/TestChannel", "TestChannel"),
            ("https://www.youtube.com/user/TestUser", "TestUser"),
        ]
        
        for url, expected_id in channel_test_cases:
            with self.subTest(url=url):
                self.assertEqual(self.detector.detect_url_type(url), URLType.CHANNEL)
                self.assertEqual(self.detector.extract_source_id(url), expected_id)
    
    def test_playlist_urls(self):
        """Test detection of playlist URLs."""
        playlist_test_cases = [
            ("https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G", "PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G"),
            ("https://youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G", "PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G"),
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G", "PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G"),
            ("https://www.youtube.com/watch?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G&v=dQw4w9WgXcQ", "PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G"),
        ]
        
        for url, expected_id in playlist_test_cases:
            with self.subTest(url=url):
                self.assertEqual(self.detector.detect_url_type(url), URLType.PLAYLIST)
                self.assertEqual(self.detector.extract_source_id(url), expected_id)
    
    def test_invalid_urls(self):
        """Test detection of invalid URLs."""
        invalid_urls = [
            "",
            None,
            "not_a_url",
            "https://www.google.com",
            "https://www.youtube.com",
            "https://www.youtube.com/",
            "https://www.youtube.com/watch",
            "https://www.youtube.com/watch?v=",
            "https://www.youtube.com/watch?v=invalid",
            "https://www.youtube.com/channel/",
            "https://www.youtube.com/playlist",
            "invalid_video_id",
            "dQw4w9WgXc",  # Too short
            "dQw4w9WgXcQQ",  # Too long
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertEqual(self.detector.detect_url_type(url), URLType.INVALID)
                self.assertIsNone(self.detector.extract_source_id(url))
    
    def test_url_validation(self):
        """Test URL validation functionality."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
            "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G",
            "dQw4w9WgXcQ",
        ]
        
        invalid_urls = [
            "",
            "not_a_url",
            "https://www.google.com",
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(self.detector.validate_url(url))
        
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(self.detector.validate_url(url))
    
    def test_get_url_info(self):
        """Test comprehensive URL information extraction."""
        test_cases = [
            {
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'expected_type': URLType.SINGLE_VIDEO,
                'expected_id': 'dQw4w9WgXcQ',
                'should_have_video_url': True,
            },
            {
                'url': 'https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw',
                'expected_type': URLType.CHANNEL,
                'expected_id': 'UCuAXFkgsw1L7xaCfnd5JJOw',
                'should_have_channel_url': True,
            },
            {
                'url': 'https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G',
                'expected_type': URLType.PLAYLIST,
                'expected_id': 'PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G',
                'should_have_playlist_url': True,
            },
        ]
        
        for case in test_cases:
            with self.subTest(url=case['url']):
                info = self.detector.get_url_info(case['url'])
                
                self.assertEqual(info['url'], case['url'])
                self.assertEqual(info['type'], case['expected_type'])
                self.assertEqual(info['source_id'], case['expected_id'])
                self.assertTrue(info['is_valid'])
                
                if case.get('should_have_video_url'):
                    self.assertIn('video_url', info)
                    self.assertIsNotNone(info['video_url'])
                
                if case.get('should_have_channel_url'):
                    self.assertIn('channel_url', info)
                    self.assertIsNotNone(info['channel_url'])
                
                if case.get('should_have_playlist_url'):
                    self.assertIn('playlist_url', info)
                    self.assertIsNotNone(info['playlist_url'])
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        self.assertEqual(detect_url_type(test_url), URLType.SINGLE_VIDEO)
        self.assertEqual(extract_source_id(test_url), "dQw4w9WgXcQ")
        self.assertTrue(validate_url(test_url))
    
    def test_edge_cases(self):
        """Test edge cases and special scenarios."""
        edge_cases = [
            # URLs with extra parameters
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be", URLType.SINGLE_VIDEO),
            # Mixed case
            ("HTTPS://WWW.YOUTUBE.COM/WATCH?V=dQw4w9WgXcQ", URLType.SINGLE_VIDEO),
            # URLs with fragments
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ#t=30s", URLType.SINGLE_VIDEO),
            # Whitespace
            ("  https://www.youtube.com/watch?v=dQw4w9WgXcQ  ", URLType.SINGLE_VIDEO),
        ]
        
        for url, expected_type in edge_cases:
            with self.subTest(url=url):
                self.assertEqual(self.detector.detect_url_type(url), expected_type)
    
    def test_playlist_priority_over_video(self):
        """Test that playlist URLs are detected as playlists even when they contain video IDs."""
        playlist_with_video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G"
        
        # Should be detected as playlist, not video
        self.assertEqual(self.detector.detect_url_type(playlist_with_video), URLType.PLAYLIST)
        self.assertEqual(self.detector.extract_source_id(playlist_with_video), "PLrAXtmRdnEQy6nuLMt9H1mu_ylNHiRr0G")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)