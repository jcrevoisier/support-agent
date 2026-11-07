import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from support_agent import storage
from support_agent.agent import build_agent
from support_agent.models import Message, Ticket

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
        self._saver = ThreadPoolExecutor(max_workers=1)
        self._add_bot_message(GREETING)

    def send(self, text: str) -> str:
        """Send the customer's message to the agent and return the bot's reply.

        When the ticket is saved or updated, the conversation is saved in the background, so the reply does not wait
        for the summary.
        """
        ticket_before = self._state().get('ticket')
        try:
            state = self.agent.invoke({'messages': [HumanMessage(text)]}, self.config)
        except Exception:
            logger.exception('Agent failed in conversation %s', self.id)
            self.failures += 1
            reply = RETRY_REPLY if self.failures == 1 else GIVE_UP_REPLY
            self._add_bot_message(reply)
            return reply
        self.failures = 0
        if state.get('ticket') != ticket_before:
            self._saver.submit(self._save, self.transcript, self.ticket)
        return state['messages'][-1].text

    def close(self) -> Path | None:
        """Save the conversation one last time and wait for every save to finish. Call it when the customer leaves.

        Returns the saved file, or ``None`` if the customer never wrote anything.
        """
        transcript = self.transcript
        if any(message.role == 'customer' for message in transcript):
            self._saver.submit(self._save, transcript, self.ticket)
        self._saver.shutdown(wait=True)
        path = storage.path_for(self.id)
        return path if path.exists() else None

    @property
    def transcript(self) -> list[Message]:
        return [
            Message(role='customer' if isinstance(message, HumanMessage) else 'bot', content=message.text)
            for message in self._state().get('messages', [])
            if isinstance(message, HumanMessage | AIMessage) and message.text
        ]

    @property
    def ticket(self) -> Ticket | None:
        ticket = self._state().get('ticket')
        return Ticket.model_validate(ticket) if ticket else None

    def _save(self, transcript: list[Message], ticket: Ticket | None) -> None:
        """Summarize and save the conversation. Runs on ``_saver``, one save at a time."""
        try:
            try:
                summary = storage.summarize(transcript)
            except Exception:
                logger.exception('Could not summarize conversation %s', self.id)
                summary = None
            storage.save(self.id, transcript, ticket, summary)
        except Exception:
            logger.exception('Could not save conversation %s', self.id)

    def _state(self) -> dict:
        return self.agent.get_state(self.config).values

    def _add_bot_message(self, text: str) -> None:
        self.agent.update_state(self.config, {'messages': [AIMessage(text)]})
