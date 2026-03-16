# Weather AI Agent — Agentic Web App with MCP Server Wrapper

A full-stack agentic application built for the **AI Builder Candidate Project**.

```
┌──────────────┐    POST /chat     ┌─────────────────────┐    SSE/MCP     ┌──────────────────┐
│   Frontend   │ ─────────────────▶│   Agent Backend     │ ─────────────▶│   MCP Server     │
│  (HTML/JS)   │                   │  LangChain ReAct    │               │  FastMCP +       │
│  port: file  │ ◀─────────────────│  FastAPI :8001      │ ◀─────────────│  OpenWeatherMap  │
└──────────────┘   JSON response   └─────────────────────┘               │  :8000/sse       │
                                                                          └──────────────────┘
```

## Architecture

| Component | Technology | Role |
|-----------|-----------|------|
| **MCP Server** | FastMCP (Python `mcp[cli]`) | Wraps OpenWeatherMap REST API into 3 MCP tools over SSE |
| **Agent Backend** | LangChain + LangGraph ReAct + FastAPI | Receives user queries, runs ReAct reasoning loop, calls MCP tools |
| **Frontend** | Vanilla HTML/CSS/JS | Chat UI that streams results and shows the tool-call trace |

### MCP Tools Exposed

| Tool | Description |
|------|-------------|
| `get_current_weather(city)` | Real-time temperature, humidity, wind, and conditions |
| `get_weather_forecast(city, days)` | Day-by-day forecast (1–5 days, 3-hour slots) |
| `get_air_quality(city)` | AQI index (1–5) and pollutant breakdown (PM2.5, PM10, NO₂, O₃, SO₂, CO) |

### ReAct Agent Flow

```
User query
    │
    ▼
[THOUGHT]  LLM decides which tool(s) to call
    │
    ▼
[ACTION]   langchain-mcp-adapters calls tool via SSE → MCP Server → OpenWeatherMap
    │
    ▼
[OBSERVATION] Tool result returned to LLM
    │
    ▼  (repeat if multiple tools needed)
    │
    ▼
[FINAL ANSWER]  Human-friendly response with advice
```

---

## Prerequisites

- Python 3.12+
- An **OpenWeatherMap** free API key → [openweathermap.org/api](https://openweathermap.org/api)
- An **Anthropic** API key → [console.anthropic.com](https://console.anthropic.com)

---

## Quick Start (Local)

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd mcp_Server_Agentic_wrapper

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

```env
OPENWEATHER_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### 3. Start the MCP Server (Terminal 1)

```bash
python -m mcp_server.server
# → Running on http://0.0.0.0:8000/sse
```

### 4. Start the Agent Backend (Terminal 2)

```bash
uvicorn agent_backend.main:app --host 0.0.0.0 --port 8001 --reload
# → Running on http://0.0.0.0:8001
```

### 5. Open the Frontend

Open `frontend/index.html` directly in your browser (no build step required).

---

## Docker Deployment

```bash
# Build and start both services
docker compose up --build

# Then open frontend/index.html in your browser
```

Services will be available at:
- MCP Server: `http://localhost:8000/sse`
- Agent Backend: `http://localhost:8001`

---

## API Reference

### `POST /chat`

```json
// Request
{ "message": "What's the weather in Tokyo and is the air quality safe?" }

// Response
{
  "response": "Tokyo currently has 18°C with partly cloudy skies...",
  "tool_calls": [
    {
      "tool_name": "get_current_weather",
      "tool_input": { "city": "Tokyo" },
      "tool_output": { "temperature_celsius": 18.2, ... }
    },
    {
      "tool_name": "get_air_quality",
      "tool_input": { "city": "Tokyo" },
      "tool_output": { "aqi_index": 2, "aqi_label": "Fair", ... }
    }
  ]
}
```

### `GET /health`

Liveness probe — returns `{ "status": "healthy" }`.

---

## Security Considerations

- **API keys** are stored in `.env` (excluded from git via `.gitignore`). They are injected via environment variables — never hardcoded.
- **CORS** is set to `*` for local development. In production, restrict `allow_origins` to the frontend's actual origin.
- **MCP Server** should not be exposed publicly — keep it internal. In production, place it behind a VPC or private network and let only the agent backend communicate with it.

---

## Deployment Strategy (Production)

| Layer | Recommendation |
|-------|---------------|
| MCP Server | Docker container in a private subnet, no public ingress |
| Agent Backend | Docker container behind an API Gateway / Load Balancer with auth |
| Frontend | Static hosting (S3 + CloudFront, Netlify, Vercel) |
| Secrets | AWS Secrets Manager / GCP Secret Manager — never in env files |
| Orchestration | Kubernetes (EKS/GKE) or AWS ECS Fargate for auto-scaling |
| Observability | LangSmith for LLM traces, Prometheus + Grafana for service metrics |

---

## Project Structure

```
mcp_Server_Agentic_wrapper/
├── mcp_server/
│   ├── __init__.py
│   ├── server.py          # FastMCP server — 3 MCP tools over SSE
│   └── weather_client.py  # OpenWeatherMap HTTP client (httpx)
├── agent_backend/
│   ├── __init__.py
│   ├── agent.py           # LangChain ReAct agent + MCP adapter wiring
│   ├── main.py            # FastAPI app — POST /chat endpoint
│   └── schemas.py         # Pydantic request/response models
├── frontend/
│   └── index.html         # Self-contained chat UI (no build step)
├── .env.example           # Environment variable template
├── .gitignore
├── docker-compose.yml     # Orchestrates both services
├── Dockerfile.mcp         # MCP server image
├── Dockerfile.agent       # Agent backend image
├── requirements.txt       # All Python dependencies
└── README.md
```

---

## Documentation Philosophy

This project follows a **self-documenting architecture** approach:

1. **Docstrings on every function** — explain *what* it does, *why* specific choices were made, and the expected input/output contract.
2. **Type annotations throughout** — the code serves as its own type documentation.
3. **README.md** covers setup, architecture diagrams, API reference, and deployment — sufficient for a new developer to be productive on day one.
4. **.env.example** documents every required environment variable with comments explaining where to get the values.
5. **Inline comments** explain non-obvious logic (e.g., the ReAct loop, tool-call ID matching).
