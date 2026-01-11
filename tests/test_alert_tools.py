"""
Tests for alert-related agent tools.
"""

import pytest
import responses
from datetime import datetime
from unittest.mock import patch, MagicMock

from temperature_agent.tools.alerts import (
    send_alert,
    set_alert_threshold,
    get_alert_preferences,
)


@pytest.fixture
def sample_config():
    """Sample configuration."""
    return {
        "ntfy_topic": "test-alerts-12345",
        "freeze_threshold_f": 60.0,
        "heat_threshold_f": 70.0,
        "sensors": {
            "Channel 7": "Basement",
            "Channel 1": "Kitchen Pipes",
            "Channel 4": "Attic",
        }
    }


# === Tests for send_alert ===

class TestSendAlert:
    """Tests for the send_alert tool."""
    
    @responses.activate
    def test_sends_alert_to_ntfy(self, sample_config):
        """Should send alert to ntfy.sh with correct topic."""
        responses.add(
            responses.POST,
            "https://ntfy.sh/test-alerts-12345",
            status=200
        )
        
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            result = send_alert(
                title="Test Alert",
                message="This is a test message"
            )
        
        assert result["success"] == True
        assert len(responses.calls) == 1
    
    @responses.activate
    def test_includes_title_in_request(self, sample_config):
        """Should include title header in ntfy request."""
        responses.add(
            responses.POST,
            "https://ntfy.sh/test-alerts-12345",
            status=200
        )
        
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            send_alert(title="Freeze Warning", message="Basement is cold")
        
        request = responses.calls[0].request
        assert request.headers.get("Title") == "Freeze Warning"
    
    @responses.activate
    def test_includes_message_in_body(self, sample_config):
        """Should include message in request body."""
        responses.add(
            responses.POST,
            "https://ntfy.sh/test-alerts-12345",
            status=200
        )
        
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            send_alert(title="Test", message="Basement is 55°F")
        
        request = responses.calls[0].request
        assert "Basement is 55°F" in request.body.decode('utf-8')
    
    @responses.activate
    def test_sets_high_priority(self, sample_config):
        """Should set high priority for alerts."""
        responses.add(
            responses.POST,
            "https://ntfy.sh/test-alerts-12345",
            status=200
        )
        
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            send_alert(title="Urgent", message="Pipes freezing!", priority="high")
        
        request = responses.calls[0].request
        assert request.headers.get("Priority") == "high"
    
    @responses.activate
    def test_handles_send_failure(self, sample_config):
        """Should handle network errors gracefully."""
        responses.add(
            responses.POST,
            "https://ntfy.sh/test-alerts-12345",
            body=Exception("Connection failed")
        )
        
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            result = send_alert(title="Test", message="Test message")
        
        assert result["success"] == False
        assert "error" in result
    
    @responses.activate
    def test_sends_temperature_summary(self, sample_config):
        """Should be able to send a temperature summary alert."""
        responses.add(
            responses.POST,
            "https://ntfy.sh/test-alerts-12345",
            status=200
        )
        
        temps = {"Basement": 55.0, "Kitchen": 68.0, "Attic": 45.0}
        
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            result = send_alert(
                title="Temperature Summary",
                message="Current temps",
                temperatures=temps
            )
        
        request = responses.calls[0].request
        body = request.body.decode('utf-8')
        
        # Should include temperature data
        assert "Basement" in body or "55" in body


# === Tests for set_alert_threshold ===

class TestSetAlertThreshold:
    """Tests for the set_alert_threshold tool."""
    
    def test_sets_low_threshold_for_sensor(self, sample_config):
        """Should set a custom low threshold for a specific sensor."""
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            with patch('temperature_agent.tools.alerts.save_preference') as mock_save:
                result = set_alert_threshold(
                    sensor_name="Basement",
                    low_threshold=55.0
                )
        
        assert result["success"] == True
        mock_save.assert_called()
        # Verify the saved data
        call_args = mock_save.call_args
        assert "Basement" in str(call_args) or call_args[0][0] == "thresholds"
    
    def test_sets_high_threshold_for_sensor(self, sample_config):
        """Should set a custom high threshold for a specific sensor."""
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            with patch('temperature_agent.tools.alerts.save_preference') as mock_save:
                result = set_alert_threshold(
                    sensor_name="Attic",
                    high_threshold=85.0
                )
        
        assert result["success"] == True
    
    def test_sets_both_thresholds(self, sample_config):
        """Should be able to set both low and high thresholds."""
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            with patch('temperature_agent.tools.alerts.save_preference') as mock_save:
                result = set_alert_threshold(
                    sensor_name="Basement",
                    low_threshold=50.0,
                    high_threshold=80.0
                )
        
        assert result["success"] == True
    
    def test_validates_sensor_exists(self, sample_config):
        """Should validate that sensor exists in config."""
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            result = set_alert_threshold(
                sensor_name="NonExistentRoom",
                low_threshold=50.0
            )
        
        assert result["success"] == False
        assert "error" in result
    
    def test_validates_threshold_range(self, sample_config):
        """Should validate threshold is in reasonable range."""
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            # -100°F is unreasonable
            result = set_alert_threshold(
                sensor_name="Basement",
                low_threshold=-100.0
            )
        
        assert result["success"] == False
    
    def test_returns_confirmation_message(self, sample_config):
        """Should return a human-readable confirmation."""
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            with patch('temperature_agent.tools.alerts.save_preference'):
                result = set_alert_threshold(
                    sensor_name="Basement",
                    low_threshold=55.0
                )
        
        assert "message" in result
        assert "55" in result["message"] or "Basement" in result["message"]


# === Tests for get_alert_preferences ===

class TestGetAlertPreferences:
    """Tests for the get_alert_preferences tool."""
    
    def test_returns_default_thresholds(self, sample_config):
        """Should return default thresholds from config."""
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            with patch('temperature_agent.tools.alerts.load_preferences', return_value={}):
                result = get_alert_preferences()
        
        assert result["default_freeze_threshold"] == 60.0
        assert result["default_heat_threshold"] == 70.0
    
    def test_returns_custom_thresholds(self, sample_config):
        """Should return custom thresholds if set."""
        custom_prefs = {
            "thresholds": {
                "Basement": {"low": 55.0},
                "Attic": {"high": 85.0}
            }
        }
        
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            with patch('temperature_agent.tools.alerts.load_preferences', return_value=custom_prefs):
                result = get_alert_preferences()
        
        assert "sensor_thresholds" in result
        assert result["sensor_thresholds"]["Basement"]["low"] == 55.0
        assert result["sensor_thresholds"]["Attic"]["high"] == 85.0
    
    def test_returns_ntfy_topic(self, sample_config):
        """Should include ntfy topic for reference."""
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            with patch('temperature_agent.tools.alerts.load_preferences', return_value={}):
                result = get_alert_preferences()
        
        assert result["ntfy_topic"] == "test-alerts-12345"
    
    def test_returns_priority_sensors(self, sample_config):
        """Should return list of priority sensors if configured."""
        prefs = {
            "priority_sensors": ["Basement", "Kitchen Pipes"]
        }
        
        with patch('temperature_agent.tools.alerts.get_config', return_value=sample_config):
            with patch('temperature_agent.tools.alerts.load_preferences', return_value=prefs):
                result = get_alert_preferences()
        
        assert "priority_sensors" in result
        assert "Basement" in result["priority_sensors"]
