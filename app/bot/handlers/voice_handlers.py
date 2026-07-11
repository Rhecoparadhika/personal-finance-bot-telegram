from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.llm.transaction_parser import parse_text_to_transactions
from app.models.enums import TransactionSource
from app.services.transaction_service import transaction_service
from app.services.voice_service import TranscriptionError, transcribe_voice
from app.bot.keyboards import confirmation_keyboard
from app.utils.formatting import render_confirmation_card, render_multi_confirmation

router = Router(name="voice")


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, "record_voice")
    file = await message.bot.get_file(message.voice.file_id)
    buffer = await message.bot.download_file(file.file_path)
    audio_bytes = buffer.read()

    try:
        text = await transcribe_voice(audio_bytes)
    except TranscriptionError as exc:
        await message.answer(f"🎙️ {exc}")
        return

    await message.answer(f"🎙️ _Heard:_ \"{text}\"", parse_mode="Markdown")

    result = await parse_text_to_transactions(text)
    if not result.transactions:
        await message.answer("🎙️ I didn't catch a transaction in that. Could you try again?")
        return

    batch = transaction_service.stage(message.chat.id, result.transactions, TransactionSource.VOICE)
    card = (
        render_confirmation_card(result.transactions[0])
        if len(result.transactions) == 1
        else render_multi_confirmation(result.transactions)
    )
    await message.answer(card, parse_mode="Markdown", reply_markup=confirmation_keyboard(batch.token))
