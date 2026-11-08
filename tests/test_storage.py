import json

from support_agent import storage
from support_agent.models import Message, Ticket, Urgency
from support_agent.summary import Summary

TRANSCRIPT = [Message(role='bot', content='Hi!'), Message(role='customer', content='Order 1001, my lamp is broken')]
TICKET = Ticket(
    order_number='1001', category='damaged_item', description='Lamp is broken.', urgency='medium', sentiment='neutral'
)
SUMMARY = Summary(text='Lamp arrived broken.', key_points=['Order 1001'])


def test_no_ticket_before_it_is_saved():
    assert storage.load_ticket('chat-1') is None


def test_save_ticket_replaces_the_previous_ticket():
    storage.save_ticket('chat-1', TICKET)
    storage.save_ticket('chat-1', TICKET.model_copy(update={'urgency': Urgency.HIGH}))
    assert storage.load_ticket('chat-1').urgency == Urgency.HIGH


def test_save_conversation_keeps_the_ticket(fake_storage):
    storage.save_ticket('chat-1', TICKET)
    path = storage.save_conversation('chat-1', TRANSCRIPT, SUMMARY)

    assert path == fake_storage / 'chat-1.json'
    record = json.loads(path.read_text())
    assert record['ticket'] == TICKET.model_dump(mode='json')
    assert record['summary'] == SUMMARY.model_dump()
    assert record['transcript'] == [message.model_dump() for message in TRANSCRIPT]
    assert list(fake_storage.iterdir()) == [path], 'no temporary file left behind'


def test_save_conversation_without_ticket_or_summary():
    record = json.loads(storage.save_conversation('chat-1', TRANSCRIPT, None).read_text())
    assert record['ticket'] is None
    assert record['summary'] is None
