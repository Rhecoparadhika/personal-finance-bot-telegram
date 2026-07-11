"""Provider-agnostic interface. Every concrete provider (OpenAI, Claude,
Gemini) implements `complete_json`, which must return a raw JSON string.
Swapping providers is a one-line change in `llm/factory.py`.

Both methods accept an optional `history` — a list of prior
{"role": "user"|"assistant", "content": str} turns — so the bot can keep
context across the last few messages (see `services/conversation_memory.py`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

# A single conversation turn as stored in memory / passed to providers.
Message = dict[str, str]


def merge_history(history: list[Message] | None, user_prompt: str) -> list[Message]:
    """Return a clean, strictly-alternating user/assistant message list that
    ends with the current `user_prompt`.

    Coalesces consecutive same-role turns (some providers — notably Claude —
    reject two user or two assistant messages in a row) and drops any leading
    assistant turn (a conversation must start with the user).
    """
    turns: list[Message] = list(history or []) + [{"role": "user", "content": user_prompt}]
    merged: list[Message] = []
    for turn in turns:
        role = "assistant" if turn.get("role") == "assistant" else "user"
        content = turn.get("content") or ""
        if merged and merged[-1]["role"] == role:
            merged[-1]["content"] += "\n" + content
        else:
            merged.append({"role": role, "content": content})
    while merged and merged[0]["role"] == "assistant":
        merged.pop(0)
    return merged


class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(
        self, system_prompt: str, user_prompt: str, history: list[Message] | None = None
    ) -> str:
        """Call the underlying model in JSON-mode and return its raw text
        response. Callers are responsible for stripping/parsing JSON.
        """
        raise NotImplementedError

    @abstractmethod
    async def complete_text(
        self, system_prompt: str, user_prompt: str, history: list[Message] | None = None
    ) -> str:
        """Call the underlying model for a free-text (non-JSON) response,
        e.g. conversational Q&A answers."""
        raise NotImplementedError
