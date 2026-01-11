"""
AgentCore Runtime entry point for the Temperature Agent.

This is the main entry point for deploying to AgentCore Runtime.
Located at the project root to simplify the Python path.
"""

import sys
import os

# Add src to path for our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
from datetime import datetime

from bedrock_agentcore import BedrockAgentCoreApp

# Now import our modules
from temperature_agent.agent_with_memory import create_agent, generate_status_greeting

logger = logging.getLogger(__name__)

# Create the AgentCore Runtime app
app = BedrockAgentCoreApp()

# Agent cache
_agents = {}


def get_or_create_agent(session_id: str):
    """Get or create an agent for a session."""
    if session_id not in _agents:
        logger.info(f"Creating new agent for session: {session_id}")
        _agents[session_id] = create_agent(session_id=session_id)
    return _agents[session_id]


@app.entrypoint
async def handler(event: dict):
    """Handle incoming requests from AgentCore Runtime (async for streaming)."""
    session_id = event.get("session_id", "default_session")
    action = event.get("action", "chat")
    
    if action == "status":
        try:
            greeting = generate_status_greeting()
        except Exception as e:
            logger.error(f"Error generating status: {e}")
            greeting = "🌡️ Temperature Assistant\n\nUnable to fetch current status."
        
        yield {
            "response": greeting,
            "action": "status",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    elif action == "help":
        yield {
            "response": """🌡️ Temperature Agent Help

I can help you with:
- **Check temperatures**: "What's the current temperature?"
- **Find extremes**: "Which room is coldest?"
- **View history**: "Show me the last 24 hours"
- **Weather forecast**: "What's the forecast?"
- **Send alerts**: "Send me an alert about the basement"
- **Set thresholds**: "Alert me if the basement drops below 50°F"

Just ask in natural language!""",
            "action": "help",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    else:
        prompt = event.get("prompt", "")
        
        if not prompt:
            yield {
                "response": "Please provide a prompt.",
                "error": "missing_prompt",
            }
            return
        
        try:
            agent = get_or_create_agent(session_id)
            response = agent(prompt)
            response_text = str(response)
            
            yield {
                "response": response_text,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            yield {
                "response": f"Sorry, I encountered an error: {str(e)}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


@app.ping
def health_check():
    """Health check for AgentCore Runtime."""
    from bedrock_agentcore.runtime.models import PingStatus
    return PingStatus.HEALTHY


# Keep this for Strands agent streaming (future enhancement)
# @app.entrypoint
# async def streaming_handler(payload):
#     """Streaming handler for real-time responses."""
#     prompt = payload.get("prompt", "")
#     agent = get_or_create_agent("streaming_session")
#     stream = agent.stream_async(prompt)
#     async for event in stream:
#         if "data" in event:
#             yield event["data"]


if __name__ == "__main__":
    app.run()
