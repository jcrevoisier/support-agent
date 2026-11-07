import json
import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

ORDERS_FILE = Path(__file__).parent / 'orders.json'


class Order(BaseModel):
    number: str
    product: str
    status: Literal['processing', 'shipped', 'delivered']
    ordered_on: date


ORDERS = {order.number: order for order in map(Order.model_validate, json.loads(ORDERS_FILE.read_text()))}


def find_order(order_number: str) -> Order:
    number = re.sub(r'[^0-9]', '', order_number)
    if not number:
        raise ValueError("That doesn't look like an order number")
    if number not in ORDERS:
        raise ValueError(f"I can't find order {number}")
    return ORDERS[number]
