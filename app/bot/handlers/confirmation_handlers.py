"""Handles the inline-keyboard callbacks attached to every confirmation
card: Save / Edit / Cancel, plus the field-picker for Edit.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards import edit_field_keyboard
from app.services.transaction_service import transaction_service
from app.utils.formatting import render_confirmation_card

router = Router(name="confirmation")


@router.callback_query(F.data.startswith("tx_save:"))
async def on_save(callback: CallbackQuery) -> None:
    token = callback.data.split(":", 1)[1]
    saved, alerts = await transaction_service.confirm_and_save(token)

    if not saved:
        await callback.answer("Nothing to save (already handled or expired).", show_alert=True)
        return

    if len(saved) == 1:
        text = render_confirmation_card(saved[0], pending=False)
    else:
        text = f"✅ *{len(saved)} transactions saved!*"

    if alerts:
        text += "\n\n" + "\n\n".join(alerts)

    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer("Saved ✅")


@router.callback_query(F.data.startswith("tx_cancel:"))
async def on_cancel(callback: CallbackQuery) -> None:
    token = callback.data.split(":", 1)[1]
    transaction_service.discard(token)
    await callback.message.edit_text("❌ Cancelled — nothing was saved.")
    await callback.answer()


@router.callback_query(F.data.startswith("tx_edit:"))
async def on_edit(callback: CallbackQuery) -> None:
    token = callback.data.split(":", 1)[1]
    batch = transaction_service.get_pending(token)
    if not batch:
        await callback.answer("This confirmation has expired.", show_alert=True)
        return
    await callback.message.edit_reply_markup(reply_markup=edit_field_keyboard(token))
    await callback.answer()


@router.callback_query(F.data.startswith("tx_back:"))
async def on_back(callback: CallbackQuery) -> None:
    token = callback.data.split(":", 1)[1]
    batch = transaction_service.get_pending(token)
    if not batch:
        await callback.answer("This confirmation has expired.", show_alert=True)
        return
    from app.bot.keyboards import confirmation_keyboard
    from app.utils.formatting import render_confirmation_card, render_multi_confirmation

    card = (
        render_confirmation_card(batch.transactions[0])
        if len(batch.transactions) == 1
        else render_multi_confirmation(batch.transactions)
    )
    await callback.message.edit_text(card, parse_mode="Markdown", reply_markup=confirmation_keyboard(token))
    await callback.answer()


@router.callback_query(F.data.startswith("tx_editfield:"))
async def on_edit_field(callback: CallbackQuery) -> None:
    _, token, field = callback.data.split(":", 2)
    batch = transaction_service.get_pending(token)
    if not batch:
        await callback.answer("This confirmation has expired.", show_alert=True)
        return
    await callback.answer(
        f"Reply with the new value for '{field}' as: /setfield {token} {field} <value>",
        show_alert=True,
    )
