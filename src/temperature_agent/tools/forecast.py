"""
Weather forecast agent tool.

Uses Open-Meteo API to get weather forecasts.
"""

import logging
import requests
from datetime import datetime
from typing import Optional

from strands import tool

from temperature_agent.config import get_config

logger = logging.getLogger(__name__)

# Open-Meteo API base URL
OPENMETEO_API_BASE = "https://api.open-meteo.com/v1/forecast"


@tool
def get_forecast() -> Optional[dict]:
    """
    Get 24-hour weather forecast including predicted highs and lows.
    
    Returns:
        dict: {
            "current_outdoor": 25.0,
            "forecast_low": 22.0,
            "forecast_low_time": "2026-01-10T03:00",
            "forecast_high": 35.0,
            "forecast_high_time": "2026-01-10T14:00",
            "freeze_warning": True,
            "heat_warning": False
        }
        or None on error
    """
    config = get_config()
    
    lat = config.get("latitude")
    lon = config.get("longitude")
    freeze_threshold = config.get("freeze_threshold_f", 60.0)
    heat_threshold = config.get("heat_threshold_f", 70.0)
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "temperature_unit": "fahrenheit",
        "timezone": "auto"
    }
    
    try:
        response = requests.get(OPENMETEO_API_BASE, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching forecast: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching forecast: {e}")
        return None
    
    # Check for API error response
    if data.get("error"):
        logger.error(f"Open-Meteo API error: {data.get('reason', 'Unknown')}")
        return None
    
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    
    if not times or not temps:
        logger.error("No forecast data returned")
        return None
    
    # Get current outdoor temp (first reading)
    current_outdoor = temps[0] if temps else None
    
    # Find min/max in next 24 hours only
    now = datetime.now()
    min_temp = float('inf')
    min_time = None
    max_temp = float('-inf')
    max_time = None
    
    future_count = 0
    for time_str, temp in zip(times, temps):
        try:
            t = datetime.fromisoformat(time_str)
            # Only look at current and future times, up to 24 hours
            if t >= now.replace(minute=0, second=0, microsecond=0):
                if future_count < 24:
                    if temp < min_temp:
                        min_temp = temp
                        min_time = time_str
                    if temp > max_temp:
                        max_temp = temp
                        max_time = time_str
                    future_count += 1
                else:
                    # We've seen 24 future hours, stop
                    break
        except (ValueError, TypeError):
            continue
    
    # Handle case where no future data found (shouldn't happen with real API)
    if min_time is None or max_time is None:
        # Fall back to first 24 positions
        for time_str, temp in zip(times[:24], temps[:24]):
            if temp < min_temp:
                min_temp = temp
                min_time = time_str
            if temp > max_temp:
                max_temp = temp
                max_time = time_str
    
    # Determine warnings
    freeze_warning = min_temp < freeze_threshold if min_temp != float('inf') else False
    heat_warning = max_temp > heat_threshold if max_temp != float('-inf') else False
    
    return {
        "current_outdoor": current_outdoor,
        "forecast_low": min_temp if min_temp != float('inf') else None,
        "forecast_low_time": min_time,
        "forecast_high": max_temp if max_temp != float('-inf') else None,
        "forecast_high_time": max_time,
        "freeze_warning": freeze_warning,
        "heat_warning": heat_warning
    }
