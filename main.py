"""
Main application for HP Paperless Sync.

This application monitors HP printer scan folders for new documents,
intelligently renames them when needed, and automatically uploads them
to Paperless-ngx via API.
"""

import logging

from folder_monitor import FolderMonitor


def main() -> int:
    """Main entry point of the application."""
    try:
        # Create and start the folder monitor
        monitor = FolderMonitor()
        monitor.start()
    
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("\nApplication interrupted by user.")
        return 0
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Application error: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
