"""
Tests for temperature-related agent tools.

These tests define the expected behavior of the temperature tools
before implementation (TDD approach).
"""

import pytest
import json
import re
import responses
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# The module we'll implement
from temperature_agent.tools.temperature import (
    get_current_temperatures,
    get_coldest_sensor,
    get_warmest_sensor,
    get_24h_history,
    get_sensor_info,
)

# URL patterns for mocking (match with query params)
ECOWITT_REALTIME_URL = re.compile(r"https://api\.ecowitt\.net/api/v3/device/real_time.*")
ECOWITT_HISTORY_URL = re.compile(r"https://api\.ecowitt\.net/api/v3/device/history.*")


# === Test Fixtures ===

@pytest.fixture
def sample_config():
    """Sample configuration matching the user's actual config structure."""
    return {
        "latitude": 42.79,
        "longitude": -74.62,
        "freeze_threshold_f": 60.0,
        "heat_threshold_f": 70.0,
        "ntfy_topic": "test-alerts",
        "sensors": {
            "Channel 7": "Basement",
            "Channel 1": "Kitchen Pipes",
            "Channel 3": "Bedroom",
            "Channel 2": "Living Room",
            "Indoor": "Kitchen",
            "Channel 4": "Attic"
        },
        "ecowitt_application_key": "test-app-key",
        "ecowitt_api_key": "test-api-key",
        "ecowitt_mac": "AA:BB:CC:DD:EE:FF"
    }


@pytest.fixture
def mock_ecowitt_realtime_response():
    """Mock response from Ecowitt real-time API."""
    # Note: API returns temp_and_humidity_chN, not temp_chN
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "indoor": {
                "temperature": {"value": "68.5", "unit": "℉"}
            },
            "outdoor": {
                "temperature": {"value": "25.0", "unit": "℉"}
            },
            "temp_and_humidity_ch1": {
                "temperature": {"value": "61.2", "unit": "℉"}
            },
            "temp_and_humidity_ch2": {
                "temperature": {"value": "67.8", "unit": "℉"}
            },
            "temp_and_humidity_ch3": {
                "temperature": {"value": "66.5", "unit": "℉"}
            },
            "temp_and_humidity_ch4": {
                "temperature": {"value": "45.2", "unit": "℉"}
            },
            "temp_and_humidity_ch7": {
                "temperature": {"value": "58.1", "unit": "℉"}
            }
        }
    }


@pytest.fixture
def mock_ecowitt_history_response():
    """Mock response from Ecowitt history API for a single sensor."""
    # Timestamps for the last 24 hours
    now = int(datetime.now().timestamp())
    return {
        "code": 0,
        "msg": "success", 
        "data": {
            "temperature": {
                "unit": "℉",
                "list": {
                    str(now - 3600): "62.0",      # 1 hour ago
                    str(now - 7200): "58.5",      # 2 hours ago (low)
                    str(now - 10800): "65.0",     # 3 hours ago
                    str(now - 14400): "70.2",     # 4 hours ago (high)
                    str(now - 18000): "68.0",     # 5 hours ago
                }
            }
        }
    }


# === Tests for get_current_temperatures ===

class TestGetCurrentTemperatures:
    """Tests for the get_current_temperatures tool."""
    
    @responses.activate
    def test_returns_all_configured_sensors(self, sample_config, mock_ecowitt_realtime_response):
        """Should return temperatures for all sensors that have data."""
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json=mock_ecowitt_realtime_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_current_temperatures()
        
        # Should return dict with sensor names as keys
        assert isinstance(result, dict)
        
        # Should use friendly names from config, not channel names
        assert "Kitchen" in result  # Indoor -> Kitchen
        assert "Kitchen Pipes" in result  # Channel 1 -> Kitchen Pipes
        assert "Basement" in result  # Channel 7 -> Basement
        assert "Attic" in result  # Channel 4 -> Attic
        
        # Should NOT contain raw channel names
        assert "Channel 1" not in result
        assert "Indoor" not in result
    
    @responses.activate
    def test_returns_correct_temperature_values(self, sample_config, mock_ecowitt_realtime_response):
        """Should return accurate temperature values."""
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json=mock_ecowitt_realtime_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_current_temperatures()
        
        assert result["Kitchen"] == 68.5
        assert result["Kitchen Pipes"] == 61.2
        assert result["Attic"] == 45.2
        assert result["Basement"] == 58.1
    
    @responses.activate
    def test_handles_celsius_conversion(self, sample_config):
        """Should convert Celsius to Fahrenheit when needed."""
        celsius_response = {
            "code": 0,
            "data": {
                "indoor": {
                    "temperature": {"value": "20.0", "unit": "℃"}  # 20°C = 68°F
                }
            }
        }
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json=celsius_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_current_temperatures()
        
        assert result["Kitchen"] == 68.0  # 20°C = 68°F
    
    @responses.activate
    def test_handles_api_error(self, sample_config):
        """Should return empty dict on API error."""
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json={"code": 500, "msg": "Internal error"},
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_current_temperatures()
        
        assert result == {}
    
    @responses.activate
    def test_handles_network_error(self, sample_config):
        """Should return empty dict on network error."""
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            body=Exception("Connection failed")
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_current_temperatures()
        
        assert result == {}


# === Tests for get_coldest_sensor ===

class TestGetColdestSensor:
    """Tests for the get_coldest_sensor tool."""
    
    @responses.activate
    def test_returns_coldest_sensor(self, sample_config, mock_ecowitt_realtime_response):
        """Should return the sensor with the lowest temperature."""
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json=mock_ecowitt_realtime_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_coldest_sensor()
        
        # Attic is coldest at 45.2°F
        assert result["name"] == "Attic"
        assert result["temperature"] == 45.2
    
    @responses.activate
    def test_excludes_outdoor_sensor(self, sample_config, mock_ecowitt_realtime_response):
        """Should not include outdoor sensor in comparison (it's expected to be cold)."""
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json=mock_ecowitt_realtime_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_coldest_sensor()
        
        # Outdoor is 25°F but should be excluded
        assert result["name"] != "Outdoor"
    
    @responses.activate
    def test_returns_none_on_no_data(self, sample_config):
        """Should return None if no temperature data available."""
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json={"code": 0, "data": {}},
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_coldest_sensor()
        
        assert result is None


# === Tests for get_warmest_sensor ===

class TestGetWarmestSensor:
    """Tests for the get_warmest_sensor tool."""
    
    @responses.activate
    def test_returns_warmest_sensor(self, sample_config, mock_ecowitt_realtime_response):
        """Should return the sensor with the highest temperature."""
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json=mock_ecowitt_realtime_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_warmest_sensor()
        
        # Kitchen (Indoor) is warmest at 68.5°F
        assert result["name"] == "Kitchen"
        assert result["temperature"] == 68.5
    
    @responses.activate
    def test_excludes_outdoor_sensor(self, sample_config, mock_ecowitt_realtime_response):
        """Should not include outdoor sensor in comparison."""
        # Modify response to make outdoor warmest
        import copy
        hot_outdoor = copy.deepcopy(mock_ecowitt_realtime_response)
        hot_outdoor["data"]["outdoor"]["temperature"]["value"] = "95.0"
        
        responses.add(
            responses.GET,
            ECOWITT_REALTIME_URL,
            json=hot_outdoor,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_warmest_sensor()
        
        assert result["name"] != "Outdoor"


# === Tests for get_24h_history ===

class TestGet24hHistory:
    """Tests for the get_24h_history tool."""
    
    @responses.activate
    def test_returns_highs_and_lows(self, sample_config, mock_ecowitt_history_response):
        """Should return both high and low temperatures for each sensor."""
        # Add response that matches any history request
        responses.add(
            responses.GET,
            ECOWITT_HISTORY_URL,
            json=mock_ecowitt_history_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_24h_history()
        
        assert "lows" in result
        assert "highs" in result
        assert isinstance(result["lows"], dict)
        assert isinstance(result["highs"], dict)
    
    @responses.activate
    def test_includes_timestamps(self, sample_config, mock_ecowitt_history_response):
        """Should include timestamps for when highs/lows occurred."""
        responses.add(
            responses.GET,
            ECOWITT_HISTORY_URL,
            json=mock_ecowitt_history_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_24h_history()
        
        # Each entry should have both timestamp and temperature
        for sensor_name, data in result["lows"].items():
            assert "timestamp" in data
            assert "temperature" in data
            assert isinstance(data["timestamp"], datetime)
    
    @responses.activate  
    def test_calculates_correct_high_low(self, sample_config, mock_ecowitt_history_response):
        """Should correctly identify the highest and lowest temperatures."""
        responses.add(
            responses.GET,
            ECOWITT_HISTORY_URL,
            json=mock_ecowitt_history_response,
            status=200
        )
        
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_24h_history()
        
        # Based on mock data: low is 58.5, high is 70.2
        if "Kitchen" in result["lows"]:
            assert result["lows"]["Kitchen"]["temperature"] == 58.5
            assert result["highs"]["Kitchen"]["temperature"] == 70.2


# === Tests for get_sensor_info ===

class TestGetSensorInfo:
    """Tests for the get_sensor_info tool."""
    
    def test_returns_all_configured_sensors(self, sample_config):
        """Should return info about all configured sensors."""
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_sensor_info()
        
        assert isinstance(result, dict)
        assert "sensors" in result
        
        # Should have all 6 sensors
        assert len(result["sensors"]) == 6
    
    def test_includes_sensor_names_and_locations(self, sample_config):
        """Should include both raw names and friendly names."""
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_sensor_info()
        
        sensors = result["sensors"]
        
        # Should have mapping info
        assert any(s["name"] == "Basement" for s in sensors)
        assert any(s["name"] == "Attic" for s in sensors)
        assert any(s["name"] == "Kitchen" for s in sensors)
    
    def test_includes_thresholds(self, sample_config):
        """Should include alert thresholds."""
        with patch('temperature_agent.tools.temperature.get_config', return_value=sample_config):
            result = get_sensor_info()
        
        assert "freeze_threshold" in result
        assert "heat_threshold" in result
        assert result["freeze_threshold"] == 60.0
        assert result["heat_threshold"] == 70.0
