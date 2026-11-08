import json

import pytest

from support_agent import storage
from support_agent.agent import SUPPORT_EMAIL, lookup_order, save_ticket
from support_agent.models import Sentiment, Ticket

TICKET = {
    'order_number': '#1001',
    'category': 'damaged_item',
    'description': 'Lamp is broken.',
    'urgency': 'low',
    'sentiment': 'neutral',
}


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


@pytest.mark.parametrize(
    ('first', 'second', 'kept'),
    [('negative', 'positive', 'negative'), ('neutral', 'negative', 'negative'), ('neutral', 'positive', 'neutral')],
)
def test_save_ticket_keeps_the_worst_sentiment(first, second, kept):
    call_save_ticket(TICKET | {'sentiment': first})
    call_save_ticket(TICKET | {'sentiment': second, 'urgency': 'high'})
    ticket = storage.load_ticket('chat-1')
    assert ticket.sentiment == Sentiment(kept)
    assert ticket.urgency == 'high', 'the other fields are updated'


def test_save_ticket_when_storage_fails(monkeypatch):
    def broken_save(*args):
        raise OSError('Disk full')

    monkeypatch.setattr(storage, 'save_ticket', broken_save)
    assert (
        call_save_ticket(TICKET) == f'Error: the ticket could not be saved. Ask the customer to email {SUPPORT_EMAIL}.'
    )


def test_save_ticket_with_a_broken_conversation_file(fake_storage):
    (fake_storage / 'chat-1.json').write_text('not json')
    assert call_save_ticket(TICKET).startswith('Error: the ticket could not be saved.')
