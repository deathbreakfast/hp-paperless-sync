"""
File processing utilities for HP Paperless Sync.

This module contains utilities for file renaming, completion detection,
and other file processing operations.
"""

import re
import time
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from config import config


logger = logging.getLogger(__name__)


def should_rename_file(file_path: Path) -> bool:
    """
    Determine if a file should be renamed based on configuration and file name.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file should be renamed, False otherwise
    """
    if config.auto_rename == 'always':
        return True
    elif config.auto_rename == 'never':
        return False
    else:  # 'smart' mode - default
        # Don't rename if file already has a unique name
        return not has_unique_name(file_path)


def has_unique_name(file_path: Path) -> bool:
    """
    Check if the file already has a unique name (contains date/timestamp).
    This avoids unnecessary renaming for files that already have unique names.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file has a unique name pattern, False otherwise
    """
    filename = file_path.name.lower()
    
    # Check for various date/timestamp patterns commonly used by scanners
    patterns = [
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY or MM-DD-YYYY
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        r'\d{2}_\d{2}_\d{4}',  # DD_MM_YYYY or MM_DD_YYYY
        r'\d{4}_\d{2}_\d{2}',  # YYYY_MM_DD
        r'\d{8}',              # YYYYMMDD
        r'\d{4}\d{2}\d{2}_\d{4}',  # YYYYMMDD_HHMM
        r'\d{2}-\d{2}-\d{4}_\d{4}',  # DD-MM-YYYY_HHMM
    ]
    
    for pattern in patterns:
        if re.search(pattern, filename):
            logger.debug(f"File has unique name pattern '{pattern}': {filename}")
            return True
    
    return False


def rename_with_timestamp(file_path: Path) -> Optional[Path]:
    """
    Rename file with timestamp to prevent conflicts.
    
    Args:
        file_path: Path to the file to rename
        
    Returns:
        New Path if rename succeeded, None otherwise
    """
    try:
        timestamp = datetime.now().strftime(config.timestamp_format)
        
        # Extract base name and extension
        stem = file_path.stem
        suffix = file_path.suffix or '.pdf'  # Default to .pdf if no extension
        
        # Create new filename
        new_name = f"{stem}_{timestamp}{suffix}"
        new_path = file_path.parent / new_name
        
        # Rename the file
        file_path.rename(new_path)
        logger.info(f"Renamed file: {file_path} -> {new_path}")
        
        return new_path
    
    except Exception as e:
        logger.error(f"Error renaming file {file_path}: {e}")
        return None


def wait_for_file_complete(file_path: Path, timeout: int = None) -> bool:
    """
    Wait for a file to be completely written by monitoring its size.
    Returns True if file is stable, False if timeout or file removed.
    
    Args:
        file_path: Path to the file to monitor
        timeout: Maximum seconds to wait (uses config default if None)
        
    Returns:
        True if file is stable and ready, False otherwise
    """
    logger.debug(f"Waiting for file to complete writing: {file_path}")
    
    if timeout is None:
        timeout = config.file_timeout
    
    stable_duration = 0
    required_stable_time = config.file_stable_time  # seconds file size must remain stable
    check_interval = 1  # check every second
    last_size = -1
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if file still exists
            if not file_path.exists():
                logger.debug(f"File no longer exists: {file_path}")
                return False
            
            # Get current file size
            current_size = file_path.stat().st_size
            
            # Check if file size has stabilized
            if current_size == last_size and current_size > 0:
                stable_duration += check_interval
                if stable_duration >= required_stable_time:
                    # Additional check: try to open the file exclusively
                    if can_access_file(file_path):
                        logger.info(f"File is ready for processing: {file_path} ({current_size} bytes)")
                        return True
            else:
                stable_duration = 0
                last_size = current_size
                logger.debug(f"File size changed to {current_size} bytes, resetting stability timer")
            
            time.sleep(check_interval)
        
        except OSError as e:
            logger.debug(f"Error checking file {file_path}: {e}")
            time.sleep(check_interval)
    
    logger.warning(f"Timeout waiting for file to stabilize: {file_path}")
    return False


def can_access_file(file_path: Path) -> bool:
    """
    Check if we can access the file for reading (indicates writing is complete).
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file is accessible, False otherwise
    """
    try:
        # Try to open the file in read mode to check if it's accessible
        with open(file_path, 'rb') as f:
            # Try to read a small chunk to ensure it's not locked
            f.read(config.file_read_chunk_size)
        return True
    except (OSError, IOError, PermissionError) as e:
        logger.debug(f"File not yet accessible: {file_path} - {e}")
        return False

