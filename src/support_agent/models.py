import json
import re
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

ORDERS_FILE = Path(__file__).parent / 'orders.json'
ORDERS = {order['number']: order for order in json.loads(ORDERS_FILE.read_text())}


def find_order(order_number: str) -> dict:
    number = re.sub(r'[^0-9]', '', order_number)
    if not number:
        raise ValueError("That doesn't look like an order number")
    if number not in ORDERS:
        raise ValueError(f"I can't find order {number}")
    return ORDERS[number]


class Category(StrEnum):
    LATE_DELIVERY = 'late_delivery'
    DAMAGED_ITEM = 'damaged_item'
    WRONG_ITEM = 'wrong_item'
    REFUND = 'refund'
    OTHER = 'other'


class Urgency(StrEnum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class Message(BaseModel):
    role: Literal['bot', 'customer']
    content: str


class Ticket(BaseModel):
    order_number: str
    category: Category
    description: str
    urgency: Urgency

    @field_validator('order_number')
    @classmethod
    def check_order_number(cls, value: str) -> str:
        return find_order(value)['number']
