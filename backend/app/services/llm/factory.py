from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from backend.app.config import settings
from backend.app.services.llm.base import LLMProvider
from backend.app.services.llm.fallback_provider import FallbackProvider
from backend.app.services.llm.gemini_provider import GeminiProvider
from backend.app.services.llm.openai_provider import OpenAICompatibleProvider

# In-memory IP rate limiter: {ip_address: [timestamp, timestamp, ...]}
_ip_rate_limits: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(client_ip: str) -> bool:
    """Returns True if request is within limits, False if rate exceeded."""
    now = datetime.now(timezone.utc).timestamp()
    window = 60.0  # 60 seconds
    limit = settings.AGENT_RATE_LIMIT_PER_MINUTE

    # Prune timestamps older than window
    timestamps = [t for t in _ip_rate_limits[client_ip] if now - t < window]
    if len(timestamps) >= limit:
        _ip_rate_limits[client_ip] = timestamps
        return False

    timestamps.append(now)
    _ip_rate_limits[client_ip] = timestamps
    return True


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """
    Factory that instantiates the appropriate LLM provider.
    Priority:
    1. Explicit requested provider (if keys exist)
    2. Configured environment default
    3. Rule-based FallbackProvider (guarantees zero downtime with NO key)
    """
    chosen = (provider_name or settings.DEFAULT_LLM_PROVIDER or "gemini").lower().strip()

    # 1. Fallback Provider (No API key needed)
    if chosen == "fallback":
        return FallbackProvider()

    # 2. Gemini Provider
    if chosen in ["gemini", "google"]:
        gemini_key = api_key or settings.GEMINI_API_KEY
        if gemini_key:
            return GeminiProvider(api_key=gemini_key, model=model or settings.GEMINI_MODEL)
        # If no key is available, gracefully fallback rather than crashing
        return FallbackProvider()

    # 3. OpenAI-Compatible Provider (Groq, OpenRouter, Ollama, OpenAI)
    if chosen in ["openai", "groq", "openrouter", "ollama", "local"]:
        openai_key = api_key or settings.OPENAI_API_KEY
        resolved_base_url = base_url or settings.OPENAI_BASE_URL
        if openai_key or "localhost" in resolved_base_url or "127.0.0.1" in resolved_base_url:
            return OpenAICompatibleProvider(
                api_key=openai_key,
                base_url=resolved_base_url,
                model=model or settings.OPENAI_MODEL,
            )
        return FallbackProvider()

    # Default fallback
    return FallbackProvider()
