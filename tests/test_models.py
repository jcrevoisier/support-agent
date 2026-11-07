import pytest
from pydantic import ValidationError

from support_agent.models import Category, Ticket, Urgency


def test_ticket():
    ticket = Ticket(order_number='1001', category='damaged_item', description='Lamp is broken.', urgency='medium')
    assert ticket.category == Category.DAMAGED_ITEM
    assert ticket.urgency == Urgency.MEDIUM


@pytest.mark.parametrize('description', ['', '   '])
def test_ticket_needs_a_description(description):
    with pytest.raises(ValidationError, match='at least 1 character'):
        Ticket(order_number='1001', category='damaged_item', description=description, urgency='medium')
