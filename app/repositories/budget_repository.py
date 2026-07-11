"""Reads/writes the 'Budget Planner' tab through Apps Script. Only ever
touches the 14 pre-existing category rows (Needs/Wants/Saving & Invest) —
never inserts rows, since the template's TOTAL/formula ranges are sized to
exactly those rows.
"""
from __future__ import annotations

from app.google.apps_script_client import apps_script_client
from app.schemas.budget_goal import BudgetStatus


class BudgetRepository:
    async def get_all(self) -> list[BudgetStatus]:
        result = await apps_script_client.call("getBudgets")
        return [BudgetStatus(**_from_camel(row)) for row in result.get("budgets", [])]

    async def set_budget_amount(self, category_label: str, amount: float) -> BudgetStatus | None:
        result = await apps_script_client.call(
            "setBudgetAmount", {"category": category_label, "amount": amount}
        )
        if result.get("found") is False:
            return None
        return BudgetStatus(**_from_camel(result["budget"]))


def _from_camel(row: dict) -> dict:
    return {
        "category": row["category"],
        "section": row["section"],
        "budget": row["budget"],
        "actual": row["actual"],
        "difference": row["difference"],
        "pct_of_income": row["pctOfIncome"],
        "status": row["status"],
    }


budget_repository = BudgetRepository()
