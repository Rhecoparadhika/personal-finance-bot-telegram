"""Powers free-form questions like "how much did I spend on food this
month?". Rather than trusting the LLM to do arithmetic, we compute exact
numbers in Python from the sheet data and only ask the LLM to phrase the
answer / decide which numbers are relevant to the question.
"""
from __future__ import annotations

import json
from datetime import date as Date

from app.llm.factory import get_llm_provider
from app.repositories.transaction_repository import transaction_repository
from app.schemas.transaction import Transaction
from app.utils.currency import format_currency

_SYSTEM_PROMPT = """You are a helpful personal finance assistant. You will be given a user's
question and a JSON dump of their relevant financial data (already computed, exact numbers).
Answer the question conversationally, in the same language as the question (Indonesian, English,
or mixed), using ONLY the numbers provided. Never invent numbers. Keep it concise, use the
provided currency formatting, and use light emoji. Respond in plain text (no markdown fences)."""


def _serialize_transactions(txs: list[Transaction]) -> list[dict]:
    return [
        {
            "date": t.date.isoformat(), "type": t.type.value, "category": t.category,
            "merchant": t.merchant, "amount": t.amount, "notes": t.notes,
        }
        for t in txs
    ]


async def answer_question(question: str, currency: str = "IDR") -> str:
    all_txs = await transaction_repository.get_all()
    today = Date.today()
    this_month = [t for t in all_txs if t.date.year == today.year and t.date.month == today.month]
    last_month_idx = today.month - 1 or 12
    last_month_year = today.year if today.month > 1 else today.year - 1
    last_month = [t for t in all_txs if t.date.year == last_month_year and t.date.month == last_month_idx]

    context = {
        "today": today.isoformat(),
        "currency": currency,
        "this_month_transactions": _serialize_transactions(this_month),
        "last_month_transactions": _serialize_transactions(last_month),
        "total_transactions_all_time": len(all_txs),
    }

    provider = get_llm_provider()
    user_prompt = f"Question: {question}\n\nData: {json.dumps(context, ensure_ascii=False)}"
    try:
        response = await provider.complete_text(_SYSTEM_PROMPT, user_prompt)
    except Exception:  # noqa: BLE001
        return "Sorry, I couldn't reach the AI service right now. Please try again in a moment."
    return response
