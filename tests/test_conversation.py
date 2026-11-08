import json

import pytest
from langchain_core.messages import AIMessage

from support_agent import storage
from support_agent.conversation import GIVE_UP_REPLY, GREETING, RETRY_REPLY, Conversation
from support_agent.models import Message, Ticket
from tests.fakes import fake_agent


def conversation(*replies) -> Conversation:
    chat = Conversation(fake_agent(*replies))
    assert chat.start() == GREETING
    return chat


def test_reply():
    chat = conversation("What's your order number?")
    assert list(chat.send('My lamp is broken')) == ["What's your order number?"]
    assert chat.transcript == [
        Message(role='bot', content=GREETING),
        Message(role='customer', content='My lamp is broken'),
        Message(role='bot', content="What's your order number?"),
    ]


def test_reply_with_several_messages():
    lookup = AIMessage(
        'Let me check that order.',
        tool_calls=[{'name': 'lookup_order', 'args': {'order_number': '1001'}, 'id': 'call-1'}],
    )
    chat = conversation(lookup, 'Your desk lamp order is marked as delivered.')
    replies = ['Let me check that order.', 'Your desk lamp order is marked as delivered.']
    assert list(chat.send('Where is order 1001?')) == replies
    assert [message.content for message in chat.transcript[2:]] == replies


def test_failures():
    chat = conversation(RuntimeError('timeout'), RuntimeError('timeout'))
    assert list(chat.send('My lamp is broken')) == [RETRY_REPLY]
    assert list(chat.send('My lamp is broken')) == [GIVE_UP_REPLY]
    assert chat.transcript[-1] == Message(role='bot', content=GIVE_UP_REPLY)


def test_failure_count_resets_after_a_reply():
    chat = conversation(RuntimeError('timeout'), "What's your order number?", RuntimeError('timeout'))
    assert list(chat.send('My lamp is broken')) == [RETRY_REPLY]
    assert list(chat.send('My lamp is broken')) == ["What's your order number?"]
    assert list(chat.send('1001')) == [RETRY_REPLY]


def test_ticket_is_saved_and_kept_at_close():
    ticket = {
        'order_number': '1001',
        'category': 'damaged_item',
        'description': 'Lamp is broken.',
        'urgency': 'low',
        'sentiment': 'neutral',
    }
    save = AIMessage('', tool_calls=[{'name': 'save_ticket', 'args': ticket, 'id': 'call-1'}])
    chat = conversation("What's your order number?", save, 'I logged that your desk lamp arrived broken.')

    list(chat.send('My lamp is broken'))
    assert chat.ticket is None
    assert list(chat.send('1001')) == ['I logged that your desk lamp arrived broken.']
    assert chat.ticket == Ticket(**ticket)

    record = json.loads(chat.close().read_text())
    assert record['ticket'] == ticket
    assert record['summary'] == {'text': 'Summary.', 'key_points': ['Point']}


def test_close_saves_with_summary():
    chat = conversation('Hello! How can I help?')
    list(chat.send('Hi'))
    record = json.loads(chat.close().read_text())
    assert record['summary'] == {'text': 'Summary.', 'key_points': ['Point']}
    assert record['transcript'] == [message.model_dump() for message in chat.transcript]


def test_close_saves_when_summary_fails(monkeypatch):
    def broken_summarize(transcript, ticket):
        raise RuntimeError('AI is down')

    monkeypatch.setattr('support_agent.conversation.summarize', broken_summarize)
    chat = conversation('Hello! How can I help?')
    list(chat.send('Hi'))
    record = json.loads(chat.close().read_text())
    assert record['summary'] is None
    assert record['transcript'] == [message.model_dump() for message in chat.transcript]


def test_close_without_customer_message_saves_nothing(fake_storage):
    assert conversation().close() is None
    assert list(fake_storage.iterdir()) == []


def test_close_reports_a_failed_save(monkeypatch):
    def broken_save(*args):
        raise OSError('Disk full')

    monkeypatch.setattr(storage, 'save_conversation', broken_save)
    chat = conversation('Hello! How can I help?')
    list(chat.send('Hi'))
    with pytest.raises(OSError):
        chat.close()
