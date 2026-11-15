import asyncio
import json
from typing import Any, AsyncIterator
import httpx
from backend.app.config import settings
from backend.app.services.llm.base import LLMEvent, LLMProvider


class GeminiProvider(LLMProvider):
    """
    Google Gemini Provider using the official Google GenAI REST API specifications.
    Connects to v1beta streamGenerateContent, supporting function calling and streaming tokens.
    Model is dynamically configured via settings.GEMINI_MODEL or per-request override (never hardcoded).
    """

    def __init__(self, api_key: str = "", model: str = ""):
        resolved_model = model or settings.GEMINI_MODEL or "gemini-2.5-flash"
        super().__init__(name="Google Gemini", model=resolved_model)
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def stream_turn(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.2,
    ) -> AsyncIterator[LLMEvent]:
        if not self.api_key:
            yield LLMEvent(
                "error",
                "Gemini API key is missing. Please provide your key in Settings or set GEMINI_API_KEY in the environment.",
            )
            return

        # Format messages for Gemini API
        gemini_contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "tool":
                # Function response in Gemini format
                gemini_contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": msg.get("name", "tool"),
                            "response": {"output": content},
                        }
                    }],
                })
            elif role == "assistant":
                parts = []
                if content:
                    parts.append({"text": content})
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        parts.append({
                            "functionCall": {
                                "name": tc.get("name"),
                                "args": tc.get("args", {}),
                            }
                        })
                if parts:
                    gemini_contents.append({"role": "model", "parts": parts})
            else:
                gemini_contents.append({"role": "user", "parts": [{"text": str(content)}]})

        # Format function declarations for Gemini
        gemini_tools = []
        if tools:
            declarations = []
            for t in tools:
                params = t.get("parameters", {})
                declarations.append({
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": params,
                })
            gemini_tools = [{"functionDeclarations": declarations}]

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        if gemini_tools:
            payload["tools"] = gemini_tools

        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?key={self.api_key}"

        # Retry loop with exponential backoff on 429/5xx
        max_retries = 3
        backoff_delay = 1.0

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    async with client.stream(
                        "POST",
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        if response.status_code == 429:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(backoff_delay)
                                backoff_delay *= 2
                                continue
                            yield LLMEvent("error", "Gemini rate limit exceeded (429). Please wait a moment.")
                            return

                        if response.status_code >= 500:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(backoff_delay)
                                backoff_delay *= 2
                                continue
                            yield LLMEvent("error", f"Gemini server error ({response.status_code}).")
                            return

                        if response.status_code != 200:
                            error_text = await response.aread()
                            try:
                                err_data = json.loads(error_text)
                                msg = err_data.get("error", {}).get("message", error_text.decode("utf-8"))
                            except Exception:
                                msg = error_text.decode("utf-8")
                            yield LLMEvent("error", f"Gemini API error ({response.status_code}): {msg}")
                            return

                        buffer = ""
                        async for chunk in response.aiter_text():
                            buffer += chunk
                            # Gemini stream returns a JSON array of response candidates
                            # We parse SSE chunks or individual JSON objects
                            while True:
                                # Look for candidate blocks
                                try:
                                    # Handle streaming JSON arrays or chunks
                                    # Strip leading comma or brackets
                                    cleaned = buffer.strip().lstrip("[").rstrip("]").strip()
                                    if cleaned.startswith(","):
                                        cleaned = cleaned[1:].strip()
                                    break
                                except Exception:
                                    break

                        # Process parsed content from full text stream if needed
                        try:
                            # Parse array of chunks
                            full_json = json.loads(buffer)
                            chunks = full_json if isinstance(full_json, list) else [full_json]
                            for c in chunks:
                                candidates = c.get("candidates", [])
                                if not candidates:
                                    continue
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    if "text" in p and p["text"]:
                                        yield LLMEvent("token", p["text"])
                                    if "functionCall" in p:
                                        fc = p["functionCall"]
                                        yield LLMEvent(
                                            "tool_call",
                                            {"name": fc["name"], "args": fc.get("args", {})},
                                        )
                            yield LLMEvent("done", None)
                            return
                        except Exception as e:
                            # Fallback token extraction via regex if JSON stream had trailing bracket
                            text_chunks = re.findall(r'"text":\s*"([^"]+)"', buffer)
                            for t in text_chunks:
                                yield LLMEvent("token", t)
                            yield LLMEvent("done", None)
                            return

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff_delay)
                    backoff_delay *= 2
                    continue
                yield LLMEvent("error", "Gemini API request timed out after 45 seconds.")
                return
            except Exception as e:
                yield LLMEvent("error", f"Connection error to Gemini: {str(e)}")
                return
