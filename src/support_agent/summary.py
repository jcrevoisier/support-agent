from pydantic import BaseModel

from support_agent.llm import chat_model
from support_agent.models import Message, Ticket

SUMMARY_PROMPT = """Summarize this chat between an online shop's support bot and a customer, in English.
Write a summary of one or two sentences, and a few short key points: the order, the problem, the urgency and the \
outcome. Take the order, the problem and the urgency from the saved ticket when there is one."""


class Summary(BaseModel):
    text: str
    key_points: list[str]


def summarize(transcript: list[Message], ticket: Ticket | None) -> Summary:
    chat = '\n'.join(f'{message.role}: {message.content}' for message in transcript)
    chat += f'\n\nSaved ticket: {ticket.model_dump_json() if ticket else "none"}'
    return chat_model().with_structured_output(Summary).invoke([('system', SUMMARY_PROMPT), ('user', chat)])
