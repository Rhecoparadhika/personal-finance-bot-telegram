"""Runs Tesseract over a preprocessed receipt image and returns raw text.
Structuring the raw text into merchant/date/items/total is delegated to the
LLM parser (it's far more robust at this than regex heuristics), so this
module's job is strictly: image bytes -> clean text.
"""
from __future__ import annotations

import pytesseract
from loguru import logger

from app.ocr.preprocess import preprocess_receipt_image


class OCRExtractionError(Exception):
    pass


def extract_text_from_receipt(image_bytes: bytes, lang: str = "ind+eng") -> str:
    try:
        processed = preprocess_receipt_image(image_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.error("Receipt preprocessing failed: {}", exc)
        raise OCRExtractionError("Could not process this image.") from exc

    try:
        text = pytesseract.image_to_string(processed, lang=lang, config="--psm 6")
    except pytesseract.TesseractError as exc:
        logger.error("Tesseract failed: {}", exc)
        raise OCRExtractionError("OCR engine failed to read this receipt.") from exc

    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not cleaned:
        raise OCRExtractionError("No readable text found on this receipt.")
    return cleaned
