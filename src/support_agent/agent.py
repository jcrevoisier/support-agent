import json
from typing import Annotated, NotRequired

from langchain.agents import AgentState, create_agent
from langchain.tools import InjectedToolCallId, tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import ValidationError

from support_agent.llm import chat_model
from support_agent.models import Category, Ticket, Urgency, find_order

PROMPT = """You are the support assistant of an online shop. You chat with a customer to open a support ticket.

To open the ticket you need:
- the order number. Once the customer gives one, check it with lookup_order. If the order does not match what the \
customer described (a different product, or delivered when they say it has not arrived), ask them to confirm the \
number before saving the ticket.
- the category of the problem.
- a short description of what went wrong, in English. What the customer already said is enough: do not ask for \
more detail.
- the urgency: high if the customer says it is urgent or mentions a close deadline or a serious impact, low if they \
say it is not urgent, otherwise medium. Do not ask the customer about it.

Rules:
- Keep messages short and friendly: one or two sentences, one question at most.
- If the customer asks something, answer briefly first, then continue.
- Do not promise refunds, replacements or delivery dates.
- If the customer wants to talk to a person, give them support@example-shop.com.
- Reply in the customer's language.
- Call save_ticket as soon as you have everything. Only after save_ticket succeeds, tell the customer what you \
logged (the product and the problem) and that a colleague will contact them soon.
- If the customer corrects something or gives new information after that (for example that it is urgent), call \
save_ticket again with the updated values."""


class SupportState(AgentState):
    ticket: NotRequired[dict]


@tool
def lookup_order(order_number: str) -> str:
    """Find an order by its number."""
    try:
        return json.dumps(find_order(order_number))
    except ValueError as error:
        return f'Error: {error}'


@tool
def save_ticket(
    order_number: str,
    category: Category,
    description: str,
    urgency: Urgency,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command | str:
    """Save the support ticket, or update it."""
    try:
        ticket = Ticket(order_number=order_number, category=category, description=description, urgency=urgency)
    except ValidationError as error:
        return 'Error: ' + '; '.join(detail['msg'] for detail in error.errors())
    return Command(
        update={
            'ticket': ticket.model_dump(mode='json'),
            'messages': [ToolMessage('Ticket saved.', tool_call_id=tool_call_id)],
        }
    )


def build_agent(model: BaseChatModel | None = None):
    return create_agent(
        model or chat_model(),
        tools=[lookup_order, save_ticket],
        system_prompt=PROMPT,
        state_schema=SupportState,
        checkpointer=InMemorySaver(),
    )
