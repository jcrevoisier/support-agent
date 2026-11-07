import json

from support_agent import storage
from support_agent.agent import lookup_order, save_ticket
from support_agent.models import Ticket

TICKET = {'order_number': '#1001', 'category': 'damaged_item', 'description': 'Lamp is broken.', 'urgency': 'low'}


def call_save_ticket(args):
    return save_ticket.invoke(args, config={'configurable': {'thread_id': 'chat-1'}})


def test_lookup_order():
    assert json.loads(lookup_order.invoke({'order_number': '1004'}))['product'] == 'Wireless headphones'


def test_lookup_unknown_order():
    assert lookup_order.invoke({'order_number': '12345'}) == "Error: I can't find order 12345"


def test_save_ticket():
    assert call_save_ticket(TICKET) == 'Ticket saved for order 1001 (Desk lamp, delivered).'
    assert storage.load_ticket('chat-1') == Ticket(**TICKET | {'order_number': '1001'})


def test_save_ticket_with_unknown_order():
    assert call_save_ticket(TICKET | {'order_number': '9999'}) == "Error: I can't find order 9999"
    assert storage.load_ticket('chat-1') is None


def test_save_ticket_without_description():
    assert call_save_ticket(TICKET | {'description': ''}).startswith('Error: description:')
    assert storage.load_ticket('chat-1') is None
