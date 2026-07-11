from app.config.categories import (
    ALL_CATEGORIES,
    BUDGET_CATEGORY_MAP,
    CATEGORY_TAXONOMY,
    EXPENSE_CATEGORIES,
    TRANSFER_CATEGORIES,
    derive_transaction_fields,
)


def test_every_category_has_taxonomy_entry():
    for cat in ALL_CATEGORIES:
        assert cat in CATEGORY_TAXONOMY


def test_derive_transaction_fields_known_category():
    type_, nwg, fv = derive_transaction_fields("Netflix")
    assert type_ == "Expense"
    assert nwg == "Want"
    assert fv == "Fixed"


def test_derive_transaction_fields_unknown_category_has_safe_fallback():
    type_, nwg, fv = derive_transaction_fields("Not A Category")
    assert type_ == "Expense"


def test_every_expense_and_transfer_category_maps_to_a_budget_row():
    # Every spendable category should auto-increment some Budget Planner row —
    # otherwise budget tracking silently misses it.
    for cat in EXPENSE_CATEGORIES + TRANSFER_CATEGORIES:
        assert cat in BUDGET_CATEGORY_MAP, f"{cat} has no Budget Planner mapping"
