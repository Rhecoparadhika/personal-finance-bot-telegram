from __future__ import annotations

from app.utils.time import current_date
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from app.config.settings import settings
from app.repositories.transaction_repository import transaction_repository
from app.services.chart_service import (
    category_bar_chart,
    category_pie_chart,
    daily_spending_line_chart,
    income_vs_expense_chart,
)
from app.services.export_service import export_transactions_csv
from app.services.report_service import generate_monthly_report
from app.services.summary_service import summary_service
from app.utils.currency import format_currency
from app.utils.formatting import render_summary

router = Router(name="summary")


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    stats = await summary_service.today_summary()
    text = render_summary(**stats, currency=settings.default_currency, period_label="Today")
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("month", "summary"))
async def cmd_month(message: Message) -> None:
    today = current_date()
    stats = await summary_service.month_summary(today.year, today.month, days_in_period=today.day)
    text = render_summary(**stats, currency=settings.default_currency, period_label=today.strftime("%B %Y"))
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("saldo", "balance"))
async def cmd_saldo(message: Message) -> None:
    """Hitung saldo — computed server-side by Apps Script from every row in
    Cashflow Harian (all-time), so it always matches the sheet exactly.
    """
    bal = await summary_service.balance()
    currency = settings.default_currency
    text = (
        "💰 *Saldo (All-Time)*\n\n"
        f"📈 Total Pemasukan: {format_currency(bal['income'], currency)}\n"
        f"📉 Total Pengeluaran: {format_currency(bal['expense'], currency)}\n"
        f"💎 Total Transfer/Tabungan: {format_currency(bal['transfer'], currency)}\n\n"
        f"🌟 *Saldo Bersih: {format_currency(bal['net'], currency)}*"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("report"))
async def cmd_report(message: Message) -> None:
    await message.answer("📄 Generating your PDF report, one moment...")
    today = current_date()
    pdf_bytes = await generate_monthly_report(today.year, today.month, currency=settings.default_currency)
    filename = f"finbot_report_{today.strftime('%Y_%m')}.pdf"
    await message.answer_document(BufferedInputFile(pdf_bytes, filename=filename), caption="📄 Your monthly report")


@router.message(Command("chart"))
async def cmd_chart(message: Message) -> None:
    today = current_date()
    txs = await transaction_repository.get_month(today.year, today.month)
    stats = summary_service.summarize(txs, days_in_period=today.day)

    pie = category_pie_chart(txs)
    bar = category_bar_chart(txs)
    line = daily_spending_line_chart(txs)
    income_expense = income_vs_expense_chart(stats["income"], stats["expense"])

    await message.answer_photo(BufferedInputFile(pie, filename="pie.png"), caption="🥧 Spending by category")
    await message.answer_photo(BufferedInputFile(bar, filename="bar.png"), caption="📊 Spending by category (bar)")
    await message.answer_photo(BufferedInputFile(line, filename="line.png"), caption="📈 Daily spending")
    await message.answer_photo(BufferedInputFile(income_expense, filename="ie.png"), caption="⚖️ Income vs Expense")


@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    txs = await transaction_repository.get_all()
    if not txs:
        await message.answer("No transactions to export yet.")
        return
    csv_bytes = export_transactions_csv(txs)
    filename = f"finbot_export_{current_date().isoformat()}.csv"
    await message.answer_document(BufferedInputFile(csv_bytes, filename=filename), caption=f"📤 {len(txs)} transactions exported")
