"""
Folder monitoring and application lifecycle management for HP Paperless Sync.

This module manages the file system observer and application lifecycle.
"""

import time
import logging
from typing import Optional

from watchdog.observers import Observer

from config import config
from file_handler import ScanFileHandler
from paperless_client import PaperlessClient


logger = logging.getLogger(__name__)


class FolderMonitor:
    """Main class for monitoring folder and managing the application."""
    
    def __init__(self) -> None:
        """Initialize the folder monitor."""
        self.logger = logging.getLogger(__name__)
        self.observer: Optional[Observer] = None
        self.event_handler = ScanFileHandler()
        self.paperless_client = PaperlessClient()
        self._shutdown_requested = False
    
    def start(self) -> None:
        """Start monitoring the folder."""
        try:
            self.logger.info(f"Starting folder monitor for: {config.watch_folder}")
            self.logger.info(f"File pattern: {config.file_pattern}")
            self.logger.info(f"Paperless-ngx URL: {config.paperless_url}")
            
            # Test connection to Paperless-ngx
            self.paperless_client.test_connection()
            
            # Setup file system observer
            self.observer = Observer()
            self.observer.schedule(
                self.event_handler,
                config.watch_folder,
                recursive=False
            )
            
            # Start monitoring
            self.observer.start()
            self.logger.info("Folder monitoring started. Press Ctrl+C to stop.")
            
            # Keep the application running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal. Stopping...")
                self.stop()
        
        except Exception as e:
            self.logger.error(f"Error starting folder monitor: {e}")
            raise
    
    def stop(self) -> None:
        """Stop monitoring the folder."""
        self._shutdown_requested = True
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)  # Wait up to 5 seconds for graceful shutdown
            self.logger.info("Folder monitoring stopped.")
    
    # Backward compatibility method for tests
    def _test_paperless_connection(self) -> None:
        """Backward compatibility wrapper for tests."""
        self.paperless_client.test_connection()

