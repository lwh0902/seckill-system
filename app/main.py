from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app.core.redis import RedisPool, shutdown_redis, startup_redis
from app.core.seckill_core import execute_seckill as run_seckill


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_redis()
    try:
        yield
    finally:
        await shutdown_redis()


app = FastAPI(lifespan=lifespan)


class SeckillRequest(BaseModel):
    item_id: str
    user_id: str


async def execute_seckill(item_id: str, user_id: str) -> int:
    stock_key = f"item_{item_id}_stock"
    users_key = f"item_{item_id}_users"
    return await run_seckill(stock_key, users_key, user_id)


@app.get("/")
async def root() -> dict[str, bool]:
    redis = await RedisPool.get_client()
    return {"redis_ping": await redis.ping()}


@app.post("/api/seckill")
async def seckill(req: SeckillRequest) -> dict[str, str | int]:
    result = await execute_seckill(req.item_id, req.user_id)

    if result == 1:
        return {"code": 1, "message": "\u62a2\u8d2d\u6210\u529f"}
    if result == 2:
        return {"code": 2, "message": "\u4e0d\u53ef\u91cd\u590d\u8d2d\u4e70"}
    return {"code": 0, "message": "\u5e93\u5b58\u4e0d\u8db3"}
