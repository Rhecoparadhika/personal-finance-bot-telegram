from __future__ import annotations

from functools import lru_cache

from app.config.settings import settings
from app.llm.base import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider
    if provider == "openai":
        from app.llm.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if provider == "claude":
        from app.llm.providers.claude_provider import ClaudeProvider
        return ClaudeProvider()
    if provider == "gemini":
        from app.llm.providers.gemini_provider import GeminiProvider
        return GeminiProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
