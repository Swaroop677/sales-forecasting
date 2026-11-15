from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    dataset_id: Optional[str] = None
    run_id: Optional[str] = None
    provider: Optional[str] = Field(default=None, description="gemini | openai | fallback")
    api_key: Optional[str] = Field(default=None, description="Optional BYOK API key")
    base_url: Optional[str] = Field(default=None, description="Optional custom base URL for OpenAI-compatible endpoints")
    model: Optional[str] = Field(default=None, description="Optional model identifier override")


class AutopilotRequest(BaseModel):
    dataset_id: str
    horizon: int = Field(default=30, ge=7, le=180)
    models: Optional[list[str]] = None


class TestConnectionRequest(BaseModel):
    provider: str  # gemini, openai, fallback
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    model: str
    provider: str


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    chart_spec: Optional[dict[str, Any]] = None
    grounding_info: Optional[dict[str, Any]] = None
    created_at: datetime


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    dataset_id: Optional[str] = None
    run_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = Field(default_factory=list)
