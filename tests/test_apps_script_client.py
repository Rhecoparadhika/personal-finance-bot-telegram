"""These tests mock httpx entirely — they verify the Python-side contract
(what gets sent, how responses are parsed) without needing a real Apps
Script deployment."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.google.apps_script_client import AppsScriptClient, AppsScriptError
from app.models.enums import TransactionSource
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreate


def _mock_response(json_data):
    mock_resp = AsyncMock()
    mock_resp.json = lambda: json_data
    mock_resp.raise_for_status = lambda: None
    return mock_resp


def test_apps_script_client_sends_secret_and_action():
    client = AppsScriptClient()
    client._url = "https://example.com/exec"
    client._secret = "s3cr3t"

    captured = {}

    class FakeAsyncClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return _mock_response({"status": "ok", "transactionId": "TRX000099"})

    with patch("app.google.apps_script_client.httpx.AsyncClient", FakeAsyncClient):
        result = asyncio.run(client.call("addTransaction", {"amount": 1000}))

    assert captured["json"]["secret"] == "s3cr3t"
    assert captured["json"]["action"] == "addTransaction"
    assert captured["json"]["payload"] == {"amount": 1000}
    assert result["transactionId"] == "TRX000099"


def test_apps_script_client_raises_on_error_status():
    client = AppsScriptClient()
    client._url = "https://example.com/exec"
    client._secret = "s3cr3t"

    class FakeAsyncClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, json):
            return _mock_response({"status": "error", "message": "boom"})

    with patch("app.google.apps_script_client.httpx.AsyncClient", FakeAsyncClient):
        with pytest.raises(AppsScriptError, match="boom"):
            asyncio.run(client.call("getBudgets"))


def test_transaction_repository_append_returns_transaction_and_alert():
    repo = TransactionRepository()
    tx = TransactionCreate(date="2026-07-11", type="Expense", category="Fuel", amount=400000)

    async def fake_call(action, payload=None):
        assert action == "addTransaction"
        assert payload["category"] == "Fuel"
        return {"status": "ok", "transactionId": "TRX000042", "budgetAlert": "⚠️ Budget Alert"}

    with patch("app.repositories.transaction_repository.apps_script_client.call", fake_call):
        saved, alert = asyncio.run(repo.append_transaction(tx, TransactionSource.TEXT))

    assert saved.transaction_id == "TRX000042"
    assert saved.amount == 400000
    assert alert == "⚠️ Budget Alert"
