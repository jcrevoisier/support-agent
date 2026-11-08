import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from support_agent import policies
from support_agent.agent import search_policies


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    """Embed with random vectors instead of an AI call. They do not show meaning, so these tests check the wiring."""
    monkeypatch.setattr(policies, 'embedding_model', lambda: DeterministicFakeEmbedding(size=8))
    policies._store.cache_clear()
    yield
    policies._store.cache_clear()


def test_search_returns_whole_sections():
    sections = policies.search('Can I return worn shoes?')
    assert len(sections) == 2
    assert all(
        section.split('\n')[0] in {'Returns', 'Refunds', 'Shipping', 'Damaged or wrong items', 'Exchanges'}
        for section in sections
    )


def test_search_policies_tool():
    question = 'How long does shipping take?'
    assert search_policies.invoke({'question': question}) == '\n\n'.join(policies.search(question))


def test_search_policies_tool_when_search_fails(monkeypatch):
    def broken_search(question):
        raise RuntimeError('API is down')

    monkeypatch.setattr(policies, 'search', broken_search)
    assert search_policies.invoke({'question': 'Can I return it?'}).startswith('Error:')
