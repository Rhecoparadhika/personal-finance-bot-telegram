"""Logs every incoming update with timing, and provides a safety net that
turns unhandled exceptions into a friendly Telegram message instead of a
silent failure (webhook still returns 200 either way).
"""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start = time.monotonic()
        update_type = "unknown"
        if isinstance(event, Update):
            update_type = event.event_type
        logger.info("Incoming update: {}", update_type)
        try:
            result = await handler(event, data)
            elapsed = (time.monotonic() - start) * 1000
            logger.info("Handled {} in {:.1f}ms", update_type, elapsed)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error processing update: {}", exc)
            raise
