from __future__ import annotations

import asyncio
from typing import Optional

from redis.asyncio import ConnectionPool, Redis


class RedisPool:
    _lock = asyncio.Lock()
    _pool: Optional[ConnectionPool] = None
    _client: Optional[Redis] = None
    _url = "redis://127.0.0.1:6379/0"

    @classmethod
    async def init(cls) -> Redis:
        if cls._client is not None:
            return cls._client

        async with cls._lock:
            if cls._client is None:
                cls._pool = ConnectionPool.from_url(
                    cls._url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=10,
                )
                cls._client = Redis(connection_pool=cls._pool)
                await cls._client.ping()

        return cls._client

    @classmethod
    async def get_client(cls) -> Redis:
        if cls._client is None:
            return await cls.init()
        return cls._client

    @classmethod
    async def close(cls) -> None:
        async with cls._lock:
            if cls._client is not None:
                await cls._client.aclose()
                cls._client = None

            if cls._pool is not None:
                await cls._pool.aclose()
                cls._pool = None


async def startup_redis() -> None:
    await RedisPool.init()


async def shutdown_redis() -> None:
    await RedisPool.close()
