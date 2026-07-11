from __future__ import annotations

from openai import AsyncOpenAI

from app.config.settings import settings
from app.llm.base import LLMProvider, Message, merge_history
from app.utils.retry import retryable


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = settings.openai_api_key
        if not api_key or not api_key.strip() or "..." in api_key or "your" in api_key.lower():
            raise RuntimeError("OpenAI API key is not configured. Set OPENAI_API_KEY to a real value in .env.")
        self._client = AsyncOpenAI(api_key=api_key)

    @retryable((Exception,), attempts=3)
    async def complete_json(
        self, system_prompt: str, user_prompt: str, history: list[Message] | None = None
    ) -> str:
        response = await self._client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system_prompt}, *merge_history(history, user_prompt)],
        )
        return response.choices[0].message.content or "{}"

    @retryable((Exception,), attempts=3)
    async def complete_text(
        self, system_prompt: str, user_prompt: str, history: list[Message] | None = None
    ) -> str:
        response = await self._client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.3,
            messages=[{"role": "system", "content": system_prompt}, *merge_history(history, user_prompt)],
        )
        return response.choices[0].message.content or ""
