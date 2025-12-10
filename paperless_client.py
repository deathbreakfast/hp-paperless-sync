"""
Paperless-ngx API client for HP Paperless Sync.

This module handles all interactions with the Paperless-ngx API,
including document uploads, connection testing, and retry logic.
"""

import mimetypes
import time
import logging
from pathlib import Path
from datetime import datetime

import requests

from config import config, DEFAULT_API_TEST_TIMEOUT


logger = logging.getLogger(__name__)


class PaperlessClient:
    """Client for interacting with Paperless-ngx API."""
    
    def __init__(self):
        """Initialize the Paperless client."""
        self.logger = logging.getLogger(__name__)
    
    def test_connection(self) -> None:
        """
        Test connection to Paperless-ngx API.
        
        Logs warnings on failure but does not raise exceptions,
        allowing the application to continue with a warning.
        """
        try:
            self.logger.info("Testing connection to Paperless-ngx...")
            
            # Test API endpoint
            test_url = f"{config.paperless_api_url}/documents/"
            response = requests.get(
                test_url,
                headers=config.get_headers(),
                timeout=DEFAULT_API_TEST_TIMEOUT
            )
            
            # Accept any 2xx status code
            if 200 <= response.status_code < 300:
                self.logger.info(f"Successfully connected to Paperless-ngx API (status: {response.status_code})")
            else:
                self.logger.warning(f"Paperless-ngx API returned status {response.status_code}")
                self.logger.warning("Continuing anyway, but uploads may fail")
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to connect to Paperless-ngx: {e}")
            self.logger.warning("Continuing anyway, but uploads will likely fail")
    
    def upload_document(self, file_path: Path) -> bool:
        """
        Upload file to Paperless-ngx with retry mechanism.
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            True if upload succeeded, False otherwise
        """
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            # Default to application/pdf if detection fails
            mime_type = 'application/pdf'
            self.logger.debug(f"Could not detect MIME type for {file_path.name}, defaulting to {mime_type}")
        
        # Retry upload with exponential backoff
        for attempt in range(1, config.upload_retry_attempts + 1):
            try:
                self.logger.info(f"Uploading file to Paperless-ngx (attempt {attempt}/{config.upload_retry_attempts}): {file_path}")
                
                # Prepare the file for upload
                with open(file_path, 'rb') as file:
                    files = {
                        'document': (file_path.name, file, mime_type)
                    }
                    
                    # Optional: Add metadata
                    data = {
                        'title': file_path.stem,
                        'created': datetime.now().isoformat(),
                    }
                    
                    # Make the upload request
                    response = requests.post(
                        config.paperless_upload_url,
                        files=files,
                        data=data,
                        headers=config.get_headers(),
                        timeout=config.upload_timeout
                    )
                    
                    # Accept any 2xx status code (200, 201, etc.)
                    if 200 <= response.status_code < 300:
                        self.logger.info(f"Successfully uploaded {file_path.name} to Paperless-ngx (status: {response.status_code})")
                        
                        # Try to parse JSON response if available
                        try:
                            content_type = response.headers.get('content-type', '')
                            if 'application/json' in content_type:
                                self.logger.debug(f"Response: {response.json()}")
                        except (ValueError, KeyError):
                            pass  # Not JSON or parsing failed, that's okay
                        
                        # Delete file after successful upload if configured
                        if config.delete_after_upload:
                            try:
                                file_path.unlink()
                                self.logger.info(f"Deleted file after successful upload: {file_path}")
                            except Exception as e:
                                self.logger.warning(f"Failed to delete file after upload: {file_path} - {e}")
                        
                        # Rate limiting: delay before next upload
                        if config.rate_limit_delay > 0:
                            time.sleep(config.rate_limit_delay)
                        
                        return True
                    else:
                        self.logger.warning(f"Upload attempt {attempt} failed. Status: {response.status_code}")
                        self.logger.debug(f"Response: {response.text[:500]}")  # Limit response text length
                        
                        # Don't retry on client errors (4xx) except 429 (rate limit)
                        if 400 <= response.status_code < 500 and response.status_code != 429:
                            self.logger.error(f"Client error, not retrying: {response.status_code}")
                            return False
                        
                        # Retry on server errors (5xx) and rate limits (429)
                        if attempt < config.upload_retry_attempts:
                            delay = config.upload_retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                            self.logger.info(f"Retrying upload in {delay:.1f} seconds...")
                            time.sleep(delay)
            
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Network error on upload attempt {attempt}: {e}")
                if attempt < config.upload_retry_attempts:
                    delay = config.upload_retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    self.logger.info(f"Retrying upload in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All upload attempts failed for {file_path.name}")
            
            except Exception as e:
                self.logger.error(f"Unexpected error uploading {file_path.name}: {e}")
                return False
        
        return False

