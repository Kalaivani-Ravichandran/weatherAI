"""
FastAPI application — Agent Backend.

Exposes a single POST /chat endpoint that:
  1. Receives a user message.
  2. Runs the LangChain ReAct agent against the MCP Server.
  3. Returns the agent's final answer plus a tool-call trace.

Start:
    uvicorn agent_backend.main:app --host 0.0.0.0 --port 8001 --reload
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent_backend.agent import run_agent
from agent_backend.schemas import ChatRequest, ChatResponse, ToolCallRecord

load_dotenv()


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
    print(f"[Agent Backend] Ready — MCP Server at {mcp_url}")
    yield
    print("[Agent Backend] Shutting down")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Weather Agent API",
    description=(
        "LangChain ReAct agent that routes weather queries to the "
        "Weather MCP Server and returns contextual answers."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Tighten in production (restrict to frontend origin)
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
async def health_check():
    """Liveness probe — confirms the backend is running."""
    return {"status": "healthy", "service": "weather-agent-backend"}


@app.post("/chat", response_model=ChatResponse, tags=["agent"])
async def chat(request: ChatRequest):
    """
    Send a natural-language weather query to the ReAct agent.

    The agent will:
    - Reason about which MCP tool(s) to call (ReAct loop)
    - Execute the tool(s) against the live Weather MCP Server
    - Return a human-friendly answer plus a structured tool-call trace

    **Example request body:**
    ```json
    { "message": "What's the weather like in Tokyo today, and is the air quality safe?" }
    ```
    """
    try:
        result = await run_agent(request.message)
        tool_calls = [ToolCallRecord(**tc) for tc in result.get("tool_calls", [])]
        return ChatResponse(response=result["response"], tool_calls=tool_calls)
    except RuntimeError as exc:
        # Configuration errors (missing API keys, MCP server unreachable, etc.)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
