"""The ONLY module that talks to Google. Every read/write goes through one
HTTP POST to a Google Apps Script Web App bound to the user's spreadsheet —
no service account, no Google Sheets API credentials, no key file at all.

Contract: POST {GAS_WEB_APP_URL} with JSON body
  {"secret": "<shared secret>", "action": "<actionName>", "payload": {...}}
and the script replies with
  {"status": "ok", ...}  or  {"status": "error", "message": "..."}

The shared secret is just a random string both sides know (set as an Apps
Script "Script Property" and as GAS_SHARED_SECRET here) — since Apps Script
Web Apps deployed with "Anyone" access are unauthenticated by default, this
is what stops randoms from POSTing fake transactions into your sheet.
"""
from __future__ import annotations

import httpx
from loguru import logger

from app.config.settings import settings
from app.utils.retry import retryable


class AppsScriptError(Exception):
    """Raised when the Apps Script Web App returns status != 'ok', or the
    HTTP call itself fails after retries."""


class AppsScriptClient:
    def __init__(self) -> None:
        self._url = settings.gas_web_app_url
        self._secret = settings.gas_shared_secret

    @retryable((httpx.HTTPError,), attempts=3)
    async def call(self, action: str, payload: dict | None = None) -> dict:
        body = {"secret": self._secret, "action": action, "payload": payload or {}}
        logger.info("Sending Apps Script action '{}' to {}", action, self._url)
        logger.debug("Apps Script payload keys: {}", list((payload or {}).keys()))
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(self._url, json=body)
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "ok":
            message = data.get("message", "Unknown error from Apps Script")
            logger.error("Apps Script action '{}' failed: {}", action, message)
            raise AppsScriptError(message)

        logger.info("Apps Script action '{}' succeeded", action)
        logger.debug("Apps Script response: {}", data)
        return data


apps_script_client = AppsScriptClient()
