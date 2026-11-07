import json

from langgraph.types import Command

from support_agent.agent import lookup_order, save_ticket

TICKET = {'order_number': '#1001', 'category': 'damaged_item', 'description': 'Lamp is broken.', 'urgency': 'low'}


def call_save_ticket(args):
    return save_ticket.invoke({'type': 'tool_call', 'id': 'call-1', 'name': 'save_ticket', 'args': args})


def test_lookup_order():
    assert json.loads(lookup_order.invoke({'order_number': '1004'}))['product'] == 'Wireless headphones'


def test_lookup_unknown_order():
    assert lookup_order.invoke({'order_number': '12345'}) == "Error: I can't find order 12345"


def test_save_ticket():
    result = call_save_ticket(TICKET)
    assert isinstance(result, Command)
    assert result.update['ticket'] == TICKET | {'order_number': '1001'}
    assert result.update['messages'][0].content == 'Ticket saved.'


def test_save_ticket_with_unknown_order():
    result = call_save_ticket(TICKET | {'order_number': '9999'})
    assert result.content == "Error: I can't find order 9999"


def test_save_ticket_without_description():
    result = call_save_ticket(TICKET | {'description': ''})
    assert result.content == 'Error: String should have at least 1 character'
