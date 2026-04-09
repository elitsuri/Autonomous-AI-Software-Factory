import time
from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass
class _CacheEntry:
    value: str
    expires_at: float | None


class InMemoryCache:
    def __init__(self) -> None:
        self._values: dict[str, _CacheEntry] = {}

    async def get_text(self, key: str) -> str | None:
        entry = self._values.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and entry.expires_at < time.time():
            self._values.pop(key, None)
            return None
        return entry.value

    async def set_text(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self._values[key] = _CacheEntry(value=value, expires_at=expires_at)


class RedisCache:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get_text(self, key: str) -> str | None:
        value = await self.redis.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def set_text(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds:
            await self.redis.set(key, value, ex=ttl_seconds)
        else:
            await self.redis.set(key, value)

