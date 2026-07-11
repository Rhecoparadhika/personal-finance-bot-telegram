"""FastAPI entrypoint. Registers the Telegram webhook automatically on
startup (Railway gives us BASE_URL; we derive the full webhook URL and tell
Telegram about it), exposes a health check, and forwards webhook POSTs into
aiogram's Dispatcher.
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import FastAPI, Request, Response
from loguru import logger

from app.bot.factory import create_bot, create_dispatcher
from app.config.settings import settings

logger.remove()
logger.add(sys.stdout, level=settings.log_level, backtrace=True, diagnose=False)

bot = create_bot()
dp = create_dispatcher()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FinBot — registering webhook at {}", settings.webhook_url)
    await bot.set_webhook(
        url=settings.webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )
    yield
    logger.info("Shutting down — removing webhook")
    await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(title="FinBot — AI Personal Finance Assistant", lifespan=lifespan)


@app.get("/")
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "finbot"}


@app.post(settings.webhook_path)
async def telegram_webhook(request: Request) -> Response:
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)
    return Response(status_code=200)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=settings.environment == "development")
