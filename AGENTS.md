# AGENTS.md - Guidelines for AI Agents Editing This Project

This file provides guidelines for AI coding assistants (Cursor, Copilot, etc.) working on this codebase.

## Project Overview

This is a temperature monitoring AI agent built with:
- **Strands Agents SDK** for agent logic
- **Amazon Bedrock** for LLM inference (Qwen3 32B)
- **AgentCore Memory** for cross-session persistence
- **Ecowitt Cloud API** for sensor data
- **ntfy.sh** for push notifications

---

## Documentation Organization

Different types of markdown files belong in different locations:

| Location | Purpose | In Git? |
|----------|---------|---------|
| `README.md` | Project overview and quick start | ✅ Yes |
| `AGENTS.md` | This file - AI assistant guidelines | ✅ Yes |
| `ADR/` | Architecture Decision Records, plans, design docs | ✅ Yes |
| `docs/` | User-facing documentation, setup guides, reports | ✅ Yes |
| `.local_docs/` | Personal notes, memos, work-in-progress | ❌ No (gitignored) |

### When to use each:

- **`ADR/`** - Use for documents that explain *why* decisions were made. The main planning document is `ADR/agent_development_plan.md`.

- **`docs/`** - Use for documents that help users or developers *use* the system. Examples:
  - `docs/agentcore_memory_setup.md` - How to set up memory
  - `docs/bedrock_model_compatibility_report.md` - Model testing results
  - `docs/maintenance.md` - Operational tasks

- **`.local_docs/`** - Use for personal notes, debugging logs, or drafts that shouldn't be shared. This folder is in `.gitignore`.

---

## Code Organization

```
src/temperature_agent/
├── agent_with_memory.py   # Main agent implementation
├── api.py                 # FastAPI REST server
├── cli.py                 # Interactive CLI
├── config.py              # Configuration loader
├── tools/                 # Agent tools
│   ├── temperature.py     # Sensor data tools
│   ├── forecast.py        # Weather forecast tools
│   ├── alerts.py          # Alert/notification tools
│   └── memory.py          # Memory storage tools
└── legacy/                # Original scripts (reference only)
```

**Key files:**
- `agent_with_memory.py` - Main agent implementation
- `api.py` - REST API for web/mobile access

---

## Testing

This project uses **Test-Driven Development (TDD)**. Tests are in the `tests/` directory.

```bash
# Run all tests
PYTHONPATH=src pytest tests/ -v

# Run specific test file
PYTHONPATH=src pytest tests/test_temperature_tools.py -v

# Run the CLI for manual testing
PYTHONPATH=src python -m temperature_agent
```

When adding new tools:
1. Write tests first in `tests/test_<category>_tools.py`
2. Implement the tool in `src/temperature_agent/tools/<category>.py`
3. Add `@tool` decorator from `strands` to register with the agent
4. Export from `tools/__init__.py`
5. Add to the tool list in `agent_with_memory.py`

---

## Configuration

Configuration is in `config.json` (not committed - use `config.example.json` as template).

Key settings:
```json
{
  "bedrock_model": "qwen.qwen3-32b-v1:0",  // DO NOT CHANGE without reading model report
  "bedrock_region": "us-east-1",
  "agentcore_memory_id": "...",             // Required - see docs/agentcore_memory_setup.md
  "api_password": "..."                     // Required for REST API
}
```

---

## Critical Lessons Learned

### 1. Model Selection is Critical

**Only use `qwen.qwen3-32b-v1:0` for this project unless instructed otherwise.**

Most Bedrock models are broken for tool-calling agents:

- Nova Pro/Lite: Leaks `<thinking>` tags
- DeepSeek R1: No tool support, leaks reasoning
- GPT-OSS 120B: Outputs JSON instead of calling tools
- Llama 4: No streaming tool support
- Claude: Requires AWS use case form

See `docs/bedrock_model_compatibility_report.md` for full details.

### 2. System Prompt Design

**Never use explicit "Call X" instructions in system prompts.**

❌ **BAD** - Causes models to output action text instead of calling tools:
```
For temperature queries like "Which room is coldest?":
- Call get_coldest_sensor, then respond with the room name and temperature
```

✅ **GOOD** - Let the model decide how to use tools:
```
You have access to tools that can check temperatures and find 
the coldest room. Use them when needed to answer questions.
```

### 3. Memory Architecture

The agent uses **AgentCore Memory** for house knowledge:
- Semantic search across sessions
- Automatic fact extraction from conversations
- Cloud persistence
- Requires `agentcore_memory_id` in config.json

**Alert history** is stored locally in `alert_history.json` as a simple log.

### 4. Tool Registration

All tools must use the `@tool` decorator from Strands:

```python
from strands import tool

@tool
def get_current_temperatures() -> dict[str, float]:
    """
    Get current temperature readings from all sensors.
    
    Returns:
        Dictionary mapping sensor location names to temperatures in °F
    """
    # implementation
```

The docstring becomes the tool description that the LLM sees.

### 5. Strands SDK Specifics

- Strands streams responses by default - don't manually print the response in CLI
- Use `AgentCoreMemorySessionManager` for memory integration
- The agent call returns a response object: `response = agent(message)`

---

## Common Tasks

### Adding a New Tool

1. Create or edit file in `src/temperature_agent/tools/`
2. Add `@tool` decorator with clear docstring
3. Add tests in `tests/test_<category>_tools.py`
4. Import and add to `get_agent_tools()` in `agent_with_memory.py`

### Changing the Model

1. **Read `docs/bedrock_model_compatibility_report.md` first**
2. Update `bedrock_model` in `config.json`
3. Test thoroughly - issues often only appear in real usage

### Testing Memory

```bash
# Clear memory before testing
PYTHONPATH=src python -m temperature_agent --clear-memory

# Start CLI - first session
PYTHONPATH=src python -m temperature_agent
> The basement has stone foundation walls
> /quit

# Start CLI - new session (tests cross-session memory)
PYTHONPATH=src python -m temperature_agent
> What do you know about my basement?
# Should mention stone walls from previous session

# Clear memory after testing
PYTHONPATH=src python -m temperature_agent --clear-memory
```

### Debugging API Issues

1. Check `config.json` has valid API keys
2. Test Ecowitt API directly:
   ```bash
   PYTHONPATH=src python src/temperature_agent/legacy/temperature_alert_cloud.py --test
   ```
3. Check AWS credentials: `aws sts get-caller-identity`

---

## Git Workflow

When making PRs:
- **Use separate commits** for each logical change (don't amend previous commits)
- This allows squash-and-merge when the PR is ready
- Write clear commit messages describing what changed and why

---

## Don't Do These Things

1. **Don't change the model** without reading the compatibility report
2. **Don't add explicit tool instructions** to system prompts
3. **Don't skip tests** - use TDD for new features
4. **Don't put user docs in `.local_docs/`** - that folder is gitignored
5. **Don't amend commits** in PRs - use separate commits for fixes

---

## Useful Commands

```bash
# Activate environment
cd /Users/bmurdock/git/temperature_alert
source venv/bin/activate

# Run tests
PYTHONPATH=src pytest tests/ -v

# Run CLI
PYTHONPATH=src python -m temperature_agent

# Run API server
PYTHONPATH=src uvicorn temperature_agent.api:app --host 0.0.0.0 --port 8000
# API docs at http://localhost:8000/docs

# Clear local memory (useful after testing)
PYTHONPATH=src python -m temperature_agent --clear-memory

# Check AWS credentials
aws sts get-caller-identity

# Check Bedrock models
aws bedrock list-foundation-models --region us-east-1

# Check AgentCore Memory status
aws bedrock-agentcore-control get-memory --memory-id temperature_agent-mcbeCMEOwX --region us-east-1
```

---

*Last updated: January 2026*
