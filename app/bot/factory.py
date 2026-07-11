from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.middlewares.error_guard import ErrorGuardMiddleware
from app.bot.middlewares.logging_middleware import LoggingMiddleware
from app.bot.routers.main_router import register_routers
from app.config.settings import settings


def create_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(ErrorGuardMiddleware())
    register_routers(dp)
    return dp
