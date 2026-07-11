"""Generates the monthly PDF report: executive summary, pie chart, category
breakdown table, income vs expense, daily spending line, saving rate, and an
AI-generated recommendation blurb.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.utils.currency import format_currency


def build_pdf_report(
    *,
    period_label: str,
    income: float,
    expense: float,
    savings: float,
    saving_rate: float,
    category_breakdown: list[tuple[str, float]],
    pie_chart_png: bytes | None,
    daily_spending_png: bytes | None,
    ai_recommendation: str,
    currency: str = "IDR",
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Financial Report — {period_label}", styles["Title"]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    summary_rows = [
        ["Income", format_currency(income, currency)],
        ["Expense", format_currency(expense, currency)],
        ["Savings", format_currency(savings, currency)],
        ["Saving Rate", f"{saving_rate:.1f}%"],
    ]
    summary_table = Table(summary_rows, colWidths=[6 * cm, 6 * cm])
    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.7 * cm))

    if pie_chart_png:
        story.append(Paragraph("Category Breakdown", styles["Heading2"]))
        story.append(Image(io.BytesIO(pie_chart_png), width=12 * cm, height=9 * cm))
        story.append(Spacer(1, 0.5 * cm))

    if category_breakdown:
        rows = [["Category", "Amount"]] + [
            [c, format_currency(a, currency)] for c, a in category_breakdown
        ]
        cat_table = Table(rows, colWidths=[8 * cm, 6 * cm])
        cat_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4053")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 0.7 * cm))

    if daily_spending_png:
        story.append(Paragraph("Daily Spending", styles["Heading2"]))
        story.append(Image(io.BytesIO(daily_spending_png), width=15 * cm, height=7 * cm))
        story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("AI Recommendation", styles["Heading2"]))
    story.append(Paragraph(ai_recommendation, styles["BodyText"]))

    doc.build(story)
    return buffer.getvalue()
