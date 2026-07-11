"""CSV export, matching the exact 'Cashflow Harian' column order so the
export can be re-imported or opened directly next to the sheet."""
from __future__ import annotations

import csv
import io

from app.schemas.transaction import Transaction

_HEADERS = [
    "Transaction ID", "Date", "Time", "Type", "Category", "Need/Want/Goal",
    "Fixed/Variable", "Amount", "Account", "Merchant", "Payment Method", "Notes", "Tags",
]


def export_transactions_csv(txs: list[Transaction]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_HEADERS)
    for t in txs:
        writer.writerow([
            t.transaction_id, t.date.isoformat(), t.time.strftime("%H:%M:%S"), t.type.value,
            t.category, t.need_want_goal, t.fixed_variable, f"{t.amount:.2f}",
            t.account or "", t.merchant or "", t.payment_method or "", t.notes or "",
            ", ".join(t.tags),
        ])
    return buf.getvalue().encode("utf-8-sig")
