"""Slot-filling flow: after a single transaction is parsed, the bot chases
every empty column one question at a time until complete or the user opts out.
Pure logic — no LLM or network involved."""
from datetime import date

from app.models.enums import TransactionSource
from app.schemas.transaction import TransactionCreate
from app.services.clarification_service import ClarificationService


def _bare_tx() -> TransactionCreate:
    # Only the essentials filled — account/merchant/payment/tags/notes empty.
    return TransactionCreate(date=date(2026, 7, 12), type="Expense", category="Dinner", amount=45000)


def test_full_slot_filling_walkthrough():
    svc = ClarificationService()
    chat = 1

    started, q = svc.start(chat, _bare_tx(), TransactionSource.TEXT)
    assert started and "akun" in q.lower()  # asks account first

    assert svc.apply_answer(chat, "BCA").status == "ask"          # -> merchant
    assert svc.apply_answer(chat, "skip").status == "ask"         # skip merchant -> payment
    assert svc.apply_answer(chat, "gopay").status == "ask"        # -> tags
    assert svc.apply_answer(chat, "keluarga, weekend").status == "ask"  # -> notes
    done = svc.apply_answer(chat, "makan malam bareng keluarga")  # -> done
    assert done.status == "done"

    tx = done.tx
    assert tx.account == "BCA"
    assert tx.merchant is None                 # was skipped
    assert tx.payment_method == "e-Wallet"     # 'gopay' normalized
    assert tx.tags == ["keluarga", "weekend"]
    assert tx.notes == "makan malam bareng keluarga"
    assert svc.get(chat) is None               # state cleared after done


def test_stop_word_finishes_immediately():
    svc = ClarificationService()
    svc.start(2, _bare_tx(), TransactionSource.TEXT)
    result = svc.apply_answer(2, "udah")
    assert result.status == "done"
    assert result.tx.account is None           # nothing forced


def test_cancel_word_aborts():
    svc = ClarificationService()
    svc.start(3, _bare_tx(), TransactionSource.TEXT)
    result = svc.apply_answer(3, "batal")
    assert result.status == "cancelled"
    assert svc.get(3) is None


def test_no_questions_when_everything_present():
    svc = ClarificationService()
    full = _bare_tx().model_copy(update={
        "account": "BCA", "merchant": "Warteg", "payment_method": "Cash",
        "tags": ["makan"], "notes": "siang",
    })
    started, q = svc.start(4, full, TransactionSource.TEXT)
    assert started is False and q is None
