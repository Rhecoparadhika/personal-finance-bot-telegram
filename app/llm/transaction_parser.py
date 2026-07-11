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

from app.llm.factory import get_llm_provider
from app.schemas.transaction import LLMParseResult, TransactionCreate
from app.utils.currency import normalize_amount_text

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


async def parse_text_to_transactions(raw_text: str, today: Date | None = None) -> LLMParseResult:
    today = today or Date.today()
    normalized = normalize_amount_text(raw_text)
    system_prompt = _load_system_prompt(today)
    provider = get_llm_provider()

    try:
        raw_response = await provider.complete_json(system_prompt, normalized)
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM provider call failed: {}", exc)
        return LLMParseResult(transactions=[], warning="AI service is temporarily unavailable. Please try again.")

    try:
        data = json.loads(_strip_json_fences(raw_response))
    except json.JSONDecodeError as exc:
        logger.error("LLM returned non-JSON: {} | raw={}", exc, raw_response[:500])
        return LLMParseResult(transactions=[], warning="Couldn't understand that. Could you rephrase?")

    transactions: list[TransactionCreate] = []
    for item in data.get("transactions", []):
        try:
            transactions.append(TransactionCreate(**item))
        except ValidationError as exc:
            logger.warning("Dropping invalid transaction from LLM output: {}", exc)

    return LLMParseResult(transactions=transactions, warning=data.get("warning"))


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
