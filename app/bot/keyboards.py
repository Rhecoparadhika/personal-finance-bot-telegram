from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirmation_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Save", callback_data=f"tx_save:{token}"),
        InlineKeyboardButton(text="✏️ Edit", callback_data=f"tx_edit:{token}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"tx_cancel:{token}"),
    ]])


def import_preview_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Import All", callback_data=f"tx_save:{token}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"tx_cancel:{token}"),
    ]])


def edit_field_keyboard(token: str) -> InlineKeyboardMarkup:
    fields = ["amount", "category", "date", "merchant", "type"]
    rows = [[InlineKeyboardButton(text=f.title(), callback_data=f"tx_editfield:{token}:{f}")] for f in fields]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"tx_back:{token}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
