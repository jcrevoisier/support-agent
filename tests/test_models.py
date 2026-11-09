import pytest
from pydantic import ValidationError

from support_agent.models import Ticket


@pytest.mark.parametrize('description', ['', '   '])
def test_ticket_needs_a_description(description):
    with pytest.raises(ValidationError, match='at least 1 character'):
        Ticket(
            order_number='1001', category='damaged_item', description=description, urgency='medium', sentiment='neutral'
        )
