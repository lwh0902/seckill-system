import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.redis import shutdown_redis, startup_redis
from app.core.seckill_core import execute_seckill as run_seckill


async def execute_seckill(item_id: str, user_id: str) -> int:
    stock_key = f"item_{item_id}_stock"
    users_key = f"item_{item_id}_users"
    return await run_seckill(stock_key, users_key, user_id)


async def main() -> None:
    await startup_redis()

    try:
        result_1 = await execute_seckill("1001", "101")
        print(f'execute_seckill("1001", "101") -> {result_1}')

        result_2 = await execute_seckill("1001", "101")
        print(f'execute_seckill("1001", "101") -> {result_2}')

        result_3 = await execute_seckill("1001", "102")
        print(f'execute_seckill("1001", "102") -> {result_3}')
    finally:
        await shutdown_redis()


if __name__ == "__main__":
    asyncio.run(main())
