"""Parses CSV exports (from banks/e-wallets or the bot's own /export) into
raw text rows that get handed to the LLM parser for structuring, same
pattern as the PDF pipeline — layouts vary too much for hardcoded columns.
"""
from __future__ import annotations

import csv
import io

from loguru import logger


class CSVParseError(Exception):
    pass


def extract_csv_text(csv_bytes: bytes, max_rows: int = 500) -> str:
    try:
        decoded = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = csv_bytes.decode("latin-1")

    reader = csv.reader(io.StringIO(decoded))
    rows = list(reader)
    if not rows:
        raise CSVParseError("This CSV file appears to be empty.")

    if len(rows) > max_rows:
        logger.warning("CSV truncated from {} to {} rows", len(rows), max_rows)
        rows = rows[:max_rows]

    return "\n".join(" | ".join(cell for cell in row) for row in rows)
