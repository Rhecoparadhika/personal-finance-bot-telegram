"""Thin wrapper over GoalRepository. Goals map onto the 3 pre-existing rows
in the 'Goal Planning' tab (their names are formula-linked from 'Cashflow'),
so this service can only read/contribute-to/retarget those — not create
arbitrary new goals, per the template's fixed structure.
"""
from __future__ import annotations

from app.repositories.goal_repository import goal_repository
from app.schemas.budget_goal import Goal


class GoalService:
    async def list_goals(self) -> list[Goal]:
        return await goal_repository.list_goals()

    async def set_target(self, name: str, target_amount: float) -> Goal | None:
        return await goal_repository.set_target(name, target_amount)

    async def contribute(self, name: str, amount: float) -> Goal | None:
        return await goal_repository.contribute(name, amount)


goal_service = GoalService()
