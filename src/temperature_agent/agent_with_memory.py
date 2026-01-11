"""
Temperature Agent with AgentCore Memory integration.

This module implements the conversational agent using Strands SDK with
AgentCore Memory for semantic search, automatic fact extraction, and
cross-session persistence.

PREREQUISITES:
1. Create an AgentCore Memory resource in AWS Console or via CLI:
   aws bedrock-agentcore-control create-memory --name "temperature-agent-memory"
   
2. Note the memory_id from the response and add it to config.json:
   "agentcore_memory_id": "temperature_agent-xxxxx"

3. Enable memory strategies (semantic) in the AWS Console
"""

import logging
import uuid

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager
)
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig
)

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
from temperature_agent.tools.memory import get_alert_history

logger = logging.getLogger(__name__)

# Default model configuration
DEFAULT_MODEL_ID = "qwen.qwen3-32b-v1:0"
DEFAULT_REGION = "us-east-1"

# For backwards compatibility with tests
MODEL_ID = DEFAULT_MODEL_ID

# System prompt
SYSTEM_PROMPT = """You are a helpful and friendly temperature monitoring assistant for a home.
Your primary purpose is to help the homeowner monitor temperatures throughout their house,
watch for freeze or heat risks, and manage temperature alerts.

## Your Capabilities

### Temperature Monitoring
- Check current temperatures from all sensors in the house
- Find the coldest or warmest sensor
- Show 24-hour temperature history with highs and lows
- Get weather forecasts to warn about upcoming temperature extremes

### Alert Management
- Send immediate alerts to the homeowner's phone via ntfy.sh
- Set custom temperature thresholds for specific sensors
- Show current alert preferences and thresholds
- Review the history of past alerts

### House Knowledge (Automatic via Memory)
- You automatically remember information the homeowner tells you about their house
- Facts about construction, insulation, layout, and concerns are stored automatically
- When answering questions, relevant memories are retrieved and shown to you
- Use the retrieved context to give better, more informed answers

## Personality & Style
- Be helpful, friendly, and concise
- Use specific temperatures and times when relevant
- Proactively mention concerns (e.g., if basement is unusually cold)
- When setting thresholds, suggest sensible defaults but respect user preferences

## Important Notes
- Temperature readings are in Fahrenheit (°F)
- The default freeze warning threshold is 60°F
- The default heat warning threshold is 70°F
- Outdoor sensors should be excluded when finding coldest/warmest indoor spots
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


def get_agent_tools() -> list:
    """Get the list of tools available to the agent."""
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
        # Alert history
        get_alert_history,
    ]


def create_agent(
    model_id: str = None,
    region: str = None,
    session_id: str = None,
    actor_id: str = "default_user"
) -> Agent:
    """
    Create and configure the temperature agent with AgentCore Memory.
    
    Args:
        model_id: Bedrock model ID to use (defaults to config.json setting)
        region: AWS region for Bedrock (defaults to config.json setting)
        session_id: Unique session ID (auto-generated if not provided)
        actor_id: User identifier for memory scoping
        
    Returns:
        Agent: Configured Strands agent with AgentCore Memory
        
    Raises:
        ValueError: If agentcore_memory_id is not configured
    """
    # Get configuration
    config = get_config()
    
    memory_id = config.get("agentcore_memory_id")
    if not memory_id:
        raise ValueError(
            "agentcore_memory_id not configured in config.json. "
            "Please create an AgentCore Memory resource and add its ID to config. "
            "See docs/agentcore_memory_setup.md for instructions."
        )
    
    # Get model config
    if model_id is None or region is None:
        config_model, config_region = get_model_config()
        model_id = model_id or config_model
        region = region or config_region
    
    # Generate session ID if not provided
    if session_id is None:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
    
    # Configure memory retrieval per namespace
    retrieval_config = {
        "/actor/{actorId}/house": RetrievalConfig(
            top_k=10,  # Return top 10 relevant memories
            relevance_score=0.3,  # Minimum relevance threshold
        )
    }
    
    # Create memory config
    memory_config = AgentCoreMemoryConfig(
        memory_id=memory_id,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config=retrieval_config,
    )
    
    # Create session manager with AgentCore Memory
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=memory_config,
        region_name=region,
    )
    
    # Configure the model
    model = BedrockModel(
        model_id=model_id,
        region_name=region
    )
    
    # Create agent with memory-enabled session manager
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=get_agent_tools(),
        session_manager=session_manager,
    )
    
    logger.info(f"Created agent with AgentCore Memory (session: {session_id})")
    
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
            lines.append(f"The outside temperature is {outdoor:.0f}°F now")
            
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
