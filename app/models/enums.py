"""Enums shared across schemas, services, and repositories.

TransactionType matches EXACTLY the 3 values used in the 'Cashflow Harian'
Type column (and its data-validation dropdown): Income, Expense, Transfer.
Everything that used to be a separate type (Investment, Saving, Debt...) is
now a Category under Transfer -> Financial Goal, per the sheet's own design
(see app/config/categories.py).
"""
from __future__ import annotations

from enum import StrEnum


class TransactionType(StrEnum):
    EXPENSE = "Expense"
    INCOME = "Income"
    TRANSFER = "Transfer"


class TransactionSource(StrEnum):
    """Not a sheet column (the template has none) — used internally for
    logging/analytics only, e.g. to tell OCR-derived rows from typed ones.
    """
    TEXT = "text"
    OCR = "ocr"
    PDF = "pdf"
    CSV = "csv"
    VOICE = "voice"
