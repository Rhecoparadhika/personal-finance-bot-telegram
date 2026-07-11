"""Extracts raw text (and tables where possible) from bank-statement PDFs.
Uses pdfplumber for text/table extraction and falls back to PyMuPDF for
PDFs pdfplumber struggles with (e.g. some scanned/rotated statements).
The extracted text is handed to the LLM parser, not parsed with regex here,
since bank statement layouts vary wildly.
"""
from __future__ import annotations

import io

import fitz  # PyMuPDF
import pdfplumber
from loguru import logger


class PDFExtractionError(Exception):
    pass


def extract_text_pdfplumber(pdf_bytes: bytes) -> str:
    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            parts.append(text)
            for table in page.extract_tables():
                for row in table:
                    parts.append(" | ".join(c or "" for c in row))
    return "\n".join(p for p in parts if p.strip())


def extract_text_pymupdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def extract_statement_text(pdf_bytes: bytes, max_chars: int = 15000) -> str:
    text = ""
    try:
        text = extract_text_pdfplumber(pdf_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber failed, falling back to PyMuPDF: {}", exc)

    if not text.strip():
        try:
            text = extract_text_pymupdf(pdf_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.error("PyMuPDF also failed: {}", exc)
            raise PDFExtractionError(
                "Couldn't read this PDF — it may be scanned/image-only or encrypted."
            ) from exc

    if not text.strip():
        raise PDFExtractionError("This PDF appears to contain no extractable text.")

    # LLM context guard: truncate very long statements, note it in logs.
    if len(text) > max_chars:
        logger.warning("Statement text truncated from {} to {} chars", len(text), max_chars)
        text = text[:max_chars]
    return text
