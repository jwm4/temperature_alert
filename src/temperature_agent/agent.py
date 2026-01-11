"""
Temperature Agent - AI-powered temperature monitoring assistant.

This module implements the conversational agent using the Strands Agents SDK.
The agent can:
- Check current temperatures across all sensors
- Find the coldest/warmest locations
- Get weather forecasts with freeze/heat warnings
- Send alerts via ntfy.sh
- Set custom alert thresholds per sensor
- Remember and recall information about the house
- Track alert history
"""

import logging
from typing import Optional

from strands import Agent
from strands.models import BedrockModel

from temperature_agent.config import get_config
from temperature_agent.tools.temperature import (
    get_current_temperatures,
    get_coldest_sensor,
    get_warmest_sensor,
    get_24h_history,
    get_sensor_info,
)
from temperature_agent.tools.forecast import get_forecast
from temperature_agent.tools.alerts import (
    send_alert,
    set_alert_threshold,
    get_alert_preferences,
)
from temperature_agent.tools.memory import (
    store_house_knowledge,
    search_house_knowledge,
    get_alert_history,
    record_alert,
)

logger = logging.getLogger(__name__)

# Default model configuration (can be overridden in config.json)
DEFAULT_MODEL_ID = "qwen.qwen3-32b-v1:0"
DEFAULT_REGION = "us-east-1"


def get_model_config() -> tuple[str, str]:
    """Get model ID and region from config.json or use defaults."""
    try:
        config = get_config()
        model_id = config.get("bedrock_model", DEFAULT_MODEL_ID)
        region = config.get("bedrock_region", DEFAULT_REGION)
        return model_id, region
    except Exception:
        return DEFAULT_MODEL_ID, DEFAULT_REGION


# For backwards compatibility
MODEL_ID = DEFAULT_MODEL_ID

# System prompt defining the agent's persona and capabilities
SYSTEM_PROMPT = """You are a helpful and friendly temperature monitoring assistant for a home. 
Your primary purpose is to help the homeowner monitor temperatures throughout their house, 
watch for freeze or heat risks, and manage temperature alerts.

## Your Capabilities

### Temperature Monitoring
- You can check current temperatures from all sensors in the house
- You can find the coldest or warmest sensor
- You can show 24-hour temperature history with highs and lows
- You can get weather forecasts to warn about upcoming temperature extremes

### Alert Management
- You can send immediate alerts to the homeowner's phone via ntfy.sh
- You can set custom temperature thresholds for specific sensors
- You can show current alert preferences and thresholds
- You can review the history of past alerts

### House Knowledge
- You can remember information the homeowner tells you about their house
  (construction, insulation, layout, specific concerns)
- You use this knowledge to give better, more contextual advice
- When asked "why" questions about temperature patterns, you'll search your 
  knowledge base for relevant context

## Personality & Style
- Be helpful, friendly, and concise
- Use specific temperatures and times when relevant
- Proactively mention concerns (e.g., if basement is unusually cold)
- When setting thresholds, suggest sensible defaults but respect user preferences
- If you notice patterns or anomalies, mention them

## Important Notes
- Temperature readings are in Fahrenheit (°F)
- The default freeze warning threshold is 60°F
- The default heat warning threshold is 70°F  
- Outdoor sensors should be excluded when finding coldest/warmest indoor spots
- When the user teaches you something about their house, store it for future reference

## How to Handle Different Query Types

For temperature queries like "Which room is coldest?":
- Call get_coldest_sensor, then respond with the room name and temperature

For alert requests like "Send me an alert about [room]":
- Get the current temperature, then call send_alert with a helpful message

When the user teaches you something about their house:
- Call store_house_knowledge to save it, then confirm you'll remember it

For analytical questions like "Why is [room] so cold?":
- Search house knowledge for relevant context, check temps and forecast,
  then provide analysis based ONLY on what you actually find stored

IMPORTANT: Only reference house knowledge that you actually retrieve from
search_house_knowledge. Do not assume or invent information about the house.
"""


def get_agent_tools() -> list:
    """
    Get the list of tools available to the agent.
    
    Returns:
        list: List of tool functions the agent can use
    """
    return [
        # Temperature tools
        get_current_temperatures,
        get_coldest_sensor,
        get_warmest_sensor,
        get_24h_history,
        get_sensor_info,
        # Forecast tools
        get_forecast,
        # Alert tools
        send_alert,
        set_alert_threshold,
        get_alert_preferences,
        # Memory tools
        store_house_knowledge,
        search_house_knowledge,
        get_alert_history,
    ]


def create_agent(
    model_id: str = None,
    region: str = None
) -> Agent:
    """
    Create and configure the temperature monitoring agent.
    
    Args:
        model_id: Bedrock model ID to use (defaults to config.json setting)
        region: AWS region for Bedrock (defaults to config.json setting)
        
    Returns:
        Agent: Configured Strands agent ready for conversation
    """
    # Get model config from config.json if not specified
    if model_id is None or region is None:
        config_model, config_region = get_model_config()
        model_id = model_id or config_model
        region = region or config_region
    
    # Configure the model
    model = BedrockModel(
        model_id=model_id,
        region_name=region
    )
    
    # Create agent with tools
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=get_agent_tools()
    )
    
    return agent


def generate_status_greeting() -> str:
    """
    Generate a status greeting showing current temperatures and forecast.
    
    This is shown when the user first connects to give them an immediate
    overview of conditions.
    
    Returns:
        str: Formatted status greeting
    """
    lines = ["🌡️ Temperature Assistant", ""]
    
    # Get current temperatures
    try:
        temps = get_current_temperatures()
    except Exception as e:
        logger.error(f"Error getting temperatures: {e}")
        temps = {}
    
    # Get forecast
    try:
        forecast = get_forecast()
    except Exception as e:
        logger.error(f"Error getting forecast: {e}")
        forecast = None
    
    # Format temperature summary
    if temps:
        # Find sensors that are concerning (outside normal range)
        concerning = []
        normal_temps = []
        
        for sensor, temp in temps.items():
            if temp < 55:
                concerning.append(f"the {sensor.lower()} is {temp:.0f}°F")
            elif temp > 80:
                concerning.append(f"the {sensor.lower()} is {temp:.0f}°F")
            else:
                normal_temps.append(temp)
        
        if normal_temps:
            avg_temp = sum(normal_temps) / len(normal_temps)
            if concerning:
                lines.append(f"Most of your sensors are in the mid {int(avg_temp // 10) * 10}'s but {' and '.join(concerning)}.")
            else:
                lines.append(f"All sensors are reading normally, averaging around {avg_temp:.0f}°F.")
        elif concerning:
            lines.append(f"Note: {' and '.join(concerning)}.")
    else:
        lines.append("Unable to retrieve current temperatures.")
    
    # Format forecast
    if forecast:
        outdoor = forecast.get("current_outdoor")
        low = forecast.get("forecast_low")
        low_time = forecast.get("forecast_low_time", "")
        
        if outdoor is not None:
            lines.append("")
            lines.append(f"The outside temperature is {outdoor:.0f}°F now", )
            
            if low is not None and low_time:
                # Parse time for display
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(low_time.replace("Z", "+00:00"))
                    time_str = dt.strftime("%-I%p").lower()  # e.g., "3am"
                    lines[-1] += f" and the forecast shows a low of {low:.0f}°F tonight around {time_str}."
                except:
                    lines[-1] += f" and the forecast low is {low:.0f}°F."
            else:
                lines[-1] += "."
    
    lines.append("")
    lines.append("How can I help you?")
    
    return "\n".join(lines)


# Convenience function for interactive use
def chat(message: str, agent: Optional[Agent] = None) -> str:
    """
    Send a message to the agent and get a response.
    
    Args:
        message: User's message
        agent: Optional pre-created agent (creates new one if not provided)
        
    Returns:
        str: Agent's response
    """
    if agent is None:
        agent = create_agent()
    
    response = agent(message)
    return str(response)
