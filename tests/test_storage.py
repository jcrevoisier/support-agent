import json

from support_agent import storage
from support_agent.models import Message, Ticket
from support_agent.summary import Summary

TRANSCRIPT = [Message(role='bot', content='Hi!'), Message(role='customer', content='Order 1001, my lamp is broken')]
TICKET = Ticket(order_number='1001', category='damaged_item', description='Lamp is broken.', urgency='medium')


def test_save(fake_storage):
    path = storage.save('chat-1', TRANSCRIPT, TICKET)

    assert path == fake_storage / 'chat-1.json'
    record = json.loads(path.read_text())
    assert record['ticket'] == TICKET.model_dump(mode='json')
    assert record['summary'] is None
    assert record['transcript'] == [message.model_dump() for message in TRANSCRIPT]
    assert list(fake_storage.iterdir()) == [path], 'no temporary file left behind'


def test_save_with_summary():
    summary = Summary(text='Lamp arrived broken.', key_points=['Order 1001'])
    record = json.loads(storage.save('chat-1', TRANSCRIPT, TICKET, summary).read_text())
    assert record['summary'] == summary.model_dump()


def test_save_replaces_previous_version():
    storage.save('chat-1', TRANSCRIPT, None)
    path = storage.save('chat-1', TRANSCRIPT, TICKET)
    assert json.loads(path.read_text())['ticket']['order_number'] == '1001'
