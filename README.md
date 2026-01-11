# Temperature Alert System

A Python service that monitors temperatures from Ecowitt sensors and sends alerts via [ntfy.sh](https://ntfy.sh). Includes an **AI-powered chat agent** for natural language interaction with your temperature data.

## Features

- **AI Chat Agent**: Ask questions like "Which room is coldest?" or "Send me an alert about the basement"
- **Semantic Memory**: Agent remembers facts about your house and retrieves them using semantic search (via AWS AgentCore)
- **Ecowitt Integration**: Reads data from Ecowitt GW1XXX gateways (Cloud mode)
- **Freeze & Heat Warnings**: Alerts when temperatures cross defined thresholds
- **Weather Forecast**: Integrates with Open-Meteo to check for upcoming temperature extremes
- **Configurable**: Customize sensors, thresholds, and alert topics

## Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Run the AI agent
PYTHONPATH=src python -m temperature_agent
```

```
🌡️  Starting Temperature Agent...
(Framework: strands, Model: qwen.qwen3-32b-v1:0)

✅ Agent ready!

You: Which room is coldest?
Assistant: The coldest room is the Attic at 55.9°F.

You: The basement has old windows that let in cold air.
Assistant: I've noted that the basement has old windows...

You: Why might the basement get cold?
Assistant: Based on what I know about your house, the old windows 
           in the basement could be letting in cold air...
```

## Project Structure

```
temperature_alert/
├── config.json                 # Your configuration
├── src/
│   └── temperature_agent/
│       ├── agent_with_memory.py # Main Strands agent with memory support
│       ├── api.py              # FastAPI REST server
│       ├── cli.py              # Interactive CLI
│       ├── tools/              # Agent tools (temperature, alerts, memory)
│       └── legacy/             # Original monitoring scripts
├── web/                        # React frontend (PatternFly Chatbot)
├── tests/                      # Test suite
├── docs/                       # Documentation
│   └── agentcore_memory_setup.md
└── venv/                       # Python virtual environment
```

## Installation

### Prerequisites

- Python 3.12+
- AWS account with Bedrock access
- Ecowitt weather station with cloud sync

### Setup

```bash
# Clone and enter directory
git clone <repo-url>
cd temperature_alert

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install strands-agents bedrock-agentcore-starter-toolkit requests pytest

# Configure AWS credentials
aws configure
```

### Configuration

Copy and edit the config file:

```bash
cp config.example.json config.json
# Edit config.json with your Ecowitt credentials and sensor names
```

## Configuration

Key fields in `config.json`:

```json
{
    "sensors": {
        "Indoor": "Kitchen",
        "Channel 1": "Living Room",
        "Channel 4": "Attic"
    },
    "freeze_threshold_f": 60.0,
    "ntfy_topic": "your-alerts-topic",
    
    "ecowitt_application_key": "YOUR_KEY",
    "ecowitt_api_key": "YOUR_KEY", 
    "ecowitt_mac": "XX:XX:XX:XX:XX:XX",
    
    "bedrock_model": "qwen.qwen3-32b-v1:0",
    "agentcore_memory_id": ""
}
```

See `config.example.json` for full template.

## Usage

### AI Chat Agent (CLI)

```bash
source venv/bin/activate
PYTHONPATH=src python -m temperature_agent
```

### REST API

Start the API server for web/mobile access:

```bash
source venv/bin/activate
PYTHONPATH=src uvicorn temperature_agent.api:app --host 0.0.0.0 --port 8000
```

**API Endpoints:**
- `GET /health` - Health check (no auth)
- `POST /auth/login` - Login with password, returns session token
- `GET /status` - Get current temperature status (requires auth)
- `POST /chat` - Send message to agent (requires auth)

**Example:**
```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "your_api_password"}'
# Returns: {"session_token": "...", "expires_in": 86400}

# Chat (use the session token)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer session:<token>" \
  -d '{"message": "Which room is coldest?"}'
```

Add `api_password` to your `config.json` to enable the API.

### Web Interface

A React-based chat interface is available in the `web/` directory:

```bash
# Install dependencies (first time only)
cd web && npm install

# Start development server
npm run dev
```

Then open http://localhost:5173/ in your browser. Make sure the API server is also running.

**Features:**
- Password-protected login
- Real-time chat with the temperature agent
- Quick action buttons for common queries
- Dark/light theme toggle
- Mobile-friendly design

**Example interactions:**
- "Which room is coldest?"
- "What's the forecast for tonight?"
- "Send me an alert about the basement"
- "Set the attic threshold to 50 degrees"
- "The kitchen pipes run along the north wall" (stores fact)
- "Why is the attic so cold?" (uses stored facts)

### Enable AgentCore Memory (Optional)

For semantic search and cross-session memory, set up AgentCore Memory:

```bash
# Create memory resource
aws bedrock-agentcore-control create-memory \
    --name "temperature_agent" \
    --event-expiry-duration 30 \
    --region us-east-1

# Add the memory ID to config.json
# "agentcore_memory_id": "temperature_agent-xxxxx"
```

See [docs/agentcore_memory_setup.md](docs/agentcore_memory_setup.md) for full setup guide.

### Legacy Scripts

The original monitoring scripts still work:

```bash
# Cloud Mode - fetches from Ecowitt cloud API
python src/temperature_agent/legacy/temperature_alert_cloud.py
```

## Obtaining Ecowitt Cloud API Credentials

To use cloud mode, you need API credentials from Ecowitt:

### Step 1: Create an Ecowitt Account

1. Go to [ecowitt.net](https://www.ecowitt.net) and create an account.
2. Make sure your device is syncing data via the WS View or Ecowitt app.

### Step 2: Get Your Application Key

1. Log into [ecowitt.net](https://www.ecowitt.net).
2. Click your username → **"Private Center"**.
3. Under **"Application Key"**, click **"Create Application Key"**.
4. Copy the key to your `config.json`.

### Step 3: Get Your API Key

1. In **"Private Center"**, find **"API Key"**.
2. Click **"Create API Key"**.
3. Copy to your `config.json`.

### Step 4: Find Your Device MAC Address

1. Go to **"My Devices"** in the Ecowitt web interface.
2. Click on your weather station/gateway.
3. Copy the MAC address (format: `XX:XX:XX:XX:XX:XX`) to your `config.json`.

**API Rate Limits:**
- 3 requests/second with Application Key
- 1 request/second with API Key

## Development

### Running Tests

```bash
source venv/bin/activate
PYTHONPATH=src python -m pytest tests/ -v
```

### Model Selection

The agent uses Amazon Bedrock. Recommended models (in `config.json`):

| Model | Notes |
|-------|-------|
| `qwen.qwen3-32b-v1:0` | **Recommended** - Clean output, good reasoning |
| `mistral.mixtral-8x7b-instruct-v0:1` | Fast, cheap alternative |

See [docs/bedrock_model_compatibility_report.md](docs/bedrock_model_compatibility_report.md) for full model testing results.

### Documentation

- [ADR/agent_development_plan.md](ADR/agent_development_plan.md) - Development roadmap and decisions
- [docs/agentcore_memory_setup.md](docs/agentcore_memory_setup.md) - Memory setup guide

## License

See [LICENSE.txt](LICENSE.txt)
