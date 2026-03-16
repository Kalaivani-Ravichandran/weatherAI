"""
Weather MCP Server — built with FastMCP.

Exposes three tools over SSE transport so any MCP-compatible client
(e.g. LangChain via langchain-mcp-adapters) can call them.

Start:
    python mcp_server/server.py          # SSE on http://0.0.0.0:8000/sse
"""

import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mcp_server.weather_client import (
    fetch_current_weather,
    fetch_forecast,
    fetch_air_quality,
)

load_dotenv()

mcp = FastMCP(
    name="Weather MCP Server",
    instructions=(
        "You are a weather data provider. Use the available tools to answer "
        "questions about current weather, forecasts, and air quality for any city."
    ),
)


# ─────────────────────────────────────────────
# Tool 1: Current weather
# ─────────────────────────────────────────────
@mcp.tool()
async def get_current_weather(city: str) -> dict:
    """Get real-time weather conditions for a city.

    Args:
        city: City name, optionally with country code (e.g. "London", "Paris,FR").

    Returns:
        Dict with temperature, feels-like, humidity, wind speed, condition, etc.
    """
    return await fetch_current_weather(city)


# ─────────────────────────────────────────────
# Tool 2: Multi-day forecast
# ─────────────────────────────────────────────
@mcp.tool()
async def get_weather_forecast(city: str, days: int = 3) -> dict:
    """Get a day-by-day weather forecast for a city.

    Args:
        city: City name, optionally with country code.
        days: Number of forecast days (1–5). Defaults to 3.

    Returns:
        Dict with per-day 3-hour-interval slots: temperature, condition, wind, humidity.
    """
    return await fetch_forecast(city, days)


# ─────────────────────────────────────────────
# Tool 3: Air quality
# ─────────────────────────────────────────────
@mcp.tool()
async def get_air_quality(city: str) -> dict:
    """Get the current Air Quality Index (AQI) and pollutant breakdown for a city.

    Args:
        city: City name, optionally with country code.

    Returns:
        Dict with AQI index (1=Good … 5=Very Poor), label, and key pollutant levels.
    """
    return await fetch_air_quality(city)


# ─────────────────────────────────────────────
# ASGI app (for uvicorn mcp_server.server:app)
# ─────────────────────────────────────────────
app = mcp.sse_app()

# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "8000"))
    print(f"[MCP Server] Starting SSE server on http://0.0.0.0:{port}/sse")
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.run(transport="sse")
