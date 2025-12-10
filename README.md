# HP Paperless Sync

A Python application that automatically monitors your HP printer's scan folder and seamlessly uploads scanned documents to Paperless-ngx. No more manual file management—just scan and forget!

## Overview

Tired of manually managing scanned documents from your HP printer? This application acts as your personal document courier, automatically:

1. **Watches** your HP printer's scan folder for new documents
2. **Intelligently renames** files when needed (only if they don't already have unique timestamps)
3. **Delivers** your scans directly to Paperless-ngx via API

Perfect for HP Envy, HP LaserJet, and other HP printers that save scans to a local folder. Works with both modern HP printers that generate unique filenames (like `hp_envy_to_paperless_22-02-2016_1110.pdf`) and legacy models that create generic names like `scan.pdf`.

## Features

- 🖨️ **HP Printer Optimized**: Designed specifically for HP printer scan workflows
- 👁️ **Real-time Monitoring**: Uses watchdog to instantly detect new scans
- 🧠 **Smart File Handling**: Only renames files when necessary, preserving unique filenames
- 📤 **Automatic Upload**: Seamlessly syncs to Paperless-ngx without manual intervention
- ⚙️ **Configurable**: Customize behavior via environment variables
- 🔒 **Robust**: Handles file completion detection and network errors gracefully
- 📝 **Comprehensive Logging**: Track all activity with detailed logs

## Requirements

- Python 3.8+
- HP Printer with scan-to-folder capability
- Paperless-ngx instance with API access
- Network access to your Paperless-ngx server

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd hp-paperless-sync
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment file and configure:
   ```bash
   cp env.example .env
   ```

5. Edit `.env` file with your settings:
   ```
   PAPERLESS_URL=http://192.168.0.45:8000
   PAPERLESS_TOKEN=your_api_token_here
   WATCH_FOLDER=C:\path\to\your\hp\scan\folder
   FILE_PATTERN=hp_envy_to_paperless_*.pdf
   ```

## Configuration

### Environment Variables

- `PAPERLESS_URL`: URL of your Paperless-ngx instance (default: http://192.168.0.45:8000)
- `PAPERLESS_TOKEN`: API token for authentication (required)
- `WATCH_FOLDER`: Path to your HP printer's scan folder (required)
- `FILE_PATTERN`: Pattern to match incoming HP scan files (default: `hp_envy_to_paperless_*.pdf`)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)
- `FILE_STABLE_TIME`: Seconds file size must remain stable before processing (default: 3)
- `FILE_TIMEOUT`: Maximum seconds to wait for file completion (default: 30)
- `AUTO_RENAME`: File renaming behavior - 'smart' (default), 'always', or 'never'
- `DELETE_AFTER_UPLOAD`: Set to 'true' to delete files after successful upload (default: false)
- `UPLOAD_TIMEOUT`: Timeout in seconds for upload requests (default: 30)
- `UPLOAD_RETRY_ATTEMPTS`: Number of retry attempts for failed uploads (default: 3)
- `UPLOAD_RETRY_DELAY`: Initial delay in seconds between retry attempts (default: 2.0)
- `RATE_LIMIT_DELAY`: Seconds to wait between uploads to prevent API overload (default: 0.5)

### Getting Paperless API Token

1. Log into your Paperless-ngx web interface
2. Navigate to Settings → API Auth Token → API Auth Token
3. Create a new token with appropriate permissions
4. Copy the token to your `.env` file

### HP Printer Setup

1. Configure your HP printer to scan to a folder on your computer
2. Note the exact folder path where scans are saved
3. Set `WATCH_FOLDER` in your `.env` to this path
4. Adjust `FILE_PATTERN` to match your HP printer's naming convention

## Usage

1. Activate the virtual environment (if not already activated):
   ```bash
   # On Linux/Mac:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

2. Run the application:
   ```bash
   python main.py
   ```

The application will:
1. Start monitoring your HP printer's scan folder
2. Detect new scans matching your configured pattern
3. Intelligently rename files only when needed
4. Automatically upload to Paperless-ngx
5. Log all activity for monitoring

To stop the application, press `Ctrl+C`.

## File Processing

### Smart Renaming (Default Behavior)

The application intelligently handles different HP printer models:

- **Modern HP Printers** with unique filenames (e.g., `hp_envy_to_paperless_22-09-2025_1110.pdf`) → Uploaded directly without renaming
- **Legacy HP Printers** with generic names (e.g., `scan.pdf`) → Renamed to `scan_20240322_143052.pdf` to prevent conflicts

### Renaming Behavior Options

- `AUTO_RENAME=smart` (default): Only rename files that don't have timestamps/dates
- `AUTO_RENAME=always`: Always rename all files with timestamps
- `AUTO_RENAME=never`: Never rename files, upload as-is

## Advanced Features

### Automatic Retry
The application automatically retries failed uploads with exponential backoff. Configure retry behavior with:
- `UPLOAD_RETRY_ATTEMPTS`: Number of retry attempts (default: 3)
- `UPLOAD_RETRY_DELAY`: Initial delay between retries in seconds (default: 2.0)

### File Cleanup
Set `DELETE_AFTER_UPLOAD=true` to automatically delete files after successful upload. This helps keep your scan folder clean.

### Rate Limiting
The application includes built-in rate limiting to prevent overwhelming the Paperless-ngx API. Adjust with `RATE_LIMIT_DELAY` (default: 0.5 seconds).

## Logging

Logs are written to both console and `app.log` file. Check the logs for:
- HP scan detection and processing events
- File renaming operations
- Upload status and errors (including retry attempts)
- Connection issues with Paperless-ngx

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the application has read/write access to your HP printer's scan folder
2. **Network Errors**: Verify Paperless-ngx URL and network connectivity
3. **API Errors**: Check your API token permissions in Paperless-ngx
4. **File Pattern Mismatch**: Verify `FILE_PATTERN` matches your HP printer's actual filename format

### Debug Mode

Set `LOG_LEVEL=DEBUG` in your `.env` file for detailed logging.

## License

MIT License - see LICENSE file for details.
