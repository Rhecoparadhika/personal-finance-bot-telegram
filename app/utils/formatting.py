"""Builds the polished Markdown confirmation cards and summary messages
shown to the user. Kept separate from handlers so the "look and feel" can be
iterated on in one place.
"""
from __future__ import annotations

from app.schemas.transaction import Transaction, TransactionCreate
from app.utils.currency import format_currency

_TYPE_EMOJI = {"Expense": "💸", "Income": "💰", "Transfer": "🔁"}

_CATEGORY_EMOJI = {
    "Salary": "🏢", "THR": "🎁", "Bonus": "🎁", "Freelance": "💻", "Side Hustle": "💼",
    "Investment Return": "📈", "Dividend": "📊", "Interest": "🏦", "Gift": "🎁",
    "Refund": "↩️", "Cashback": "↩️", "Other Income": "💵",
    "Breakfast": "🍳", "Lunch": "🍜", "Dinner": "🍽️", "Groceries": "🛒",
    "Transportation": "🚗", "Fuel": "⛽", "Parking": "🅿️", "Toll": "🛣️",
    "Rent": "🏠", "Electricity": "💡", "Water": "🚰", "Internet": "🌐",
    "Mobile Phone": "📱", "Healthcare": "🏥", "Insurance": "🛡️", "Tax": "🏛️",
    "Education": "📚", "Parents": "👨‍👩‍👧", "Child": "🧒", "Household": "🧹",
    "Debt Payment": "🧾", "Coffee": "☕", "Dining Out": "🍽️", "Shopping": "🛍️",
    "Fashion": "👗", "Gadget": "📱", "Electronics": "💻", "Gaming": "🎮",
    "Entertainment": "🎬", "Movie": "🎥", "Netflix": "📺", "Spotify": "🎵",
    "YouTube Premium": "📺", "Travel": "✈️", "Vacation": "🏖️", "Hobby": "🎨",
    "Beauty": "💄", "Skincare": "🧴", "Emergency Fund": "🚨", "Investment": "📈",
    "Retirement": "🏖️", "House": "🏡", "Wedding": "💍", "Car": "🚙",
    "Education Fund": "🎓", "Business Capital": "🏭", "Vacation Fund": "🧳",
}


def _emoji_for(category: str) -> str:
    return _CATEGORY_EMOJI.get(category, "🔹")


def render_confirmation_card(tx: TransactionCreate, currency: str = "IDR", pending: bool = True) -> str:
    header = "🧾 *Confirm Transaction*" if pending else "✅ *Transaction Saved*"
    lines = [
        header,
        "",
        f"{_emoji_for(tx.category)} *Category*",
        f"{tx.category} ({tx.need_want_goal})" if tx.need_want_goal != "-" else tx.category,
        "",
        f"{_TYPE_EMOJI.get(tx.type.value, '🔹')} *Amount*",
        f"{format_currency(tx.amount, currency)}  ({tx.type.value})",
        "",
        "📅 *Date*",
        f"{tx.date.isoformat()} {tx.time.strftime('%H:%M')}",
    ]
    if tx.merchant:
        lines += ["", "🏪 *Merchant*", tx.merchant]
    if tx.payment_method:
        lines += ["", "💳 *Payment*", tx.payment_method]
    if tx.account:
        lines += ["", "🏦 *Account*", tx.account]
    if tx.notes:
        lines += ["", "📝 *Notes*", tx.notes]
    if tx.tags:
        lines += ["", "🏷️ *Tags*", ", ".join(tx.tags)]
    if tx.confidence < 0.6:
        lines += ["", f"⚠️ _Low confidence ({tx.confidence:.0%}) — please double-check._"]
    return "\n".join(lines)


def render_multi_confirmation(txs: list[TransactionCreate], currency: str = "IDR") -> str:
    lines = [f"🧾 *Found {len(txs)} transactions* — review below:\n"]
    total = 0.0
    for i, tx in enumerate(txs, start=1):
        label = tx.merchant or tx.category
        sign = "+" if tx.type.value == "Income" else "-"
        lines.append(f"{i}. {_emoji_for(tx.category)} {label} ({tx.category}) — {sign}{format_currency(tx.amount, currency)}")
        total += tx.amount if tx.type.value == "Income" else -tx.amount
    lines.append(f"\nNet: {format_currency(abs(total), currency)} {'📈' if total >= 0 else '📉'}")
    return "\n".join(lines)


def render_summary(
    income: float, expense: float, savings: float, saving_rate: float,
    top_categories: list[tuple[str, float]], top_merchants: list[tuple[str, float]],
    avg_daily: float, largest_expense: float, currency: str, period_label: str,
) -> str:
    lines = [
        f"📊 *{period_label} Summary*",
        "",
        f"💰 Income: {format_currency(income, currency)}",
        f"💸 Expense: {format_currency(expense, currency)}",
        f"🐖 Tabungan & Investasi (Transfer): {format_currency(savings, currency)}",
        f"📈 Saving Rate: {saving_rate:.1f}%",
        f"📅 Avg Daily Spend: {format_currency(avg_daily, currency)}",
        f"🔺 Largest Expense: {format_currency(largest_expense, currency)}",
    ]
    if top_categories:
        lines += ["", "*Top Categories*"]
        lines += [f"  {i+1}. {c} — {format_currency(a, currency)}" for i, (c, a) in enumerate(top_categories[:5])]
    if top_merchants:
        lines += ["", "*Top Merchants*"]
        lines += [f"  {i+1}. {m} — {format_currency(a, currency)}" for i, (m, a) in enumerate(top_merchants[:5])]
    return "\n".join(lines)
