from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional


class LLMEvent:
    def __init__(self, event_type: str, data: Any):
        self.event_type = event_type  # token, tool_call, error, done
        self.data = data


class LLMProvider(ABC):
    """Abstract interface for LLM Providers (Gemini, OpenAI-Compatible, Fallback)."""

    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    @abstractmethod
    async def stream_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[LLMEvent]:
        """
        Streams one model turn.
        Yields LLMEvent objects:
        - LLMEvent('token', 'text chunk')
        - LLMEvent('tool_call', {'name': 'tool_name', 'args': {...}})
        - LLMEvent('error', 'error description')
        - LLMEvent('done', None)
        """
        pass
