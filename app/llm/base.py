"""Provider-agnostic interface. Every concrete provider (OpenAI, Claude,
Gemini) implements `complete_json`, which must return a raw JSON string.
Swapping providers is a one-line change in `llm/factory.py`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        """Call the underlying model in JSON-mode and return its raw text
        response. Callers are responsible for stripping/parsing JSON.
        """
        raise NotImplementedError

    @abstractmethod
    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        """Call the underlying model for a free-text (non-JSON) response,
        e.g. conversational Q&A answers."""
        raise NotImplementedError
