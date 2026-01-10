#!/usr/bin/env python3
"""
Hello World Agent - Testing Strands Agents SDK with Bedrock

This is a simple test to verify:
1. Strands Agents SDK is working
2. Bedrock model is accessible
3. Basic agent functionality works
"""

from strands import Agent
from strands.models import BedrockModel

# Configure the model - using Qwen3 32B
# Selected for: clean output, good reasoning, very low cost
model = BedrockModel(
    model_id="qwen.qwen3-32b-v1:0",
    region_name="us-east-1"
)

# Create a simple agent
agent = Agent(
    model=model,
    system_prompt="""You are a friendly assistant helping to test the Strands Agents SDK.
    Keep your responses brief and helpful."""
)

if __name__ == "__main__":
    print("Testing Strands Agent with Qwen3 32B...")
    print("-" * 50)
    
    # Test a simple query
    response = agent("Hello! Say hi in a fun way!")
    
    print(f"Agent Response:\n{response}")
    print("-" * 50)
    print("✅ Agent test successful!")
