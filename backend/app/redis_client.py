import json
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def redis_set(key: str, value: Any, ex: int | None = None) -> None:
    r = await get_redis()
    await r.set(key, json.dumps(value), ex=ex)


async def redis_get(key: str) -> Any | None:
    r = await get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw is not None else None


async def redis_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def redis_publish(channel: str, message: Any) -> None:
    r = await get_redis()
    await r.publish(channel, json.dumps(message))
