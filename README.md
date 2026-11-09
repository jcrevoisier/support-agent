# Support agent

A customer support agent for a fictional online shop. It chats with the customer by text or by voice, collects what
the support team needs, checks it, and saves a ticket and a summary of the conversation as JSON.

For each conversation it collects:

| Field | Values |
|---|---|
| Order number | must exist in the shop's orders (`#1001` and `1001` both work) |
| Category | `late_delivery`, `damaged_item`, `wrong_item`, `refund`, `other` |
| Description | short, in English, whatever the customer's language |
| Urgency | `low`, `medium`, `high` |
| Sentiment | `positive`, `neutral`, `negative` |

It also answers questions about returns, refunds, shipping and exchanges from a small policy file (RAG), and replies in
the customer's language.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) and an OpenAI API key. On Linux, also install PortAudio:
`sudo apt-get install libportaudio2` (macOS and Windows include it).

```
uv sync
cp .env.example .env          # then set OPENAI_API_KEY
uv run support-agent          # chat by text
uv run support-agent --voice  # talk: press Enter to speak, Enter again when done
```

Press Ctrl+D (or Ctrl+C) to end the chat. The conversation is saved to `conversations/<id>.json`.

Voice mode needs a microphone; macOS asks for permission the first time.

Test orders:

| Order | Product | Status |
|---|---|---|
| 1001 | Desk lamp | delivered |
| 1002 | Blue sweater | delivered |
| 1003 | Coffee mug | delivered |
| 1004 | Wireless headphones | shipped |
| 1005 | Running shoes | delivered |
| 1006 | Backpack | processing |

[docs/examples.md](docs/examples.md) has example conversations with the tickets they produce.

## Example

```
Bot: Hi! How can I help you today?
You: This is ridiculous, the mug from order 1003 arrived completely smashed!!
Bot: I'm sorry, that's really frustrating. I've logged that the coffee mug from order 1003 arrived completely smashed,
     and a colleague will contact you soon.
```

Saved to `conversations/<id>.json`:

```json
{
  "id": "79c634a6-c4bb-4ef9-8ac8-991af0f98ff2",
  "saved_at": "2026-11-08T11:59:09.981616Z",
  "ticket": {
    "order_number": "1003",
    "category": "damaged_item",
    "description": "The coffee mug arrived completely smashed.",
    "urgency": "medium",
    "sentiment": "negative"
  },
  "summary": {
    "text": "The customer reported that the coffee mug from order 1003 arrived completely smashed and expressed negative sentiment. The issue was logged as a damaged item with medium urgency, and a colleague will contact the customer soon.",
    "key_points": [
      "Order: 1003",
      "Problem: Coffee mug arrived completely smashed",
      "Urgency: Medium",
      "Customer sentiment: Negative",
      "Outcome: Issue logged; a colleague will follow up soon"
    ]
  },
  "transcript": ["…"]
}
```

The customer is upset, so the sentiment is `negative`, but nothing makes it time-sensitive, so the urgency is `medium`.

## How it works

```
customer ──text or voice──▶ Conversation ──▶ LangChain agent (LLM + tools) ──▶ reply
                                                  │
                         lookup_order ◀───────────┤  checks the order number
                         search_policies ◀────────┤  finds the relevant policy sections
                         save_ticket ◀────────────┘  validates and saves the ticket
```

1. The customer writes (or speaks; voice is transcribed to text first).
2. The agent decides what to do: ask a question, look up the order, search the policies, or save the ticket. Tools
   return `Error: …` on bad input (unknown order, empty description), so the model sees the problem and asks again.
3. Each bot message is shown (and spoken in voice mode) as soon as the agent writes it.
4. When the chat ends, the transcript and an AI summary are added to the conversation file. The ticket is already
   there: `save_ticket` writes it as soon as it is complete, so it is not lost if the program stops.

| File | Role |
|---|---|
| `src/support_agent/cli.py` | Command line: text or voice mode, saves the conversation at the end |
| `src/support_agent/conversation.py` | One conversation: greeting, sending messages, error replies, closing |
| `src/support_agent/agent.py` | The prompt and the three tools |
| `src/support_agent/models.py` | `Ticket` and its validation (pydantic) |
| `src/support_agent/orders.py`, `orders.json` | The fictional order database |
| `src/support_agent/policies.py`, `policies.md` | Policy search with embeddings (RAG) |
| `src/support_agent/summary.py` | Summary with key points (structured output) |
| `src/support_agent/storage.py` | JSON files, one per conversation |
| `src/support_agent/voice.py` | Microphone, speech-to-text, text-to-speech |
| `src/support_agent/llm.py` | Model setup from `.env` |

## Design choices

**The model.** `gpt-6-luna` with low reasoning effort. The task needs reliable tool calls and instruction following
more than deep reasoning, so I compared models with the evals:

| Model | Evals passed | Seconds per turn |
|---|---|---|
| `gpt-6-luna`, reasoning low | 130/130 | ~5.5 |
| `gpt-5.4-mini`, no reasoning | fails "Second problem" (1/10) | ~2.1 |
| `gpt-4.1-mini` | fails: asks the customer for the urgency | ~1.7 |

Voice uses OpenAI's `gpt-4o-mini-transcribe` and `gpt-4o-mini-tts`: fast, cheap, and multilingual without any setting.

**Urgency and sentiment are separate.** Urgency is about the problem: high for a deadline, a serious impact, or a
customer who has already contacted us about it. Sentiment is about the customer's tone. An angry customer with a
broken mug is `negative` and `medium`; a calm customer flying tomorrow is `neutral` and `high`.

**Memory.** The LLM API is stateless, so a LangGraph checkpointer keeps each conversation's messages and tool calls
and sends them with every turn.

**Storage.** One JSON file per conversation, written to a temporary file and then renamed, so an interrupted write
never leaves a broken file.

## Error handling

| Problem | What happens |
|---|---|
| Unknown or invalid order number | The bot says it can't find it and asks again |
| Order does not match what the customer described | The bot asks the customer to confirm the number |
| Empty description or invalid value | The tool returns the validation error and the model fixes it |
| LLM error or timeout (20 s, 2 retries) | "Could you send that again?", then the support email if it fails again |
| Policy search fails | The bot says a colleague will help; the conversation continues |
| Saving the ticket fails | The bot gives the support email; the conversation continues |
| Speech-to-text fails | The customer is asked to type the message instead |
| Text-to-speech fails | The reply is still printed |
| Summary fails | The conversation is saved without a summary |
| Saving the conversation fails | "Could not save the conversation", with the details in the log |
| Empty API key or invalid `LLM_MODEL_OPTIONS` | A clear message at startup |
| Wrong API key | Handled like an LLM error, since it only fails on the first call |

Errors are logged to `support-agent.log`.

## Tests and evals

```
uv run pytest                    # 41 tests, offline, under a second
uv run python -m evals --runs 10 # real model, about 5 minutes, a few cents
```

The tests use a fake model, so they check the code (tools, validation, error handling, storage, voice loop) without
calling any API.

The evals play fixed customer conversations against the real model and check the saved ticket exactly. Each scenario
runs ten times in parallel, because the model does not answer the same way every time.

| Scenario | Passed |
|---|---|
| Normal | 10/10 |
| Unknown order, then fixed | 10/10 |
| Order mismatch, then corrected (and never saved for the wrong order) | 10/10 |
| Urgent, said later | 10/10 |
| French | 10/10 |
| Policy question (and the policy search was used) | 10/10 |
| Angry, first contact (negative, medium) | 10/10 |
| Third contact (negative, high) | 10/10 |
| Upset after the ticket (negative, still medium) | 10/10 |
| Second problem (the ticket keeps the first one) | 10/10 |
| General question (answered, no ticket) | 10/10 |
| No order number (no ticket, gives the support email) | 10/10 |
| Wants a person (gives the support email) | 10/10 |

The evals check data, not wording: they do not yet check that the bot replied in French or never promised a refund.
That would need an LLM judge.

## Latency

A normal turn is one model call, about 1.5 s. A turn that saves the ticket makes three calls (look up, save, reply)
and takes about 4 to 6 s.
Voice adds about 1 s for speech-to-text and 1.5 s before the bot starts speaking. While one message plays, the agent
already works on the next one.

## Known limitations

- One problem per conversation: the bot asks the customer to start a new conversation for a second problem. This is
  a prompt rule, not enforced in code, and the summary still mentions the second problem.
- Without an order number there is no ticket: general questions are answered from the policies, and a customer who
  can't find their number is sent to the support email.
- The bot does not know today's date, so it can't judge how late a delivery is.
- Repeat contact is detected only when the customer says so, there is no contact history.
- The transcript and the summary are saved when the chat ends. If the program is killed, only the ticket survives,
  and a conversation without a ticket is lost.
- Anyone who knows an order number can see its product and status: there is no login.
- Prompt injection is not tested automatically.
- The log file can contain customer messages.
