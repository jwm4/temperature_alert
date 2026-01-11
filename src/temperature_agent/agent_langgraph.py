"""
Temperature Agent - LangGraph Implementation.

This implementation uses LangGraph instead of Strands, allowing:
- Filtering of thinking/reasoning tags from model output
- More model flexibility (Nova Pro, GPT-OSS, etc.)
- Non-streaming mode for better control
"""

import re
import logging
from typing import Optional, Annotated

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool as langchain_tool
from langgraph.prebuilt import create_react_agent

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
)

logger = logging.getLogger(__name__)

# Default model configuration
DEFAULT_MODEL_ID = "qwen.qwen3-32b-v1:0"
DEFAULT_REGION = "us-east-1"

# Patterns to filter from model output
THINKING_PATTERNS = [
    r'<thinking>.*?</thinking>',
    r'<reasoning>.*?</reasoning>',
    r'<scratchpad>.*?</scratchpad>',
    r'<thought>.*?</thought>',
    r'<think>.*?</think>',  # DeepSeek R1 uses this
    r'<\|SYS\|>.*?(?=<\|SYS\|>|$)',  # Mistral internal markers
    r'<\|[A-Z]+\|>',  # Generic special tokens like <|SYS|>, <|END|>, etc.
]

# System prompt (same as Strands version)
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


def get_model_config() -> tuple[str, str]:
    """Get model ID and region from config.json or use defaults."""
    try:
        config = get_config()
        model_id = config.get("bedrock_model", DEFAULT_MODEL_ID)
        region = config.get("bedrock_region", DEFAULT_REGION)
        return model_id, region
    except Exception:
        return DEFAULT_MODEL_ID, DEFAULT_REGION


def filter_thinking_tags(text: str) -> str:
    """
    Remove thinking/reasoning tags from model output.
    
    This allows us to use models like Nova Pro and GPT-OSS that leak
    their chain-of-thought reasoning in XML tags.
    """
    if not text:
        return text
    
    result = text
    for pattern in THINKING_PATTERNS:
        result = re.sub(pattern, '', result, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up any extra whitespace left behind
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
    result = result.strip()
    
    return result


# --- LangChain Tool Wrappers ---
# These wrap the Strands tools to make them LangChain-compatible

def _unwrap(func):
    """Get the underlying function from a Strands @tool wrapper."""
    return func.__wrapped__ if hasattr(func, '__wrapped__') else func

@langchain_tool
def lc_get_current_temperatures() -> dict:
    """Get current temperature readings from all sensors in the house. Returns a dict mapping sensor names to temperatures in Fahrenheit."""
    return _unwrap(get_current_temperatures)()

@langchain_tool
def lc_get_coldest_sensor() -> dict:
    """Find the coldest indoor sensor. Returns a dict with 'sensor' name and 'temperature' in Fahrenheit."""
    return _unwrap(get_coldest_sensor)()

@langchain_tool
def lc_get_warmest_sensor() -> dict:
    """Find the warmest indoor sensor. Returns a dict with 'sensor' name and 'temperature' in Fahrenheit."""
    return _unwrap(get_warmest_sensor)()

@langchain_tool
def lc_get_24h_history() -> dict:
    """Get 24-hour temperature history showing highs and lows for each sensor."""
    return _unwrap(get_24h_history)()

@langchain_tool
def lc_get_sensor_info() -> dict:
    """Get information about all configured sensors including names and thresholds."""
    return _unwrap(get_sensor_info)()

@langchain_tool
def lc_get_forecast() -> dict:
    """Get the 24-hour weather forecast including current outdoor temp, forecasted high/low, and any freeze/heat warnings."""
    return _unwrap(get_forecast)()

@langchain_tool
def lc_send_alert(title: str, message: str) -> dict:
    """Send a push notification alert to the homeowner's phone via ntfy.sh.
    
    Args:
        title: The alert title (e.g., "Temperature Warning")
        message: The alert message body with details
    """
    return _unwrap(send_alert)(title, message)

@langchain_tool
def lc_set_alert_threshold(sensor_name: str, low_threshold: float = None, high_threshold: float = None) -> dict:
    """Set custom temperature alert thresholds for a specific sensor.
    
    Args:
        sensor_name: Name of the sensor (e.g., "Basement", "Attic")
        low_threshold: Temperature below which to trigger freeze alert (°F)
        high_threshold: Temperature above which to trigger heat alert (°F)
    """
    return _unwrap(set_alert_threshold)(sensor_name, low_threshold, high_threshold)

@langchain_tool
def lc_get_alert_preferences() -> dict:
    """Get current alert preferences including default and custom thresholds for each sensor."""
    return _unwrap(get_alert_preferences)()

@langchain_tool
def lc_store_house_knowledge(content: str, category: str = "general") -> dict:
    """Store information about the house for future reference (e.g., insulation details, construction, pipe locations).
    
    Args:
        content: The information to remember about the house
        category: Category for the knowledge (e.g., "insulation", "plumbing", "construction")
    """
    return _unwrap(store_house_knowledge)(content, category)

@langchain_tool
def lc_search_house_knowledge(query: str, limit: int = 3) -> list:
    """Search stored house knowledge for information relevant to a question.
    
    Args:
        query: What to search for (e.g., "attic insulation", "pipe locations")
        limit: Maximum number of results to return
    """
    return _unwrap(search_house_knowledge)(query, limit)

@langchain_tool
def lc_get_alert_history(limit: int = 5, sensor: str = None, alert_type: str = None) -> list:
    """Get history of past temperature alerts.
    
    Args:
        limit: Maximum number of alerts to return
        sensor: Filter by sensor name (optional)
        alert_type: Filter by type - "freeze" or "heat" (optional)
    """
    return _unwrap(get_alert_history)(limit, sensor, alert_type)


def get_langgraph_tools() -> list:
    """Get LangChain-compatible tools for the LangGraph agent."""
    return [
        lc_get_current_temperatures,
        lc_get_coldest_sensor,
        lc_get_warmest_sensor,
        lc_get_24h_history,
        lc_get_sensor_info,
        lc_get_forecast,
        lc_send_alert,
        lc_set_alert_threshold,
        lc_get_alert_preferences,
        lc_store_house_knowledge,
        lc_search_house_knowledge,
        lc_get_alert_history,
    ]


def create_langgraph_agent(
    model_id: str = None,
    region: str = None
):
    """
    Create a LangGraph ReAct agent.
    
    Args:
        model_id: Bedrock model ID to use (defaults to config.json setting)
        region: AWS region for Bedrock (defaults to config.json setting)
        
    Returns:
        LangGraph agent ready for conversation
    """
    # Get model config from config.json if not specified
    if model_id is None or region is None:
        config_model, config_region = get_model_config()
        model_id = model_id or config_model
        region = region or config_region
    
    # Create the LLM
    llm = ChatBedrock(
        model_id=model_id,
        region_name=region,
    )
    
    # Get tools
    tools = get_langgraph_tools()
    
    # Create ReAct agent with system prompt
    agent = create_react_agent(
        llm,
        tools,
        prompt=SYSTEM_PROMPT,
    )
    
    return agent


class LangGraphChat:
    """
    Chat wrapper for LangGraph agent that handles conversation state
    and filters thinking tags from responses.
    """
    
    def __init__(self, model_id: str = None, region: str = None):
        self.agent = create_langgraph_agent(model_id, region)
        self.messages = []
    
    def chat(self, user_message: str) -> str:
        """
        Send a message and get a response.
        
        Args:
            user_message: The user's message
            
        Returns:
            str: The agent's response (with thinking tags filtered)
        """
        # Add user message to history
        self.messages.append(HumanMessage(content=user_message))
        
        # Invoke agent
        result = self.agent.invoke({
            "messages": self.messages
        })
        
        # Extract the final AI message
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        if ai_messages:
            last_message = ai_messages[-1]
            response = last_message.content
            
            # Filter thinking tags
            response = filter_thinking_tags(response)
            
            # Update messages with cleaned response
            self.messages.append(AIMessage(content=response))
            
            return response
        
        return "I apologize, but I couldn't generate a response."
    
    def reset(self):
        """Clear conversation history."""
        self.messages = []


def generate_status_greeting() -> str:
    """
    Generate a status greeting showing current temperatures and forecast.
    
    This is shown when the user first connects to give them an immediate
    overview of conditions.
    """
    lines = ["🌡️ Temperature Assistant", ""]
    
    # Get current temperatures
    try:
        # Unwrap if needed
        temp_func = get_current_temperatures.__wrapped__ if hasattr(get_current_temperatures, '__wrapped__') else get_current_temperatures
        temps = temp_func()
    except Exception as e:
        logger.error(f"Error getting temperatures: {e}")
        temps = {}
    
    # Get forecast
    try:
        forecast_func = get_forecast.__wrapped__ if hasattr(get_forecast, '__wrapped__') else get_forecast
        forecast = forecast_func()
    except Exception as e:
        logger.error(f"Error getting forecast: {e}")
        forecast = None
    
    # Format temperature summary
    if temps:
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
            lines.append(f"The outside temperature is {outdoor:.0f}°F now")
            
            if low is not None and low_time:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(low_time.replace("Z", "+00:00"))
                    time_str = dt.strftime("%-I%p").lower()
                    lines[-1] += f" and the forecast shows a low of {low:.0f}°F tonight around {time_str}."
                except:
                    lines[-1] += f" and the forecast low is {low:.0f}°F."
            else:
                lines[-1] += "."
    
    lines.append("")
    lines.append("How can I help you?")
    
    return "\n".join(lines)
