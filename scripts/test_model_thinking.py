#!/usr/bin/env python3
"""
Test thinking leakage across different models using LangChain (not Strands).

This helps determine if thinking leakage is a model issue or framework issue.
"""

from langchain_aws import ChatBedrock

# Models to test
MODELS = [
    ("Qwen3 32B", "qwen.qwen3-32b-v1:0"),
    ("Nova Pro", "us.amazon.nova-pro-v1:0"),
    ("Nemotron", "nvidia.nemotron-4-340b-reward:0"),
    # ("GPT-OSS", "???"),  # Need to find the correct model ID
]

TEST_PROMPT = "What is the capital of France? Please think through this step by step."


def test_model(name: str, model_id: str):
    """Test a single model for thinking leakage."""
    print(f"\n{'='*60}")
    print(f"Testing: {name} ({model_id})")
    print('='*60)
    
    try:
        llm = ChatBedrock(
            model_id=model_id,
            region_name="us-east-1"
        )
        
        response = llm.invoke(TEST_PROMPT)
        content = response.content
        
        print(f"\nResponse:\n{content[:500]}")
        
        # Check for thinking tags
        has_thinking = "<thinking>" in content.lower() or "</thinking>" in content.lower()
        has_scratchpad = "<scratchpad>" in content.lower() or "scratchpad" in content.lower()
        
        if has_thinking:
            print(f"\n⚠️  THINKING TAGS DETECTED")
        elif has_scratchpad:
            print(f"\n⚠️  SCRATCHPAD DETECTED")
        else:
            print(f"\n✅ No thinking leakage detected")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


def main():
    print("Testing models for thinking leakage using LangChain")
    print("(This is independent of Strands SDK)")
    
    for name, model_id in MODELS:
        test_model(name, model_id)
    
    print(f"\n{'='*60}")
    print("Test complete!")


if __name__ == "__main__":
    main()
