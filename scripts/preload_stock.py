import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.redis import RedisPool, shutdown_redis, startup_redis


async def main() -> None:
    item_id = "1001"
    stock_key = f"item_{item_id}_stock"
    users_key = f"item_{item_id}_users"

    await startup_redis()

    try:
        redis = await RedisPool.get_client()

        await redis.set(stock_key, 10)
        await redis.delete(users_key)

        stock = await redis.get(stock_key)
        users_count = await redis.scard(users_key)

        print("Preload completed.")
        print(f"item_id: {item_id}")
        print(f"stock_key: {stock_key}, stock: {stock}")
        print(f"users_key: {users_key}, users_count: {users_count}")
    finally:
        await shutdown_redis()


if __name__ == "__main__":
    asyncio.run(main())
