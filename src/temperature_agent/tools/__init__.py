"""
Temperature Agent Tools Package.

This package contains the tools available to the temperature agent:
- temperature: Query temperature sensors
- forecast: Get weather forecasts
- alerts: Send alerts and manage thresholds
- memory: Alert history (house knowledge handled by AgentCore Memory)
"""

from temperature_agent.tools.temperature import (
    get_current_temperatures,
    get_coldest_sensor,
    get_warmest_sensor,
    get_24h_history,
    get_sensor_info,
)

from temperature_agent.tools.forecast import (
    get_forecast,
)

from temperature_agent.tools.alerts import (
    send_alert,
    set_alert_threshold,
    get_alert_preferences,
)

from temperature_agent.tools.memory import (
    get_alert_history,
    record_alert,
)

__all__ = [
    # Temperature tools
    "get_current_temperatures",
    "get_coldest_sensor",
    "get_warmest_sensor",
    "get_24h_history",
    "get_sensor_info",
    # Forecast tools
    "get_forecast",
    # Alert tools
    "send_alert",
    "set_alert_threshold",
    "get_alert_preferences",
    # Memory tools
    "get_alert_history",
    "record_alert",
]
