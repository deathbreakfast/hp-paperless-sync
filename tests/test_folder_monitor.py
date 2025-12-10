"""Tests for FolderMonitor class."""

from unittest.mock import Mock, patch, MagicMock
import pytest
import requests

from folder_monitor import FolderMonitor
from config import DEFAULT_API_TEST_TIMEOUT


class TestConnectionTesting:
    """Test Paperless-ngx connection testing."""
    
    def test_successful_connection(self, mock_config, mock_requests):
        """Test successful connection to Paperless-ngx."""
        monitor = FolderMonitor()
        
        mock_requests['response'].status_code = 200
        
        # Should not raise exception
        monitor._test_paperless_connection()
        
        # Verify API call was made
        mock_requests['get'].assert_called_once()
        call_args = mock_requests['get'].call_args
        assert 'documents/' in call_args[0][0]  # URL contains documents endpoint
        assert call_args[1]['timeout'] == DEFAULT_API_TEST_TIMEOUT
    
    def test_connection_with_201_status(self, mock_config, mock_requests):
        """Test connection with 201 status (also valid 2xx)."""
        monitor = FolderMonitor()
        
        mock_requests['response'].status_code = 201
        
        # Should not raise exception (2xx is valid)
        monitor._test_paperless_connection()
    
    def test_connection_with_3xx_status(self, mock_config, mock_requests):
        """Test connection with 3xx status (warning but continues)."""
        monitor = FolderMonitor()
        
        mock_requests['response'].status_code = 301
        
        # Should not raise exception, but logs warning
        monitor._test_paperless_connection()
    
    def test_connection_with_4xx_status(self, mock_config, mock_requests):
        """Test connection with 4xx status (warning but continues)."""
        monitor = FolderMonitor()
        
        mock_requests['response'].status_code = 404
        
        # Should not raise exception, but logs warning
        monitor._test_paperless_connection()
    
    def test_connection_with_5xx_status(self, mock_config, mock_requests):
        """Test connection with 5xx status (warning but continues)."""
        monitor = FolderMonitor()
        
        mock_requests['response'].status_code = 500
        
        # Should not raise exception, but logs warning
        monitor._test_paperless_connection()
    
    def test_connection_network_error(self, mock_config, mock_requests):
        """Test connection failure with network error."""
        monitor = FolderMonitor()
        
        mock_requests['get'].side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        # Should not raise exception, but logs error
        monitor._test_paperless_connection()
    
    def test_connection_timeout_error(self, mock_config, mock_requests):
        """Test connection failure with timeout."""
        monitor = FolderMonitor()
        
        mock_requests['get'].side_effect = requests.exceptions.Timeout("Request timeout")
        
        # Should not raise exception, but logs error
        monitor._test_paperless_connection()
    
    def test_connection_uses_correct_headers(self, mock_config, mock_requests):
        """Test that connection test uses correct authentication headers."""
        monitor = FolderMonitor()
        
        mock_requests['response'].status_code = 200
        
        monitor._test_paperless_connection()
        
        # Verify headers were passed
        call_args = mock_requests['get'].call_args
        assert 'headers' in call_args[1]
        headers = call_args[1]['headers']
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Token test_token_12345'


class TestLifecycleMethods:
    """Test lifecycle methods (start/stop)."""
    
    def test_stop_without_observer(self, mock_config):
        """Test stop when observer is None."""
        monitor = FolderMonitor()
        monitor.observer = None
        
        # Should not raise exception
        monitor.stop()
        assert monitor._shutdown_requested is True
    
    def test_stop_with_observer(self, mock_config):
        """Test stop with active observer."""
        monitor = FolderMonitor()
        
        # Mock observer
        mock_observer = Mock()
        mock_observer.stop = Mock()
        mock_observer.join = Mock()
        monitor.observer = mock_observer
        
        monitor.stop()
        
        assert monitor._shutdown_requested is True
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5)
    
    @patch('folder_monitor.Observer')
    def test_start_initialization(self, mock_observer_class, mock_config):
        """Test start method initialization."""
        monitor = FolderMonitor()
        
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        # Mock the connection test and observer methods
        with patch.object(monitor, '_test_paperless_connection'):
            with patch('time.sleep', side_effect=KeyboardInterrupt()):
                try:
                    monitor.start()
                except KeyboardInterrupt:
                    pass
        
        # Verify observer was created and scheduled
        mock_observer_class.assert_called_once()
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()
    
    @patch('folder_monitor.Observer')
    def test_start_keyboard_interrupt(self, mock_observer_class, mock_config):
        """Test start method handles keyboard interrupt gracefully."""
        monitor = FolderMonitor()
        
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        with patch.object(monitor, '_test_paperless_connection'):
            with patch('time.sleep', side_effect=KeyboardInterrupt()):
                try:
                    monitor.start()
                except KeyboardInterrupt:
                    pass
        
        # Should call stop on interrupt
        mock_observer.stop.assert_called()
    
    @patch('folder_monitor.Observer')
    def test_start_exception_handling(self, mock_observer_class, mock_config):
        """Test start method exception handling."""
        monitor = FolderMonitor()
        
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        mock_observer.start.side_effect = Exception("Test error")
        
        with patch.object(monitor, '_test_paperless_connection'):
            with pytest.raises(Exception, match="Test error"):
                monitor.start()

