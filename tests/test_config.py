"""Tests for configuration module."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from config import Config, DEFAULT_FILE_READ_CHUNK_SIZE, DEFAULT_UPLOAD_TIMEOUT, DEFAULT_API_TEST_TIMEOUT


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_missing_paperless_url(self, monkeypatch, tmp_path):
        """Test that missing PAPERLESS_URL raises error."""
        monkeypatch.setenv('PAPERLESS_URL', '')  # Set to empty string to trigger validation
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        
        with pytest.raises(ValueError, match="PAPERLESS_URL is required"):
            Config()
    
    def test_missing_paperless_token(self, monkeypatch, tmp_path):
        """Test that missing PAPERLESS_TOKEN raises error."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.delenv('PAPERLESS_TOKEN', raising=False)
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        
        with pytest.raises(ValueError, match="PAPERLESS_TOKEN is required"):
            Config()
    
    def test_missing_watch_folder(self, monkeypatch):
        """Test that missing WATCH_FOLDER raises error."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.delenv('WATCH_FOLDER', raising=False)
        
        with pytest.raises(ValueError, match="WATCH_FOLDER is required"):
            Config()
    
    def test_invalid_url(self, monkeypatch, tmp_path):
        """Test that invalid URL format raises error."""
        monkeypatch.setenv('PAPERLESS_URL', 'not-a-valid-url')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        
        with pytest.raises(ValueError, match="PAPERLESS_URL is not a valid URL"):
            Config()
    
    def test_nonexistent_watch_folder(self, monkeypatch, tmp_path):
        """Test that nonexistent watch folder raises error."""
        nonexistent_path = tmp_path / "nonexistent"
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(nonexistent_path))
        
        with pytest.raises(ValueError, match="WATCH_FOLDER does not exist"):
            Config()
    
    def test_watch_folder_not_directory(self, monkeypatch, tmp_path):
        """Test that watch folder that is a file raises error."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("test")
        
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(test_file))
        
        with pytest.raises(ValueError, match="WATCH_FOLDER is not a directory"):
            Config()
    
    def test_valid_config(self, monkeypatch, tmp_path):
        """Test that valid configuration initializes successfully."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        
        config = Config()
        assert config.paperless_url == 'http://test.local:8000'
        assert config.paperless_token == 'test_token'
        assert config.watch_folder == str(tmp_path)


class TestConfigProperties:
    """Test configuration properties."""
    
    def test_paperless_api_url(self, mock_config):
        """Test paperless_api_url property."""
        assert mock_config.paperless_api_url == 'http://test.paperless.local:8000/api'
    
    def test_paperless_api_url_with_trailing_slash(self, monkeypatch, tmp_path):
        """Test paperless_api_url property with trailing slash in base URL."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000/')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        
        config = Config()
        assert config.paperless_api_url == 'http://test.local:8000/api'
    
    def test_paperless_upload_url(self, mock_config):
        """Test paperless_upload_url property."""
        assert mock_config.paperless_upload_url == 'http://test.paperless.local:8000/api/documents/post_document/'
    
    def test_get_headers(self, mock_config):
        """Test get_headers method."""
        headers = mock_config.get_headers()
        assert headers == {'Authorization': 'Token test_token_12345'}


class TestConfigDefaults:
    """Test configuration default values."""
    
    def test_default_file_pattern(self, monkeypatch, tmp_path):
        """Test default file pattern."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('FILE_PATTERN', raising=False)
        
        config = Config()
        assert config.file_pattern == 'hp_envy_to_paperless_*.pdf'
    
    def test_default_timestamp_format(self, monkeypatch, tmp_path):
        """Test default timestamp format."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('TIMESTAMP_FORMAT', raising=False)
        
        config = Config()
        assert config.timestamp_format == '%Y%m%d_%H%M%S'
    
    def test_default_file_stable_time(self, monkeypatch, tmp_path):
        """Test default file stable time."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('FILE_STABLE_TIME', raising=False)
        
        config = Config()
        assert config.file_stable_time == 3
    
    def test_default_file_timeout(self, monkeypatch, tmp_path):
        """Test default file timeout."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('FILE_TIMEOUT', raising=False)
        
        config = Config()
        assert config.file_timeout == 30
    
    def test_default_auto_rename(self, monkeypatch, tmp_path):
        """Test default auto rename mode."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('AUTO_RENAME', raising=False)
        
        config = Config()
        assert config.auto_rename == 'smart'
    
    def test_default_delete_after_upload(self, monkeypatch, tmp_path):
        """Test default delete after upload setting."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('DELETE_AFTER_UPLOAD', raising=False)
        
        config = Config()
        assert config.delete_after_upload is False
    
    def test_default_upload_timeout(self, monkeypatch, tmp_path):
        """Test default upload timeout."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('UPLOAD_TIMEOUT', raising=False)
        
        config = Config()
        assert config.upload_timeout == DEFAULT_UPLOAD_TIMEOUT
    
    def test_default_upload_retry_attempts(self, monkeypatch, tmp_path):
        """Test default upload retry attempts."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('UPLOAD_RETRY_ATTEMPTS', raising=False)
        
        config = Config()
        assert config.upload_retry_attempts == 3
    
    def test_default_upload_retry_delay(self, monkeypatch, tmp_path):
        """Test default upload retry delay."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('UPLOAD_RETRY_DELAY', raising=False)
        
        config = Config()
        assert config.upload_retry_delay == 2.0
    
    def test_default_rate_limit_delay(self, monkeypatch, tmp_path):
        """Test default rate limit delay."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('RATE_LIMIT_DELAY', raising=False)
        
        config = Config()
        assert config.rate_limit_delay == 0.5
    
    def test_default_file_read_chunk_size(self, monkeypatch, tmp_path):
        """Test default file read chunk size."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.delenv('FILE_READ_CHUNK_SIZE', raising=False)
        
        config = Config()
        assert config.file_read_chunk_size == DEFAULT_FILE_READ_CHUNK_SIZE


class TestConfigEnvironmentParsing:
    """Test parsing of environment variables."""
    
    def test_custom_file_pattern(self, monkeypatch, tmp_path):
        """Test custom file pattern."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('FILE_PATTERN', 'custom_*.pdf')
        
        config = Config()
        assert config.file_pattern == 'custom_*.pdf'
    
    def test_custom_timestamp_format(self, monkeypatch, tmp_path):
        """Test custom timestamp format."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('TIMESTAMP_FORMAT', '%Y-%m-%d_%H-%M-%S')
        
        config = Config()
        assert config.timestamp_format == '%Y-%m-%d_%H-%M-%S'
    
    def test_auto_rename_always(self, monkeypatch, tmp_path):
        """Test auto rename always mode."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('AUTO_RENAME', 'always')
        
        config = Config()
        assert config.auto_rename == 'always'
    
    def test_auto_rename_never(self, monkeypatch, tmp_path):
        """Test auto rename never mode."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('AUTO_RENAME', 'never')
        
        config = Config()
        assert config.auto_rename == 'never'
    
    def test_delete_after_upload_true(self, monkeypatch, tmp_path):
        """Test delete after upload enabled."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('DELETE_AFTER_UPLOAD', 'true')
        
        config = Config()
        assert config.delete_after_upload is True
    
    def test_log_level_parsing(self, monkeypatch, tmp_path):
        """Test log level parsing."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('LOG_LEVEL', 'ERROR')
        
        config = Config()
        assert config.log_level == 'ERROR'

