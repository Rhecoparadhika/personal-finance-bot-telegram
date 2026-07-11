from __future__ import annotations

import asyncio

import google.generativeai as genai

from app.config.settings import settings
from app.llm.base import LLMProvider
from app.utils.retry import retryable


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config={"response_mime_type": "application/json", "temperature": 0},
        )
        self._text_model = genai.GenerativeModel(
            settings.gemini_model, generation_config={"temperature": 0.3}
        )

    @retryable((Exception,), attempts=3)
    async def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
        # google-generativeai's client is sync; run it off the event loop thread.
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        return response.text or "{}"

    @retryable((Exception,), attempts=3)
    async def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
        response = await asyncio.to_thread(self._text_model.generate_content, prompt)
        return response.text or ""
