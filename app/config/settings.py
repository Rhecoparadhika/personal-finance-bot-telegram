"""Centralized application configuration.

Loaded once as a singleton `settings` object. Every other module imports
`settings` from here instead of reading os.environ directly.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str = Field(..., alias="BOT_TOKEN")
    base_url: str = Field(..., alias="BASE_URL")
    webhook_secret: str = Field(default="change-me", alias="WEBHOOK_SECRET")

    # LLM
    llm_provider: Literal["openai", "claude", "gemini"] = Field(default="openai", alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    claude_api_key: str | None = Field(default=None, alias="CLAUDE_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    claude_model: str = Field(default="claude-sonnet-4-6", alias="CLAUDE_MODEL")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    whisper_model: str = Field(default="whisper-1", alias="WHISPER_MODEL")

    # Google Sheets — via Apps Script Web App (NO service account / API key).
    # See google-apps-script/Code.gs and README "Google Apps Script Setup".
    gas_web_app_url: str = Field(..., alias="GAS_WEB_APP_URL")
    gas_shared_secret: str = Field(..., alias="GAS_SHARED_SECRET")

    # App
    port: int = Field(default=8000, alias="PORT")
    timezone: str = Field(default="Asia/Jakarta", alias="TIMEZONE")
    default_currency: str = Field(default="IDR", alias="DEFAULT_CURRENCY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    environment: Literal["development", "production"] = Field(default="production", alias="ENVIRONMENT")

    @property
    def webhook_path(self) -> str:
        return f"/webhook/{self.webhook_secret}"

    @property
    def webhook_url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
