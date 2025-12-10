"""
File system event handler for HP Paperless Sync.

This module handles file system events (file creation, moves) and
orchestrates the file processing workflow.
"""

import fnmatch
import logging
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler

from config import config
from file_processing import (
    should_rename_file,
    has_unique_name,
    rename_with_timestamp,
    wait_for_file_complete,
    can_access_file
)
from paperless_client import PaperlessClient


class ScanFileHandler(FileSystemEventHandler):
    """Handler for file system events in the monitored folder."""
    
    def __init__(self) -> None:
        """Initialize the handler."""
        self.logger = logging.getLogger(__name__)
        self.watch_folder_path = Path(config.watch_folder).resolve()
        self.paperless_client = PaperlessClient()
    
    def on_created(self, event) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path).resolve()
        
        # Validate file is within watch folder (security: prevent path traversal)
        if not self._is_file_in_watch_folder(file_path):
            self.logger.warning(f"File outside watch folder ignored: {file_path}")
            return
        
        self.logger.info(f"New file detected: {file_path}")
        
        # Check if the file matches our pattern
        if self._matches_pattern(file_path.name):
            self.logger.info(f"File matches pattern '{config.file_pattern}': {file_path}")
            self._process_scan_file(file_path)
    
    def on_moved(self, event) -> None:
        """Handle file move events (sometimes files are moved instead of created)."""
        if event.is_directory:
            return
        
        file_path = Path(event.dest_path).resolve()
        
        # Validate file is within watch folder (security: prevent path traversal)
        if not self._is_file_in_watch_folder(file_path):
            self.logger.warning(f"File outside watch folder ignored: {file_path}")
            return
        
        self.logger.info(f"File moved to: {file_path}")
        
        if self._matches_pattern(file_path.name):
            self.logger.info(f"Moved file matches pattern '{config.file_pattern}': {file_path}")
            self._process_scan_file(file_path)
    
    def _is_file_in_watch_folder(self, file_path: Path) -> bool:
        """
        Check if file is within the watch folder (security check).
        
        Prevents path traversal attacks by ensuring files are within the
        configured watch folder.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is within watch folder, False otherwise
        """
        try:
            resolved_file = file_path.resolve()
            resolved_watch = self.watch_folder_path.resolve()
            
            # Python 3.9+ has is_relative_to method
            try:
                return resolved_file.is_relative_to(resolved_watch)
            except AttributeError:
                # Python < 3.9 compatibility: use string comparison
                file_str = str(resolved_file)
                watch_str = str(resolved_watch)
                # Ensure paths use same separator and check prefix
                return file_str.startswith(watch_str) and len(file_str) > len(watch_str)
        except Exception as e:
            self.logger.debug(f"Error checking file path: {e}")
            return False
    
    def _matches_pattern(self, filename: str) -> bool:
        """
        Check if filename matches the configured pattern.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if filename matches pattern, False otherwise
        """
        return fnmatch.fnmatch(filename.lower(), config.file_pattern.lower())
    
    def _process_scan_file(self, file_path: Path) -> None:
        """
        Process a detected scan file.
        
        This orchestrates the workflow: wait for file completion,
        optionally rename, and upload to Paperless.
        
        Args:
            file_path: Path to the file to process
        """
        try:
            # Wait for file to be completely written
            if not wait_for_file_complete(file_path):
                self.logger.warning(f"File write timeout or file removed: {file_path}")
                return
            
            # Determine if we should rename the file
            if should_rename_file(file_path):
                # Rename the file with timestamp
                new_path = rename_with_timestamp(file_path)
                if new_path:
                    self.paperless_client.upload_document(new_path)
            else:
                # Upload directly without renaming
                self.logger.info(f"Uploading file without renaming: {file_path}")
                self.paperless_client.upload_document(file_path)
        
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
    
    # Backward compatibility methods for tests
    def _should_rename_file(self, file_path: Path) -> bool:
        """Backward compatibility wrapper for tests."""
        return should_rename_file(file_path)
    
    def _has_unique_name(self, file_path: Path) -> bool:
        """Backward compatibility wrapper for tests."""
        return has_unique_name(file_path)
    
    def _rename_with_timestamp(self, file_path: Path) -> Optional[Path]:
        """Backward compatibility wrapper for tests."""
        return rename_with_timestamp(file_path)
    
    def _wait_for_file_complete(self, file_path: Path, timeout: int = None) -> bool:
        """Backward compatibility wrapper for tests."""
        return wait_for_file_complete(file_path, timeout)
    
    def _can_access_file(self, file_path: Path) -> bool:
        """Backward compatibility wrapper for tests."""
        return can_access_file(file_path)
    
    def _upload_to_paperless(self, file_path: Path) -> bool:
        """Backward compatibility wrapper for tests."""
        return self.paperless_client.upload_document(file_path)

