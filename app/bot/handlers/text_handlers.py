"""Handles free-text messages: the primary way users log transactions.
Also doubles as the AI-chat entry point when the LLM parser finds no
transaction in the message (treated as a question instead).

Two behaviours layered on top of plain parsing:
  1. Short-term memory — the last few turns per chat are kept and fed back to
     the LLM so context isn't lost (`conversation_memory`).
  2. Slot-filling — when a single transaction is parsed but columns are empty,
     the bot asks follow-up questions one at a time until it's complete or the
     user opts out (`clarification_service`).
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.bot.keyboards import confirmation_keyboard
from app.llm.transaction_parser import parse_text_to_transactions
from app.models.enums import TransactionSource
from app.schemas.transaction import TransactionCreate
from app.services.ai_chat_service import answer_finance_question
from app.services.clarification_service import clarification_service
from app.services.conversation_memory import conversation_memory
from app.services.transaction_service import transaction_service
from app.utils.formatting import render_confirmation_card, render_multi_confirmation

router = Router(name="text")


async def _reply(message: Message, text: str, **kwargs) -> None:
    """Send a reply and remember it, so the next turn has full context."""
    await message.answer(text, **kwargs)
    conversation_memory.record_assistant(message.chat.id, text)


async def _stage_and_show(
    message: Message,
    transactions: list[TransactionCreate],
    source: TransactionSource,
    warning: str | None = None,
) -> None:
    batch = transaction_service.stage(message.chat.id, transactions, source)
    if len(transactions) == 1:
        card = render_confirmation_card(transactions[0])
    else:
        card = render_multi_confirmation(transactions)
    if warning:
        card += f"\n\n⚠️ _{warning}_"
    await message.answer(card, parse_mode="Markdown", reply_markup=confirmation_keyboard(batch.token))
    # A compact marker (not the full card) keeps the memory window useful.
    conversation_memory.record_assistant(message.chat.id, "(menampilkan kartu konfirmasi transaksi)")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message) -> None:
    text = message.text or ""
    chat_id = message.chat.id
    # Snapshot the prior turns BEFORE recording this one, so the current
    # message isn't duplicated (once in history, once as the prompt).
    history = conversation_memory.history(chat_id)
    conversation_memory.record_user(chat_id, text)
    await message.bot.send_chat_action(chat_id, "typing")

    # 1. Mid-clarification? Treat this message as the answer to the pending field.
    if clarification_service.get(chat_id):
        step = clarification_service.apply_answer(chat_id, text)
        if step.status == "cancelled":
            await _reply(message, "❌ Oke, dibatalkan — tidak ada yang disimpan.")
            return
        if step.status == "ask":
            await _reply(message, step.question)
            return
        if step.tx is not None:  # status == "done"
            await _stage_and_show(message, [step.tx], TransactionSource.TEXT)
            return

    # 2. Normal parse, with the last few turns as context.
    result = await parse_text_to_transactions(text, history=history)

    if result.chat_response:
        # Not a transaction — the parser only detected "this is conversation",
        # its own reply text is ungrounded (no spreadsheet access) and is
        # discarded. Answer for real using actual data from the sheet.
        answer = await answer_finance_question(text, history=history)
        await _reply(message, answer)
        return

    if not result.transactions:
        await _reply(message, result.warning or "Maaf, saya tidak mengerti. Bisa coba lagi?")
        return

    # 3. Single transaction -> chase empty columns before showing the card.
    if len(result.transactions) == 1:
        started, question = clarification_service.start(
            chat_id, result.transactions[0], TransactionSource.TEXT
        )
        if started:
            await _reply(message, question)
            return

    await _stage_and_show(message, result.transactions, TransactionSource.TEXT, warning=result.warning)
