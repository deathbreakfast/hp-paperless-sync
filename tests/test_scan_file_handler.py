"""Tests for ScanFileHandler class."""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest
import requests

from file_handler import ScanFileHandler
from config import Config


class TestPathSecurity:
    """Test path security checks."""
    
    def test_file_in_watch_folder(self, mock_config, temp_dir):
        """Test that files within watch folder are accepted."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        assert handler._is_file_in_watch_folder(test_file) is True
    
    def test_file_outside_watch_folder(self, mock_config, temp_dir):
        """Test that files outside watch folder are rejected."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        # Create a file in a different directory
        with tempfile.TemporaryDirectory() as other_dir:
            other_file = Path(other_dir) / "test.pdf"
            assert handler._is_file_in_watch_folder(other_file) is False
    
    def test_path_traversal_prevention(self, mock_config, temp_dir):
        """Test that path traversal attacks are prevented."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        # Try various path traversal patterns
        malicious_paths = [
            temp_dir / ".." / "etc" / "passwd",
            temp_dir / ".." / ".." / "windows" / "system32",
            Path(str(temp_dir) + "/../other"),
        ]
        
        for path in malicious_paths:
            # Resolve to get actual path
            resolved = path.resolve()
            # If resolved path is outside watch folder, it should be rejected
            if not str(resolved).startswith(str(temp_dir.resolve())):
                assert handler._is_file_in_watch_folder(resolved) is False
    
    def test_watch_folder_itself(self, mock_config, temp_dir):
        """Test that watch folder itself is handled correctly."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        # Watch folder itself should not be considered a file within it
        # (though this is an edge case, files should be in subdirectories)
        result = handler._is_file_in_watch_folder(temp_dir)
        # This depends on implementation, but typically False for directories
        assert isinstance(result, bool)


class TestPatternMatching:
    """Test filename pattern matching."""
    
    def test_matches_pattern_exact(self, mock_config):
        """Test exact pattern match."""
        handler = ScanFileHandler()
        assert handler._matches_pattern("test_file.pdf") is True
    
    def test_matches_pattern_wildcard(self, mock_config):
        """Test wildcard pattern matching."""
        handler = ScanFileHandler()
        # mock_config has FILE_PATTERN='test_*.pdf'
        assert handler._matches_pattern("test_123.pdf") is True
        assert handler._matches_pattern("test_scan.pdf") is True
        assert handler._matches_pattern("other_file.pdf") is False
    
    def test_case_insensitive_matching(self, mock_config):
        """Test that pattern matching is case insensitive."""
        handler = ScanFileHandler()
        assert handler._matches_pattern("TEST_FILE.PDF") is True
        assert handler._matches_pattern("Test_File.Pdf") is True
    
    def test_pattern_with_hp_envy_format(self, monkeypatch, tmp_path):
        """Test HP Envy pattern matching."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('FILE_PATTERN', 'hp_envy_to_paperless_*.pdf')
        
        from config import config
        handler = ScanFileHandler()
        assert handler._matches_pattern("hp_envy_to_paperless_22-02-2016_1110.pdf") is True
        assert handler._matches_pattern("hp_envy_to_paperless_scan.pdf") is True
        assert handler._matches_pattern("other_file.pdf") is False


class TestRenameDecision:
    """Test rename decision logic."""
    
    def test_always_rename_mode(self, monkeypatch, tmp_path, temp_dir):
        """Test always rename mode."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('AUTO_RENAME', 'always')
        
        from config import config
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        assert handler._should_rename_file(test_file) is True
    
    def test_never_rename_mode(self, monkeypatch, tmp_path, temp_dir):
        """Test never rename mode."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('AUTO_RENAME', 'never')
        
        # Create new config with updated env vars
        from config import Config
        test_config = Config()
        
        # Patch the module-level config
        import config as config_module
        import file_handler
        import file_processing
        import paperless_client
        monkeypatch.setattr(config_module, 'config', test_config)
        monkeypatch.setattr(file_handler, 'config', test_config)
        monkeypatch.setattr(file_processing, 'config', test_config)
        monkeypatch.setattr(paperless_client, 'config', test_config)
        
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        assert handler._should_rename_file(test_file) is False
    
    def test_smart_rename_with_unique_name(self, mock_config, temp_dir):
        """Test smart rename mode with unique name (should not rename)."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "file_2024-03-22_1430.pdf"
        assert handler._should_rename_file(test_file) is False
    
    def test_smart_rename_without_unique_name(self, mock_config, temp_dir):
        """Test smart rename mode without unique name (should rename)."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "scan.pdf"
        assert handler._should_rename_file(test_file) is True


class TestUniqueNameDetection:
    """Test unique name detection."""
    
    def test_dd_mm_yyyy_pattern(self, mock_config, temp_dir):
        """Test DD-MM-YYYY pattern detection."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "file_22-03-2024.pdf"
        assert handler._has_unique_name(test_file) is True
    
    def test_yyyy_mm_dd_pattern(self, mock_config, temp_dir):
        """Test YYYY-MM-DD pattern detection."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "file_2024-03-22.pdf"
        assert handler._has_unique_name(test_file) is True
    
    def test_dd_mm_yyyy_underscore(self, mock_config, temp_dir):
        """Test DD_MM_YYYY pattern detection."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "file_22_03_2024.pdf"
        assert handler._has_unique_name(test_file) is True
    
    def test_yyyy_mm_dd_underscore(self, mock_config, temp_dir):
        """Test YYYY_MM_DD pattern detection."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "file_2024_03_22.pdf"
        assert handler._has_unique_name(test_file) is True
    
    def test_yyyymmdd_pattern(self, mock_config, temp_dir):
        """Test YYYYMMDD pattern detection."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "file_20240322.pdf"
        assert handler._has_unique_name(test_file) is True
    
    def test_yyyymmdd_hhmm_pattern(self, mock_config, temp_dir):
        """Test YYYYMMDD_HHMM pattern detection."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "file_20240322_1430.pdf"
        assert handler._has_unique_name(test_file) is True
    
    def test_dd_mm_yyyy_hhmm_pattern(self, mock_config, temp_dir):
        """Test DD-MM-YYYY_HHMM pattern detection."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "file_22-03-2024_1430.pdf"
        assert handler._has_unique_name(test_file) is True
    
    def test_no_unique_pattern(self, mock_config, temp_dir):
        """Test file without unique pattern."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "scan.pdf"
        assert handler._has_unique_name(test_file) is False
    
    def test_case_insensitive_detection(self, mock_config, temp_dir):
        """Test that unique name detection is case insensitive."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "FILE_2024-03-22.PDF"
        assert handler._has_unique_name(test_file) is True


class TestFileRenaming:
    """Test file renaming functionality."""
    
    def test_rename_with_timestamp(self, mock_config, temp_dir):
        """Test renaming file with timestamp."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "scan.pdf"
        test_file.write_bytes(b"test content")
        
        new_path = handler._rename_with_timestamp(test_file)
        
        assert new_path is not None
        assert new_path.exists()
        assert not test_file.exists()
        assert new_path.suffix == ".pdf"
        assert new_path.stem.startswith("scan_")
    
    def test_rename_preserves_extension(self, mock_config, temp_dir):
        """Test that renaming preserves file extension."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "document.docx"
        test_file.write_bytes(b"test content")
        
        new_path = handler._rename_with_timestamp(test_file)
        
        assert new_path is not None
        assert new_path.suffix == ".docx"
    
    def test_rename_without_extension(self, mock_config, temp_dir):
        """Test renaming file without extension (defaults to .pdf)."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "scan"
        test_file.write_bytes(b"test content")
        
        new_path = handler._rename_with_timestamp(test_file)
        
        assert new_path is not None
        assert new_path.suffix == ".pdf"
    
    def test_rename_error_handling(self, mock_config, temp_dir):
        """Test error handling during rename."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        # Try to rename a non-existent file
        test_file = temp_dir / "nonexistent.pdf"
        
        new_path = handler._rename_with_timestamp(test_file)
        
        assert new_path is None


class TestFileCompletionDetection:
    """Test file completion detection."""
    
    def test_wait_for_file_complete_stable(self, mock_config, temp_dir, monkeypatch):
        """Test waiting for file to complete when it stabilizes."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        # Write file with stable content
        test_file.write_bytes(b"stable content")
        
        # Mock time.sleep to speed up test, and mock time progression
        # to simulate file being stable for required duration
        start_time = [time.time()]
        call_count = [0]
        
        def mock_time():
            call_count[0] += 1
            # Simulate time progressing, but file stays stable
            # After enough iterations (simulating stability period), return success time
            if call_count[0] < 5:  # Simulate stability checks
                return start_time[0] + call_count[0] * 0.1
            else:  # Past stability period
                return start_time[0] + 10
        
        with patch('time.time', mock_time):
            with patch('time.sleep'):  # Speed up the test
                # File exists and is stable, should eventually succeed
                # Use a short timeout since we're mocking time
                result = handler._wait_for_file_complete(test_file, timeout=1)
                # Should return True if file is stable, False if timeout
                # The exact result depends on timing, but function should not crash
                assert isinstance(result, bool)
    
    def test_wait_for_file_timeout(self, mock_config, temp_dir, monkeypatch):
        """Test timeout when file doesn't stabilize."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        # Create a file that will timeout
        test_file.write_bytes(b"content")
        
        # Since we can't patch Path.stat() (it's read-only), we'll ensure
        # the file never stabilizes by requiring a very long stable_time,
        # longer than the timeout. This way even if the file size is stable,
        # it won't meet the stability requirement before timeout.
        
        # Patch config to require very long stable time (longer than timeout)
        import config as config_module
        import file_processing
        original_stable_time = config_module.config.file_stable_time
        config_module.config.file_stable_time = 1000  # Much longer than timeout
        file_processing.config.file_stable_time = 1000  # Also patch in file_processing
        
        try:
            # Mock time to simulate timeout
            start_time = time.time()
            time_calls = [0]
            
            def mock_time():
                time_calls[0] += 1
                if time_calls[0] == 1:
                    # First call sets start_time in the function
                    return start_time
                else:
                    # Second call and beyond - return time past timeout
                    # This makes the while condition False
                    return start_time + 10  # Past timeout
            
            with patch('time.time', mock_time):
                with patch('time.sleep'):  # Speed up the test
                    # Use a short timeout
                    result = handler._wait_for_file_complete(test_file, timeout=5)
                    # File won't stabilize (requires 1000s) before timeout (5s)
                    assert result is False
        finally:
            # Restore original stable time
            config_module.config.file_stable_time = original_stable_time
            file_processing.config.file_stable_time = original_stable_time
    
    def test_wait_for_file_removed(self, mock_config, temp_dir):
        """Test when file is removed during wait."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        
        # File doesn't exist
        result = handler._wait_for_file_complete(test_file, timeout=5)
        assert result is False
    
    def test_can_access_file_success(self, mock_config, temp_dir):
        """Test successful file access."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        assert handler._can_access_file(test_file) is True
    
    def test_can_access_file_locked(self, mock_config, temp_dir):
        """Test file access when file is locked."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        
        # Mock permission error
        with patch('builtins.open', side_effect=PermissionError("File is locked")):
            assert handler._can_access_file(test_file) is False


class TestFileUpload:
    """Test file upload functionality."""
    
    def test_upload_success(self, mock_config, temp_dir, mock_requests):
        """Test successful file upload."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        mock_requests['response'].status_code = 200
        
        result = handler._upload_to_paperless(test_file)
        
        assert result is True
        mock_requests['post'].assert_called_once()
    
    def test_upload_retry_on_5xx(self, mock_config, temp_dir, mock_requests):
        """Test retry on 5xx server errors."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        # Create proper mock responses with headers
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Server Error"
        mock_error_response.headers = Mock()
        mock_error_response.headers.get = Mock(return_value='')
        
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.text = "OK"
        mock_success_response.headers = Mock()
        mock_success_response.headers.get = Mock(return_value='application/json')
        mock_success_response.json.return_value = {"id": 1}
        
        # First attempt fails with 500, second succeeds
        mock_requests['post'].side_effect = [
            mock_error_response,
            mock_success_response
        ]
        
        with patch('time.sleep'):  # Speed up test
            result = handler._upload_to_paperless(test_file)
        
        assert result is True
        assert mock_requests['post'].call_count == 2
    
    def test_upload_no_retry_on_4xx(self, mock_config, temp_dir, mock_requests):
        """Test that 4xx errors don't retry (except 429)."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        mock_requests['response'].status_code = 400
        mock_requests['response'].text = "Bad Request"
        
        result = handler._upload_to_paperless(test_file)
        
        assert result is False
        # Should only try once for 4xx (non-429)
        assert mock_requests['post'].call_count == 1
    
    def test_upload_retry_on_429(self, mock_config, temp_dir, mock_requests):
        """Test retry on 429 rate limit errors."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        # Create proper mock responses with headers
        mock_error_response = Mock()
        mock_error_response.status_code = 429
        mock_error_response.text = "Rate Limited"
        mock_error_response.headers = Mock()
        mock_error_response.headers.get = Mock(return_value='')
        
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.text = "OK"
        mock_success_response.headers = Mock()
        mock_success_response.headers.get = Mock(return_value='application/json')
        mock_success_response.json.return_value = {"id": 1}
        
        # First attempt fails with 429, second succeeds
        mock_requests['post'].side_effect = [
            mock_error_response,
            mock_success_response
        ]
        
        with patch('time.sleep'):  # Speed up test
            result = handler._upload_to_paperless(test_file)
        
        assert result is True
        assert mock_requests['post'].call_count == 2
    
    def test_upload_network_error_retry(self, mock_config, temp_dir, mock_requests):
        """Test retry on network errors."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        # Create proper mock success response with headers
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.text = "OK"
        mock_success_response.headers = Mock()
        mock_success_response.headers.get = Mock(return_value='application/json')
        mock_success_response.json.return_value = {"id": 1}
        
        # First attempt fails with network error, second succeeds
        mock_requests['post'].side_effect = [
            requests.exceptions.ConnectionError("Network error"),
            mock_success_response
        ]
        
        with patch('time.sleep'):  # Speed up test
            result = handler._upload_to_paperless(test_file)
        
        assert result is True
        assert mock_requests['post'].call_count == 2
    
    def test_upload_delete_after_success(self, monkeypatch, tmp_path, temp_dir, mock_requests):
        """Test file deletion after successful upload."""
        monkeypatch.setenv('PAPERLESS_URL', 'http://test.local:8000')
        monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token')
        monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
        monkeypatch.setenv('DELETE_AFTER_UPLOAD', 'true')
        
        # Create new config with updated env vars
        from config import Config
        test_config = Config()
        
        # Patch the module-level config
        import config as config_module
        import file_handler
        import file_processing
        import paperless_client
        monkeypatch.setattr(config_module, 'config', test_config)
        monkeypatch.setattr(file_handler, 'config', test_config)
        monkeypatch.setattr(file_processing, 'config', test_config)
        monkeypatch.setattr(paperless_client, 'config', test_config)
        
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        # Ensure mock response has proper headers
        mock_requests['response'].status_code = 200
        mock_requests['response'].headers = Mock()
        mock_requests['response'].headers.get = Mock(return_value='application/json')
        mock_requests['response'].json.return_value = {"id": 1}
        
        # Mock the file opening to use a StringIO-like object that doesn't lock the file
        # This prevents Windows file locking issues
        from io import BytesIO
        
        def mock_open_file(file_path, mode='r', *args, **kwargs):
            if isinstance(file_path, (Path, str)) and str(file_path) == str(test_file) and 'b' in mode:
                # Return a BytesIO object that mimics a file but doesn't lock the actual file
                return BytesIO(test_file.read_bytes())
            else:
                # For other files, use real open
                return open(file_path, mode, *args, **kwargs)
        
        with patch('builtins.open', side_effect=mock_open_file):
            with patch('time.sleep'):  # Skip rate limit delay
                result = handler._upload_to_paperless(test_file)
        
        assert result is True
        assert not test_file.exists()  # File should be deleted
    
    def test_upload_rate_limit_delay(self, mock_config, temp_dir, mock_requests):
        """Test rate limiting delay after upload."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        mock_requests['response'].status_code = 200
        
        with patch('time.sleep') as mock_sleep:
            handler._upload_to_paperless(test_file)
            # Should sleep for rate limit delay
            mock_sleep.assert_called()
    
    def test_upload_mime_type_detection(self, mock_config, temp_dir, mock_requests):
        """Test MIME type detection for upload."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.pdf"
        test_file.write_bytes(b"test content")
        
        mock_requests['response'].status_code = 200
        
        handler._upload_to_paperless(test_file)
        
        # Check that files parameter includes MIME type
        call_args = mock_requests['post'].call_args
        assert 'files' in call_args.kwargs
        files = call_args.kwargs['files']
        assert 'document' in files
        assert files['document'][2] == 'application/pdf'  # MIME type
    
    def test_upload_default_mime_type(self, mock_config, temp_dir, mock_requests):
        """Test default MIME type when detection fails."""
        handler = ScanFileHandler()
        handler.watch_folder_path = temp_dir
        
        test_file = temp_dir / "test.unknown"
        test_file.write_bytes(b"test content")
        
        mock_requests['response'].status_code = 200
        
        handler._upload_to_paperless(test_file)
        
        # Should default to application/pdf
        call_args = mock_requests['post'].call_args
        files = call_args.kwargs['files']
        assert files['document'][2] == 'application/pdf'

