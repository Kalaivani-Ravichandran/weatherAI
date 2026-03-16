"""
Pydantic schemas for the FastAPI request/response contract.
"""

from typing import Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's natural-language query")


class ToolCallRecord(BaseModel):
    tool_name: str
    tool_input: dict
    tool_output: Any


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's final answer")
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list,
        description="Ordered list of tool invocations made during reasoning",
    )
