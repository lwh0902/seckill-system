import json

from app.core.redis import RedisPool


QUEUE_KEY = "seckill:order_queue"


async def push_order_message(message: dict) -> int:
    redis = await RedisPool.get_client()
    payload = json.dumps(message, ensure_ascii=False)
    return await redis.rpush(QUEUE_KEY, payload)


async def get_queue_length() -> int:
    redis = await RedisPool.get_client()
    return await redis.llen(QUEUE_KEY)
