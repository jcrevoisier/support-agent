from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class Sentiment(StrEnum):
    POSITIVE = 'positive'
    NEUTRAL = 'neutral'
    NEGATIVE = 'negative'


class Message(BaseModel):
    role: Literal['bot', 'customer']
    content: str


class Ticket(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_number: str
    category: Category
    description: str = Field(min_length=1)
    urgency: Urgency
    sentiment: Sentiment
