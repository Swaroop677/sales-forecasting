import asyncio
import json
from typing import Any, AsyncIterator
import httpx
from backend.app.config import settings
from backend.app.services.llm.base import LLMEvent, LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """
    OpenAI-compatible streaming provider.
    Works seamlessly with OpenAI, Groq, OpenRouter, Ollama, and LocalAI.
    Base URL, API Key, and Model are fully customizable per request or via environment.
    """

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        resolved_model = model or settings.OPENAI_MODEL or "gpt-4o-mini"
        super().__init__(name="OpenAI-Compatible", model=resolved_model)
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")

    async def stream_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[LLMEvent]:
        # Formatted messages with system prompt
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "tool":
                formatted_messages.append({
                    "role": "tool",
                    "content": json.dumps(content) if isinstance(content, (dict, list)) else str(content),
                    "tool_call_id": m.get("tool_call_id", f"call_{m.get('name', 'tool')}"),
                })
            elif role == "assistant":
                item = {"role": "assistant", "content": content or ""}
                if m.get("tool_calls"):
                    item["tool_calls"] = [
                        {
                            "id": f"call_{tc.get('name')}",
                            "type": "function",
                            "function": {
                                "name": tc.get("name"),
                                "arguments": json.dumps(tc.get("args", {})),
                            },
                        }
                        for tc in m["tool_calls"]
                    ]
                formatted_messages.append(item)
            else:
                formatted_messages.append({"role": "user", "content": str(content)})

        # Formatted tools for OpenAI API
        formatted_tools = [
            {"type": "function", "function": t}
            for t in tools
        ] if tools else None

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "stream": True,
        }
        if formatted_tools:
            payload["tools"] = formatted_tools
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
        }

        url = f"{self.base_url}/chat/completions"

        max_retries = 3
        backoff_delay = 1.0

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    async with client.stream(
                        "POST",
                        url,
                        json=payload,
                        headers=headers,
                    ) as response:
                        if response.status_code == 429:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(backoff_delay)
                                backoff_delay *= 2
                                continue
                            yield LLMEvent("error", "Rate limit reached (429). Please retry shortly.")
                            return

                        if response.status_code >= 500:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(backoff_delay)
                                backoff_delay *= 2
                                continue
                            yield LLMEvent("error", f"Provider service error ({response.status_code}).")
                            return

                        if response.status_code != 200:
                            err_body = await response.aread()
                            yield LLMEvent("error", f"Provider error ({response.status_code}): {err_body.decode('utf-8')}")
                            return

                        # Accumulate tool calls if streamed in parts
                        tool_calls_acc: dict[int, dict[str, Any]] = {}

                        async for line in response.aiter_lines():
                            line = line.strip()
                            if not line or not line.startswith("data:"):
                                continue

                            data_str = line[len("data:"):].strip()
                            if data_str == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data_str)
                            except Exception:
                                continue

                            choices = chunk.get("choices", [])
                            if not choices:
                                continue

                            delta = choices[0].get("delta", {})

                            # Content tokens
                            if "content" in delta and delta["content"]:
                                yield LLMEvent("token", delta["content"])

                            # Tool calls
                            if "tool_calls" in delta and delta["tool_calls"]:
                                for tc in delta["tool_calls"]:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_calls_acc:
                                        tool_calls_acc[idx] = {
                                            "name": "",
                                            "args_str": "",
                                        }

                                    func = tc.get("function", {})
                                    if func.get("name"):
                                        tool_calls_acc[idx]["name"] = func["name"]
                                    if func.get("arguments"):
                                        tool_calls_acc[idx]["args_str"] += func["arguments"]

                        # Emit completed tool calls
                        for idx, tc_data in tool_calls_acc.items():
                            name = tc_data["name"]
                            args_str = tc_data["args_str"]
                            try:
                                args = json.loads(args_str) if args_str else {}
                            except Exception:
                                args = {}
                            yield LLMEvent("tool_call", {"name": name, "args": args})

                        yield LLMEvent("done", None)
                        return

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= 2
                    continue
                yield LLMEvent("error", "Request timed out after 45 seconds.")
                return
            except Exception as e:
                yield LLMEvent("error", f"Provider connection error: {str(e)}")
                return
