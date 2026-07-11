"""The ONLY module (besides apps_script_client) involved in getting
transactions into/out of the sheet. All calls go through the Apps Script
Web App — this repository just knows the JSON contract's action names and
turns responses into/from Pydantic `Transaction` objects.

Budget threshold checking (80/90/100%) happens server-side inside Apps
Script's addTransaction handler, atomically with the write — it returns an
optional `budgetAlert` string alongside the created transaction so there's
no separate read-modify-write race between Python and the sheet.
"""
from __future__ import annotations

from datetime import date as Date

from app.google.apps_script_client import apps_script_client
from app.utils.time import current_date
from app.models.enums import TransactionSource
from app.schemas.transaction import Transaction, TransactionCreate


class TransactionRepository:
    async def append_transaction(
        self, tx: TransactionCreate, source: TransactionSource
    ) -> tuple[Transaction, str | None]:
        result = await apps_script_client.call("addTransaction", tx.to_payload())
        saved = Transaction(**tx.model_dump(), transaction_id=result["transactionId"], source=source)
        return saved, result.get("budgetAlert")

    async def append_transactions(
        self, txs: list[TransactionCreate], source: TransactionSource
    ) -> tuple[list[Transaction], list[str]]:
        if not txs:
            return [], []
        result = await apps_script_client.call(
            "addTransactions", {"transactions": [t.to_payload() for t in txs]}
        )
        ids = result["transactionIds"]
        saved = [
            Transaction(**tx.model_dump(), transaction_id=tid, source=source)
            for tx, tid in zip(txs, ids)
        ]
        alerts = [a for a in result.get("budgetAlerts", []) if a]
        return saved, alerts

    async def get_transactions(
        self, *, date_from: Date | None = None, date_to: Date | None = None,
        category: str | None = None, type_: str | None = None,
    ) -> list[Transaction]:
        payload = {
            "dateFrom": date_from.isoformat() if date_from else None,
            "dateTo": date_to.isoformat() if date_to else None,
            "category": category,
            "type": type_,
        }
        result = await apps_script_client.call("getTransactions", payload)
        return [Transaction.from_apps_script_row(r) for r in result.get("transactions", [])]

    async def get_today(self, today: Date | None = None) -> list[Transaction]:
        today = today or current_date()
        return await self.get_transactions(date_from=today, date_to=today)

    async def get_month(self, year: int, month: int) -> list[Transaction]:
        import calendar

        last_day = calendar.monthrange(year, month)[1]
        return await self.get_transactions(
            date_from=Date(year, month, 1), date_to=Date(year, month, last_day)
        )

    async def get_all(self) -> list[Transaction]:
        return await self.get_transactions()

    async def get_balance(self, year: int | None = None, month: int | None = None) -> dict:
        """Delegates the actual summing to Apps Script — one server-side pass
        over the sheet, instead of pulling every row over HTTP to add up here.
        """
        result = await apps_script_client.call("getBalance", {"year": year, "month": month})
        return result["balance"]

    async def update_transaction(self, transaction_id: str, **updates) -> Transaction | None:
        result = await apps_script_client.call(
            "editTransaction", {"transactionId": transaction_id, "fields": updates}
        )
        if result.get("found") is False:
            return None
        return Transaction.from_apps_script_row(result["transaction"])

    async def delete_transaction(self, transaction_id: str) -> bool:
        result = await apps_script_client.call("deleteTransaction", {"transactionId": transaction_id})
        return bool(result.get("found", False))


transaction_repository = TransactionRepository()
