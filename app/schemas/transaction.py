"""Pydantic v2 models for a single financial transaction.

Column layout matches the 'Cashflow Harian' tab EXACTLY (A:M, header row 2,
data from row 3):
A Transaction ID · B Date · C Time · D Type · E Category ·
F Need/Want/Goal · G Fixed/Variable · H Amount · I Account · J Merchant ·
K Payment Method · L Notes · M Tags

`TransactionCreate` is what the LLM parser must produce. Need/Want/Goal and
Fixed/Variable are NOT asked of the LLM — they're derived deterministically
from the category via `derive_transaction_fields`, so they always match the
sheet's own dropdown lookup table and can never drift out of sync with it.

`transaction_id` (the "TRX000123" sheet primary key) is assigned by the
Google Apps Script Web App at write time, not by this app — Apps Script can
see the real current max ID in the sheet and avoid collisions; Python never
has to guess it.
"""
from __future__ import annotations

from datetime import date as Date
from datetime import time as Time

from app.utils.time import current_time
from pydantic import BaseModel, Field, field_validator

from app.config.categories import ALL_CATEGORIES, PAYMENT_METHODS, derive_transaction_fields
from app.models.enums import TransactionSource, TransactionType


class TransactionCreate(BaseModel):
    """Structured output contract for the LLM parser."""

    date: Date
    time: Time = Field(default_factory=current_time)
    type: TransactionType
    category: str
    amount: float = Field(gt=0)
    account: str | None = None
    merchant: str | None = None
    payment_method: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)  # internal only, not persisted

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v: str) -> str:
        for c in ALL_CATEGORIES:
            if c.lower() == v.strip().lower():
                return c
        raise ValueError(f"'{v}' is not a category in the spreadsheet's dropdown list")

    @field_validator("payment_method")
    @classmethod
    def _validate_payment_method(cls, v: str | None) -> str | None:
        if v is None:
            return None
        for p in PAYMENT_METHODS:
            if p.lower() == v.strip().lower():
                return p
        return None

    @field_validator("amount")
    @classmethod
    def _round_amount(cls, v: float) -> float:
        return round(v, 2)

    @property
    def need_want_goal(self) -> str:
        return derive_transaction_fields(self.category)[1]

    @property
    def fixed_variable(self) -> str:
        return derive_transaction_fields(self.category)[2]

    def to_payload(self) -> dict:
        """Serialize into the exact field names the Apps Script Web App
        expects (camelCase, matching its JSON contract)."""
        return {
            "date": self.date.isoformat(),
            "time": self.time.strftime("%H:%M:%S"),
            "type": self.type.value,
            "category": self.category,
            "needWantGoal": self.need_want_goal,
            "fixedVariable": self.fixed_variable,
            "amount": self.amount,
            "account": self.account or "",
            "merchant": self.merchant or "",
            "paymentMethod": self.payment_method or "",
            "notes": self.notes or "",
            "tags": ", ".join(self.tags),
        }


class Transaction(TransactionCreate):
    """Full record as read back from the sheet (includes the server-assigned
    Transaction ID). `source` is app-internal bookkeeping, never sent to or
    read from the sheet.
    """

    transaction_id: str
    source: TransactionSource = TransactionSource.TEXT

    @classmethod
    def from_apps_script_row(cls, row: dict) -> "Transaction":
        """Parse a row dict as returned by the Apps Script `getTransactions`
        action (camelCase keys matching `to_payload`, plus `transactionId`).
        """
        return cls(
            transaction_id=row["transactionId"],
            date=row["date"],
            time=row.get("time") or "00:00:00",
            type=TransactionType(row["type"]),
            category=row["category"],
            amount=float(row.get("amount") or 0),
            account=row.get("account") or None,
            merchant=row.get("merchant") or None,
            payment_method=row.get("paymentMethod") or None,
            notes=row.get("notes") or None,
            tags=[t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
        )


class LLMParseResult(BaseModel):
    """Wrapper the LLM parser returns: zero or more transactions plus any
    clarification note if the input was ambiguous.
    """

    transactions: list[TransactionCreate] = Field(default_factory=list)
    warning: str | None = None
    chat_response: str | None = None
