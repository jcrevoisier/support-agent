import json

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from support_agent import storage
from support_agent.agent import build_agent
from support_agent.conversation import GIVE_UP_REPLY, GREETING, RETRY_REPLY, Conversation
from support_agent.models import Message, Ticket


class FakeModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


class Replies:
    """Returns the given replies in order, and raises the ones that are exceptions."""

    def __init__(self, *items):
        self.items = list(items)

    def __iter__(self):
        return self

    def __next__(self):
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def conversation(*replies) -> Conversation:
    return Conversation(build_agent(FakeModel(messages=Replies(*replies))))


def test_reply():
    chat = conversation("What's your order number?")
    assert chat.send('My lamp is broken') == "What's your order number?"
    assert chat.transcript == [
        Message(role='bot', content=GREETING),
        Message(role='customer', content='My lamp is broken'),
        Message(role='bot', content="What's your order number?"),
    ]


def test_failures():
    chat = conversation(RuntimeError('timeout'), RuntimeError('timeout'))
    assert chat.send('My lamp is broken') == RETRY_REPLY
    assert chat.send('My lamp is broken') == GIVE_UP_REPLY
    assert chat.transcript[-1] == Message(role='bot', content=GIVE_UP_REPLY)


def test_failure_count_resets_after_a_reply():
    chat = conversation(RuntimeError('timeout'), "What's your order number?", RuntimeError('timeout'))
    assert chat.send('My lamp is broken') == RETRY_REPLY
    assert chat.send('My lamp is broken') == "What's your order number?"
    assert chat.send('1001') == RETRY_REPLY


def test_ticket_update_saves_the_conversation(monkeypatch):
    saves = []

    def summarize(transcript):
        saves.append(len(transcript))
        return storage.Summary(summary='Lamp arrived broken.', key_points=[])

    monkeypatch.setattr(storage, 'summarize', summarize)
    ticket = {'order_number': '1001', 'category': 'damaged_item', 'description': 'Lamp is broken.', 'urgency': 'low'}
    save = AIMessage('', tool_calls=[{'name': 'save_ticket', 'args': ticket, 'id': 'call-1'}])
    chat = conversation("What's your order number?", save, 'I logged that your desk lamp arrived broken.')

    chat.send('My lamp is broken')
    assert chat.send('1001') == 'I logged that your desk lamp arrived broken.'
    assert chat.ticket == Ticket(**ticket)

    record = json.loads(chat.close().read_text())
    assert saves == [5, 5], 'one save for the ticket, one when the chat closes'
    assert record['ticket'] == ticket
    assert record['summary'] == 'Lamp arrived broken.'


def test_close_saves_with_summary():
    chat = conversation('Hello! How can I help?')
    chat.send('Hi')
    record = json.loads(chat.close().read_text())
    assert record['summary'] == 'Summary.'
    assert len(record['transcript']) == 3


def test_close_saves_when_summary_fails(monkeypatch):
    def broken_summarize(transcript):
        raise RuntimeError('AI is down')

    monkeypatch.setattr(storage, 'summarize', broken_summarize)
    chat = conversation('Hello! How can I help?')
    chat.send('Hi')
    record = json.loads(chat.close().read_text())
    assert record['summary'] is None
    assert len(record['transcript']) == 3


def test_close_without_customer_message_saves_nothing(fake_storage):
    assert conversation().close() is None
    assert list(fake_storage.iterdir()) == []


def test_close_reports_a_failed_save(monkeypatch):
    def broken_save(*args):
        raise OSError('Disk full')

    monkeypatch.setattr(storage, 'save', broken_save)
    chat = conversation('Hello! How can I help?')
    chat.send('Hi')
    with pytest.raises(RuntimeError, match='Could not save conversation'):
        chat.close()
