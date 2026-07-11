"""Implements `/setfield <token> <field> <value>`, the lightweight way to
correct a single field on a staged (not-yet-saved) transaction before
confirming. Triggered from the Edit button's instructions.
"""
from __future__ import annotations

from datetime import date as Date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.keyboards import confirmation_keyboard
from app.services.transaction_service import transaction_service
from app.utils.formatting import render_confirmation_card, render_multi_confirmation

router = Router(name="edit")

_EDITABLE = {"amount", "category", "date", "merchant", "type"}


@router.message(Command("setfield"))
async def cmd_setfield(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Usage: /setfield <token> <field> <value>")
        return

    _, token, field, value = parts
    field = field.lower()
    if field not in _EDITABLE:
        await message.answer(f"Field must be one of: {', '.join(sorted(_EDITABLE))}")
        return

    batch = transaction_service.get_pending(token)
    if not batch or not batch.transactions:
        await message.answer("This confirmation has expired. Please send the transaction again.")
        return

    tx = batch.transactions[0]
    try:
        if field == "amount":
            tx.amount = float(value.replace(",", "").replace(".", ""))
        elif field == "date":
            tx.date = Date.fromisoformat(value)
        else:
            setattr(tx, field, value)
    except Exception:  # noqa: BLE001
        await message.answer(f"Couldn't apply that value to '{field}'. Please check the format.")
        return

    card = (
        render_confirmation_card(batch.transactions[0])
        if len(batch.transactions) == 1
        else render_multi_confirmation(batch.transactions)
    )
    await message.answer(card, parse_mode="Markdown", reply_markup=confirmation_keyboard(token))
