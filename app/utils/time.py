from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from datetime import time as Time
from zoneinfo import ZoneInfo

from app.config.settings import settings


def current_date(tz: str | None = None) -> Date:
    tz = tz or settings.timezone
    return datetime.now(ZoneInfo(tz)).date()


def current_time(tz: str | None = None) -> Time:
    tz = tz or settings.timezone
    return datetime.now(ZoneInfo(tz)).time().replace(microsecond=0)
