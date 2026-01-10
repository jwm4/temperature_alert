"""
Tests for weather forecast tool.
"""

import pytest
import re
import responses
from datetime import datetime, timedelta
from unittest.mock import patch

from temperature_agent.tools.forecast import get_forecast

# URL pattern for mocking (match with query params)
OPENMETEO_URL = re.compile(r"https://api\.open-meteo\.com/v1/forecast.*")


@pytest.fixture
def sample_config():
    """Sample configuration."""
    return {
        "latitude": 42.79,
        "longitude": -74.62,
        "freeze_threshold_f": 60.0,
        "heat_threshold_f": 70.0,
    }


@pytest.fixture
def mock_openmeteo_response():
    """Mock response from Open-Meteo forecast API."""
    now = datetime.now()
    times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(25)]
    
    # Create temperature pattern: starts at 30, drops to 22 at hour 8, rises to 45 at hour 14
    temps = [30, 28, 26, 24, 23, 22, 22, 23, 22, 25, 30, 35, 40, 44, 45, 44, 42, 38, 35, 32, 30, 28, 26, 25, 24]
    
    return {
        "hourly": {
            "time": times,
            "temperature_2m": temps
        }
    }


class TestGetForecast:
    """Tests for the get_forecast tool."""
    
    @responses.activate
    def test_returns_forecast_data(self, sample_config, mock_openmeteo_response):
        """Should return forecast with min/max temperatures."""
        responses.add(
            responses.GET,
            OPENMETEO_URL,
            json=mock_openmeteo_response,
            status=200
        )
        
        with patch('temperature_agent.tools.forecast.get_config', return_value=sample_config):
            result = get_forecast()
        
        assert "forecast_low" in result
        assert "forecast_high" in result
        assert "forecast_low_time" in result
        assert "forecast_high_time" in result
    
    @responses.activate
    def test_identifies_correct_low(self, sample_config, mock_openmeteo_response):
        """Should correctly identify the forecasted low temperature."""
        responses.add(
            responses.GET,
            OPENMETEO_URL,
            json=mock_openmeteo_response,
            status=200
        )
        
        with patch('temperature_agent.tools.forecast.get_config', return_value=sample_config):
            result = get_forecast()
        
        assert result["forecast_low"] == 22  # Minimum in our mock data
    
    @responses.activate
    def test_identifies_correct_high(self, sample_config, mock_openmeteo_response):
        """Should correctly identify the forecasted high temperature."""
        responses.add(
            responses.GET,
            OPENMETEO_URL,
            json=mock_openmeteo_response,
            status=200
        )
        
        with patch('temperature_agent.tools.forecast.get_config', return_value=sample_config):
            result = get_forecast()
        
        assert result["forecast_high"] == 45  # Maximum in our mock data
    
    @responses.activate
    def test_includes_current_outdoor_temp(self, sample_config, mock_openmeteo_response):
        """Should include the current outdoor temperature."""
        responses.add(
            responses.GET,
            OPENMETEO_URL,
            json=mock_openmeteo_response,
            status=200
        )
        
        with patch('temperature_agent.tools.forecast.get_config', return_value=sample_config):
            result = get_forecast()
        
        assert "current_outdoor" in result
        assert result["current_outdoor"] == 30  # First value in mock data
    
    @responses.activate
    def test_includes_freeze_warning(self, sample_config, mock_openmeteo_response):
        """Should include freeze warning if low is below threshold."""
        responses.add(
            responses.GET,
            OPENMETEO_URL,
            json=mock_openmeteo_response,
            status=200
        )
        
        with patch('temperature_agent.tools.forecast.get_config', return_value=sample_config):
            result = get_forecast()
        
        # 22°F is below freeze threshold of 60°F
        assert result["freeze_warning"] == True
    
    @responses.activate
    def test_includes_heat_warning(self, sample_config):
        """Should include heat warning if high is above threshold."""
        now = datetime.now()
        times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(25)]
        temps = [70, 72, 75, 78, 80, 82, 85, 82, 80, 78, 75, 72, 70, 68, 65, 63, 62, 61, 60, 60, 61, 62, 63, 65, 68]
        
        responses.add(
            responses.GET,
            OPENMETEO_URL,
            json={"hourly": {"time": times, "temperature_2m": temps}},
            status=200
        )
        
        with patch('temperature_agent.tools.forecast.get_config', return_value=sample_config):
            result = get_forecast()
        
        # 85°F is above heat threshold of 70°F
        assert result["heat_warning"] == True
    
    @responses.activate
    def test_handles_api_error(self, sample_config):
        """Should return error info on API failure."""
        responses.add(
            responses.GET,
            OPENMETEO_URL,
            json={"error": True, "reason": "Invalid coordinates"},
            status=400
        )
        
        with patch('temperature_agent.tools.forecast.get_config', return_value=sample_config):
            result = get_forecast()
        
        assert result is None or "error" in result
    
    @responses.activate
    def test_only_looks_at_next_24_hours(self, sample_config):
        """Should only consider the next 24 hours of forecast."""
        now = datetime.now()
        # 48 hours of data, but extreme temps only after 24 hours
        times = [(now + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(48)]
        temps = [50] * 24 + [0, 100] * 12  # Extreme temps only after 24h
        
        responses.add(
            responses.GET,
            OPENMETEO_URL,
            json={"hourly": {"time": times, "temperature_2m": temps}},
            status=200
        )
        
        with patch('temperature_agent.tools.forecast.get_config', return_value=sample_config):
            result = get_forecast()
        
        # Should only see temps from first 24 hours (all 50°F)
        assert result["forecast_low"] == 50
        assert result["forecast_high"] == 50
