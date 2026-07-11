"""OpenCV-based preprocessing to improve Tesseract accuracy on photographed
receipts (skew, noise, uneven lighting).
"""
from __future__ import annotations

import cv2
import numpy as np


def preprocess_receipt_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Upscale small images for better OCR accuracy
    h, w = gray.shape[:2]
    if max(h, w) < 1600:
        scale = 1600 / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Denoise + adaptive threshold to handle uneven receipt lighting
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return thresh
