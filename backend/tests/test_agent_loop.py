import asyncio
import json
from typing import Any, AsyncIterator
import pytest
from sqlmodel import Session, select
from backend.app.api.datasets import create_sample_dataset
from backend.app.db import engine, init_db
from backend.app.models.chat import ChatMessage, ChatSession
from backend.app.models.dataset import Dataset
from backend.app.services.agent_runner import run_agent_stream
from backend.app.services.llm.base import LLMEvent, LLMProvider


class MockTwoTurnProvider(LLMProvider):
    """Mocks a 2-turn conversation: Turn 1 triggers a tool, Turn 2 gives final answer."""

    def __init__(self):
        super().__init__(name="MockLLM", model="mock-model-v1")
        self.turn_count = 0

    async def stream_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[LLMEvent]:
        self.turn_count += 1
        # Check if last message is a tool response
        last_msg = messages[-1] if messages else {}
        if last_msg.get("role") == "tool":
            # Turn 2: Answer with verified facts from tool
            yield LLMEvent("token", "Dataset health score is 99 out of 100.")
            yield LLMEvent("done", None)
        else:
            # Turn 1: Emit tool call
            yield LLMEvent("tool_call", {"name": "validate_data", "args": {}})


class MockInfiniteLoopProvider(LLMProvider):
    """Mocks an adversarial provider that requests tools indefinitely to test the 6-step iteration cap."""

    def __init__(self):
        super().__init__(name="MockLoopLLM", model="mock-loop-v1")

    async def stream_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[LLMEvent]:
        # Always request a tool call
        yield LLMEvent("tool_call", {"name": "validate_data", "args": {}})


@pytest.fixture(autouse=True)
def setup_data():
    init_db()
    with Session(engine) as session:
        if not session.exec(select(Dataset).limit(1)).first():
            create_sample_dataset(session)


def test_agent_orchestration_loop_success():
    async def _run():
        with Session(engine) as session:
            dataset_id = session.exec(select(Dataset).limit(1)).first().id

        mock_provider = MockTwoTurnProvider()
        events_received = []

        async for chunk in run_agent_stream(
            user_query="Please validate my dataset",
            provider=mock_provider,
            dataset_id=dataset_id,
        ):
            for line in chunk.strip().split("\n"):
                if line.startswith("event:"):
                    events_received.append(line[len("event:"):].strip())

        # Verify event sequence
        assert "tool_start" in events_received
        assert "tool_result" in events_received
        assert "token" in events_received
        assert "grounding" in events_received
        assert "done" in events_received

        # Verify ChatSession and Messages are stored in SQLite
        with Session(engine) as session:
            latest_session = session.exec(select(ChatSession).order_by(ChatSession.created_at.desc()).limit(1)).first()
            assert latest_session is not None
            msgs = session.exec(select(ChatMessage).where(ChatMessage.session_id == latest_session.id)).all()
            assert len(msgs) == 2  # user message + assistant message
            assistant_msg = [m for m in msgs if m.role == "assistant"][0]
            assert "health score is 99 out of 100" in assistant_msg.content
            assert len(assistant_msg.tool_calls) == 1
            assert assistant_msg.tool_calls[0]["name"] == "validate_data"

    asyncio.run(_run())


def test_agent_tool_loop_caps_at_max_steps():
    async def _run():
        with Session(engine) as session:
            dataset_id = session.exec(select(Dataset).limit(1)).first().id

        loop_provider = MockInfiniteLoopProvider()
        tool_starts = 0

        async for chunk in run_agent_stream(
            user_query="Trigger infinite loop test",
            provider=loop_provider,
            dataset_id=dataset_id,
        ):
            if "event: tool_start" in chunk:
                tool_starts += 1

        # Must be bounded by MAX_AGENT_TOOL_STEPS (6)
        assert tool_starts <= 6

    asyncio.run(_run())
