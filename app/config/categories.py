"""Category taxonomy — copied EXACTLY from the lookup table in columns
P:S of the 'Cashflow Harian' tab in the user's spreadsheet (rows 3-58).
This is the single source of truth: every category name here must match
the spreadsheet's dropdown list character-for-character, or Google Sheets
data validation on that column will reject the row.

Each entry maps: category -> (Type, Need/Want/Goal, Fixed/Variable)
so the bot can derive all three sheet columns from one LLM-picked category,
instead of asking the LLM to independently guess three enum values that
have to stay consistent with each other.
"""
from __future__ import annotations

# category -> (type, need_want_goal, fixed_variable)
CATEGORY_TAXONOMY: dict[str, tuple[str, str, str]] = {
    # Income
    "Salary": ("Income", "-", "Fixed"),
    "THR": ("Income", "-", "Variable"),
    "Bonus": ("Income", "-", "Variable"),
    "Freelance": ("Income", "-", "Variable"),
    "Side Hustle": ("Income", "-", "Variable"),
    "Investment Return": ("Income", "-", "Variable"),
    "Dividend": ("Income", "-", "Variable"),
    "Interest": ("Income", "-", "Variable"),
    "Gift": ("Income", "-", "Variable"),
    "Refund": ("Income", "-", "Variable"),
    "Cashback": ("Income", "-", "Variable"),
    "Other Income": ("Income", "-", "Variable"),
    # Expense - Need
    "Breakfast": ("Expense", "Need", "Variable"),
    "Lunch": ("Expense", "Need", "Variable"),
    "Dinner": ("Expense", "Need", "Variable"),
    "Groceries": ("Expense", "Need", "Variable"),
    "Transportation": ("Expense", "Need", "Variable"),
    "Fuel": ("Expense", "Need", "Variable"),
    "Parking": ("Expense", "Need", "Variable"),
    "Toll": ("Expense", "Need", "Variable"),
    "Rent": ("Expense", "Need", "Fixed"),
    "Electricity": ("Expense", "Need", "Fixed"),
    "Water": ("Expense", "Need", "Fixed"),
    "Internet": ("Expense", "Need", "Fixed"),
    "Mobile Phone": ("Expense", "Need", "Fixed"),
    "Healthcare": ("Expense", "Need", "Variable"),
    "Insurance": ("Expense", "Need", "Fixed"),
    "Tax": ("Expense", "Need", "Fixed"),
    "Education": ("Expense", "Need", "Fixed"),
    "Parents": ("Expense", "Need", "Fixed"),
    "Child": ("Expense", "Need", "Fixed"),
    "Household": ("Expense", "Need", "Variable"),
    "Debt Payment": ("Expense", "Need", "Fixed"),
    # Expense - Want
    "Coffee": ("Expense", "Want", "Variable"),
    "Dining Out": ("Expense", "Want", "Variable"),
    "Shopping": ("Expense", "Want", "Variable"),
    "Fashion": ("Expense", "Want", "Variable"),
    "Gadget": ("Expense", "Want", "Variable"),
    "Electronics": ("Expense", "Want", "Variable"),
    "Gaming": ("Expense", "Want", "Variable"),
    "Entertainment": ("Expense", "Want", "Variable"),
    "Movie": ("Expense", "Want", "Variable"),
    "Netflix": ("Expense", "Want", "Fixed"),
    "Spotify": ("Expense", "Want", "Fixed"),
    "YouTube Premium": ("Expense", "Want", "Fixed"),
    "Travel": ("Expense", "Want", "Variable"),
    "Vacation": ("Expense", "Want", "Variable"),
    "Hobby": ("Expense", "Want", "Variable"),
    "Beauty": ("Expense", "Want", "Variable"),
    "Skincare": ("Expense", "Want", "Variable"),
    # Transfer - Financial Goal
    "Emergency Fund": ("Transfer", "Financial Goal", "Variable"),
    "Investment": ("Transfer", "Financial Goal", "Variable"),
    "Retirement": ("Transfer", "Financial Goal", "Fixed"),
    "House": ("Transfer", "Financial Goal", "Variable"),
    "Wedding": ("Transfer", "Financial Goal", "Variable"),
    "Car": ("Transfer", "Financial Goal", "Variable"),
    "Education Fund": ("Transfer", "Financial Goal", "Variable"),
    "Business Capital": ("Transfer", "Financial Goal", "Variable"),
    "Vacation Fund": ("Transfer", "Financial Goal", "Variable"),
}

ALL_CATEGORIES: list[str] = list(CATEGORY_TAXONOMY.keys())

INCOME_CATEGORIES = [c for c, (t, _, _) in CATEGORY_TAXONOMY.items() if t == "Income"]
EXPENSE_CATEGORIES = [c for c, (t, _, _) in CATEGORY_TAXONOMY.items() if t == "Expense"]
TRANSFER_CATEGORIES = [c for c, (t, _, _) in CATEGORY_TAXONOMY.items() if t == "Transfer"]

PAYMENT_METHODS: list[str] = [
    "Cash", "Bank Transfer", "QRIS", "Debit Card", "Credit Card", "e-Wallet", "Auto Debit",
]

# Maps a Cashflow Harian category to its row label in the 'Budget Planner' tab,
# so a saved expense/transfer can auto-increment that row's AKTUAL (D) column.
# Labels here are copied verbatim from Budget Planner!B8:B14, B18:B22, B26:B28.
BUDGET_CATEGORY_MAP: dict[str, str] = {
    # Needs
    "Rent": "Sewa/Cicilan Rumah",
    "Breakfast": "Makanan & Kebutuhan Dapur",
    "Lunch": "Makanan & Kebutuhan Dapur",
    "Dinner": "Makanan & Kebutuhan Dapur",
    "Groceries": "Makanan & Kebutuhan Dapur",
    "Transportation": "Transportasi",
    "Fuel": "Transportasi",
    "Parking": "Transportasi",
    "Toll": "Transportasi",
    "Electricity": "Tagihan Utilitas",
    "Water": "Tagihan Utilitas",
    "Internet": "Tagihan Utilitas",
    "Mobile Phone": "Tagihan Utilitas",
    "Insurance": "Asuransi",
    "Healthcare": "Kesehatan & Obat",
    "Tax": "Kebutuhan Lainnya",
    "Education": "Kebutuhan Lainnya",
    "Parents": "Kebutuhan Lainnya",
    "Child": "Kebutuhan Lainnya",
    "Household": "Kebutuhan Lainnya",
    "Debt Payment": "Kebutuhan Lainnya",
    # Wants
    "Entertainment": "Hiburan & Streaming",
    "Movie": "Hiburan & Streaming",
    "Netflix": "Hiburan & Streaming",
    "Spotify": "Hiburan & Streaming",
    "YouTube Premium": "Hiburan & Streaming",
    "Gaming": "Hiburan & Streaming",
    "Coffee": "Makan di Luar / Kafe",
    "Dining Out": "Makan di Luar / Kafe",
    "Shopping": "Belanja Fashion & Lifestyle",
    "Fashion": "Belanja Fashion & Lifestyle",
    "Gadget": "Belanja Fashion & Lifestyle",
    "Electronics": "Belanja Fashion & Lifestyle",
    "Beauty": "Belanja Fashion & Lifestyle",
    "Skincare": "Belanja Fashion & Lifestyle",
    "Hobby": "Hobi & Rekreasi",
    "Travel": "Hobi & Rekreasi",
    "Vacation": "Hobi & Rekreasi",
    # Saving & Invest
    "Emergency Fund": "Dana Darurat (target 3-6 bln)",
    "Investment": "Investasi Jangka Panjang",
    "Retirement": "Investasi Jangka Panjang",
    "House": "Tabungan Tujuan Khusus",
    "Wedding": "Tabungan Tujuan Khusus",
    "Car": "Tabungan Tujuan Khusus",
    "Education Fund": "Tabungan Tujuan Khusus",
    "Business Capital": "Tabungan Tujuan Khusus",
    "Vacation Fund": "Tabungan Tujuan Khusus",
}


def derive_transaction_fields(category: str) -> tuple[str, str, str]:
    """Given a validated category name, return (type, need_want_goal,
    fixed_variable) exactly as defined in the sheet's own lookup table.
    """
    return CATEGORY_TAXONOMY.get(category, ("Expense", "Need", "Variable"))

