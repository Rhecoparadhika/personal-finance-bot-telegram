"""Interactive slot-filling: after a transaction is parsed from a single
message, the bot walks the user through every column that came back empty
(Account, Merchant, Payment Method, Tags, Notes), one question at a time,
until they're all filled or the user opts out.

State is per-chat and in-memory (like `transaction_service._PENDING`). The
user can:
  - answer a question       -> value is filled, next empty field is asked
  - "skip" / "lewati" / "-" -> that one field is left blank, move on
  - "udah" / "selesai"      -> stop asking, show the confirmation card now
  - "batal" / "cancel"      -> drop the whole thing

Only kicks in for a SINGLE parsed transaction — batch imports (receipts, PDF
statements, multi-line messages) skip straight to the confirmation card.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config.categories import PAYMENT_METHODS
from app.models.enums import TransactionSource
from app.schemas.transaction import TransactionCreate

# Fields we chase, in the order we ask, with the question shown to the user.
_QUESTIONS: dict[str, str] = {
    "account": "🏦 Dari akun/dompet mana? (mis. BCA, GoPay, Cash)",
    "merchant": "🏪 Beli di mana / dari siapa? (nama merchant/tempat)",
    "payment_method": "💳 Bayar pakai apa? (Cash, Transfer, QRIS, Kartu Debit/Kredit, e-Wallet, Auto Debit)",
    "tags": "🏷️ Mau kasih tag? (pisah pakai koma, mis. keluarga, weekend)",
    "notes": "📝 Ada catatan tambahan?",
}
_FIELD_ORDER = list(_QUESTIONS.keys())

_SKIP_WORDS = {"skip", "lewati", "lewat", "-", "ga", "gak", "engga", "nggak", "no", "kosong", "tidak", "gaada", "ga ada"}
_STOP_WORDS = {"udah", "sudah", "selesai", "simpan", "cukup", "done", "stop", "lengkap", "itu aja", "gitu aja", "oke"}
_CANCEL_WORDS = {"batal", "cancel", "gajadi", "gak jadi", "ga jadi", "batalkan"}

# Common Indonesian ways of naming a payment method -> the sheet's exact value.
_PM_SYNONYMS: dict[str, str] = {
    "cash": "Cash", "tunai": "Cash",
    "transfer": "Bank Transfer", "tf": "Bank Transfer", "bank": "Bank Transfer",
    "banktransfer": "Bank Transfer", "mbanking": "Bank Transfer", "m-banking": "Bank Transfer",
    "qris": "QRIS", "qr": "QRIS",
    "debit": "Debit Card", "kartu debit": "Debit Card", "debitcard": "Debit Card",
    "kredit": "Credit Card", "credit": "Credit Card", "cc": "Credit Card", "kartu kredit": "Credit Card",
    "ewallet": "e-Wallet", "e-wallet": "e-Wallet", "e wallet": "e-Wallet", "dompet digital": "e-Wallet",
    "gopay": "e-Wallet", "ovo": "e-Wallet", "dana": "e-Wallet", "shopeepay": "e-Wallet",
    "linkaja": "e-Wallet", "gojek": "e-Wallet",
    "autodebit": "Auto Debit", "auto debit": "Auto Debit", "autodebet": "Auto Debit", "auto debet": "Auto Debit",
}


def _normalize_payment_method(text: str) -> str:
    key = text.strip().lower()
    if key in _PM_SYNONYMS:
        return _PM_SYNONYMS[key]
    for p in PAYMENT_METHODS:
        if p.lower() == key:
            return p
    # Unknown term — keep the user's own words rather than losing the answer.
    return text.strip()


def _empty_fields(tx: TransactionCreate) -> list[str]:
    missing = []
    for field in _FIELD_ORDER:
        value = tx.tags if field == "tags" else getattr(tx, field)
        if not value:
            missing.append(field)
    return missing


@dataclass
class Clarification:
    chat_id: int
    tx: TransactionCreate
    source: TransactionSource
    pending: list[str]           # fields still to ask, in order
    current: str | None = None   # the field we're currently waiting on


@dataclass
class ClarifyResult:
    status: str                              # "ask" | "done" | "cancelled"
    question: str | None = None              # set when status == "ask"
    tx: TransactionCreate | None = None      # set when status == "done"


class ClarificationService:
    def __init__(self) -> None:
        self._active: dict[int, Clarification] = {}

    def get(self, chat_id: int) -> Clarification | None:
        return self._active.get(chat_id)

    def discard(self, chat_id: int) -> None:
        self._active.pop(chat_id, None)

    def start(
        self, chat_id: int, tx: TransactionCreate, source: TransactionSource
    ) -> tuple[bool, str | None]:
        """Begin chasing empty fields. Returns (started, first_question).
        If nothing is missing, returns (False, None) — caller should show the
        confirmation card directly."""
        missing = _empty_fields(tx)
        if not missing:
            self._active.pop(chat_id, None)
            return False, None
        first, rest = missing[0], missing[1:]
        self._active[chat_id] = Clarification(
            chat_id=chat_id, tx=tx, source=source, pending=rest, current=first
        )
        return True, _QUESTIONS[first]

    def apply_answer(self, chat_id: int, text: str) -> ClarifyResult:
        state = self._active.get(chat_id)
        if state is None:
            return ClarifyResult(status="done", tx=None)

        answer = text.strip()
        low = answer.lower()

        if low in _CANCEL_WORDS:
            self._active.pop(chat_id, None)
            return ClarifyResult(status="cancelled")

        if low in _STOP_WORDS:
            tx = state.tx
            self._active.pop(chat_id, None)
            return ClarifyResult(status="done", tx=tx)

        # Fill the current field unless the user chose to skip it.
        if low not in _SKIP_WORDS and state.current:
            state.tx = self._set_field(state.tx, state.current, answer)

        # Advance to the next still-empty field.
        if state.pending:
            state.current = state.pending.pop(0)
            return ClarifyResult(status="ask", question=_QUESTIONS[state.current])

        tx = state.tx
        self._active.pop(chat_id, None)
        return ClarifyResult(status="done", tx=tx)

    @staticmethod
    def _set_field(tx: TransactionCreate, field: str, raw: str) -> TransactionCreate:
        if field == "payment_method":
            value: object = _normalize_payment_method(raw)
        elif field == "tags":
            value = [t.strip() for t in raw.replace(";", ",").split(",") if t.strip()]
        else:
            value = raw
        return tx.model_copy(update={field: value})


clarification_service = ClarificationService()
