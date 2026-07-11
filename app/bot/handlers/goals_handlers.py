"""`/goals` lists the 3 goals already in the template (Dana Darurat, Mobil,
Menikah — read live from 'Goal Planning'); `/goals add <name> <amount>`
contributes to one by name; `/goals target <name> <amount>` updates its
target. New goal *names* can't be created here — they're formula-linked
from the 'Cashflow' tab's TABUNGAN & INVESTASI section in the template, so
adding a new one means adding it there first.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config.settings import settings
from app.services.goal_service import goal_service
from app.utils.currency import format_currency

router = Router(name="goals")


@router.message(Command("goals"))
async def cmd_goals(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) == 1:
        goals = await goal_service.list_goals()
        if not goals:
            await message.answer("Couldn't reach the Goal Planning tab. Please try again shortly.")
            return
        lines = ["*🎯 Your Goals*", ""]
        for g in goals:
            bar_len = 10
            filled = min(bar_len, int(g.progress_pct / 100 * bar_len))
            bar = "█" * filled + "░" * (bar_len - filled)
            lines.append(
                f"*{g.name}*\n{bar} {g.progress_pct:.0f}%\n"
                f"{format_currency(g.current_amount, settings.default_currency)} / "
                f"{format_currency(g.target_amount, settings.default_currency)}"
                + (f"\n_{g.feasibility}_" if g.feasibility else "")
                + "\n"
            )
        lines.append("Add funds: `/goals add <name> <amount>`\nChange target: `/goals target <name> <amount>`")
        await message.answer("\n".join(lines), parse_mode="Markdown")
        return

    args = parts[1].split(maxsplit=1)
    if len(args) != 2 or args[0].lower() not in ("add", "target"):
        await message.answer(
            "Usage:\n`/goals` — list\n`/goals add <name> <amount>` — contribute\n"
            "`/goals target <name> <amount>` — change target",
            parse_mode="Markdown",
        )
        return

    subcommand, rest = args[0].lower(), args[1]
    remainder = rest.rsplit(maxsplit=1)
    if len(remainder) != 2:
        await message.answer("Please include both the goal name and an amount.")
        return
    name, amount_str = remainder
    try:
        amount = float(amount_str.replace(".", "").replace(",", ""))
    except ValueError:
        await message.answer("Please provide a valid amount.")
        return

    if subcommand == "add":
        updated = await goal_service.contribute(name.strip(), amount)
        verb = "Added"
    else:
        updated = await goal_service.set_target(name.strip(), amount)
        verb = "Target set for"

    if not updated:
        await message.answer(
            f"❌ '{name.strip()}' doesn't match a goal in your Goal Planning tab. "
            "Use `/goals` with no arguments to see the exact names.",
            parse_mode="Markdown",
        )
        return

    await message.answer(
        f"✅ {verb} *{updated.name}* — now "
        f"{format_currency(updated.current_amount, settings.default_currency)} / "
        f"{format_currency(updated.target_amount, settings.default_currency)} "
        f"({updated.progress_pct:.0f}%)",
        parse_mode="Markdown",
    )
