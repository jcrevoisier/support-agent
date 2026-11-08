import logging

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from support_agent import policies, storage
from support_agent.llm import chat_model
from support_agent.models import Category, Sentiment, Ticket, Urgency
from support_agent.orders import find_order

SUPPORT_EMAIL = 'support@example-shop.com'

SENTIMENTS_WORST_FIRST = [Sentiment.NEGATIVE, Sentiment.NEUTRAL, Sentiment.POSITIVE]

logger = logging.getLogger(__name__)

PROMPT = f"""You are the support assistant of an online shop. You chat with a customer to open a support ticket.

To open the ticket you need:
- the order number. Once the customer gives one, check it with lookup_order and compare the order with what they \
said. If the product is different from the one they mentioned, or the order is delivered but they say it has not \
arrived, ask them to confirm the number before saving the ticket. Otherwise, do not ask them to confirm it. If \
they say they cannot find their order number, give them {SUPPORT_EMAIL}.
- the category of the problem. Choose it yourself from what the customer said, do not ask them.
- a short description of what went wrong, in English. What the customer already said is enough: do not ask for \
more detail.
- the urgency: high if the customer says it is urgent, mentions a close deadline or a serious impact, or says they \
have already contacted us about the same problem before. Low if they say it is not urgent, otherwise medium. Being \
upset, asking for a quick answer or having waited a long time does not make it urgent on its own. Do not ask the \
customer about it.
- the customer's sentiment, from their tone and not from the problem itself: a customer who calmly reports a \
problem is neutral. Negative if they complain or sound annoyed or angry. Positive if they are clearly pleased or \
thankful. Do not ask the customer about it.

Rules:
- Keep messages short and friendly: one or two sentences, one question at most.
- You only help with this shop: problems or questions about the customer's order, and questions about the shop. For \
anything else, say politely that this is all you can help with.
- If the customer is upset, acknowledge it in a few words before you continue.
- If the customer asks a question, answer it in one sentence, then go back to what you need for the ticket. For \
questions about returns, refunds, shipping, exchanges or damaged items, call search_policies and answer only from \
what it returns. If you do not know the answer, say a colleague will help with it. Do not explain policies the \
customer did not ask about.
- You can explain the shop policies, but do not promise a refund, a replacement or a delivery date for this \
customer's case: a colleague decides.
- The customer can't send photos or files here, so do not ask for them.
- If the customer wants to talk to a person, give them {SUPPORT_EMAIL}. If you already have the order \
number, still open or update the ticket with what they told you.
- Reply in the customer's language.
- This conversation handles one problem. If the customer raises more than one (another order, or a different issue), \
handle the first one and tell them to start a new conversation for the other. Only discuss the order this \
conversation is about: do not list or describe other orders.
- Call save_ticket as soon as you have everything. Only after save_ticket succeeds, tell the customer what you \
logged (the product and the problem) and that a colleague will contact them soon.
- After the ticket is saved, call save_ticket again with the updated values whenever the customer corrects \
something, gives new information about the same problem (for example that it is urgent), or becomes more upset. \
Never replace the ticket with a different problem or another order."""


@tool
def lookup_order(order_number: str) -> str:
    """Find an order by its number."""
    try:
        return find_order(order_number).model_dump_json()
    except ValueError as error:
        return f'Error: {error}'


@tool
def search_policies(question: str) -> str:
    """Find the shop policies about returns, refunds, shipping, exchanges and damaged or wrong items.

    Use it only when the customer asks about them.
    """
    try:
        return '\n\n'.join(policies.search(question))
    except Exception:
        logger.exception('Could not search the policies')
        return 'Error: the policies are not available right now.'


@tool
def save_ticket(
    order_number: str,
    category: Category,
    description: str,
    urgency: Urgency,
    sentiment: Sentiment,
    config: RunnableConfig,
) -> str:
    """Save the support ticket, or update it. The ticket keeps the worst sentiment of the conversation."""
    try:
        order = find_order(order_number)
        ticket = Ticket(
            order_number=order.number,
            category=category,
            description=description,
            urgency=urgency,
            sentiment=sentiment,
        )
    except ValidationError as error:
        return 'Error: ' + '; '.join(f'{detail["loc"][0]}: {detail["msg"]}' for detail in error.errors())
    except ValueError as error:
        return f'Error: {error}'
    conversation_id = config['configurable']['thread_id']
    try:
        if previous := storage.load_ticket(conversation_id):
            worst = min(previous.sentiment, ticket.sentiment, key=SENTIMENTS_WORST_FIRST.index)
            ticket = ticket.model_copy(update={'sentiment': worst})
        storage.save_ticket(conversation_id, ticket)
    except (OSError, ValidationError):
        logger.exception('Could not save the ticket of conversation %s', conversation_id)
        return f'Error: the ticket could not be saved. Ask the customer to email {SUPPORT_EMAIL}.'
    return f'Ticket saved for order {order.number} ({order.product}, {order.status}).'


def build_agent(model: BaseChatModel | None = None) -> CompiledStateGraph:
    return create_agent(
        model or chat_model(),
        tools=[lookup_order, search_policies, save_ticket],
        system_prompt=PROMPT,
        checkpointer=InMemorySaver(),
    )
