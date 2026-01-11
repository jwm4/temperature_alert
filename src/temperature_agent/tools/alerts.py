"""
Alert-related agent tools.

Handles sending alerts via ntfy.sh and managing alert preferences/thresholds.
"""

import json
import logging
import requests
from pathlib import Path
from typing import Optional

from strands import tool

from temperature_agent.config import get_config, get_project_root

logger = logging.getLogger(__name__)

# Preferences file location
PREFERENCES_FILE = "agent_preferences.json"


def _get_preferences_path() -> Path:
    """Get the path to the preferences file."""
    return get_project_root() / PREFERENCES_FILE


def load_preferences() -> dict:
    """Load saved user preferences."""
    prefs_path = _get_preferences_path()
    try:
        if prefs_path.exists():
            with open(prefs_path, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error loading preferences: {e}")
    return {}


def save_preference(key: str, value) -> None:
    """Save a user preference."""
    prefs = load_preferences()
    prefs[key] = value
    
    prefs_path = _get_preferences_path()
    try:
        with open(prefs_path, 'w') as f:
            json.dump(prefs, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving preferences: {e}")
        raise


def _get_sensor_names() -> list:
    """Get list of valid sensor friendly names from config."""
    config = get_config()
    sensor_mapping = config.get("sensors", {})
    return list(sensor_mapping.values())


@tool
def send_alert(
    title: str,
    message: str,
    priority: str = "default",
    temperatures: Optional[dict] = None
) -> dict:
    """
    Send an alert notification via ntfy.sh.
    
    Args:
        title: Alert title
        message: Alert message body
        priority: Alert priority ("low", "default", "high", "urgent")
        temperatures: Optional dict of current temperatures to include
    
    Returns:
        dict: {"success": True} or {"success": False, "error": "..."}
    """
    config = get_config()
    topic = config.get("ntfy_topic")
    
    if not topic:
        return {"success": False, "error": "No ntfy_topic configured"}
    
    # Build message body
    body = message
    if temperatures:
        body += "\n\nCurrent Temperatures:"
        for sensor, temp in temperatures.items():
            body += f"\n  {sensor}: {temp}°F"
    
    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Title": title,
        "Priority": priority
    }
    
    try:
        response = requests.post(url, data=body.encode('utf-8'), headers=headers, timeout=30)
        response.raise_for_status()
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")
        return {"success": False, "error": str(e)}


@tool
def set_alert_threshold(
    sensor_name: str,
    low_threshold: Optional[float] = None,
    high_threshold: Optional[float] = None
) -> dict:
    """
    Set custom alert thresholds for a specific sensor.
    
    Args:
        sensor_name: Name of the sensor (e.g., "Basement")
        low_threshold: Temperature (°F) below which to alert
        high_threshold: Temperature (°F) above which to alert
    
    Returns:
        dict: {"success": True, "message": "..."} or {"success": False, "error": "..."}
    """
    # Validate sensor exists
    valid_sensors = _get_sensor_names()
    if sensor_name not in valid_sensors:
        return {
            "success": False,
            "error": f"Unknown sensor '{sensor_name}'. Valid sensors: {', '.join(valid_sensors)}"
        }
    
    # Validate threshold ranges (reasonable temperatures in Fahrenheit)
    if low_threshold is not None:
        if low_threshold < -50 or low_threshold > 150:
            return {
                "success": False,
                "error": f"Low threshold {low_threshold}°F is outside reasonable range (-50 to 150°F)"
            }
    
    if high_threshold is not None:
        if high_threshold < -50 or high_threshold > 150:
            return {
                "success": False,
                "error": f"High threshold {high_threshold}°F is outside reasonable range (-50 to 150°F)"
            }
    
    # Load current thresholds
    prefs = load_preferences()
    thresholds = prefs.get("thresholds", {})
    
    # Update threshold for this sensor
    if sensor_name not in thresholds:
        thresholds[sensor_name] = {}
    
    if low_threshold is not None:
        thresholds[sensor_name]["low"] = low_threshold
    if high_threshold is not None:
        thresholds[sensor_name]["high"] = high_threshold
    
    # Save
    try:
        save_preference("thresholds", thresholds)
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    # Build confirmation message
    parts = []
    if low_threshold is not None:
        parts.append(f"low threshold to {low_threshold}°F")
    if high_threshold is not None:
        parts.append(f"high threshold to {high_threshold}°F")
    
    message = f"Set {sensor_name} {' and '.join(parts)}"
    
    return {"success": True, "message": message}


@tool
def get_alert_preferences() -> dict:
    """
    Get current alert preferences and thresholds.
    
    Returns:
        dict: {
            "default_freeze_threshold": 60.0,
            "default_heat_threshold": 70.0,
            "sensor_thresholds": {"Basement": {"low": 55.0}, ...},
            "ntfy_topic": "...",
            "priority_sensors": ["Basement", "Kitchen Pipes"]
        }
    """
    config = get_config()
    prefs = load_preferences()
    
    return {
        "default_freeze_threshold": config.get("freeze_threshold_f", 60.0),
        "default_heat_threshold": config.get("heat_threshold_f", 70.0),
        "sensor_thresholds": prefs.get("thresholds", {}),
        "ntfy_topic": config.get("ntfy_topic", ""),
        "priority_sensors": prefs.get("priority_sensors", [])
    }
