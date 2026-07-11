"""Normalize Indonesian-style shorthand amounts ("25rb", "100 ribu", "5jt",
"15 juta") into plain numbers, and format numbers back into IDR display
strings. Used as a deterministic pre/post pass around the LLM so the model
doesn't have to be perfectly reliable at arithmetic.
"""
from __future__ import annotations

import re

_MULTIPLIERS = {
    "rb": 1_000, "ribu": 1_000, "k": 1_000,
    "jt": 1_000_000, "juta": 1_000_000, "m": 1_000_000,
    "b": 1_000_000_000, "miliar": 1_000_000_000, "milyar": 1_000_000_000,
}

_AMOUNT_PATTERN = re.compile(
    r"(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>ribu|rb|jt|juta|k|m|miliar|milyar|b)?",
    re.IGNORECASE,
)


def normalize_amount_text(text: str) -> str:
    """Rewrite shorthand amounts in free text into plain digit form so the
    LLM sees "25000" instead of "25rb". Non-amount numbers are left alone
    when there's no unit suffix attached.
    """

    def _replace(match: re.Match[str]) -> str:
        num_raw = match.group("num")
        unit = (match.group("unit") or "").lower()
        if not unit:
            return match.group(0)
        num = float(num_raw.replace(",", "."))
        value = num * _MULTIPLIERS[unit]
        return f"{value:.0f}"

    return _AMOUNT_PATTERN.sub(_replace, text)


def format_currency(amount: float, currency: str = "IDR") -> str:
    if currency == "IDR":
        return f"Rp{amount:,.0f}".replace(",", ".")
    return f"{amount:,.2f} {currency}"
