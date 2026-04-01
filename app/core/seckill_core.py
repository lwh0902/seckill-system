from __future__ import annotations

import asyncio
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import NoScriptError

from app.core.redis import RedisPool


SECKILL_LUA_SCRIPT = """
if redis.call("SISMEMBER", KEYS[2], ARGV[1]) == 1 then
    return 2
end

local stock = tonumber(redis.call("GET", KEYS[1]) or "0")
if stock <= 0 then
    return 0
end

redis.call("DECR", KEYS[1])
redis.call("SADD", KEYS[2], ARGV[1])
return 1
"""


_script_sha: Optional[str] = None
_script_lock = asyncio.Lock()


async def load_seckill_script(redis: Optional[Redis] = None) -> str:
    client = redis or await RedisPool.get_client()

    global _script_sha
    if _script_sha is not None:
        return _script_sha

    async with _script_lock:
        if _script_sha is None:
            _script_sha = await client.script_load(SECKILL_LUA_SCRIPT)

    return _script_sha


async def execute_seckill(
    stock_key: str,
    user_set_key: str,
    user_id: str,
    redis: Optional[Redis] = None,
) -> int:
    client = redis or await RedisPool.get_client()
    script_sha = await load_seckill_script(client)

    try:
        result = await client.evalsha(
            script_sha,
            2,
            stock_key,
            user_set_key,
            user_id,
        )
    except NoScriptError:
        # Reload the script once if Redis lost its cached Lua scripts.
        script_sha = await client.script_load(SECKILL_LUA_SCRIPT)

        global _script_sha
        _script_sha = script_sha

        result = await client.evalsha(
            script_sha,
            2,
            stock_key,
            user_set_key,
            user_id,
        )

    return int(result)
