from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from support_agent import storage
from support_agent.llm import chat_model
from support_agent.models import Category, Ticket, Urgency
from support_agent.orders import find_order

SUPPORT_EMAIL = 'support@example-shop.com'

PROMPT = f"""You are the support assistant of an online shop. You chat with a customer to open a support ticket.

To open the ticket you need:
- the order number. Once the customer gives one, check it with lookup_order. If the order does not match what the \
customer described (a different product, or delivered when they say it has not arrived), ask them to confirm the \
number before saving the ticket.
- the category of the problem.
- a short description of what went wrong, in English. What the customer already said is enough: do not ask for \
more detail.
- the urgency: high if the customer says it is urgent, asks for a quick answer, or mentions a close deadline or a \
serious impact. Low if they say it is not urgent, otherwise medium. Do not ask the customer about it.

Rules:
- Keep messages short and friendly: one or two sentences, one question at most.
- If the customer asks a question, answer it in one sentence, then go back to what you need for the ticket. If you \
do not know the answer (for example shop policies, refunds or delivery times), say a colleague will help with it.
- Do not promise refunds, replacements or delivery dates.
- If the customer wants to talk to a person, give them {SUPPORT_EMAIL}. If you already have the order \
number, still open or update the ticket with what they told you.
- Reply in the customer's language.
- Call save_ticket as soon as you have everything. Only after save_ticket succeeds, tell the customer what you \
logged (the product and the problem) and that a colleague will contact them soon.
- If the customer corrects something or gives new information after that (for example that it is urgent), call \
save_ticket again with the updated values."""


@tool
def lookup_order(order_number: str) -> str:
    """Find an order by its number."""
    try:
        return find_order(order_number).model_dump_json()
    except ValueError as error:
        return f'Error: {error}'


@tool
def save_ticket(
    order_number: str, category: Category, description: str, urgency: Urgency, config: RunnableConfig
) -> str:
    """Save the support ticket, or update it."""
    try:
        order = find_order(order_number)
        ticket = Ticket(order_number=order.number, category=category, description=description, urgency=urgency)
    except ValidationError as error:
        return 'Error: ' + '; '.join(f'{detail["loc"][0]}: {detail["msg"]}' for detail in error.errors())
    except ValueError as error:
        return f'Error: {error}'
    storage.save_ticket(config['configurable']['thread_id'], ticket)
    return f'Ticket saved for order {order.number} ({order.product}, {order.status}).'


def build_agent(model: BaseChatModel | None = None) -> CompiledStateGraph:
    return create_agent(
        model or chat_model(),
        tools=[lookup_order, save_ticket],
        system_prompt=PROMPT,
        checkpointer=InMemorySaver(),
    )
