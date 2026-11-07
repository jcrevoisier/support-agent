from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langgraph.graph.state import CompiledStateGraph

from support_agent.agent import build_agent


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


def fake_agent(*replies) -> CompiledStateGraph:
    """An agent whose model answers with the given replies, in order."""
    return build_agent(FakeModel(messages=Replies(*replies)))
