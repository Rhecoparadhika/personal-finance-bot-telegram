"""Turns free-form text into validated `TransactionCreate` objects.

Flow: normalize shorthand amounts -> call the active LLM provider -> parse
JSON -> validate through Pydantic (invalid rows are dropped, not silently
coerced) -> return `LLMParseResult`. The LLM NEVER touches Google Sheets;
this module's only output is in-memory Pydantic objects.
"""
from __future__ import annotations

import json
from datetime import date as Date
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from app.config.settings import settings
from app.llm.factory import get_llm_provider
from app.schemas.transaction import LLMParseResult, TransactionCreate
from app.utils.currency import normalize_amount_text
from app.utils.time import current_date

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "transaction_parser_system.txt"


def _load_system_prompt(today: Date) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("<TODAY>", today.isoformat())


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text.removeprefix("json").strip()
    return text.strip()


def _build_provider_warning(exc: Exception) -> str:
    detail = str(exc).strip().lower()
    provider_name = settings.llm_provider.lower()
    key_name = {
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(provider_name, "LLM provider API key")

    if any(token in detail for token in ["not configured", "api key", "authentication", "unauthorized", "401", "403", "invalid", "credential"]):
        return (
            f"AI service is not configured correctly. Set {key_name} to a real value in .env "
            f"and restart the app."
        )
    return "AI service is temporarily unavailable. Please try again."


async def parse_text_to_transactions(
    raw_text: str,
    today: Date | None = None,
    history: list[dict[str, str]] | None = None,
) -> LLMParseResult:
    today = today or current_date()
    normalized = normalize_amount_text(raw_text)
    system_prompt = _load_system_prompt(today)
    provider = get_llm_provider()

    try:
        raw_response = await provider.complete_text(system_prompt, normalized, history=history)
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM provider call failed")
        return LLMParseResult(transactions=[], warning=_build_provider_warning(exc))

    transactions: list[TransactionCreate] = []
    chat_response: str | None = None
    data = None

    try:
        data = json.loads(_strip_json_fences(raw_response))
    except json.JSONDecodeError:
        chat_response = raw_response.strip()
        return LLMParseResult(transactions=[], warning=None, chat_response=chat_response)

    if not isinstance(data, dict) or "transactions" not in data:
        chat_response = raw_response.strip()
        return LLMParseResult(transactions=[], warning=None, chat_response=chat_response)

    for item in data.get("transactions", []):
        try:
            transactions.append(TransactionCreate(**item))
        except ValidationError as exc:
            logger.warning("Dropping invalid transaction from LLM output: {}", exc)

    return LLMParseResult(transactions=transactions, warning=data.get("warning"), chat_response=None)


async def parse_receipt_text(ocr_text: str, today: Date | None = None) -> LLMParseResult:
    """Same parser, different framing: tells the model the text came from a
    photographed receipt (noisy OCR) and to prioritize the grand total.
    """
    framed = (
        "The following text was extracted via OCR from a photo of a physical receipt. "
        "It may contain OCR noise/typos. Find the merchant, date, line items, tax, and the "
        "GRAND TOTAL, and produce ONE transaction using the grand total as the amount "
        "(ignore individual line items unless there is no total).\n\n"
        f"OCR TEXT:\n{ocr_text}"
    )
    return await parse_text_to_transactions(framed, today=today)


async def parse_pdf_statement_text(statement_text: str, today: Date | None = None) -> LLMParseResult:
    """Frames extracted bank-statement text for multi-transaction extraction."""
    framed = (
        "The following text was extracted from a bank/e-wallet statement PDF. It likely "
        "contains many transaction rows (date, description, debit/credit amount). Extract "
        "EVERY transaction you can find as a separate entry.\n\n"
        f"STATEMENT TEXT:\n{statement_text}"
    )
    return await parse_text_to_transactions(framed, today=today)
