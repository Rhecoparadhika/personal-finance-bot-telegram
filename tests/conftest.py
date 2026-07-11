"""Provides dummy required env vars so Settings() can be constructed during
test collection, without needing a real .env file or real credentials."""
import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST-TOKEN")
os.environ.setdefault("BASE_URL", "https://example.com")
os.environ.setdefault("GAS_WEB_APP_URL", "https://script.google.com/macros/s/test/exec")
os.environ.setdefault("GAS_SHARED_SECRET", "test-secret")
