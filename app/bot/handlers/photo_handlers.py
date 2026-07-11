from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.llm.transaction_parser import parse_receipt_text
from app.models.enums import TransactionSource
from app.ocr.receipt_ocr import OCRExtractionError, extract_text_from_receipt
from app.bot.keyboards import confirmation_keyboard
from app.services.transaction_service import transaction_service
from app.utils.formatting import render_confirmation_card, render_multi_confirmation

router = Router(name="photo")


@router.message(F.photo)
async def handle_photo(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, "typing")
    largest = message.photo[-1]
    file = await message.bot.get_file(largest.file_id)
    buffer = await message.bot.download_file(file.file_path)
    image_bytes = buffer.read()

    try:
        ocr_text = extract_text_from_receipt(image_bytes)
    except OCRExtractionError as exc:
        await message.answer(f"📸 {exc}")
        return

    result = await parse_receipt_text(ocr_text)
    if not result.transactions:
        await message.answer(
            "📸 I couldn't find a clear transaction on this receipt. "
            "You can type it manually instead, e.g. \"Makan bakso 25rb\"."
        )
        return

    batch = transaction_service.stage(message.chat.id, result.transactions, TransactionSource.OCR)
    card = (
        render_confirmation_card(result.transactions[0])
        if len(result.transactions) == 1
        else render_multi_confirmation(result.transactions)
    )
    if result.warning:
        card += f"\n\n⚠️ _{result.warning}_"
    await message.answer(card, parse_mode="Markdown", reply_markup=confirmation_keyboard(batch.token))
