from __future__ import annotations

from openai import AsyncOpenAI

from app.config.settings import settings
from app.llm.base import LLMProvider
from app.utils.retry import retryable


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @retryable((Exception,), attempts=3)
    async def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or "{}"

    @retryable((Exception,), attempts=3)
    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
