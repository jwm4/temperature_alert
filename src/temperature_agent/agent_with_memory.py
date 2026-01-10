"""
Temperature Agent with AgentCore Memory integration.

This module implements the conversational agent using Strands SDK with
AgentCore Memory for semantic search, automatic fact extraction, and
cross-session persistence.

PREREQUISITES:
1. Create an AgentCore Memory resource in AWS Console or via CLI:
   aws bedrock-agentcore create-memory --memory-name "temperature-agent-memory"
   
2. Note the memory_id from the response and add it to config.json:
   "agentcore_memory_id": "arn:aws:bedrock-agentcore:us-east-1:123456789:memory/abc123"

3. Enable memory strategies (semantic, user_preference) in the AWS Console
"""

import logging
import uuid
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
    get_alert_history,
)

logger = logging.getLogger(__name__)

# Default model configuration
DEFAULT_MODEL_ID = "qwen.qwen3-32b-v1:0"
DEFAULT_REGION = "us-east-1"

# System prompt - simplified since AgentCore handles memory
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
        # Alert history (memory tools replaced by AgentCore)
        get_alert_history,
        # Note: store_house_knowledge and search_house_knowledge are NOT needed
        # AgentCore Memory handles this automatically via semantic strategy
    ]


def create_agent_with_memory(
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
            "Please create an AgentCore Memory resource and add its ID to config."
        )
    
    # Get model config
    if model_id is None or region is None:
        config_model, config_region = get_model_config()
        model_id = model_id or config_model
        region = region or config_region
    
    # Generate session ID if not provided
    if session_id is None:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
    
    # Import AgentCore Memory integration
    from bedrock_agentcore.memory.integrations.strands.session_manager import (
        AgentCoreMemorySessionManager
    )
    from bedrock_agentcore.memory.integrations.strands.config import (
        AgentCoreMemoryConfig,
        RetrievalConfig
    )
    
    # Configure memory retrieval per namespace
    # The retrieval_config is a dict mapping namespace patterns to RetrievalConfig
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
        session_manager=session_manager,  # This enables AgentCore Memory!
    )
    
    logger.info(f"Created agent with AgentCore Memory (session: {session_id})")
    
    return agent


def create_agent_without_memory(
    model_id: str = None,
    region: str = None
) -> Agent:
    """
    Create agent without AgentCore Memory (fallback for local development).
    
    Uses the original local file-based memory from memory.py.
    """
    from temperature_agent.tools.memory import store_house_knowledge, search_house_knowledge
    
    if model_id is None or region is None:
        config_model, config_region = get_model_config()
        model_id = model_id or config_model
        region = region or config_region
    
    model = BedrockModel(
        model_id=model_id,
        region_name=region
    )
    
    # Include local memory tools
    tools = get_agent_tools() + [store_house_knowledge, search_house_knowledge]
    
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )
    
    return agent


def create_agent(
    model_id: str = None,
    region: str = None,
    session_id: str = None,
    actor_id: str = "default_user",
    use_agentcore_memory: bool = None
) -> Agent:
    """
    Create agent with automatic memory backend selection.
    
    If agentcore_memory_id is configured, uses AgentCore Memory.
    Otherwise, falls back to local file-based memory.
    
    Args:
        model_id: Bedrock model ID
        region: AWS region
        session_id: Session ID (for AgentCore Memory)
        actor_id: User ID (for AgentCore Memory)
        use_agentcore_memory: Force AgentCore Memory on/off (None = auto-detect)
    """
    config = get_config()
    
    # Auto-detect whether to use AgentCore Memory
    if use_agentcore_memory is None:
        use_agentcore_memory = bool(config.get("agentcore_memory_id"))
    
    if use_agentcore_memory:
        logger.info("Using AgentCore Memory")
        return create_agent_with_memory(
            model_id=model_id,
            region=region,
            session_id=session_id,
            actor_id=actor_id
        )
    else:
        logger.info("Using local file-based memory")
        return create_agent_without_memory(
            model_id=model_id,
            region=region
        )


# Re-export generate_status_greeting from original agent
from temperature_agent.agent import generate_status_greeting
