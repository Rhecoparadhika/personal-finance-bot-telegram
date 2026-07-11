from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.llm.transaction_parser import parse_pdf_statement_text, parse_text_to_transactions
from app.models.enums import TransactionSource
from app.pdf.csv_extractor import CSVParseError, extract_csv_text
from app.pdf.statement_extractor import PDFExtractionError, extract_statement_text
from app.bot.keyboards import import_preview_keyboard
from app.services.transaction_service import transaction_service
from app.utils.formatting import render_multi_confirmation

router = Router(name="document")

_MAX_PREVIEW = 15


@router.message(F.document)
async def handle_document(message: Message) -> None:
    doc = message.document
    filename = (doc.file_name or "").lower()
    await message.bot.send_chat_action(message.chat.id, "typing")

    file = await message.bot.get_file(doc.file_id)
    buffer = await message.bot.download_file(file.file_path)
    file_bytes = buffer.read()

    if filename.endswith(".pdf") or doc.mime_type == "application/pdf":
        try:
            text = extract_statement_text(file_bytes)
        except PDFExtractionError as exc:
            await message.answer(f"📄 {exc}")
            return
        result = await parse_pdf_statement_text(text)
        source = TransactionSource.PDF

    elif filename.endswith(".csv") or doc.mime_type == "text/csv":
        try:
            text = extract_csv_text(file_bytes)
        except CSVParseError as exc:
            await message.answer(f"📄 {exc}")
            return
        result = await parse_text_to_transactions(
            "The following is raw CSV data (rows separated by newline, cells by ' | '). "
            "The first row is likely a header. Extract every transaction row.\n\n" + text
        )
        source = TransactionSource.CSV

    else:
        await message.answer("📄 I can only import PDF bank statements or CSV files for now.")
        return

    if not result.transactions:
        await message.answer("📄 I couldn't find any transactions in this file.")
        return

    batch = transaction_service.stage(message.chat.id, result.transactions, source)
    preview_txs = result.transactions[:_MAX_PREVIEW]
    card = render_multi_confirmation(preview_txs)
    if len(result.transactions) > _MAX_PREVIEW:
        card += f"\n\n_... and {len(result.transactions) - _MAX_PREVIEW} more (all will be imported)_"
    if result.warning:
        card += f"\n\n⚠️ _{result.warning}_"

    await message.answer(card, parse_mode="Markdown", reply_markup=import_preview_keyboard(batch.token))
