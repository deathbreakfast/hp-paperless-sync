"""Shared fixtures and test utilities for pytest."""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, MagicMock

import pytest

from config import Config


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(monkeypatch, tmp_path):
    """Create a mock config object and patch the module-level config."""
    # Set environment variables
    monkeypatch.setenv('PAPERLESS_URL', 'http://test.paperless.local:8000')
    monkeypatch.setenv('PAPERLESS_TOKEN', 'test_token_12345')
    monkeypatch.setenv('WATCH_FOLDER', str(tmp_path))
    monkeypatch.setenv('FILE_PATTERN', 'test_*.pdf')
    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    
    # Create a new config instance
    config_instance = Config()
    
    # Patch the module-level config in config module and all modules that import it
    import config as config_module
    monkeypatch.setattr(config_module, 'config', config_instance)
    
    # Also patch in modules that import config
    import file_handler
    import file_processing
    import paperless_client
    import folder_monitor
    monkeypatch.setattr(file_handler, 'config', config_instance)
    monkeypatch.setattr(file_processing, 'config', config_instance)
    monkeypatch.setattr(paperless_client, 'config', config_instance)
    monkeypatch.setattr(folder_monitor, 'config', config_instance)
    
    return config_instance


@pytest.fixture
def sample_pdf_file(temp_dir: Path) -> Path:
    """Create a sample PDF file for testing."""
    test_file = temp_dir / "test_file.pdf"
    test_file.write_bytes(b"%PDF-1.4\nfake pdf content")
    return test_file


@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests module for testing API calls."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "title": "test"}
    mock_response.text = '{"id": 1, "title": "test"}'
    # Make headers.get() return a proper string
    mock_response.headers = Mock()
    mock_response.headers.get = Mock(return_value='application/json')
    
    mock_post = Mock(return_value=mock_response)
    mock_get = Mock(return_value=mock_response)
    
    monkeypatch.setattr('requests.post', mock_post)
    monkeypatch.setattr('requests.get', mock_get)
    
    return {
        'post': mock_post,
        'get': mock_get,
        'response': mock_response
    }


@pytest.fixture
def mock_file_stat(monkeypatch):
    """Mock file stat operations for testing file completion detection."""
    def create_stat_mock(size: int):
        stat_mock = Mock()
        stat_mock.st_size = size
        return stat_mock
    
    return create_stat_mock

