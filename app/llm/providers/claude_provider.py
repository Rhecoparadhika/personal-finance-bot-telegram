from __future__ import annotations

from anthropic import AsyncAnthropic

from app.config.settings import settings
from app.llm.base import LLMProvider
from app.utils.retry import retryable


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.claude_api_key)

    @retryable((Exception,), attempts=3)
    async def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.messages.create(
            model=settings.claude_model,
            max_tokens=2000,
            temperature=0,
            system=system_prompt + "\n\nRespond with ONLY the JSON object, no other text.",
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]  # type: ignore[attr-defined]
        return "".join(text_blocks) or "{}"

    @retryable((Exception,), attempts=3)
    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.messages.create(
            model=settings.claude_model,
            max_tokens=1000,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_blocks = [b.text for b in response.content if b.type == "text"]  # type: ignore[attr-defined]
        return "".join(text_blocks)
