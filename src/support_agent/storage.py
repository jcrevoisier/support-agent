from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from support_agent.llm import chat_model
from support_agent.models import Message, Ticket

CONVERSATIONS_DIR = Path('conversations')

SUMMARY_PROMPT = """Summarize this chat between an online shop's support bot and a customer, in English.
Write a summary of one or two sentences, and a few short key points: the order, the problem, the urgency and the \
outcome."""


class Summary(BaseModel):
    summary: str
    key_points: list[str]


class ConversationRecord(BaseModel):
    id: str
    saved_at: datetime
    ticket: Ticket | None
    summary: str | None
    key_points: list[str]
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
        summary=summary.summary if summary else None,
        key_points=summary.key_points if summary else [],
        transcript=transcript,
    )
    CONVERSATIONS_DIR.mkdir(exist_ok=True)
    path = path_for(conversation_id)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(record.model_dump_json(indent=2))
    temporary.replace(path)
    return path


def path_for(conversation_id: str) -> Path:
    return CONVERSATIONS_DIR / f'{conversation_id}.json'


def summarize(transcript: list[Message]) -> Summary:
    chat = '\n'.join(f'{message.role}: {message.content}' for message in transcript)
    return chat_model().with_structured_output(Summary).invoke([('system', SUMMARY_PROMPT), ('user', chat)])
