#!/usr/bin/env python3
"""
Test thinking leakage with tool-calling using LangChain.

The leakage was observed when tools were being called, so let's test that.
"""

from langchain_aws import ChatBedrock
from langchain_core.tools import tool


@tool
def get_temperature(location: str) -> str:
    """Get the current temperature for a location."""
    return f"The temperature in {location} is 65°F"


@tool
def get_forecast(location: str) -> str:
    """Get the weather forecast for a location."""
    return f"The forecast for {location}: Low of 45°F tonight"


# Models to test
MODELS = [
    ("Qwen3 32B", "qwen.qwen3-32b-v1:0"),
    ("Nova Pro", "us.amazon.nova-pro-v1:0"),
    ("GPT-OSS 120B", "openai.gpt-oss-120b-1:0"),
]

TEST_PROMPT = "What's the temperature in the attic and what's the forecast?"


def test_model(name: str, model_id: str):
    """Test a single model for thinking leakage with tools."""
    print(f"\n{'='*60}")
    print(f"Testing: {name} ({model_id})")
    print('='*60)
    
    try:
        llm = ChatBedrock(
            model_id=model_id,
            region_name="us-east-1"
        )
        
        # Bind tools
        llm_with_tools = llm.bind_tools([get_temperature, get_forecast])
        
        response = llm_with_tools.invoke(TEST_PROMPT)
        content = response.content
        
        print(f"\nResponse content:\n{content[:800] if content else '(no content)'}")
        
        # Also check tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"\nTool calls: {response.tool_calls}")
        
        # Check for thinking/reasoning tags
        has_thinking = content and ("<thinking>" in content.lower() or "</thinking>" in content.lower())
        has_reasoning = content and ("<reasoning>" in content.lower() or "</reasoning>" in content.lower())
        has_scratchpad = content and ("<scratchpad>" in content.lower() or "scratchpad" in content.lower())
        
        if has_thinking:
            print(f"\n⚠️  <thinking> TAGS DETECTED")
        elif has_reasoning:
            print(f"\n⚠️  <reasoning> TAGS DETECTED")
        elif has_scratchpad:
            print(f"\n⚠️  SCRATCHPAD DETECTED")
        else:
            print(f"\n✅ No thinking leakage detected")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    print("Testing models for thinking leakage WITH TOOLS using LangChain")
    print("(This tests if tool-calling triggers thinking leakage)")
    
    for name, model_id in MODELS:
        test_model(name, model_id)
    
    print(f"\n{'='*60}")
    print("Test complete!")


if __name__ == "__main__":
    main()
