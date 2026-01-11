# Temperature Alert AI Agent Development Plan

## Project Overview

Build an AI-powered conversational agent for the temperature alert system using **Amazon Bedrock AgentCore**. The agent will allow natural language interactions to query sensor data, view historical information, and trigger alerts—accessible from any device via a web interface.

### Goals
- 🗣️ Natural language chat interface ("Which sensor is coldest right now?")
- 🧠 Agentic memory (remembers conversation context and learns user preferences)
- 🚨 On-demand alert triggering via conversation + custom threshold alerts
- 📱 Cross-device web access with simple password authentication
- ☁️ Leverage existing `temperature_alert_cloud.py` capabilities

---

## Current Status (January 2026)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Foundation & Learning | ✅ **DONE** | AWS configured, Strands working |
| Phase 2: Agent Tools Development | ✅ **DONE** | All tools implemented with TDD |
| Phase 3: Agent Core Logic | ✅ **DONE** | CLI working, local testing complete |
| Phase 4: Memory Implementation | ✅ **DONE** | AgentCore Memory integrated |
| Phase 5: Web Interface | ⬜ **NOT STARTED** | PatternFly Chatbot selected |
| Phase 6: AWS Deployment | ⬜ **NOT STARTED** | |
| Phase 7: Testing & Polish | ⬜ **NOT STARTED** | |
| Phase 8: Monitoring & Documentation | ⬜ **NOT STARTED** | |

---

## Decisions Made

Based on development work, the following decisions have been finalized:

| Decision | Choice | Notes |
|----------|--------|-------|
| **Agent Framework** | Strands Agents SDK | Native AgentCore integration, simpler than LangGraph |
| **LLM Model** | Qwen3 32B (`qwen.qwen3-32b-v1:0`) | Clean output, good reasoning, ~$0.35/1M tokens |
| **Chat UI** | PatternFly Chatbot (`@patternfly/chatbot`) | Enterprise-grade, accessible |
| **Authentication** | Simple password protection | To be implemented in Phase 5 |
| **Memory System** | AgentCore Memory (required) | Semantic memory strategy enabled |
| **Alert Customization** | Yes - per-sensor thresholds via chat | Implemented |
| **Startup Behavior** | Auto-show current temperatures on login | Implemented in CLI |
| **Budget** | $5-20/month acceptable | |

### Key Technical Decisions

1. **Model Selection**: Extensive testing revealed most Bedrock models have issues with tool calling. See [docs/bedrock_model_compatibility_report.md](../docs/bedrock_model_compatibility_report.md) for details. Qwen3 32B is the only model that works reliably without filtering.

2. **Framework Choice**: Initially considered LangGraph for output filtering, but returned to Strands because:
   - Native AgentCore Memory integration
   - Model filtering wasn't needed with Qwen3
   - Simpler codebase

3. **Memory Architecture**: Using AgentCore Memory with semantic strategy for house knowledge (required). Alert history stored locally in `alert_history.json`.

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Interface                             │
│              (React/HTML - Responsive Chat UI)                   │
│              + Simple Password Authentication                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Amazon API Gateway                            │
│                  (REST/WebSocket endpoint)                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│               Amazon Bedrock AgentCore Runtime                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Temperature Alert Agent                      │   │
│  │           (Strands Agents SDK - Python)                   │   │
│  │                                                           │   │
│  │  Tools:                                                   │   │
│  │  • get_current_temperatures()                             │   │
│  │  • get_coldest_sensor() / get_warmest_sensor()           │   │
│  │  • get_24h_history()                                      │   │
│  │  • get_forecast()                                         │   │
│  │  • send_alert()                                           │   │
│  │  • set_alert_threshold()                                  │   │
│  │  • get_alert_preferences()                                │   │
│  │  • get_alert_history()                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  AgentCore       │  │    Ecowitt      │  │   Open-Meteo    │
│   Memory         │  │   Cloud API     │  │   Forecast API  │
│                  │  │                 │  │                 │
│ • Short-term     │  │ • Real-time     │  │ • 24h forecast  │
│ • Long-term:     │  │ • History       │  │                 │
│   - Preferences  │  └─────────────────┘  └─────────────────┘
│   - Alert history│    
│   - Thresholds   │  ┌─────────────────┐
│ • Semantic:      │  │    ntfy.sh      │
│   - House info   │  │   Alert Service │
│   - Area/climate │  └─────────────────┘
│   - Observations │
└──────────────────┘
```

---

## Completed Phases

### Phase 1: Foundation & Learning ✅ DONE

**What was completed:**
- [x] AWS CLI installed and configured with IAM user credentials
- [x] Amazon Bedrock enabled in AWS account (us-east-1 region)
- [x] Model access requested and granted for multiple models
- [x] Strands Agents SDK installed: `pip install strands-agents strands-agents-tools`
- [x] AgentCore Memory SDK installed: `pip install bedrock-agentcore`
- [x] Hello World agent working locally
- [x] Extensive model testing completed (see compatibility report)
- [x] Lessons learned documented

**Files created:**
- `src/temperature_agent/hello_agent.py` - Test agent
- `docs/bedrock_model_compatibility_report.md` - Model testing results
- `.local_docs/agent_core_lessons_learned.md` - Development notes

**Key learnings:**
- Most Bedrock models don't work well for tool-calling agents
- Qwen3 32B is the recommended model (clean output, no filtering needed)
- Claude models require a use case form submission
- System prompts must avoid explicit "Call X" instructions (causes leakage on some models)

---

### Phase 2: Agent Tools Development ✅ DONE

**What was completed:**
- [x] Project restructured with `src/` and `tests/` directories
- [x] TDD approach - all tests written first, then implementation
- [x] All tools implemented and tested

**Tool implementations:**

| Tool | File | Purpose |
|------|------|---------|
| `get_current_temperatures()` | `tools/temperature.py` | All current sensor readings |
| `get_coldest_sensor()` | `tools/temperature.py` | Coldest sensor with temp |
| `get_warmest_sensor()` | `tools/temperature.py` | Warmest sensor with temp |
| `get_24h_history()` | `tools/temperature.py` | Highs/lows for all sensors |
| `get_sensor_info()` | `tools/temperature.py` | Configured sensors and locations |
| `get_forecast()` | `tools/forecast.py` | 24h weather forecast |
| `send_alert()` | `tools/alerts.py` | Send ntfy.sh notification |
| `set_alert_threshold()` | `tools/alerts.py` | Set custom threshold for sensor |
| `get_alert_preferences()` | `tools/alerts.py` | Current alert settings |
| `get_alert_history()` | `tools/memory.py` | Past alert records |
| `record_alert()` | `tools/memory.py` | Log an alert event |

Note: House knowledge storage/retrieval is handled automatically by AgentCore Memory.

**Test files:**
- `tests/test_temperature_tools.py` - 8 tests
- `tests/test_forecast_tools.py` - 5 tests
- `tests/test_alert_tools.py` - 6 tests
- `tests/test_memory_tools.py` - 6 tests
- `tests/test_agent_config.py` - 3 tests
- `tests/test_agent_responses.py` - 4 tests

**Run tests:**
```bash
cd /Users/bmurdock/git/temperature_alert
source venv/bin/activate
PYTHONPATH=src pytest tests/ -v
```

---

### Phase 3: Agent Core Logic ✅ DONE

**What was completed:**
- [x] Agent persona and system prompt defined
- [x] All tools registered with `@tool` decorator
- [x] Conversation handling implemented
- [x] CLI interface working
- [x] Local testing successful
- [x] Response quality tuned

**Files created:**
- `src/temperature_agent/agent_with_memory.py` - Main agent implementation
- `src/temperature_agent/cli.py` - Interactive CLI
- `src/temperature_agent/config.py` - Configuration loader

**Run the CLI:**
```bash
cd /Users/bmurdock/git/temperature_alert
source venv/bin/activate
PYTHONPATH=src python -m temperature_agent
```

**CLI Features:**
- `/help` - Show commands
- `/status` - Show current temperatures and forecast
- `/quit` - Exit
- Natural language queries work as expected

**Example interactions verified working:**
```
User: Which room is coldest right now?
Agent: The Basement is currently the coldest at 58.2°F.

User: What about the attic?
Agent: The Attic is currently at 55.6°F.

User: The basement has old stone walls
Agent: I've stored that information about your basement...

User: Why is the basement so cold?
Agent: [Retrieves stored knowledge about stone walls and provides contextual answer]
```

---

### Phase 4: Memory Implementation ✅ DONE

**What was completed:**
- [x] AgentCore Memory resource created in AWS
- [x] Semantic memory strategy enabled ("house_facts")
- [x] Strands integration via `AgentCoreMemorySessionManager`
- [x] Cross-session memory verified working

**AWS Memory Resource:**
- Memory ID: `temperature_agent-mcbeCMEOwX`
- Region: `us-east-1`
- Event expiry: 30 days
- Strategy: Semantic (`house_facts`)

**Memory architecture:**
```
AgentCore Memory (Required)
├── Semantic Strategy: house_facts
│   └── Namespace: /actor/{actorId}/house
│   └── Auto-extracts facts from conversations
│   └── Enables semantic search across sessions

Local Storage
└── alert_history.json - Simple log of alerts sent
```

**Configuration in `config.json`:**
```json
{
  "agentcore_memory_id": "temperature_agent-mcbeCMEOwX"
}
```

AgentCore Memory is required. The agent will not start without a valid `agentcore_memory_id`.

**Setup documentation:** See [docs/agentcore_memory_setup.md](../docs/agentcore_memory_setup.md)

---

## Remaining Phases

### Phase 5: Web Interface ⬜ NOT STARTED

**Goal:** Create a responsive web chat interface with password protection using PatternFly Chatbot.

#### Selected Framework: PatternFly Chatbot

Already decided - see comparison in original plan. Selected for:
- Professional, polished look out of the box
- Enterprise-grade accessibility (WCAG compliant)
- Built-in dark/light themes
- Multiple display modes
- Active maintenance by Red Hat

#### Tasks:
- [ ] Set up React project with Vite
- [ ] Install PatternFly core and chatbot packages
  ```bash
  npm install @patternfly/react-core @patternfly/chatbot
  ```
- [ ] Configure PatternFly CSS and theming
- [ ] Implement password authentication screen
- [ ] Create chat container component
- [ ] Connect to AgentCore API endpoint (or local API for now)
- [ ] Implement message streaming
- [ ] Implement auto-status on login (use `generate_status_greeting()` from agent)
- [ ] Configure welcome prompt with quick actions:
  - "Check all temperatures"
  - "Which room is coldest?"
  - "Show 24h highs and lows"
  - "Send me an alert"
- [ ] Add dark/light mode toggle
- [ ] Test on mobile devices
- [ ] Add loading states and error handling

#### Reference Implementation

The CLI's `generate_status_greeting()` function already produces the greeting format:
```
🌡️ Temperature Assistant

Most of your sensors are in the mid 60's but the basement is 58°F.

The outside temperature is 27°F now and the forecast shows a low of 22°F tonight around 3am.

How can I help you?
```

#### Deliverables:
- `web/` directory with React application
- Responsive web chat interface using PatternFly Chatbot
- Password-protected access
- Real-time streaming responses
- Quick action prompts for common queries
- Dark/light theme support
- Mobile-friendly design

---

### Phase 6: AWS Deployment ⬜ NOT STARTED

**Goal:** Deploy the complete system to AWS

#### Tasks:
- [ ] Create deployment package for agent
- [ ] Deploy agent to AgentCore Runtime using Starter Toolkit
- [ ] Configure AgentCore Gateway for API access
- [ ] Set up API Gateway (REST or WebSocket)
- [ ] Deploy web interface (S3 + CloudFront or Amplify)
- [ ] Configure password authentication (Lambda authorizer or similar)
- [ ] Set up custom domain (optional)
- [ ] Configure HTTPS

#### Deployment Commands (using Starter Toolkit):
```bash
# Install starter toolkit
pip install bedrock-agentcore-starter-toolkit

# Configure your agent
agentcore configure --entrypoint temperature_agent.py

# Optional: Local testing
agentcore launch --local

# Deploy to AWS
agentcore launch

# Test your agent
agentcore invoke '{"prompt": "Which room is coldest?"}'
```

#### Deliverables:
- Production-deployed agent on AgentCore Runtime
- Public web URL for chat interface
- Secure, password-protected API endpoints
- Deployment documentation

---

### Phase 7: Testing & Polish ⬜ NOT STARTED

**Goal:** Ensure reliability and good user experience

#### Tasks:
- [ ] End-to-end testing of all conversation flows
- [ ] Test memory persistence across browser sessions
- [ ] Test alert functionality (manual + threshold-based)
- [ ] Performance testing (response times)
- [ ] Error handling and edge cases
- [ ] UI polish and bug fixes
- [ ] Cross-device testing (phone, tablet, desktop)

#### Deliverables:
- Test report
- Bug fixes
- Polished, production-ready system

---

### Phase 8: Monitoring & Documentation ⬜ NOT STARTED

**Goal:** Set up observability and document the system

#### Tasks:
- [ ] Configure AgentCore Observability
- [ ] Set up CloudWatch alarms for errors
- [ ] Create usage dashboard
- [ ] Write user documentation
- [ ] Document architecture and deployment process
- [ ] Create troubleshooting guide

#### Deliverables:
- Monitoring dashboard
- Alert configuration for system issues
- User guide (how to use the chat interface)
- Operations guide (how to maintain/troubleshoot)

---

## Project Structure

```
temperature_alert/
├── ADR/                           # Architecture Decision Records
│   └── agent_development_plan.md  # This file
├── docs/                          # User-facing documentation
│   ├── agentcore_memory_setup.md  # Memory setup instructions
│   ├── bedrock_model_compatibility_report.md
│   ├── maintenance.md
│   └── walkthrough.md
├── src/
│   └── temperature_agent/
│       ├── __init__.py
│       ├── __main__.py            # Entry point for CLI
│       ├── agent_with_memory.py   # Main agent implementation
│       ├── cli.py                 # Interactive CLI
│       ├── config.py              # Configuration loader
│       ├── hello_agent.py         # Test agent
│       ├── legacy/                # Original scripts (non-agent mode)
│       │   ├── temperature_alert_cloud.py
│       │   └── temperature_alert.py
│       └── tools/                 # Agent tools
│           ├── __init__.py
│           ├── alerts.py
│           ├── forecast.py
│           ├── memory.py          # Alert history only
│           └── temperature.py
├── tests/                         # Test suite
│   ├── test_temperature_tools.py
│   ├── test_forecast_tools.py
│   ├── test_alert_tools.py
│   ├── test_memory_tools.py
│   ├── test_agent_config.py
│   └── test_agent_responses.py
├── config.json                    # Configuration (not in repo)
├── config.example.json            # Configuration template
├── alert_history.json             # Local alert history
├── pyproject.toml                 # Python package config
└── README.md
```

---

## Configuration

The agent is configured via `config.json`. Key settings:

```json
{
  // Temperature thresholds
  "freeze_threshold_f": 60.0,
  "heat_threshold_f": 70.0,
  
  // AI settings
  "bedrock_model": "qwen.qwen3-32b-v1:0",
  "bedrock_region": "us-east-1",
  
  // Memory (required)
  "agentcore_memory_id": "temperature_agent-mcbeCMEOwX"
}
```

See `config.example.json` for full template.

---

## Development Environment Setup

For anyone continuing this work:

```bash
# Clone and enter directory
cd /Users/bmurdock/git/temperature_alert

# Create/activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy config template
cp config.example.json config.json
# Edit config.json with your API keys

# Run tests
PYTHONPATH=src pytest tests/ -v

# Run the CLI
PYTHONPATH=src python -m temperature_agent
```

**AWS CLI Setup:**
```bash
# Configure AWS credentials (IAM user with Bedrock access)
aws configure

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

---

## Cost Considerations

### Current Costs (Development)
- Bedrock Qwen3 32B: ~$0.35 per 1M input tokens, ~$1.40 per 1M output tokens
- AgentCore Memory: Minimal during development

### Estimated Production Costs
- **Runtime**: Charged per invocation and compute time
- **Memory**: Charged per API call and storage
- **Gateway**: Charged per request
- API Gateway: ~$3.50 per million requests
- S3/CloudFront: ~$1-2/month for static hosting

**Estimated Monthly Cost**: $5-20 for personal/light usage

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model changes/deprecation | Service disruption | Config allows easy model switching |
| API rate limits (Ecowitt) | Service disruption | Implement caching, respect limits |
| Cost overruns | Budget | Set billing alerts, optimize calls |
| AgentCore changes | Breaking changes | Pin SDK versions, test updates |

---

## Timeline Summary

| Phase | Description | Duration | Status |
|-------|-------------|----------|--------|
| 1 | Foundation & Learning | 1-2 days | ✅ Done |
| 2 | Agent Tools Development | 2-3 days | ✅ Done |
| 3 | Agent Core Logic | 2-3 days | ✅ Done |
| 4 | Memory Implementation | 2-3 days | ✅ Done |
| 5 | Web Interface | 2-3 days | ⬜ Not Started |
| 6 | AWS Deployment | 1-2 days | ⬜ Not Started |
| 7 | Testing & Polish | 1-2 days | ⬜ Not Started |
| 8 | Monitoring & Documentation | 1 day | ⬜ Not Started |

**Remaining Time Estimate: 6-9 days**

---

## Handoff Notes

For the person continuing this work:

1. **Start with Phase 5** - The backend is complete and working. The CLI can be used to test interactions.

2. **Test the current system first:**
   ```bash
   PYTHONPATH=src python -m temperature_agent
   ```
   Try queries like "Which room is coldest?", "Tell me about the forecast", "The attic has poor insulation" (to test memory).

3. **Key files to understand:**
   - `src/temperature_agent/agent_with_memory.py` - Main agent logic
   - `src/temperature_agent/cli.py` - How the agent is invoked
   - `config.json` - All configuration (must include `agentcore_memory_id`)

4. **Web interface notes:**
   - The `generate_status_greeting()` function returns the formatted greeting
   - The `chat()` function takes a message and returns a response
   - Consider creating a simple Flask/FastAPI wrapper before full PatternFly integration

5. **AWS deployment notes:**
   - The agent uses AWS credentials from the environment
   - AgentCore Memory is already configured in AWS
   - See `docs/agentcore_memory_setup.md` for memory details

---

*Plan created: January 9, 2026*  
*Last updated: January 11, 2026*
