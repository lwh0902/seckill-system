from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.db import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_no = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String(64), nullable=False)
    item_id = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="CREATED")
    create_time = Column(DateTime, nullable=False, default=datetime.now)
