from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

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


def test_ticket():
    ticket = {'order_number': '1001', 'category': 'damaged_item', 'description': 'Lamp is broken.', 'urgency': 'low'}
    save = AIMessage('', tool_calls=[{'name': 'save_ticket', 'args': ticket, 'id': 'call-1'}])
    chat = conversation(save, 'I logged that your desk lamp arrived broken.')

    assert chat.ticket is None
    assert chat.send('Order 1001, my lamp is broken') == 'I logged that your desk lamp arrived broken.'
    assert chat.ticket == Ticket(**ticket)
