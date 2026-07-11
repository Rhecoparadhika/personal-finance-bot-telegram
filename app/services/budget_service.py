"""Thin wrapper over BudgetRepository. Threshold alerting (80/90/100%)
happens server-side in Apps Script as part of addTransaction — this
service is just for the /budget command's read/set flows.
"""
from __future__ import annotations

from app.repositories.budget_repository import budget_repository
from app.schemas.budget_goal import BudgetStatus


class BudgetService:
    async def status_for_month(self) -> list[BudgetStatus]:
        return await budget_repository.get_all()

    async def set_budget(self, category_label: str, amount: float) -> BudgetStatus | None:
        return await budget_repository.set_budget_amount(category_label, amount)


budget_service = BudgetService()
