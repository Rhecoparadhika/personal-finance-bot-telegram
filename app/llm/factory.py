from __future__ import annotations

from functools import lru_cache

from app.llm.base import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    from app.llm.providers.openai_provider import OpenAIProvider

    return OpenAIProvider()
