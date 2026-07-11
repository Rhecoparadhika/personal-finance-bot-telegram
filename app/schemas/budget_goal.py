"""DTOs for Budget Planner and Goal Planning rows.

Unlike Transaction, these are NOT append-only — they map onto a small,
FIXED set of pre-existing rows in the user's template (Budget Planner has
14 category rows across Needs/Wants/Saving; Goal Planning has 3 pre-filled
goals). We never insert new rows into these sheets: the template's SUM/
formula ranges are sized to those exact rows, and the user asked not to
change the spreadsheet's structure. All values here come back from the
Apps Script Web App, which reads the live (formula-evaluated) cells.
"""
from __future__ import annotations

from pydantic import BaseModel


class BudgetStatus(BaseModel):
    category: str          # row label from Budget Planner!B (e.g. "Transportasi")
    section: str            # "Needs" | "Wants" | "Saving & Invest"
    budget: float            # column C
    actual: float             # column D
    difference: float          # column E (formula, read-only)
    pct_of_income: float        # column F (formula, read-only)
    status: str                  # column G (formula, read-only)


class Goal(BaseModel):
    name: str                  # Goal Planning!B (formula-linked to Cashflow)
    target_amount: float         # column C
    current_amount: float          # column D
    horizon_years: float | None      # column E
    monthly_saving: float | None       # column F (formula, read-only)
    future_value: float | None           # column I (formula, read-only)
    feasibility: str | None                # column K (formula, read-only)

    @property
    def progress_pct(self) -> float:
        if self.target_amount <= 0:
            return 0.0
        return min(100.0, round(self.current_amount / self.target_amount * 100, 1))
