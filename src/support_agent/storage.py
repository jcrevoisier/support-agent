from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from support_agent.models import Message, Ticket
from support_agent.summary import Summary

CONVERSATIONS_DIR = Path('conversations')


class ConversationRecord(BaseModel):
    id: str
    saved_at: datetime
    ticket: Ticket | None
    summary: Summary | None
    transcript: list[Message]


def save(
    conversation_id: str, transcript: list[Message], ticket: Ticket | None, summary: Summary | None = None
) -> Path:
    """Write the conversation to ``conversations/<id>.json``, replacing the previous version.

    Writes to a temporary file first, so an interrupted write never leaves a broken file.
    """
    record = ConversationRecord(
        id=conversation_id,
        saved_at=datetime.now(UTC),
        ticket=ticket,
        summary=summary,
        transcript=transcript,
    )
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    path = CONVERSATIONS_DIR / f'{conversation_id}.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(record.model_dump_json(indent=2))
    temporary.replace(path)
    return path
