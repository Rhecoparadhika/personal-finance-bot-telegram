"""Finance Q&A must be grounded in real spreadsheet data, not guessed by the
LLM. These tests mock the repository/provider boundaries and assert that
`answer_finance_question` (a) actually fetches transactions and (b) hands the
LLM a prompt containing real, exact numbers rather than letting it improvise.
"""
import asyncio
from datetime import date

from app.models.enums import TransactionSource, TransactionType
from app.schemas.transaction import Transaction


def _tx(d: str, amount: float, category: str = "Dinner", type_=TransactionType.EXPENSE) -> Transaction:
    return Transaction(
        transaction_id="TRX000001", date=date.fromisoformat(d), type=type_,
        category=category, amount=amount, source=TransactionSource.TEXT,
    )


class _FakeProvider:
    def __init__(self):
        self.last_prompt: str | None = None
        self.last_history = None

    async def complete_text(self, system_prompt, user_prompt, history=None):
        self.last_prompt = user_prompt
        self.last_history = history
        return "Minggu ini kamu habis Rp 90.000."


def test_answer_finance_question_fetches_real_data_and_grounds_the_prompt(monkeypatch):
    today = date(2026, 7, 12)
    week_txs = [_tx("2026-07-10", 45000), _tx("2026-07-11", 45000)]

    async def fake_get_transactions(*, date_from=None, date_to=None, category=None, type_=None):
        # Every window in _build_financial_context asks for a date range —
        # return the week's data regardless of exact bounds for this test.
        return week_txs

    async def fake_balance(year=None, month=None):
        return {"income": 0, "expense": 90000, "transfer": 0, "net": -90000}

    fake_provider = _FakeProvider()

    monkeypatch.setattr(
        "app.repositories.transaction_repository.transaction_repository.get_transactions",
        fake_get_transactions,
    )
    monkeypatch.setattr(
        "app.services.summary_service.summary_service.balance", fake_balance
    )
    monkeypatch.setattr(
        "app.services.ai_chat_service.get_llm_provider", lambda: fake_provider
    )

    from app.services.ai_chat_service import answer_finance_question

    reply = asyncio.run(
        answer_finance_question("saya mau tau seminggu terakhir saya habis berapa", today=today)
    )

    assert reply == "Minggu ini kamu habis Rp 90.000."
    # The LLM must have been given the real computed total, not asked to guess.
    assert "90000" in fake_provider.last_prompt
    assert "FINANCIAL CONTEXT" in fake_provider.last_prompt
    assert "last_7_days" in fake_provider.last_prompt


def test_answer_finance_question_degrades_gracefully_when_sheet_unavailable(monkeypatch):
    async def fake_get_transactions(*, date_from=None, date_to=None, category=None, type_=None):
        raise RuntimeError("Apps Script unreachable")

    fake_provider = _FakeProvider()

    monkeypatch.setattr(
        "app.repositories.transaction_repository.transaction_repository.get_transactions",
        fake_get_transactions,
    )
    monkeypatch.setattr(
        "app.services.ai_chat_service.get_llm_provider", lambda: fake_provider
    )

    from app.services.ai_chat_service import answer_finance_question

    reply = asyncio.run(answer_finance_question("habis berapa minggu ini?", today=date(2026, 7, 12)))

    assert reply == "Minggu ini kamu habis Rp 90.000."  # provider still called
    assert "Could not load financial data" in fake_provider.last_prompt
