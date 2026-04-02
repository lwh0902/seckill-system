import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


MYSQL_URL = os.getenv(
    "MYSQL_URL",
    "mysql+pymysql://root:123456@127.0.0.1:3306/seckill_system?charset=utf8mb4",
)

engine = create_engine(
    MYSQL_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
