from __future__ import annotations

import json
from datetime import date as Date

from app.llm.factory import get_llm_provider
from app.pdf.report_generator import build_pdf_report
from app.repositories.transaction_repository import transaction_repository
from app.services.chart_service import category_pie_chart, daily_spending_line_chart
from app.services.summary_service import summary_service

_RECOMMENDATION_PROMPT = """You are a friendly personal finance coach. Given the JSON summary of a
user's month, write 3-5 sentences of specific, actionable advice (in the same mix of
Indonesian/English the data suggests, default to Indonesian). Be encouraging but honest. Plain text,
no markdown headers."""


async def generate_monthly_report(year: int, month: int, currency: str = "IDR") -> bytes:
    import calendar

    txs = await transaction_repository.get_month(year, month)
    days_in_month = calendar.monthrange(year, month)[1]
    stats = summary_service.summarize(txs, days_in_period=days_in_month)

    pie_png = category_pie_chart(txs)
    daily_png = daily_spending_line_chart(txs)

    provider = get_llm_provider()
    try:
        recommendation = await provider.complete_text(
            _RECOMMENDATION_PROMPT,
            json.dumps({**stats, "period": f"{year}-{month:02d}"}, default=str, ensure_ascii=False),
        )
    except Exception:  # noqa: BLE001
        recommendation = "Keep tracking consistently — that's the biggest driver of financial progress."

    period_label = Date(year, month, 1).strftime("%B %Y")
    return build_pdf_report(
        period_label=period_label,
        income=stats["income"], expense=stats["expense"], savings=stats["savings"],
        saving_rate=stats["saving_rate"], category_breakdown=stats["top_categories"],
        pie_chart_png=pie_png, daily_spending_png=daily_png,
        ai_recommendation=recommendation, currency=currency,
    )
