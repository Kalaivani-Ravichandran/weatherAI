import os
import json
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

load_dotenv(override=True)  

SYSTEM_PROMPT = """You are a knowledgeable and friendly weather assistant powered by real-time data.

You have access to three tools:
• get_current_weather: current conditions (temperature, humidity, wind, etc.)
• get_weather_forecast: day-by-day forecast for up to 5 days
• get_air_quality: Air Quality Index (AQI) and pollutant breakdown

Guidelines:
1. Always call the appropriate tool(s) before answering — never guess weather data.
2. If a question involves multiple cities or aspects, call multiple tools.
3. Translate raw numbers into plain language.
4. Provide practical advice when relevant.
5. Report temperatures in Celsius and wind in m/s unless the user asks otherwise.
6. For air quality, explain what the AQI level means in everyday terms.
7. Keep your final answer concise and well-structured.
"""

async def run_agent(user_message: str) -> dict[str, Any]:
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    print("Using model:", llm_model)
    print("Using key prefix:", openai_api_key[:12])  # debug only, then remove

    llm = ChatOpenAI(
        model=llm_model,
        openai_api_key=openai_api_key,
        temperature=0,
        max_tokens=4096,
    )

    mcp_client = MultiServerMCPClient(
        {
            "weather": {
                "url": mcp_server_url,
                "transport": "sse",
            }
        }
    )
    tools = await mcp_client.get_tools()

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=user_message)]}
    )

    messages = result["messages"]
    final_answer = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            final_answer = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    tool_call_log = []
    pending_calls: dict[str, dict] = {}

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                pending_calls[tc["id"]] = {
                    "tool_name": tc["name"],
                    "tool_input": tc["args"],
                }
        elif isinstance(msg, ToolMessage):
            call_info = pending_calls.pop(msg.tool_call_id, {})
            raw_output = msg.content
            try:
                parsed = json.loads(raw_output) if isinstance(raw_output, str) else raw_output
            except (json.JSONDecodeError, TypeError):
                parsed = raw_output

            tool_call_log.append(
                {
                    "tool_name": call_info.get("tool_name", "unknown"),
                    "tool_input": call_info.get("tool_input", {}),
                    "tool_output": parsed,
                }
            )

    return {"response": final_answer, "tool_calls": tool_call_log}