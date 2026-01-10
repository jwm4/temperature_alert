"""
Temperature-related agent tools.

These tools allow the agent to query temperature data from Ecowitt sensors.
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Optional

from strands import tool

from temperature_agent.config import get_config

logger = logging.getLogger(__name__)

# Ecowitt API base URL
ECOWITT_API_BASE = "https://api.ecowitt.net/api/v3"


def _ecowitt_api_request(endpoint: str, extra_params: dict = None) -> Optional[dict]:
    """
    Make a request to the Ecowitt Cloud API.
    
    Args:
        endpoint: API endpoint (e.g., "device/real_time")
        extra_params: Additional query parameters
        
    Returns:
        dict: API response data, or None on error
    """
    config = get_config()
    
    params = {
        "application_key": config.get("ecowitt_application_key"),
        "api_key": config.get("ecowitt_api_key"),
        "mac": config.get("ecowitt_mac"),
    }
    if extra_params:
        params.update(extra_params)
    
    url = f"{ECOWITT_API_BASE}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors
        if data.get("code") != 0:
            logger.error(f"Ecowitt API error: {data.get('msg', 'Unknown error')}")
            return None
        
        return data.get("data", {})
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error calling Ecowitt API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling Ecowitt API: {e}")
        return None


def _parse_temperature(temp_data: dict) -> Optional[float]:
    """Parse temperature from Ecowitt API response, converting to Fahrenheit if needed."""
    if not temp_data or "value" not in temp_data:
        return None
    
    try:
        temp_f = float(temp_data.get("value", 0))
        # Convert if in Celsius
        if temp_data.get("unit") == "℃":
            temp_f = temp_f * 9/5 + 32
        return round(temp_f, 1)
    except (ValueError, TypeError):
        return None


@tool
def get_current_temperatures() -> dict:
    """
    Get current temperatures from all configured sensors.
    
    Returns:
        dict: Mapping of sensor friendly names to temperatures (°F)
        Example: {"Basement": 58.2, "Kitchen": 68.5, "Attic": 45.0}
    """
    config = get_config()
    sensor_names = config.get("sensors", {})
    temps = {}
    
    data = _ecowitt_api_request("device/real_time", {"call_back": "all"})
    if not data:
        return temps
    
    # Parse indoor temperature
    indoor = data.get("indoor", {})
    if "temperature" in indoor:
        temp = _parse_temperature(indoor["temperature"])
        if temp is not None:
            name = sensor_names.get("Indoor", "Indoor")
            temps[name] = temp
    
    # Parse outdoor temperature
    outdoor = data.get("outdoor", {})
    if "temperature" in outdoor:
        temp = _parse_temperature(outdoor["temperature"])
        if temp is not None:
            name = sensor_names.get("Outdoor", "Outdoor")
            temps[name] = temp
    
    # Parse channel sensors (temp_and_humidity_ch1, temp_and_humidity_ch2, etc.)
    # Note: API returns temp_and_humidity_chN, not temp_chN
    for i in range(1, 9):  # Channels 1-8
        ch_key = f"temp_and_humidity_ch{i}"
        if ch_key in data:
            ch_data = data[ch_key]
            if "temperature" in ch_data:
                temp = _parse_temperature(ch_data["temperature"])
                if temp is not None:
                    raw_name = f"Channel {i}"
                    name = sensor_names.get(raw_name, raw_name)
                    temps[name] = temp
    
    return temps


@tool
def get_coldest_sensor() -> Optional[dict]:
    """
    Get the indoor sensor with the lowest temperature.
    
    Excludes outdoor sensors from comparison.
    
    Returns:
        dict: {"name": "Attic", "temperature": 45.2} or None if no data
    """
    temps = get_current_temperatures()
    if not temps:
        return None
    
    # Get outdoor sensor name to exclude it
    config = get_config()
    sensor_names = config.get("sensors", {})
    outdoor_name = sensor_names.get("Outdoor", "Outdoor")
    
    # Filter out outdoor sensor
    indoor_temps = {k: v for k, v in temps.items() if k != outdoor_name}
    
    if not indoor_temps:
        return None
    
    coldest_name = min(indoor_temps, key=indoor_temps.get)
    return {
        "name": coldest_name,
        "temperature": indoor_temps[coldest_name]
    }


@tool
def get_warmest_sensor() -> Optional[dict]:
    """
    Get the indoor sensor with the highest temperature.
    
    Excludes outdoor sensors from comparison.
    
    Returns:
        dict: {"name": "Kitchen", "temperature": 68.5} or None if no data
    """
    temps = get_current_temperatures()
    if not temps:
        return None
    
    # Get outdoor sensor name to exclude it
    config = get_config()
    sensor_names = config.get("sensors", {})
    outdoor_name = sensor_names.get("Outdoor", "Outdoor")
    
    # Filter out outdoor sensor
    indoor_temps = {k: v for k, v in temps.items() if k != outdoor_name}
    
    if not indoor_temps:
        return None
    
    warmest_name = max(indoor_temps, key=indoor_temps.get)
    return {
        "name": warmest_name,
        "temperature": indoor_temps[warmest_name]
    }


@tool
def get_24h_history() -> dict:
    """
    Get 24-hour temperature history with highs and lows for each sensor.
    
    Returns:
        dict: {
            "lows": {"Basement": {"timestamp": datetime, "temperature": 55.1}, ...},
            "highs": {"Basement": {"timestamp": datetime, "temperature": 62.3}, ...}
        }
    """
    config = get_config()
    sensor_names = config.get("sensors", {})
    
    lows = {}
    highs = {}
    
    # Calculate time range for last 24 hours
    now = datetime.now()
    start = now - timedelta(hours=24)
    
    # Format dates for API
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    def process_temp_history(sensor_data: dict, sensor_name: str):
        """Process temperature history for a single sensor."""
        if "temperature" not in sensor_data:
            return None, None
        
        temp_history = sensor_data["temperature"]
        if not isinstance(temp_history, dict) or "list" not in temp_history:
            return None, None
        
        readings = temp_history.get("list", {})
        unit = temp_history.get("unit", "℉")
        
        if not readings:
            return None, None
        
        min_temp = float('inf')
        min_time = None
        max_temp = float('-inf')
        max_time = None
        
        for timestamp_str, temp_val in readings.items():
            try:
                temp_f = float(temp_val)
                if unit == "℃":
                    temp_f = temp_f * 9/5 + 32
                
                timestamp = datetime.fromtimestamp(int(timestamp_str))
                
                if temp_f < min_temp:
                    min_temp = temp_f
                    min_time = timestamp
                if temp_f > max_temp:
                    max_temp = temp_f
                    max_time = timestamp
            except (ValueError, TypeError):
                continue
        
        if min_time and max_time:
            return (
                {"timestamp": min_time, "temperature": round(min_temp, 1)},
                {"timestamp": max_time, "temperature": round(max_temp, 1)}
            )
        return None, None
    
    # Request history for each sensor type
    sensor_types = ["indoor", "outdoor"]
    for i in range(1, 9):
        sensor_types.append(f"temp_and_humidity_ch{i}")
    
    for sensor_type in sensor_types:
        data = _ecowitt_api_request("device/history", {
            "start_date": start_str,
            "end_date": end_str,
            "call_back": sensor_type,
        })
        
        if not data:
            continue
        
        sensor_data = data.get(sensor_type, data)
        
        # Determine display name
        if sensor_type == "indoor":
            name = sensor_names.get("Indoor", "Indoor")
        elif sensor_type == "outdoor":
            name = sensor_names.get("Outdoor", "Outdoor")
        elif sensor_type.startswith("temp_and_humidity_ch"):
            ch_num = sensor_type.replace("temp_and_humidity_ch", "")
            raw_name = f"Channel {ch_num}"
            name = sensor_names.get(raw_name, raw_name)
        else:
            name = sensor_type
        
        low, high = process_temp_history(sensor_data, name)
        if low:
            lows[name] = low
        if high:
            highs[name] = high
    
    return {"lows": lows, "highs": highs}


@tool
def get_sensor_info() -> dict:
    """
    Get information about configured sensors and thresholds.
    
    Returns:
        dict: {
            "sensors": [{"name": "Basement", "raw_name": "Channel 7"}, ...],
            "freeze_threshold": 60.0,
            "heat_threshold": 70.0
        }
    """
    config = get_config()
    sensor_mapping = config.get("sensors", {})
    
    sensors = []
    for raw_name, friendly_name in sensor_mapping.items():
        sensors.append({
            "name": friendly_name,
            "raw_name": raw_name
        })
    
    return {
        "sensors": sensors,
        "freeze_threshold": config.get("freeze_threshold_f", 60.0),
        "heat_threshold": config.get("heat_threshold_f", 70.0)
    }
