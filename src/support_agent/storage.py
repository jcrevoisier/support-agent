from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from support_agent.models import Message, Ticket
from support_agent.summary import Summary

CONVERSATIONS_DIR = Path('conversations')


class ConversationRecord(BaseModel):
    id: str
    saved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ticket: Ticket | None = None
    summary: Summary | None = None
    transcript: list[Message] = []


def save_ticket(conversation_id: str, ticket: Ticket) -> None:
    """Write the ticket to the conversation file, replacing the previous ticket."""
    record = _load(conversation_id)
    record.ticket = ticket
    _write(record)


def save_conversation(conversation_id: str, transcript: list[Message], summary: Summary | None) -> Path:
    """Write the transcript and the summary to the conversation file, and keep its ticket."""
    record = _load(conversation_id)
    record.transcript = transcript
    record.summary = summary
    return _write(record)


def load_ticket(conversation_id: str) -> Ticket | None:
    return _load(conversation_id).ticket


def _path(conversation_id: str) -> Path:
    return CONVERSATIONS_DIR / f'{conversation_id}.json'


def _load(conversation_id: str) -> ConversationRecord:
    path = _path(conversation_id)
    if path.exists():
        return ConversationRecord.model_validate_json(path.read_text())
    return ConversationRecord(id=conversation_id)


def _write(record: ConversationRecord) -> Path:
    """Write to a temporary file first, so an interrupted write never leaves a broken file."""
    record.saved_at = datetime.now(UTC)
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    path = _path(record.id)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(record.model_dump_json(indent=2))
    temporary.replace(path)
    return path
