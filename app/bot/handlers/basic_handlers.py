from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="basic")

_WELCOME = """👋 *Welcome to FinBot!*

I'm your personal finance assistant. Just chat with me like a friend:

_"Makan bakso 25rb"_
_"Isi bensin 100 ribu"_
_"Gajian 15 juta"_
_"Beli saham BBCA 5 lot"_

I understand text, receipt photos 📸, bank statement PDFs 📄, CSV files, and voice notes 🎙️.

Type /help to see everything I can do."""

_HELP = """*🤖 FinBot Commands*

*Recording*
Just type naturally, send a receipt photo, a PDF/CSV statement, or a voice note.

*Reports*
/today — today's summary
/month — this month's summary
/summary — quick overview
/report — generate a PDF report
/chart — visualize your spending
/export — export your data

*Planning*
/budget — set & check budgets
/goals — track savings goals

*Other*
/settings — preferences
/help — this message

*Ask me anything*, e.g. "How much did I spend on food this month?" 💬"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(_WELCOME, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(_HELP, parse_mode="Markdown")
