"""
Memory-related agent tools.

Alert history is stored locally as a simple log file.
House knowledge is handled automatically by AgentCore Memory.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from strands import tool

from temperature_agent.config import get_project_root

logger = logging.getLogger(__name__)

# Storage file path
ALERT_HISTORY_FILE = "alert_history.json"


def load_alert_history() -> list:
    """Load alert history from storage."""
    history_path = get_project_root() / ALERT_HISTORY_FILE
    try:
        if history_path.exists():
            with open(history_path, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error loading alert history: {e}")
    return []


def save_alert_history(history: list):
    """Save alert history to storage."""
    history_path = get_project_root() / ALERT_HISTORY_FILE
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2, default=str)


def clear_alert_history() -> dict:
    """
    Clear the alert history file.
    
    Returns:
        dict: {"success": True} or {"success": False, "error": "..."}
    """
    try:
        save_alert_history([])
        return {"success": True, "cleared": [ALERT_HISTORY_FILE]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_alert_history(
    limit: int = 20,
    sensor: Optional[str] = None,
    alert_type: Optional[str] = None
) -> dict:
    """
    Get history of alerts that have been sent.
    
    Args:
        limit: Maximum number of alerts to return
        sensor: Filter by sensor name
        alert_type: Filter by alert type ("freeze" or "heat")
    
    Returns:
        dict: {
            "alerts": [...],
            "total_count": 10
        }
    """
    history = load_alert_history()
    
    # Apply filters
    if sensor:
        history = [a for a in history if a.get("sensor") == sensor]
    if alert_type:
        history = [a for a in history if a.get("type") == alert_type]
    
    total_count = len(history)
    
    # Sort by timestamp (newest first)
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Apply limit
    alerts = history[:limit]
    
    return {
        "alerts": alerts,
        "total_count": total_count
    }


def record_alert(
    alert_type: str,
    sensor: str,
    temperature: float,
    message: str = ""
) -> dict:
    """
    Record an alert in history (called after sending an alert).
    
    Args:
        alert_type: "freeze" or "heat"
        sensor: Sensor name
        temperature: Temperature at time of alert
        message: Alert message
    
    Returns:
        dict: {"success": True} or {"success": False, "error": "..."}
    """
    try:
        history = load_alert_history()
        
        history.append({
            "timestamp": datetime.now().isoformat() + "Z",
            "type": alert_type,
            "sensor": sensor,
            "temperature": temperature,
            "message": message
        })
        
        # Keep only last 1000 alerts
        if len(history) > 1000:
            history = history[-1000:]
        
        save_alert_history(history)
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to record alert: {e}")
        return {"success": False, "error": str(e)}
