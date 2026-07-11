"""Powers free-form chat and finance Q&A. The user may ask about their money,
request a summary, or just talk casually, and the bot should reply naturally.

For finance questions we do NOT let the LLM guess numbers — we pull the real
rows from the spreadsheet (via `transaction_repository`, same as /today and
/summary use), pre-compute exact totals in Python with `summary_service`, and
hand the LLM that JSON as grounded context. The LLM's only job is picking the
right numbers for the question and phrasing the answer.
"""
from __future__ import annotations

import json
from datetime import date as Date
from datetime import timedelta

from app.utils.time import current_date
from loguru import logger

from app.llm.factory import get_llm_provider
from app.schemas.transaction import Transaction
from app.services.summary_service import summary_service

_SYSTEM_PROMPT = """You are a friendly, conversational chatbot and personal finance assistant.
The user may ask about finances, budgets, recent spending, or just chat casually.
Always respond in the same language the user used (Indonesian, English, or mixed).

If the user asks a finance question, answer using ONLY the numbers in the FINANCIAL CONTEXT
JSON block below the user's message — those numbers are already computed exactly from the
user's real spreadsheet data, so trust them as-is and never recompute or estimate totals
yourself. If the context doesn't cover the exact period asked (e.g. a specific custom date
range), say so and answer with the closest period you do have data for instead of inventing
a number.
If the user speaks casually or writes a greeting, ignore the financial context and reply
naturally and helpfully.
If the user asks something unrelated to finance, you may still respond politely as a chatbot.
Keep responses concise, plain text, and use light emoji when appropriate. Do not use
markdown fences and do not print raw JSON back to the user."""

_CHAT_SYSTEM_PROMPT = """You are a friendly, conversational chatbot.
The user is greeting you or talking casually, and you should respond naturally.
Do not provide transaction summaries, monthly reports, or finance context unless the user asks for it.
Keep the reply short, kind, and plain text, with light emoji when appropriate."""


def _serialize_transactions(txs: list[Transaction]) -> list[dict]:
    return [
        {
            "date": t.date.isoformat(), "type": t.type.value, "category": t.category,
            "merchant": t.merchant, "amount": t.amount, "notes": t.notes,
        }
        for t in txs
    ]


async def _build_financial_context(today: Date) -> dict:
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    from app.repositories.transaction_repository import transaction_repository

    week_txs = await transaction_repository.get_transactions(date_from=week_start, date_to=today)
    month_txs = await transaction_repository.get_transactions(date_from=month_start, date_to=today)
    last_month_txs = await transaction_repository.get_transactions(
        date_from=last_month_start, date_to=last_month_end
    )
    balance = await summary_service.balance()

    recent = sorted(week_txs, key=lambda t: (t.date, t.time), reverse=True)[:15]

    return {
        "today": today.isoformat(),
        "last_7_days": {
            "from": week_start.isoformat(), "to": today.isoformat(),
            **summary_service.summarize(week_txs, days_in_period=7),
        },
        "this_month": {
            "from": month_start.isoformat(), "to": today.isoformat(),
            **summary_service.summarize(month_txs, days_in_period=(today - month_start).days + 1),
        },
        "last_month": {
            "from": last_month_start.isoformat(), "to": last_month_end.isoformat(),
            **summary_service.summarize(
                last_month_txs, days_in_period=(last_month_end - last_month_start).days + 1
            ),
        },
        "all_time_balance": balance,
        "recent_transactions_last_7_days": _serialize_transactions(recent),
    }


async def answer_finance_question(
    message: str, history: list[dict[str, str]] | None = None, today: Date | None = None
) -> str:
    """Grounded Q&A entry point — fetches real spreadsheet data first, then
    lets the LLM phrase an answer using only those numbers."""
    today = today or current_date()
    provider = get_llm_provider()

    try:
        context = await _build_financial_context(today)
        prompt = (
            f"USER MESSAGE: {message}\n\n"
            f"FINANCIAL CONTEXT (JSON, already computed from the real spreadsheet — "
            f"trust these exact numbers, do not recompute):\n{json.dumps(context, ensure_ascii=False)}"
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to fetch financial context from the spreadsheet")
        prompt = (
            f"USER MESSAGE: {message}\n\n"
            f"(Could not load financial data from the spreadsheet right now — tell the "
            f"user briefly and ask them to try again in a moment.)"
        )

    try:
        return await provider.complete_text(_SYSTEM_PROMPT, prompt, history=history)
    except Exception:  # noqa: BLE001
        logger.exception("LLM call failed while answering a finance question")
        return "Hi! Ada yang bisa saya bantu?"


async def chat_text(message: str, history: list[dict[str, str]] | None = None) -> str:
    """Plain casual chat, no financial context attached — used when the
    caller already knows the message isn't finance-related."""
    provider = get_llm_provider()
    try:
        return await provider.complete_text(_CHAT_SYSTEM_PROMPT, message, history=history)
    except Exception:  # noqa: BLE001
        return "Hi! Ada yang bisa saya bantu?"
