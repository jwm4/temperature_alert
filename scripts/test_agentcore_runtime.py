"""
Minimal test to understand AgentCore Runtime interface.

This file demonstrates the bare minimum needed to run an agent
on AgentCore Runtime. We'll use this to learn the interface
before converting our real agent.

Run with:
    cd /Users/bmurdock/git/temperature_alert
    source venv/bin/activate
    
    # Configure this as an agent
    agentcore configure -e scripts/test_agentcore_runtime.py -n test_agent
    
    # Run locally
    agentcore dev
    
    # Test in another terminal
    curl http://localhost:8080/ping
    curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "Hello!"}'
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Create the AgentCore app
app = BedrockAgentCoreApp()


@app.entrypoint
def handler(event: dict) -> dict:
    """
    Handle incoming requests.
    
    AgentCore Runtime calls this function for each request.
    The 'event' contains the request payload.
    
    Args:
        event: Request payload (typically {"prompt": "..."})
        
    Returns:
        Response dict with the agent's output
    """
    # Extract the prompt from the event
    prompt = event.get("prompt", "")
    
    # For now, just echo back - we'll replace with real agent logic
    response = f"Echo: {prompt}"
    
    return {
        "response": response,
        "event_received": event,
    }


# Optional: Custom ping handler for health checks
@app.ping
def health_check():
    """
    Custom health check logic.
    
    AgentCore Runtime calls this for the /ping endpoint.
    Return HEALTHY, HEALTHY_BUSY, or UNHEALTHY.
    """
    from bedrock_agentcore.runtime.models import PingStatus
    return PingStatus.HEALTHY


if __name__ == "__main__":
    # This lets AgentCore Runtime control the server
    app.run()
