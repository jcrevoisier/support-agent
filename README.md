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
Bot: I'm sorry, that's frustrating. Damaged items must be reported within 14 days of delivery with a photo; a
     replacement or full refund may be offered, and you don't need to return the item. I've logged that the coffee
     mug from order 1003 arrived completely smashed, and a colleague will contact you soon.
```

Saved to `conversations/<id>.json` (transcript left out):

```json
{
  "id": "ab779356-be4a-419e-9d0b-279abf3991ec",
  "saved_at": "2026-11-08T09:51:53.166741Z",
  "ticket": {
    "order_number": "1003",
    "category": "damaged_item",
    "description": "The coffee mug arrived completely smashed.",
    "urgency": "medium",
    "sentiment": "negative"
  },
  "summary": {
    "text": "The customer reported that the coffee mug from order 1003 arrived completely smashed. The bot logged the issue and said a colleague would follow up; the customer may be offered a replacement or full refund without returning the item.",
    "key_points": [
      "Order: 1003",
      "Problem: Coffee mug arrived completely smashed",
      "Urgency: Medium",
      "Sentiment: Negative",
      "Outcome: Issue logged; colleague to contact customer"
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
| `gpt-6-luna`, reasoning low | 65/65 | ~5.5 |
| `gpt-5.4-mini`, no reasoning | fails "Second problem" (1/10) | ~2.1 |
| `gpt-4.1-mini` | fails: asks the customer for the urgency | ~1.7 |

`gpt-5.4-mini` is about 2.5 times faster. Making three implicit prompt rules explicit (choose the category yourself,
only confirm an order that contradicts the customer, update the ticket when their mood changes) brought it to 50/50,
but it does not follow the one-problem-per-conversation rule, even when the rule is in the tool description. For a
text chat, a few seconds on the turn that saves the ticket is acceptable, so I kept the more reliable model. For
voice, I would move hard rules like this one into code, so that a faster model is safe to use.

Any model LangChain supports can be used by setting `LLM_MODEL` and `LLM_MODEL_OPTIONS` in `.env` (for another
provider, add its LangChain package), and the evals show whether it still behaves. Voice uses OpenAI's
`gpt-4o-mini-transcribe` and `gpt-4o-mini-tts`: fast, cheap, and multilingual without any setting.

**Urgency and sentiment are separate.** Urgency is about the problem: high for a deadline, a serious impact, or a
customer who has already contacted us about it. Sentiment is about the customer's tone. An angry customer with a
broken mug is `negative` and `medium`; a calm customer flying tomorrow is `neutral` and `high`. They lead to different
actions (how fast, and who handles it), so mixing them would hide information.

**RAG at a small scale.** No knowledge base came with the assignment, so I wrote `policies.md` (returns, refunds,
shipping, damaged items, exchanges). Each section is embedded once, on the first policy question, and the agent
searches it with a tool. At five sections the whole file would fit in the prompt; retrieval is there to show the
pattern, which stays the same with hundreds of help articles. The prompt tells the bot to answer only from what the
search returns, to explain the policy without promising an outcome for this customer, and to hand over to a colleague
when it does not know.

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
| Speech-to-text fails | The customer is asked to type the message instead |
| Text-to-speech fails | The reply is still printed |
| Summary fails | The conversation is saved without a summary |
| Missing API key or bad `.env` | A clear message at startup |

Errors are logged to `support-agent.log`.

## Tests and evals

```
uv run pytest                    # 37 tests, offline, under a second
uv run python -m evals --runs 5  # real model, about 2 minutes, a few cents
```

The tests use a fake model, so they check the code (tools, validation, error handling, storage, voice loop) without
calling any API.

The evals play fixed customer conversations against the real model and check the saved ticket exactly. Each scenario
runs five times in parallel, because the model does not answer the same way every time.

| Scenario | Passed |
|---|---|
| Normal | 5/5 |
| Unknown order, then fixed | 5/5 |
| Order mismatch, then corrected (and never saved for the wrong order) | 5/5 |
| Urgent, said later | 5/5 |
| French | 5/5 |
| Policy question (and the policy search was used) | 5/5 |
| Angry, first contact (negative, medium) | 5/5 |
| Third contact (negative, high) | 5/5 |
| Upset after the ticket (negative, still medium) | 5/5 |
| Second problem (the ticket keeps the first one) | 5/5 |
| General question (answered, no ticket) | 5/5 |
| No order number (no ticket, gives the support email) | 5/5 |
| Wants a person (gives the support email) | 5/5 |

The evals check data, not wording: they do not yet check that the bot replied in French or never promised a refund.
That needs an LLM judge (see next steps).

The evals already caught real problems: a wording change made a calm "my lamp arrived broken" come out as negative, and
waiting time sometimes raised urgency. Both were fixed in the prompt.

## Latency

A normal turn is one model call, about 1.5 s. A turn that saves the ticket makes three calls (look up, save, reply)
and takes about 4 to 6 s.
Voice adds about 1 s for speech-to-text and 1.5 s before the bot starts speaking. While one message plays, the agent
already works on the next one.

## In production

- **Storage:** conversations in Postgres through LangGraph's `PostgresSaver`, tickets sent to the helpdesk or a tickets table.
- **Service:** a FastAPI endpoint instead of the command line, so a web chat or phone line can use it, with a timeout
  that closes abandoned chats.
- **Routing:** the helpdesk's rules use urgency and sentiment to pick the queue and escalate.
- **Knowledge base:** a vector database (for example pgvector), re-indexed when the policies change.
- **Voice:** a voice framework for hands-free listening, interruptions and phone calls.
- **Monitoring:** traces of each conversation, and the evals run on every prompt change.

## Known limitations

- One problem per conversation: the bot asks the customer to start a new conversation for a second problem. This is
  a prompt rule, not enforced in code, and the summary still mentions the second problem.
- Without an order number there is no ticket: general questions are answered from the policies, and a customer who
  can't find their number is sent to the support email.
- The bot does not know today's date, so it can't judge how late a delivery is.
- Repeat contact is detected only when the customer says so; there is no contact history.
- Sentiment is the value from the last time the ticket was saved, not the worst one: if the ticket is saved again
  after an angry customer calms down, it ends up neutral.
- Anyone who knows an order number can see its product and status: there is no login.
- Prompt injection is not tested automatically.
- The log file can contain customer messages.
- Voice mode needs an OpenAI key even when the chat model is from another provider.

## Next steps

1. **Production basics:** database and API, contact history from past tickets, routing and escalation rules.
2. **Quality and safety:** an LLM judge in the evals (language, no promises, no invented policy, prompt injection), and
   more cases (several tickets per chat, today's date for late orders).
3. **Experience:** smoother voice (hands-free, interruptions, faster speech), memory across conversations for
   returning customers, a faster model compared with the evals.
