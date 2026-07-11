"""Catches exceptions that escape handlers and replies to the user with a
friendly message instead of leaving them hanging, while still letting the
logging middleware/log record the real error for debugging.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger


class ErrorGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error guard caught: {}", exc)
            chat = None
            if isinstance(event, Update):
                if event.message:
                    chat = event.message.chat
                elif event.callback_query and event.callback_query.message:
                    chat = event.callback_query.message.chat
            if chat is not None:
                bot = data.get("bot")
                if bot is not None:
                    try:
                        await bot.send_message(
                            chat.id,
                            "⚠️ Something went wrong on my end. Please try again in a moment.",
                        )
                    except Exception:  # noqa: BLE001
                        logger.error("Failed to send error notice to user")
            return None
