from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.redis import RedisPool, shutdown_redis, startup_redis
from app.core.seckill_core import execute_seckill as run_seckill
from app.model.order import Order
from app.service.queue_service import push_order_message


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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
        message = {
            "order_no": uuid4().hex,
            "item_id": req.item_id,
            "user_id": req.user_id,
            "create_time": datetime.now().isoformat(),
        }
        await push_order_message(message)
        return {"code": 1, "message": "\u62a2\u8d2d\u6210\u529f\uff0c\u6392\u961f\u4e2d"}

    if result == 2:
        return {"code": 2, "message": "\u4e0d\u53ef\u91cd\u590d\u8d2d\u4e70"}

    return {"code": 0, "message": "\u5e93\u5b58\u4e0d\u8db3"}


@app.get("/api/orders/{order_no}")
async def get_order(order_no: str, db: Session = Depends(get_db)) -> dict[str, object]:
    order = db.query(Order).filter(Order.order_no == order_no).first()

    if order is None:
        return {"code": 0, "message": "\u8ba2\u5355\u4e0d\u5b58\u5728"}

    return {
        "code": 1,
        "message": "\u67e5\u8be2\u6210\u529f",
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "user_id": order.user_id,
            "item_id": order.item_id,
            "status": order.status,
            "create_time": order.create_time.isoformat(),
        },
    }
