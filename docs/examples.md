# Example conversations

Fields to collect:
- `order_number`: a number that exists in `orders.json` (`#1001` and `1001` both work)
- `category`: `late_delivery`, `damaged_item`, `wrong_item`, `refund`, `other`
- `description`: free text
- `urgency`: `low`, `medium`, `high`, set by the bot from what the customer says (`medium` if nothing indicates it)
- `sentiment`: `positive`, `neutral`, `negative`, set by the bot from the customer's tone (a calm report of a problem is `neutral`)

## 1. Normal

> **Bot:** Hi! How can I help you today?
> **Customer:** My package arrived and the lamp inside is broken.
> **Bot:** I'm sorry about that. What's your order number?
> **Customer:** 1001
> **Bot:** Thanks. I've logged a damaged-item report for order 1001. A colleague will contact you soon.

```json
{
  "order_number": "1001",
  "category": "damaged_item",
  "description": "The lamp in the package arrived broken.",
  "urgency": "medium",
  "sentiment": "neutral"
}
```

## 2. Invalid information

> **Bot:** Hi! How can I help you today?
> **Customer:** I ordered a blue sweater but got a red one. Order 12345. No rush.
> **Bot:** Sorry for the mix-up. I can't find order 12345. Can you check the number?
> **Customer:** Oh right, it's 1002.
> **Bot:** Thanks. I've logged a wrong-item report for order 1002. A colleague will contact you soon.

```json
{
  "order_number": "1002",
  "category": "wrong_item",
  "description": "Ordered a blue sweater, received a red one.",
  "urgency": "low",
  "sentiment": "neutral"
}
```

## 3. Correction

> **Bot:** Hi! How can I help you today?
> **Customer:** My order hasn't arrived and it's been three weeks. It's a gift for a birthday on Saturday.
> **Bot:** I'm sorry for the wait. What's your order number?
> **Customer:** 1003
> **Bot:** Order 1003 is for a coffee mug and shows as delivered. Could you confirm the order number?
> **Customer:** Sorry, it's 1004.
> **Bot:** Thanks. I've logged a late-delivery report for your wireless headphones. A colleague will contact you soon.

```json
{
  "order_number": "1004",
  "category": "late_delivery",
  "description": "Order has not arrived after three weeks. It is a gift for a birthday on Saturday.",
  "urgency": "high",
  "sentiment": "neutral"
}
```

## 4. API failure

> **Bot:** Hi! How can I help you today?
> **Customer:** I want a refund.
> **Bot:** Sure. What's your order number?
> **Customer:** 1005, the shoes don't fit.
> *(LLM fails 3 times)*
> **Bot:** Sorry, something went wrong. Could you send that again?
> **Customer:** 1005, the shoes don't fit.
> **Bot:** Thanks. I've logged a refund request for order 1005. A colleague will contact you soon.

```json
{
  "order_number": "1005",
  "category": "refund",
  "description": "The shoes don't fit.",
  "urgency": "medium",
  "sentiment": "neutral"
}
```

If it fails again on the next message:

> **Bot:** Sorry, I'm having trouble right now. Please email us at support@example-shop.com and we'll help you.

## 5. Policy question

The bot answers from `policies.md` (found with `search_policies`), then goes back to the ticket.

> **Bot:** Hi! How can I help you today?
> **Customer:** My running shoes are too small. Can I return them if I wore them once?
> **Bot:** Worn shoes can't be returned unless they're faulty. What's your order number so I can open a support ticket about the sizing issue?
> **Customer:** Order 1005.
> **Bot:** I've logged your running shoes as too small and worn once. A colleague will contact you soon.

```json
{
  "order_number": "1005",
  "category": "refund",
  "description": "Running shoes are too small; customer wore them once and asks whether they can return them.",
  "urgency": "medium",
  "sentiment": "neutral"
}
```

## 6. Upset, but not urgent

> **Bot:** Hi! How can I help you today?
> **Customer:** This is ridiculous, the mug from order 1003 arrived completely smashed!!
> **Bot:** I'm sorry it arrived smashed. Damaged items should be reported within 14 days of delivery with a photo; the shop's policy allows a replacement or full refund, and you don't need to return the item. I've logged the smashed coffee mug, and a colleague will contact you soon.

```json
{
  "order_number": "1003",
  "category": "damaged_item",
  "description": "The coffee mug arrived completely smashed.",
  "urgency": "medium",
  "sentiment": "negative"
}
```

The customer is upset, so sentiment is `negative`, but there is no deadline, serious impact or repeat contact, so urgency stays `medium`.

## 7. Repeat contact

> **Bot:** Hi! How can I help you today?
> **Customer:** THIS IS THE THIRD TIME I write about order 1004. My headphones are still not here, this is ridiculous!
> **Bot:** I'm sorry you've had to contact us so many times. I've logged a ticket about your wireless headphones not arriving, and a colleague will contact you soon.

```json
{
  "order_number": "1004",
  "category": "late_delivery",
  "description": "The wireless headphones have not arrived; customer says this is the third time they have contacted us about the issue.",
  "urgency": "high",
  "sentiment": "negative"
}
```

Urgency is `high` because the customer has already contacted us about it. Sentiment is `negative` because of their tone. A calm "this is my second message about it" gives `high` and `neutral`.
