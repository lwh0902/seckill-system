import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.db import Base, SessionLocal, engine
from app.core.redis import RedisPool, shutdown_redis, startup_redis
from app.model.order import Order
from app.schema.order_message import OrderMessage
from app.service.queue_service import QUEUE_KEY


async def consume_orders() -> None:
    redis = await RedisPool.get_client()

    while True:
        _, payload = await redis.blpop(QUEUE_KEY, timeout=0)
        message = OrderMessage.model_validate_json(payload)

        db = SessionLocal()
        try:
            order = Order(
                order_no=message.order_no,
                item_id=message.item_id,
                user_id=message.user_id,
                create_time=datetime.fromisoformat(message.create_time),
            )
            db.add(order)
            db.commit()
            print(f"订单创建成功: order_no={message.order_no}")
        except IntegrityError as exc:
            db.rollback()
            if "Duplicate entry" in str(exc.orig) or "1062" in str(exc.orig):
                print(f"重复订单，已跳过: order_no={message.order_no}")
            else:
                print(f"订单写入失败: order_no={message.order_no}, error={exc}")
        except Exception as exc:
            db.rollback()
            print(f"订单写入失败: order_no={message.order_no}, error={exc}")
        finally:
            db.close()


async def main() -> None:
    Base.metadata.create_all(bind=engine)
    await startup_redis()

    try:
        await consume_orders()
    finally:
        await shutdown_redis()


if __name__ == "__main__":
    asyncio.run(main())
