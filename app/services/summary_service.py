"""Aggregates transactions into the summary numbers shown by /today,
/month, and /summary, and provides the raw building blocks the AI chat
service uses to answer free-form questions.
"""
from __future__ import annotations

from collections import defaultdict

from app.repositories.transaction_repository import transaction_repository
from app.schemas.transaction import Transaction


class SummaryService:
    def _split_income_expense(self, txs: list[Transaction]) -> tuple[float, float]:
        income = sum(t.amount for t in txs if t.type.value == "Income")
        expense = sum(t.amount for t in txs if t.type.value == "Expense")
        return income, expense

    def _top_n(self, txs: list[Transaction], key: str, n: int = 5) -> list[tuple[str, float]]:
        totals: dict[str, float] = defaultdict(float)
        for t in txs:
            if t.type.value != "Expense":
                continue
            k = getattr(t, key) or "Unknown"
            totals[k] += t.amount
        return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:n]

    def summarize(self, txs: list[Transaction], days_in_period: int) -> dict:
        income, expense = self._split_income_expense(txs)
        savings = sum(t.amount for t in txs if t.type.value == "Transfer")
        saving_rate = (savings / income * 100) if income > 0 else 0.0
        top_categories = self._top_n(txs, "category")
        top_merchants = self._top_n(txs, "merchant")
        avg_daily = expense / days_in_period if days_in_period > 0 else 0.0
        largest_expense = max((t.amount for t in txs if t.type.value == "Expense"), default=0.0)
        return {
            "income": income, "expense": expense, "savings": savings, "saving_rate": saving_rate,
            "top_categories": top_categories, "top_merchants": top_merchants,
            "avg_daily": avg_daily, "largest_expense": largest_expense,
        }

    async def today_summary(self) -> dict:
        return self.summarize(await transaction_repository.get_today(), days_in_period=1)

    async def month_summary(self, year: int, month: int, days_in_period: int) -> dict:
        txs = await transaction_repository.get_month(year, month)
        return self.summarize(txs, days_in_period=days_in_period)

    async def balance(self, year: int | None = None, month: int | None = None) -> dict:
        """Saldo — computed server-side by Apps Script (income - expense -
        transfer, over the given month or all-time if no month is given).
        """
        return await transaction_repository.get_balance(year=year, month=month)


summary_service = SummaryService()
