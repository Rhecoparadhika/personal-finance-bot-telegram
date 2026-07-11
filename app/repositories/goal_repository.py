"""Reads/writes the 'Goal Planning' tab through Apps Script. Only touches
the 3 pre-existing goals (Dana Darurat, Mobil, Menikah) that the template
ships with — their names are formula-linked back to the 'Cashflow' tab's
TABUNGAN & INVESTASI section, so goal *names* aren't editable from here by
design; only target/current amount are.
"""
from __future__ import annotations

from app.google.apps_script_client import apps_script_client
from app.schemas.budget_goal import Goal


class GoalRepository:
    async def list_goals(self) -> list[Goal]:
        result = await apps_script_client.call("getGoals")
        return [_goal_from_row(row) for row in result.get("goals", [])]

    async def set_target(self, name: str, target_amount: float) -> Goal | None:
        result = await apps_script_client.call("setGoalTarget", {"name": name, "amount": target_amount})
        if result.get("found") is False:
            return None
        return _goal_from_row(result["goal"])

    async def contribute(self, name: str, amount: float) -> Goal | None:
        result = await apps_script_client.call("contributeGoal", {"name": name, "amount": amount})
        if result.get("found") is False:
            return None
        return _goal_from_row(result["goal"])


def _goal_from_row(row: dict) -> Goal:
    return Goal(
        name=row["name"],
        target_amount=row["targetAmount"],
        current_amount=row["currentAmount"],
        horizon_years=row.get("horizonYears"),
        monthly_saving=row.get("monthlySaving"),
        future_value=row.get("futureValue"),
        feasibility=row.get("feasibility"),
    )


goal_repository = GoalRepository()
