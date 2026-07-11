"""Business logic for turning parsed input into saved transactions.

Handlers call into this service; it owns the "pending confirmation" cache
(in-memory, keyed by a short token) and talks to the repository once the
user confirms via the inline keyboard.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.models.enums import TransactionSource
from app.repositories.transaction_repository import transaction_repository
from app.schemas.transaction import Transaction, TransactionCreate

# In-memory staging store. Fine for a single-process personal bot; if this
# ever needs to survive restarts or scale horizontally, swap for Redis.
_PENDING: dict[str, "PendingBatch"] = {}


@dataclass
class PendingBatch:
    chat_id: int
    transactions: list[TransactionCreate]
    source: TransactionSource
    token: str = field(default_factory=lambda: uuid.uuid4().hex[:10])


class TransactionService:
    def stage(self, chat_id: int, transactions: list[TransactionCreate], source: TransactionSource) -> PendingBatch:
        batch = PendingBatch(chat_id=chat_id, transactions=transactions, source=source)
        _PENDING[batch.token] = batch
        return batch

    def get_pending(self, token: str) -> PendingBatch | None:
        return _PENDING.get(token)

    def discard(self, token: str) -> None:
        _PENDING.pop(token, None)

    async def confirm_and_save(self, token: str) -> tuple[list[Transaction], list[str]]:
        """Returns (saved transactions, budget alert messages)."""
        batch = _PENDING.pop(token, None)
        if batch is None:
            return [], []

        if len(batch.transactions) == 1:
            saved_tx, alert = await transaction_repository.append_transaction(
                batch.transactions[0], batch.source
            )
            return [saved_tx], ([alert] if alert else [])

        saved, alerts = await transaction_repository.append_transactions(batch.transactions, batch.source)
        return saved, alerts

    async def save_single(self, tx_create: TransactionCreate, source: TransactionSource) -> Transaction:
        tx, _alert = await transaction_repository.append_transaction(tx_create, source)
        return tx


transaction_service = TransactionService()
