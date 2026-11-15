import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    title: str = Field(default="New Conversation")
    dataset_id: Optional[str] = Field(default=None, index=True)
    run_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: str = Field(default_factory=generate_uuid, primary_key=True)
    session_id: str = Field(index=True)
    role: str = Field(index=True)  # user, assistant, system, tool
    content: str = Field(default="")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    chart_spec: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    grounding_info: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
