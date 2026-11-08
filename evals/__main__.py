"""Run fixed customer scenarios against the real model, several times each, and report a pass rate per scenario.

Usage: ``uv run python -m evals --runs 5``. It calls the real LLM, so it costs a few cents and is not part of pytest.
"""

import argparse
import os
import re
import statistics
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage

from support_agent import storage
from support_agent.agent import SUPPORT_EMAIL
from support_agent.conversation import GIVE_UP_REPLY, RETRY_REPLY, Conversation
from support_agent.llm import DEFAULT_MODEL


@dataclass
class Run:
    replies: list[str]
    ticket: dict | None
    tools_called: list[str]
    saved_orders: list[str]
    seconds_per_turn: float


Check = Callable[[Run], str | None]


@dataclass
class Scenario:
    name: str
    messages: list[str]
    ticket: dict[str, str | set[str]]
    checks: list[Check] = field(default_factory=list)


def never_saved(order_number: str) -> Check:
    return lambda run: f'saved a ticket for {order_number}' if order_number in run.saved_orders else None


def called(tool_name: str) -> Check:
    return lambda run: None if tool_name in run.tools_called else f'never called {tool_name}'


def gives_support_email(run: Run) -> str | None:
    return None if any(SUPPORT_EMAIL in reply for reply in run.replies) else 'no support email'


SCENARIOS = [
    Scenario(
        'Normal',
        ['My desk lamp arrived broken, the order number is 1001.'],
        {'order_number': '1001', 'category': 'damaged_item', 'urgency': 'medium', 'sentiment': 'neutral'},
    ),
    Scenario(
        'Unknown order, then fixed',
        ['I ordered a blue sweater but got a red one. Order 12345. No rush.', 'Sorry, it is order 1002.'],
        {'order_number': '1002', 'category': 'wrong_item', 'urgency': 'low'},
    ),
    Scenario(
        'Order mismatch, then corrected',
        [
            'My wireless headphones have not arrived yet. Order 1003.',
            'Oh sorry, it is 1004. I need them for a trip on Monday.',
        ],
        {'order_number': '1004', 'category': 'late_delivery', 'urgency': 'high'},
        [never_saved('1003')],
    ),
    Scenario(
        'Urgent, said later',
        ['My running shoes arrived damaged, order 1005.', 'Please be quick, I need them for a race this weekend.'],
        {'order_number': '1005', 'category': 'damaged_item', 'urgency': 'high'},
    ),
    Scenario(
        'French',
        ['Bonjour, ma tasse à café est arrivée cassée. Commande 1003.'],
        {'order_number': '1003', 'category': 'damaged_item'},
    ),
    Scenario(
        'Policy question',
        ['My running shoes are too small. Can I return them if I wore them once?', 'Order 1005.'],
        {'order_number': '1005', 'category': {'refund', 'other'}},
        [called('search_policies')],
    ),
    Scenario(
        'Angry, first contact',
        ["My headphones from order 1004 still haven't arrived. This is ridiculous, worst shop ever!"],
        {'order_number': '1004', 'category': 'late_delivery', 'urgency': 'medium', 'sentiment': 'negative'},
    ),
    Scenario(
        'Third contact',
        ['THIS IS THE THIRD TIME I write about order 1004. My headphones are still not here, this is ridiculous!'],
        {'order_number': '1004', 'category': 'late_delivery', 'urgency': 'high', 'sentiment': 'negative'},
    ),
    Scenario(
        'Upset after the ticket',
        [
            'My running shoes arrived damaged, order 1005.',
            "Seriously? That's all? I've been waiting two weeks for these and you can't even tell me what happens next?",
        ],
        {'order_number': '1005', 'category': 'damaged_item', 'urgency': 'medium', 'sentiment': 'negative'},
    ),
    Scenario(
        'Wants a person',
        ['My backpack from order 1006 is taking forever. I want to talk to a human.'],
        {'order_number': '1006', 'category': 'late_delivery'},
        [gives_support_email],
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=5, help='runs per scenario')
    args = parser.parse_args()
    load_dotenv()

    problems = []
    print(f'Model: {os.getenv("LLM_MODEL", DEFAULT_MODEL)}, {args.runs} runs per scenario, run in parallel\n')
    print('| Scenario | Passed | Seconds per turn |\n|---|---|---|')
    with tempfile.TemporaryDirectory() as folder:
        storage.CONVERSATIONS_DIR = Path(folder)
        for scenario in SCENARIOS:
            with ThreadPoolExecutor(args.runs) as pool:
                runs = list(pool.map(_run, [scenario] * args.runs))
            failures = [_failures(scenario, run) for run in runs]
            passed = sum(not failure for failure in failures)
            seconds = statistics.mean(run.seconds_per_turn for run in runs)
            print(f'| {scenario.name} | {passed}/{args.runs} | {seconds:.1f} |')
            problems += [f'{scenario.name}: {"; ".join(failure)}' for failure in failures if failure]
    if problems:
        print('\nFailures:\n' + '\n'.join(f'- {problem}' for problem in problems))


def _run(scenario: Scenario) -> Run:
    chat = Conversation()
    chat.start()
    replies = []
    start = time.time()
    for text in scenario.messages:
        replies += chat.send(text)
    seconds_per_turn = (time.time() - start) / len(scenario.messages)
    messages = chat.agent.get_state(chat.config).values['messages']
    calls = [call for message in messages if isinstance(message, AIMessage) for call in message.tool_calls]
    saved_orders = [
        re.sub(r'[^0-9]', '', call['args']['order_number']) for call in calls if call['name'] == 'save_ticket'
    ]
    ticket = chat.ticket.model_dump(mode='json') if chat.ticket else None
    return Run(replies, ticket, [call['name'] for call in calls], saved_orders, seconds_per_turn)


def _failures(scenario: Scenario, run: Run) -> list[str]:
    """Return why the run failed, or an empty list if it passed."""
    if any(reply in (RETRY_REPLY, GIVE_UP_REPLY) for reply in run.replies):
        return ['agent error']
    if run.ticket is None:
        return ['no ticket saved']
    failures = [
        f'{key} is {run.ticket[key]}, expected {expected}'
        for key, expected in scenario.ticket.items()
        if run.ticket[key] not in (expected if isinstance(expected, set) else {expected})
    ]
    failures += [failure for check in scenario.checks if (failure := check(run))]
    return failures


if __name__ == '__main__':
    main()
