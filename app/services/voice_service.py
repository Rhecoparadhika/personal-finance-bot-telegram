"""Transcribes Telegram voice notes (OGG/Opus) using the OpenAI Whisper API.
Whisper is used regardless of the active LLM_PROVIDER since it's the most
reliable hosted speech-to-text option; the resulting text is then handed to
the normal text transaction parser.
"""
from __future__ import annotations

import io

from openai import AsyncOpenAI

from app.config.settings import settings
from app.utils.retry import retryable


class TranscriptionError(Exception):
    pass


@retryable((Exception,), attempts=3)
async def transcribe_voice(ogg_bytes: bytes, filename: str = "voice.ogg") -> str:
    if not settings.openai_api_key:
        raise TranscriptionError("Voice transcription requires OPENAI_API_KEY to be set.")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    audio_file = io.BytesIO(ogg_bytes)
    audio_file.name = filename  # the SDK reads .name for multipart upload

    try:
        transcript = await client.audio.transcriptions.create(
            model=settings.whisper_model,
            file=audio_file,
            language=None,  # auto-detect Indonesian/English/mixed
        )
    except Exception as exc:  # noqa: BLE001
        raise TranscriptionError("Could not transcribe this voice note.") from exc

    text = (transcript.text or "").strip()
    if not text:
        raise TranscriptionError("Voice note seems to be empty or unclear.")
    return text
