import pytest

from support_agent import storage
from support_agent.summary import Summary


@pytest.fixture(autouse=True)
def fake_storage(monkeypatch, tmp_path):
    """Save conversations to a temporary folder, with a fixed summary instead of an AI call."""
    monkeypatch.setattr(storage, 'CONVERSATIONS_DIR', tmp_path)
    monkeypatch.setattr(
        'support_agent.conversation.summarize',
        lambda transcript, ticket: Summary(text='Summary.', key_points=['Point']),
    )
    return tmp_path
