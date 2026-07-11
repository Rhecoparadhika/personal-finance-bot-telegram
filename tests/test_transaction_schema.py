import pytest
from pydantic import ValidationError

from app.schemas.transaction import Transaction, TransactionCreate


def test_transaction_create_valid():
    tx = TransactionCreate(date="2026-07-11", type="Expense", category="Lunch", amount=25000)
    assert tx.amount == 25000
    assert tx.category == "Lunch"


def test_transaction_create_category_case_insensitive():
    # LLM output might not match the dropdown's exact casing; we normalize it.
    tx = TransactionCreate(date="2026-07-11", type="Expense", category="lunch", amount=25000)
    assert tx.category == "Lunch"


def test_transaction_create_default_time_is_set():
    tx = TransactionCreate(date="2026-07-11", type="Expense", category="Lunch", amount=25000)
    assert tx.time.microsecond == 0
    assert 0 <= tx.time.hour < 24


def test_transaction_create_rejects_unknown_category():
    with pytest.raises(ValidationError):
        TransactionCreate(date="2026-07-11", type="Expense", category="NotARealCategory", amount=1000)


def test_transaction_create_rejects_negative_amount():
    with pytest.raises(ValidationError):
        TransactionCreate(date="2026-07-11", type="Expense", category="Lunch", amount=-10)


def test_need_want_goal_and_fixed_variable_derived_from_category():
    tx = TransactionCreate(date="2026-07-11", type="Expense", category="Rent", amount=2000000)
    assert tx.need_want_goal == "Need"
    assert tx.fixed_variable == "Fixed"

    tx2 = TransactionCreate(date="2026-07-11", type="Transfer", category="Emergency Fund", amount=500000)
    assert tx2.need_want_goal == "Financial Goal"


def test_to_payload_matches_apps_script_contract():
    tx = TransactionCreate(
        date="2026-07-11", time="08:30:00", type="Expense", category="Breakfast",
        amount=25000, merchant="Nasi Uduk", payment_method="qris",
    )
    payload = tx.to_payload()
    assert payload["date"] == "2026-07-11"
    assert payload["time"] == "08:30:00"
    assert payload["category"] == "Breakfast"
    assert payload["needWantGoal"] == "Need"
    assert payload["fixedVariable"] == "Variable"
    assert payload["paymentMethod"] == "QRIS"  # normalized casing


def test_transaction_from_apps_script_row_round_trip():
    payload = TransactionCreate(
        date="2026-07-11", type="Expense", category="Lunch", amount=25000, merchant="Warteg",
    ).to_payload()
    row = dict(payload)
    row["transactionId"] = "TRX000042"
    restored = Transaction.from_apps_script_row(row)
    assert restored.transaction_id == "TRX000042"
    assert restored.amount == 25000
    assert restored.merchant == "Warteg"
