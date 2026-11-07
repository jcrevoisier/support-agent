import pytest
from pydantic import ValidationError

from support_agent.models import Category, Ticket, Urgency, find_order


@pytest.mark.parametrize('value', ['1001', '#1001', ' 1001 ', 'order 1001', 'ORD-1001'])
def test_find_order(value):
    assert find_order(value)['product'] == 'Desk lamp'


@pytest.mark.parametrize('value', ['', 'abc', '١٠٠١'])
def test_find_order_with_wrong_format(value):
    with pytest.raises(ValueError, match="doesn't look like an order number"):
        find_order(value)


def test_find_order_unknown():
    with pytest.raises(ValueError, match="can't find order 9999"):
        find_order('9999')


def test_ticket_cleans_order_number():
    ticket = Ticket(order_number='#1001', category='damaged_item', description='Lamp is broken.', urgency='medium')
    assert ticket.order_number == '1001'
    assert ticket.category == Category.DAMAGED_ITEM
    assert ticket.urgency == Urgency.MEDIUM


def test_ticket_with_unknown_order():
    with pytest.raises(ValidationError, match="can't find order 9999"):
        Ticket(order_number='9999', category='damaged_item', description='Lamp is broken.', urgency='medium')
