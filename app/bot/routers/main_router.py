"""Central place that wires all feature routers into the Dispatcher.

Order matters: specific content-type/command routers are registered before
the catch-all text handler so commands and media aren't swallowed by it.
"""
from __future__ import annotations

from aiogram import Dispatcher

from app.bot.handlers import (
    basic_handlers,
    budget_handlers,
    confirmation_handlers,
    document_handlers,
    edit_handlers,
    goals_handlers,
    photo_handlers,
    settings_handlers,
    summary_handlers,
    text_handlers,
    voice_handlers,
)


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(basic_handlers.router)
    dp.include_router(summary_handlers.router)
    dp.include_router(budget_handlers.router)
    dp.include_router(goals_handlers.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(edit_handlers.router)
    dp.include_router(confirmation_handlers.router)
    dp.include_router(photo_handlers.router)
    dp.include_router(document_handlers.router)
    dp.include_router(voice_handlers.router)
    # Catch-all free text handler must be last.
    dp.include_router(text_handlers.router)
