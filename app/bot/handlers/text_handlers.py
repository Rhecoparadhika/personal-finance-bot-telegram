"""Handles free-text messages: the primary way users log transactions.
Also doubles as the AI-chat entry point when the LLM parser finds no
transaction in the message (treated as a question instead).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.llm.transaction_parser import parse_text_to_transactions
from app.models.enums import TransactionSource
from app.services.ai_chat_service import answer_question
from app.services.transaction_service import transaction_service
from app.utils.formatting import render_confirmation_card, render_multi_confirmation
from app.bot.keyboards import confirmation_keyboard

router = Router(name="text")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message) -> None:
    text = message.text or ""
    await message.bot.send_chat_action(message.chat.id, "typing")

    result = await parse_text_to_transactions(text)

    if not result.transactions:
        # No transaction detected -> treat as a conversational question.
        answer = await answer_question(text)
        await message.answer(answer)
        return

    batch = transaction_service.stage(message.chat.id, result.transactions, TransactionSource.TEXT)

    if len(result.transactions) == 1:
        card = render_confirmation_card(result.transactions[0])
    else:
        card = render_multi_confirmation(result.transactions)

    if result.warning:
        card += f"\n\n⚠️ _{result.warning}_"

    await message.answer(card, parse_mode="Markdown", reply_markup=confirmation_keyboard(batch.token))
