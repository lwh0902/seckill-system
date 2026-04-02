from pydantic import BaseModel


class OrderMessage(BaseModel):
    order_no: str
    item_id: str
    user_id: str
    create_time: str
