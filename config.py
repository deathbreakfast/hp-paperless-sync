"""Configuration module for hp-paperless-sync application."""

import os
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
DEFAULT_FILE_READ_CHUNK_SIZE = 1024  # bytes
DEFAULT_UPLOAD_TIMEOUT = 30  # seconds
DEFAULT_API_TEST_TIMEOUT = 10  # seconds


class Config:
    """Configuration class for application settings."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # Paperless-ngx settings
        self.paperless_url = os.getenv('PAPERLESS_URL', 'http://192.168.0.45:8000')
        self.paperless_token = os.getenv('PAPERLESS_TOKEN')
        
        # Folder monitoring settings
        watch_folder_raw = os.getenv('WATCH_FOLDER')
        self.watch_folder = os.path.normpath(watch_folder_raw) if watch_folder_raw else None
        self.file_pattern = os.getenv('FILE_PATTERN', 'hp_envy_to_paperless_*.pdf')
        
        # Logging settings
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # File naming settings
        self.timestamp_format = os.getenv('TIMESTAMP_FORMAT', '%Y%m%d_%H%M%S')
        
        # File completion detection settings
        self.file_stable_time = int(os.getenv('FILE_STABLE_TIME', '3'))  # seconds file must be stable
        self.file_timeout = int(os.getenv('FILE_TIMEOUT', '30'))  # max seconds to wait for file completion
        
        # File processing settings
        self.auto_rename = os.getenv('AUTO_RENAME', 'smart').lower()  # 'always', 'never', or 'smart'
        self.delete_after_upload = os.getenv('DELETE_AFTER_UPLOAD', 'false').lower() == 'true'
        
        # Upload settings
        self.upload_timeout = int(os.getenv('UPLOAD_TIMEOUT', str(DEFAULT_UPLOAD_TIMEOUT)))
        self.upload_retry_attempts = int(os.getenv('UPLOAD_RETRY_ATTEMPTS', '3'))
        self.upload_retry_delay = float(os.getenv('UPLOAD_RETRY_DELAY', '2.0'))  # seconds
        
        # Rate limiting
        self.rate_limit_delay = float(os.getenv('RATE_LIMIT_DELAY', '0.5'))  # seconds between uploads
        
        # File read chunk size
        self.file_read_chunk_size = int(os.getenv('FILE_READ_CHUNK_SIZE', str(DEFAULT_FILE_READ_CHUNK_SIZE)))
        
        # Validate required settings
        self._validate_config()
        
        # Setup logging
        self._setup_logging()
    
    def _validate_config(self) -> None:
        """Validate that required configuration is present."""
        errors = []
        
        # Validate Paperless URL
        if not self.paperless_url:
            errors.append("PAPERLESS_URL is required")
        else:
            try:
                parsed = urlparse(self.paperless_url)
                if not parsed.scheme or not parsed.netloc:
                    errors.append(f"PAPERLESS_URL is not a valid URL: {self.paperless_url}")
            except Exception as e:
                errors.append(f"PAPERLESS_URL validation error: {e}")
        
        if not self.paperless_token:
            errors.append("PAPERLESS_TOKEN is required")
        
        if not self.watch_folder:
            errors.append("WATCH_FOLDER is required")
        else:
            # Normalize and validate path
            watch_path = Path(self.watch_folder).resolve()
            if not watch_path.exists():
                errors.append(f"WATCH_FOLDER does not exist: {self.watch_folder}")
            elif not watch_path.is_dir():
                errors.append(f"WATCH_FOLDER is not a directory: {self.watch_folder}")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"- {error}" for error in errors))
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Convert string log level to logging constant
        log_levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        log_level = log_levels.get(self.log_level, logging.INFO)
        
        # Configure logging format
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler('app.log'),
                logging.StreamHandler()
            ]
        )
        
        # Get logger for this module
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured with level: {self.log_level}")
    
    @property
    def paperless_api_url(self) -> str:
        """Get the full API URL for Paperless-ngx."""
        return f"{self.paperless_url.rstrip('/')}/api"
    
    @property
    def paperless_upload_url(self) -> str:
        """Get the document upload URL for Paperless-ngx."""
        return f"{self.paperless_api_url}/documents/post_document/"
    
    def get_headers(self) -> dict:
        """Get HTTP headers for API requests."""
        return {
            'Authorization': f'Token {self.paperless_token}'
        }


# Global configuration instance
config = Config()
