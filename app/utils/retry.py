"""Shared retry policies built on tenacity, used to wrap flaky I/O
(Google Sheets API calls, LLM provider calls) with exponential backoff.
"""
from __future__ import annotations

from loguru import logger
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


def retryable(exceptions: tuple[type[Exception], ...], attempts: int = 3):
    """Decorator factory: retry on the given exception types with exponential
    backoff (0.5s, 1s, 2s), logging each retry attempt.
    """
    return retry(
        reraise=True,
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, "WARNING"),  # type: ignore[arg-type]
    )
