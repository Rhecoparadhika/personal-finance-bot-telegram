from __future__ import annotations

import asyncio

import google.generativeai as genai

from app.config.settings import settings
from app.llm.base import LLMProvider, Message, merge_history
from app.utils.retry import retryable


def _fold_history(history: list[Message] | None, user_prompt: str) -> str:
    """Gemini's simple text client has no multi-turn message array here, so we
    fold the conversation into one labelled transcript ending with the user."""
    lines = []
    for turn in merge_history(history, user_prompt):
        tag = "Assistant" if turn["role"] == "assistant" else "User"
        lines.append(f"{tag}: {turn['content']}")
    return "\n".join(lines)


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = settings.gemini_api_key
        if not api_key or not api_key.strip() or "..." in api_key or "your" in api_key.lower():
            raise RuntimeError("Gemini API key is not configured. Set GEMINI_API_KEY to a real value in .env.")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config={"response_mime_type": "application/json", "temperature": 0},
        )
        self._text_model = genai.GenerativeModel(
            settings.gemini_model, generation_config={"temperature": 0.3}
        )

    @retryable((Exception,), attempts=3)
    async def complete_json(
        self, system_prompt: str, user_prompt: str, history: list[Message] | None = None
    ) -> str:
        prompt = f"{system_prompt}\n\n---\n\n{_fold_history(history, user_prompt)}"
        # google-generativeai's client is sync; run it off the event loop thread.
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        return response.text or "{}"

    @retryable((Exception,), attempts=3)
    async def complete_text(
        self, system_prompt: str, user_prompt: str, history: list[Message] | None = None
    ) -> str:
        prompt = f"{system_prompt}\n\n---\n\n{_fold_history(history, user_prompt)}"
        response = await asyncio.to_thread(self._text_model.generate_content, prompt)
        return response.text or ""
