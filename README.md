# Apex tool action

`GetOrderStatus.cls` is the invocable Apex class the agent calls in Step 3 to look
up live order data. It's the "tool" in the tool-calling loop.

## Design note (why it's faithful)
The method returns **structured facts, and null when a value is absent** — it never
default-fills a missing delivery date or tracking number. That's the discipline
that lets the agent stay honest: the LLM writes the prose, but it can only speak to
the fields Apex actually returned. If `Delivery_Date__c` is null in the record, the
agent has nothing to state, so it says the date isn't available yet rather than
inventing one.

`with sharing` makes the query run under the calling user's permissions
(the EinsteinServiceAgent User), so record access is governed by that user's
object + field-level security — see the permission steps in `../BUILD_GUIDE.md`.

## Custom object it depends on: `NTO_Order__c`
Create this custom object with the following custom fields (API names must match
the SOQL in the class):

| Field API name        | Type        | Notes                                  |
|-----------------------|-------------|----------------------------------------|
| `Name`                | Text (std)  | Used as the order number (e.g. "1001") |
| `Status__c`           | Text/Picklist | e.g. Shipped, Processing             |
| `Item__c`             | Text        | Product name                           |
| `Delivery_Date__c`    | Date        | **Leave null on one record** for the faithfulness test |
| `Tracking_Number__c`  | Text        | Also leave null on that same record    |

Seed a few records, including:
- a happy-path order (all fields populated),
- one with `Delivery_Date__c` and `Tracking_Number__c` **null** (the anti-
  hallucination test — the agent must not invent them),
- and simply omit an order number (e.g. "9999") to test the not-found path.

## Deploy
Paste the class into Setup → Apex Classes → New, or deploy with the Salesforce CLI
(`sf project deploy start`). Then grant the EinsteinServiceAgent User **Apex Class
Access** to `GetOrderStatus` plus **object + field-level Read** on `NTO_Order__c`
(both layers are required — see the guide).
