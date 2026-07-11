from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config.settings import settings

router = Router(name="settings")


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    text = (
        "*⚙️ Settings*\n\n"
        f"🌐 Timezone: `{settings.timezone}`\n"
        f"💱 Currency: `{settings.default_currency}`\n"
        f"🧠 AI Provider: `{settings.llm_provider}`\n\n"
        "_To change these, update the environment variables and redeploy._"
    )
    await message.answer(text, parse_mode="Markdown")
