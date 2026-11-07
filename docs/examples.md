# Example conversations

Fields to collect:
- `order_number`: a number that exists in `orders.json` (`#1001` and `1001` both work)
- `category`: `late_delivery`, `damaged_item`, `wrong_item`, `refund`, `other`
- `description`: free text
- `urgency`: `low`, `medium`, `high`, set by the bot from what the customer says (`medium` if nothing indicates it)

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
  "urgency": "medium"
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
  "urgency": "low"
}
```

## 3. Correction

> **Bot:** Hi! How can I help you today?
> **Customer:** My order hasn't arrived and it's been three weeks. It's a gift for a birthday on Saturday.
> **Bot:** I'm sorry for the wait. What's your order number?
> **Customer:** 1003
> **Bot:** Thanks. I've logged a late-delivery report for order 1003. A colleague will contact you soon.
> **Customer:** Wait, sorry, it's 1004.
> **Bot:** No problem, I've updated the report to order 1004.

```json
{
  "order_number": "1004",
  "category": "late_delivery",
  "description": "Order has not arrived after three weeks. It is a gift for a birthday on Saturday.",
  "urgency": "high"
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
  "urgency": "medium"
}
```

If it fails again on the next message:

> **Bot:** Sorry, I'm having trouble right now. Please email us at support@example-shop.com and we'll help you.
