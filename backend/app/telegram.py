"""Telegram error notifications — sends ERROR+ log records to @code2py."""
import asyncio
import logging
import traceback
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = "8349431843:AAHmGqlB5NxiDGfVFOMAGHhvvF4_utGMLi4"
TARGET_USERNAME = "code2py"
_BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

_chat_id: Optional[int] = None


async def resolve_chat_id() -> None:
    """Find chat_id by scanning recent messages sent to the bot from @code2py.
    The user must have sent at least one message to the bot for this to work."""
    global _chat_id
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{_BASE_URL}/getUpdates",
                params={"limit": 100, "allowed_updates": ["message"]},
            )
            data = r.json()
        if not data.get("ok"):
            logger.warning("Telegram getUpdates failed: %s", data)
            return
        for update in reversed(data.get("result", [])):
            msg = update.get("message", {})
            from_ = msg.get("from", {})
            username = (from_.get("username") or "").lower()
            if username == TARGET_USERNAME.lower():
                _chat_id = msg["chat"]["id"]
                logger.info("Telegram chat_id resolved: %d (@%s)", _chat_id, username)
                return
        logger.warning(
            "Telegram: no messages from @%s found. "
            "Send any message to the bot to enable notifications.",
            TARGET_USERNAME,
        )
    except Exception:
        logger.warning("Could not resolve Telegram chat_id", exc_info=True)


async def send_error(title: str, detail: str = "") -> None:
    """Fire-and-forget error notification to Telegram."""
    global _chat_id
    if _chat_id is None:
        await resolve_chat_id()
    if _chat_id is None:
        return

    text = f"🚨 <b>{title}</b>"
    if detail:
        safe = detail[:3500].replace("<", "&lt;").replace(">", "&gt;")
        text += f"\n<pre>{safe}</pre>"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{_BASE_URL}/sendMessage",
                json={"chat_id": _chat_id, "text": text, "parse_mode": "HTML"},
            )
    except Exception:
        logger.error("Failed to send Telegram notification", exc_info=True)


class TelegramHandler(logging.Handler):
    """Logging handler that forwards ERROR+ records to Telegram."""

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return
        try:
            msg = self.format(record)
            if record.exc_info:
                msg += "\n" + "".join(traceback.format_exception(*record.exc_info))
        except Exception:
            msg = record.getMessage()

        title = f"[{record.levelname}] {record.name}"
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(send_error(title, msg))
        except RuntimeError:
            pass  # No running event loop — skip notification
        except Exception:
            pass
