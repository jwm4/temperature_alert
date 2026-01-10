# AgentCore Memory Setup Guide

This guide explains how to enable AgentCore Memory for the Temperature Agent.

## What You Get

With AgentCore Memory enabled:

| Feature | Without AgentCore | With AgentCore |
|---------|-------------------|----------------|
| Search | Substring matching | **Semantic/vector search** |
| Fact extraction | Manual only | **Automatic from conversations** |
| Deduplication | None | **Automatic consolidation** |
| Storage | Local JSON files | **AWS cloud** |
| Cross-device | No | **Yes** |
| Cross-session | Limited | **Full persistence** |

## Prerequisites

1. AWS account with Bedrock access
2. AWS CLI v2 configured (`aws configure`)
3. IAM permissions for Bedrock AgentCore

## Step 1: Create Memory Resource

```bash
# Create a memory resource for the temperature agent
# Note: Use bedrock-agentcore-control (not bedrock-agentcore)
# Note: Name must use underscores, not hyphens
# Note: event-expiry-duration is in DAYS (max 365)

aws bedrock-agentcore-control create-memory \
    --name "temperature_agent" \
    --description "Memory for home temperature monitoring agent" \
    --event-expiry-duration 30 \
    --region us-east-1
```

Save the `id` from the response (e.g., `temperature_agent-mcbeCMEOwX`).

Wait for status to become ACTIVE:
```bash
aws bedrock-agentcore-control get-memory \
    --memory-id "YOUR_MEMORY_ID" \
    --region us-east-1 \
    --query "memory.status"
```

## Step 2: Add Semantic Memory Strategy

Once the memory is ACTIVE, add the semantic strategy:

```bash
aws bedrock-agentcore-control update-memory \
    --memory-id "YOUR_MEMORY_ID" \
    --memory-strategies '{
        "addMemoryStrategies": [{
            "semanticMemoryStrategy": {
                "name": "house_facts",
                "description": "Facts about the house construction and layout",
                "namespaces": ["/actor/{actorId}/house"]
            }
        }]
    }' \
    --region us-east-1
```

This enables automatic extraction of facts from conversations.

## Step 3: Configure the Agent

Add the memory ID to `config.json`:

```json
{
    "agentcore_memory_id": "temperature_agent-mcbeCMEOwX"
}
```

## Step 4: Run the Agent

```bash
PYTHONPATH=src python -m temperature_agent
```

You should see:
```
🌡️  Starting Temperature Agent...
(Framework: strands, Model: qwen.qwen3-32b-v1:0)
(Memory: AgentCore)

📚 AgentCore Memory enabled
✅ Agent ready!
```

## How It Works

### Automatic Fact Extraction

When you tell the agent something about your house:

```
You: The basement has old single-pane windows that let in cold air.
Assistant: I've noted that the basement has old single-pane windows...
```

AgentCore automatically (within 20-40 seconds):
1. Extracts the fact: "basement has old single-pane windows"
2. Stores it with semantic embeddings
3. Makes it searchable for future sessions

### Semantic Search (Cross-Session)

In a **new session**, when you ask:

```
You: What do you know about my basement?
```

AgentCore:
1. Searches memories semantically (not just substring matching)
2. Finds "old single-pane windows" even though you didn't use those words
3. Injects this context into the conversation
4. Agent gives an informed answer referencing the windows

**This is the key improvement over local file storage** - semantic search finds related concepts, not just exact text matches.

## Costs

- Storage: $0.75 per 1000 memories/month
- Retrieval: Included in Bedrock API costs
- Extraction: Async processing (minimal additional cost)

For a personal home monitoring agent, expect < $5/month.

## Fallback Mode

If `agentcore_memory_id` is empty or not set, the agent automatically falls back to local file-based memory. This is useful for:
- Local development without AWS
- Testing
- Offline usage

The local fallback uses substring matching (less powerful than semantic search).

## Troubleshooting

### "Memory is in transitional state CREATING"
- Wait 30-60 seconds for the memory to become ACTIVE
- Check status with `get-memory` command

### "Validation error on config"
- Ensure `retrieval_config` is formatted as a dict mapping namespaces to configs
- Check that memory ID matches exactly (including the random suffix)

### "Access denied"
- Ensure IAM permissions include `bedrock-agentcore-control:*` and `bedrock-agentcore:*`
- Check AWS credentials are configured

### Memories not appearing immediately
- Extraction is async (20-40 seconds after conversation)
- Within-session memory works immediately
- Cross-session requires extraction to complete

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Temperature Agent                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Strands   │  │   Qwen3     │  │   AgentCore Memory  │ │
│  │    Agent    │──│   Model     │──│   SessionManager    │ │
│  └─────────────┘  └─────────────┘  └──────────┬──────────┘ │
└───────────────────────────────────────────────┼─────────────┘
                                                │
                    ┌───────────────────────────┼───────────┐
                    │         AWS Cloud         │           │
                    │  ┌────────────────────────▼────────┐  │
                    │  │       AgentCore Memory          │  │
                    │  │  ┌──────────────────────────┐   │  │
                    │  │  │    Semantic Strategy     │   │  │
                    │  │  │  (house_facts namespace) │   │  │
                    │  │  └──────────────────────────┘   │  │
                    │  │  ┌──────────┐ ┌──────────────┐  │  │
                    │  │  │ Vector   │ │ Consolidation│  │  │
                    │  │  │ Search   │ │   Engine     │  │  │
                    │  │  └──────────┘ └──────────────┘  │  │
                    │  └─────────────────────────────────┘  │
                    └───────────────────────────────────────┘
```
