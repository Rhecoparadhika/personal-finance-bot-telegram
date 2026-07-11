"""`/budget` with no args shows current status (read live from the Budget
Planner tab); `/budget <label> <amount>` sets the budget for one of the
template's 14 pre-existing category rows.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config.settings import settings
from app.services.budget_service import budget_service
from app.utils.currency import format_currency

router = Router(name="budget")


@router.message(Command("budget"))
async def cmd_budget(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) == 1:
        statuses = await budget_service.status_for_month()
        if not statuses:
            await message.answer("Couldn't reach the Budget Planner tab. Please try again shortly.")
            return
        lines = ["*💰 Budget Status — Budget Planner*", ""]
        current_section = None
        for s in statuses:
            if s.section != current_section:
                current_section = s.section
                lines.append(f"_{current_section}_")
            pct = (s.actual / s.budget * 100) if s.budget else 0
            bar_len = 10
            filled = min(bar_len, int(pct / 100 * bar_len))
            bar = "█" * filled + "░" * (bar_len - filled)
            emoji = "🚨" if pct >= 100 else "⚠️" if pct >= 80 else "✅"
            lines.append(
                f"{emoji} *{s.category}*\n{bar} {pct:.0f}%\n"
                f"{format_currency(s.actual, settings.default_currency)} / "
                f"{format_currency(s.budget, settings.default_currency)}\n"
            )
        await message.answer("\n".join(lines), parse_mode="Markdown")
        return

    # /budget <label...> <amount> — label may contain spaces, so split off
    # only the trailing numeric token.
    remainder = parts[1].rsplit(maxsplit=1)
    if len(remainder) != 2:
        await message.answer("Usage: `/budget <label> <amount>`\nExample: `/budget Transportasi 500000`", parse_mode="Markdown")
        return

    label, amount_str = remainder
    try:
        amount = float(amount_str.replace(".", "").replace(",", ""))
    except ValueError:
        await message.answer("Please provide a valid number for the amount.")
        return

    updated = await budget_service.set_budget(label.strip(), amount)
    if not updated:
        await message.answer(
            f"❌ '{label.strip()}' isn't one of the categories in your Budget Planner tab. "
            "Use `/budget` with no arguments to see the exact labels.",
            parse_mode="Markdown",
        )
        return

    await message.answer(
        f"✅ Budget updated: *{updated.category}* — {format_currency(amount, settings.default_currency)}/month",
        parse_mode="Markdown",
    )
