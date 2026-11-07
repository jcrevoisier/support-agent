import logging
import uuid
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from support_agent import storage
from support_agent.agent import build_agent
from support_agent.models import Message, Ticket
from support_agent.summary import summarize

GREETING = 'Hi! How can I help you today?'
RETRY_REPLY = 'Sorry, something went wrong. Could you send that again?'
GIVE_UP_REPLY = "Sorry, I'm having trouble right now. Please email us at support@example-shop.com and we'll help you."

logger = logging.getLogger(__name__)


class Conversation:
    def __init__(self, agent=None):
        self.agent = agent or build_agent()
        self.id = str(uuid.uuid4())
        self.config = {'configurable': {'thread_id': self.id}, 'recursion_limit': 10}
        self.failures = 0
        self._add_bot_message(GREETING)

    def send(self, text: str) -> str:
        """Send the customer's message to the agent and return the bot's reply."""
        try:
            state = self.agent.invoke({'messages': [HumanMessage(text)]}, self.config)
        except Exception:
            logger.exception('Agent failed in conversation %s', self.id)
            self.failures += 1
            reply = RETRY_REPLY if self.failures == 1 else GIVE_UP_REPLY
            self._add_bot_message(reply)
            return reply
        self.failures = 0
        return state['messages'][-1].text

    def close(self) -> Path | None:
        """Summarize and save the conversation. Call it when the customer leaves.

        Returns the saved file, or ``None`` if the customer never wrote anything.
        """
        transcript = self.transcript
        if not any(message.role == 'customer' for message in transcript):
            return None
        try:
            summary = summarize(transcript, self.ticket)
        except Exception:
            logger.exception('Could not summarize conversation %s', self.id)
            summary = None
        return storage.save_conversation(self.id, transcript, summary)

    @property
    def transcript(self) -> list[Message]:
        return [
            Message(role='customer' if isinstance(message, HumanMessage) else 'bot', content=message.text)
            for message in self._state().get('messages', [])
            if isinstance(message, HumanMessage | AIMessage) and message.text
        ]

    @property
    def ticket(self) -> Ticket | None:
        return storage.load_ticket(self.id)

    def _state(self) -> dict:
        return self.agent.get_state(self.config).values

    def _add_bot_message(self, text: str) -> None:
        self.agent.update_state(self.config, {'messages': [AIMessage(text)]})
