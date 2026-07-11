"""Generates bar/pie/line charts as PNG bytes (matplotlib, non-interactive
Agg backend) ready to send as a Telegram photo or embed in the PDF report.
"""
from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.schemas.transaction import Transaction

_COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2",
           "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"]


def _fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def category_pie_chart(txs: list[Transaction], title: str = "Spending by Category") -> bytes:
    totals: dict[str, float] = {}
    for t in txs:
        if t.type.value == "Expense":
            totals[t.category] = totals.get(t.category, 0) + t.amount
    fig, ax = plt.subplots(figsize=(6, 6))
    if not totals:
        ax.text(0.5, 0.5, "No expense data", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)
    labels, values = zip(*sorted(totals.items(), key=lambda kv: kv[1], reverse=True))
    ax.pie(values, labels=labels, autopct="%1.1f%%", colors=_COLORS, startangle=90)
    ax.set_title(title)
    return _fig_to_png(fig)


def category_bar_chart(txs: list[Transaction], title: str = "Spending by Category") -> bytes:
    totals: dict[str, float] = {}
    for t in txs:
        if t.type.value == "Expense":
            totals[t.category] = totals.get(t.category, 0) + t.amount
    fig, ax = plt.subplots(figsize=(8, 5))
    if not totals:
        ax.text(0.5, 0.5, "No expense data", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)
    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    labels, values = zip(*items)
    ax.bar(labels, values, color=_COLORS[: len(labels)])
    ax.set_title(title)
    ax.set_ylabel("Amount")
    plt.xticks(rotation=45, ha="right")
    return _fig_to_png(fig)


def daily_spending_line_chart(txs: list[Transaction], title: str = "Daily Spending") -> bytes:
    daily: dict = {}
    for t in txs:
        if t.type.value == "Expense":
            daily[t.date] = daily.get(t.date, 0) + t.amount
    fig, ax = plt.subplots(figsize=(9, 4))
    if not daily:
        ax.text(0.5, 0.5, "No expense data", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)
    dates = sorted(daily.keys())
    values = [daily[d] for d in dates]
    ax.plot(dates, values, marker="o", color=_COLORS[0])
    ax.set_title(title)
    ax.set_ylabel("Amount")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    return _fig_to_png(fig)


def income_vs_expense_chart(income: float, expense: float, title: str = "Income vs Expense") -> bytes:
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.bar(["Income", "Expense"], [income, expense], color=[_COLORS[2], _COLORS[3]])
    ax.set_title(title)
    return _fig_to_png(fig)
