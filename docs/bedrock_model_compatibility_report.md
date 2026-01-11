# Amazon Bedrock Model Compatibility Report

**Date:** January 2026  
**Project:** Temperature Alert Agent  
**Frameworks Tested:** LangChain, LangGraph, Strands Agents SDK  

## Executive Summary

While Amazon Bedrock offers access to many popular LLMs, **only 2-3 models work reliably** for tool-calling agents out of the box. Most models exhibit various issues ranging from leaked internal markers to complete tool-calling failures. This report documents our findings from extensive testing.

## Test Methodology

We tested models at three levels:
1. **Raw Bedrock Converse API** - Direct boto3 calls to isolate Bedrock-level issues
2. **LangChain ChatBedrock** - Standard LangChain integration
3. **LangGraph ReAct Agent** - Full agent with tool calling

Test query: "What is the temperature in the attic?" with a simple `get_temperature(room: str)` tool.

---

## Model Compatibility Matrix

| Model | Converse API | LangChain | LangGraph | Status |
|-------|--------------|-----------|-----------|--------|
| Qwen3 32B | ✅ Clean | ✅ Clean | ✅ Clean | **RECOMMENDED** |
| Mixtral 8x7B | ❌ No tool support | ✅ Works | ✅ Works | **OK** |
| Nova Pro | ⚠️ Leaks `<thinking>` | ⚠️ Leaks | ⚠️ Leaks | Needs filtering |
| Nova Lite | ⚠️ Leaks `<thinking>` | ⚠️ Leaks | ⚠️ Leaks | Needs filtering |
| Mistral Small 24.02 | ✅ Clean | ✅ Clean | ⚠️ Leaks with prompts | Prompt-sensitive |
| Mistral Large 24.02 | ✅ Clean | ✅ Clean | ⚠️ Leaks with prompts | Prompt-sensitive |
| Mistral Large 3 (675B) | ❌ Wrong API format | ❌ Fails | ❌ Fails | **BROKEN** |
| DeepSeek R1 | ❌ No tool support | ❌ Fails | ⚠️ Leaks reasoning | **BROKEN** |
| GPT-OSS 120B | ⚠️ Hallucinates | ❌ JSON output | ❌ Fails | **BROKEN** |
| Llama 4 Maverick | ❌ No streaming tools | ❌ Fails | ❌ Fails | **BROKEN** |
| Claude models | N/A | N/A | N/A | Requires use case form |
| Cohere Command R+ | ✅ Clean | ❌ Not supported | ❌ Not supported | LangChain gap |
| AI21 Jamba | ✅ Clean | ❌ Not supported | ❌ Not supported | LangChain gap |

---

## Detailed Findings

### 1. Amazon Nova Pro/Lite - Thinking Tag Leakage

**Issue:** Model outputs `<thinking>` tags as part of its response at the raw Bedrock API level.

**Evidence:**
```python
# Raw Bedrock Converse API response
{
    "content": [
        {"text": "<thinking> To determine the temperature... </thinking>\n"},
        {"toolUse": {"name": "get_temperature", "input": {"room": "attic"}}}
    ]
}
```

**Root Cause:** This appears to be intentional behavior by Amazon, possibly for transparency or debugging. The thinking tags are included in the text content block alongside tool calls.

**Workaround:** Filter `<thinking>.*?</thinking>` patterns from responses.

---

### 2. Mistral Small/Large (24.02) - Prompt-Triggered Markers

**Issue:** When system prompts contain explicit tool-calling instructions, the model outputs text-based action markers instead of using structured tool calls.

**Trigger Prompt Pattern:**
```
For temperature queries like "Which room is coldest?":
- Call get_coldest_sensor, then respond with the room name and temperature
```

**Result:**
```
<<SYS>> Call search_house_knowledge("attic") to get the temperature data.
A: Let me check the temperature in the attic for you...
```

**Root Cause:** The model interprets "Call X" instructions as a cue to output its action planning as text using `<<SYS>>`, `<<ACTION>>`, or `<</SYS>>` markers, rather than invoking the actual tool mechanism.

**Evidence - Raw API is Clean:**
```python
# Without problematic prompts, Converse API works correctly
response = client.converse(modelId="mistral.mistral-small-2402-v1:0", ...)
# Returns clean tool_use block, no leaked markers
```

**Workaround:** Avoid explicit "Call X, then respond with Y" patterns in system prompts. Use implicit instructions like "You have access to tools that can check temperatures."

---

### 3. DeepSeek R1 - No Tool Support + Reasoning Leakage

**Issue:** Two problems:
1. Bedrock's Converse API doesn't support tool use for this model
2. When LangChain/LangGraph fall back to other methods, the model leaks its chain-of-thought reasoning

**Evidence:**
```python
# Converse API
client.converse(modelId="us.deepseek.r1-v1:0", toolConfig={...})
# ValidationException: This model doesn't support tool use.

# LangGraph output
"Okay, the user is asking about the attic. Let me check the current temperature...
<|end_of_sentence|><|begin_of_sentence|><|System|>You are a helpful..."
```

**Root Cause:** DeepSeek R1 is primarily a reasoning model not designed for tool use. Bedrock doesn't expose tool calling for it. When frameworks try to work around this, the model's extensive chain-of-thought and special tokens leak through.

**Workaround:** None viable. Do not use for tool-calling agents.

---

### 4. GPT-OSS 120B - Hallucination Before Tool Execution

**Issue:** Model outputs both a hallucinated answer AND a tool call simultaneously.

**Evidence:**
```python
# Converse API response
{
    "content": [
        {"text": "The temperature in the attic is currently **78°F**."},  # Hallucinated!
        {"toolUse": {"name": "get_temperature", "input": {"room": "attic"}}}
    ]
}
```

**Root Cause:** The model generates an answer before/alongside the tool call instead of waiting for the tool result. This defeats the purpose of tool calling.

**Additional Issue:** When used through LangChain, often outputs raw JSON instead of executing tools:
```
{"function": "get_current_temperatures", "arguments": {}}
```

**Workaround:** None viable. Do not use for tool-calling agents.

---

### 5. Mistral Large 3 (675B) - Wrong API Format

**Issue:** Uses OpenAI-compatible API format instead of Bedrock's native format.

**Error:**
```
ValidationException: Failed to deserialize the JSON body into the target type: 
unknown variant `prompt`, expected one of `messages`, `tools`, ...
```

**Root Cause:** Newer Mistral models on Bedrock use a different API contract that LangChain's ChatBedrock doesn't handle correctly.

**Workaround:** Use older Mistral models (Mixtral 8x7B) or wait for LangChain updates.

---

### 6. Llama 4 Maverick - No Streaming Tool Support

**Issue:** Model doesn't support tool use in streaming mode, which Strands SDK requires.

**Error:**
```
ValidationException: This model doesn't support tool use in streaming mode.
```

**Root Cause:** Bedrock limitation - the model's tool calling implementation doesn't support streaming responses.

**Workaround:** None for Strands. LangGraph may work with non-streaming configuration.

---

### 7. Cohere & AI21 - LangChain Gap

**Issue:** These models work at the raw Bedrock API level but LangChain's ChatBedrock doesn't support them.

**Error:**
```
Provider cohere model does not support chat.
Provider ai21 model does not support chat.
```

**Root Cause:** LangChain's `langchain-aws` package hasn't implemented chat support for these providers.

**Workaround:** Use raw boto3 calls or wait for LangChain updates.

---

## Recommendations

### For Production Use

1. **Primary Choice: Qwen3 32B**
   - Clean output, no filtering needed
   - Good reasoning capabilities
   - Cost-effective
   - Works with all frameworks

2. **Alternative: Mixtral 8x7B**
   - Fast and cheap
   - Clean output
   - Note: May not actually execute tools via Converse API, but LangGraph handles it

3. **If you need Amazon model: Nova Pro with filtering**
   - Add post-processing to remove `<thinking>` tags
   - Use LangGraph for better control over output

### Prompt Engineering Guidelines

To maximize model compatibility:

❌ **Avoid:**
```
For temperature queries:
- Call get_coldest_sensor, then respond with the room name
```

✅ **Use Instead:**
```
You have access to tools that can check temperatures and find 
the coldest room. Use them when needed to answer questions.
```

### Framework Recommendations

| Use Case | Recommended Framework |
|----------|----------------------|
| Simple agents, Qwen3 | Strands SDK |
| Need output filtering | LangGraph |
| Maximum model flexibility | Raw boto3 + Converse API |

---

## Test Code

The following code was used to test models at the raw Bedrock API level:

```python
import boto3

client = boto3.client('bedrock-runtime', region_name='us-east-1')

tools = [{
    "toolSpec": {
        "name": "get_temperature",
        "description": "Get the current temperature for a room",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "room": {"type": "string", "description": "The room name"}
                },
                "required": ["room"]
            }
        }
    }
}]

response = client.converse(
    modelId="MODEL_ID_HERE",
    messages=[{"role": "user", "content": [{"text": "What is the temperature in the attic?"}]}],
    toolConfig={"tools": tools},
    inferenceConfig={"maxTokens": 500}
)

# Check response for leaked markers and proper tool calls
```

---

## Conclusion

The promise of "model flexibility" with Bedrock is significantly limited in practice for tool-calling agents. Out of 12+ models tested, only **Qwen3 32B** works reliably without workarounds. This is due to a combination of:

1. Bedrock's varying implementation of tool calling across model providers
2. Models' different interpretations of prompts and tool-calling protocols  
3. Gaps in LangChain's support for newer models and providers
4. Intentional design choices (like Nova's thinking tags) that conflict with clean UX

Teams building production agents on Bedrock should test thoroughly and be prepared to either:
- Commit to a single proven model (Qwen3)
- Implement robust output filtering
- Accept limited model choices

---

*Report generated from testing conducted January 2026*
