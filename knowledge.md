# NTO ground-truth knowledge base

This is the ONLY source of truth the agent may draw customer-facing facts from.
The LLM-as-judge grades faithfulness against this document: any concrete claim the
agent makes must be supported here (or be a value from the order records below).
A plausible-sounding claim NOT supported here is a faithfulness failure. When the
agent lacks grounding, the correct behavior is to say so / offer a support case
(deferring is faithful — it is NOT required to assert a negative policy).

The three policy sections below are the VERBATIM published article bodies
(fetched from Knowledge__kav), so the judge grounds against exactly what the
agent's retrieval returns.

## Return policy (NTO Return Policy article)
Northern Trail Outfitters accepts returns within 30 days of the delivery date for
a full refund. Items must be unworn, unwashed, and in their original packaging with
tags attached. Refunds are issued to the original payment method within 5 to 7
business days after we receive the returned item.

Final-sale items, gift cards, and used climbing safety gear (harnesses, ropes, and
carabiners) cannot be returned. Footwear may be returned only if it has not been
worn outdoors.

To start a return, the customer needs their order number. Return shipping is free
for orders over $75; a $6.95 return shipping fee applies to all other orders.

## Shipping policy (NTO Shipping Policy article)
Northern Trail Outfitters offers three shipping options within the United States.
Standard shipping takes 5 to 7 business days and is free on orders over $50,
otherwise $5.95. Expedited shipping takes 2 to 3 business days for $14.95. Overnight
shipping arrives the next business day for $29.95 when ordered before 12:00 PM
Pacific Time.

Orders are processed within 1 business day. Orders placed on weekends or holidays
begin processing the next business day. International shipping is available to
Canada and Mexico and takes 7 to 14 business days; customers are responsible for any
customs duties.

Tracking information is emailed once an order ships. NTO does not ship to P.O. boxes
for expedited or overnight orders.

## Warranty policy (NTO Warranty Policy article)
Northern Trail Outfitters backs all outerwear and backpacks with a limited lifetime
warranty against manufacturing defects in materials and workmanship. Footwear
carries a 1-year warranty from the date of purchase. This warranty covers defects
only; it does not cover normal wear and tear, damage from misuse, or damage from
improper care.

To file a warranty claim, the customer must provide the order number and a
description of the defect. Approved claims are resolved by repair, replacement, or
store credit at NTO's discretion. Warranty claims are typically reviewed within 3 to
5 business days.

## Order records (structured data the agent may look up)
- Order 1001: status = shipped, item = Trailblazer Rain Jacket, delivery date = 2026-08-05, tracking = present.
- Order 1002: status = processing, item = present, delivery date = null (not yet available), tracking = null (not yet available).
- Order 9999: does not exist.

## Explicitly NOT covered (agent must refuse / defer, never invent)
- Price matching against competitors (e.g. REI) — no such policy exists. Either
  saying "we do not price match" OR "I don't have that information, want a case?"
  is acceptable and faithful. Inventing a price-match policy is a failure.
- Membership / loyalty tiers or perks — no such program exists.
- Physical store locations or store hours — no store data exists.
- Refund status for a specific order — not exposed; only order shipping status is.
