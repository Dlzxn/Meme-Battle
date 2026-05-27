"""Tests for Telegram notification module."""
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── resolve_chat_id ───────────────────────────────────────────


async def test_resolve_chat_id_finds_username():
    import app.telegram as tg
    tg._chat_id = None

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "ok": True,
        "result": [
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": 123456789},
                    "from": {"username": "code2py"},
                },
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.telegram.httpx.AsyncClient", return_value=mock_client):
        await tg.resolve_chat_id()

    assert tg._chat_id == 123456789


async def test_resolve_chat_id_no_matching_user():
    import app.telegram as tg
    tg._chat_id = None

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "ok": True,
        "result": [
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": 999},
                    "from": {"username": "someoneelse"},
                },
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.telegram.httpx.AsyncClient", return_value=mock_client):
        await tg.resolve_chat_id()

    assert tg._chat_id is None


async def test_resolve_chat_id_api_error():
    import app.telegram as tg
    tg._chat_id = None

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "description": "Unauthorized"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.telegram.httpx.AsyncClient", return_value=mock_client):
        await tg.resolve_chat_id()  # must not raise

    assert tg._chat_id is None


async def test_resolve_chat_id_network_error():
    import app.telegram as tg
    tg._chat_id = None

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

    with patch("app.telegram.httpx.AsyncClient", return_value=mock_client):
        await tg.resolve_chat_id()  # must not raise

    assert tg._chat_id is None


# ── send_error ────────────────────────────────────────────────


async def test_send_error_sends_message():
    import app.telegram as tg
    tg._chat_id = 987654321

    mock_response = MagicMock()
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.telegram.httpx.AsyncClient", return_value=mock_client):
        await tg.send_error("Test error", "some detail")

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args[1]
    assert call_kwargs["json"]["chat_id"] == 987654321
    assert "Test error" in call_kwargs["json"]["text"]


async def test_send_error_resolves_chat_id_if_missing():
    import app.telegram as tg
    tg._chat_id = None

    resolve_called = []

    async def fake_resolve():
        resolve_called.append(True)
        # leave _chat_id as None so send is skipped

    with patch("app.telegram.resolve_chat_id", fake_resolve):
        await tg.send_error("oops")

    assert resolve_called == [True]


async def test_send_error_truncates_long_detail():
    import app.telegram as tg
    tg._chat_id = 111

    posted_texts = []

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    async def capture_post(url, **kwargs):
        posted_texts.append(kwargs["json"]["text"])

    mock_client.post = capture_post

    with patch("app.telegram.httpx.AsyncClient", return_value=mock_client):
        await tg.send_error("title", "x" * 5000)

    assert len(posted_texts) == 1
    assert len(posted_texts[0]) < 4200  # truncated


async def test_send_error_skips_if_chat_id_stays_none():
    import app.telegram as tg
    tg._chat_id = None

    post_called = []

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=lambda *a, **kw: post_called.append(True))

    async def no_op_resolve():
        pass  # leaves _chat_id = None

    with (
        patch("app.telegram.resolve_chat_id", no_op_resolve),
        patch("app.telegram.httpx.AsyncClient", return_value=mock_client),
    ):
        await tg.send_error("no chat id")

    assert post_called == []


async def test_send_error_network_failure_is_silent():
    import app.telegram as tg
    tg._chat_id = 222

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=Exception("timeout"))

    with patch("app.telegram.httpx.AsyncClient", return_value=mock_client):
        await tg.send_error("boom")  # must not raise


# ── TelegramHandler ───────────────────────────────────────────


def test_telegram_handler_ignores_warning():
    import app.telegram as tg
    tg._chat_id = 333

    handler = tg.TelegramHandler()
    record = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="", lineno=0,
        msg="just a warning", args=(), exc_info=None,
    )

    tasks_created = []
    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock(side_effect=lambda coro: tasks_created.append(coro))

    with patch("asyncio.get_running_loop", return_value=mock_loop):
        handler.emit(record)

    assert tasks_created == []  # WARNING is not forwarded


def test_telegram_handler_emits_error():
    import app.telegram as tg
    tg._chat_id = 444

    handler = tg.TelegramHandler()
    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="an error occurred", args=(), exc_info=None,
    )

    tasks_created = []
    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock(side_effect=lambda coro: tasks_created.append(coro))

    with patch("asyncio.get_running_loop", return_value=mock_loop):
        handler.emit(record)

    assert len(tasks_created) == 1
    # Close the coroutine to avoid ResourceWarning
    for t in tasks_created:
        try:
            t.close()
        except Exception:
            pass


def test_telegram_handler_no_loop_is_silent():
    """When there's no running event loop, emit must not raise."""
    import app.telegram as tg
    tg._chat_id = 555

    handler = tg.TelegramHandler()
    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="error without loop", args=(), exc_info=None,
    )

    with patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")):
        handler.emit(record)  # must not raise
