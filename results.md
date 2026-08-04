# NTO Agent — Faithfulness & Accuracy Eval

**Pass rate:** 18/18  (100%)  
**Avg latency:** 3.8s  
**LLM-as-judge:** on

## By category

- faithfulness-negative: 4/4
- multi-intent: 1/1
- order-status: 3/3
- policy-rag: 10/10

## Scenarios

### [PASS] order-1001-happy  (6.12s)
**Prompt:** Where is my order 1001?  
**Response:** Your order 1001 for the Trailblazer Rain Jacket has shipped. The expected delivery date is August 5, 2026. Would you like the tracking number or need help with anything else?  
**Judge:** FAITHFUL — All concrete claims (order 1001 status = shipped, item = Trailblazer Rain Jacket, delivery date = 2026-08-05) are directly supported by the order records, and the agent appropriately offers the tracking number that is documented as present.  

### [PASS] order-1002-null-delivery  (4.26s)
**Prompt:** When will order 1002 be delivered and what's the tracking number?  
**Response:** Order 1002 is still processing. There is no delivery date or tracking number available yet. Would you like to receive an update when the order ships, or do you have another question about your order?  
**Judge:** FAITHFUL — The agent correctly states that Order 1002 is processing with no delivery date or tracking number available yet, which directly matches the order records (status = processing, delivery date = null, tracking = null).  

### [PASS] order-9999-notfound  (4.33s)
**Prompt:** Can you check the status of order 9999?  
**Response:** I could not find an order with the number 9999. Would you like me to create a support case to help resolve this? If you have another order number, please provide it and I can check again.  
**Judge:** FAITHFUL — The agent correctly stated that order 9999 does not exist (supported by the order records section), and appropriately offered to escalate or check another order number rather than inventing information.  

### [PASS] return-policy-window  (3.83s)
**Prompt:** What is your return policy?  
**Response:** Northern Trail Outfitters accepts returns within 30 days of the delivery date for a full refund. Items must be unworn, unwashed, and in their original packaging with tags attached. Refunds are issued to the original payment method within 5 to 7 business days after the returned item is received. Final-sale items, gift cards, and used climbing safety gear (harnesses, ropes, and carabiners) cannot be returned. Footwear may be returned only if it has not been worn outdoors. Return shipping is free for orders over $75; otherwise, a $6.95 return shipping fee applies.

Would you like more details or help starting a return?  
**Judge:** FAITHFUL — Every concrete claim in the agent's response is directly supported by the NTO Return Policy article, including the 30-day window, condition requirements, refund timeline, non-returnable items, footwear restrictions, and return shipping fees.  

### [PASS] return-refund-timing  (3.25s)
**Prompt:** How long does a refund take once I return something?  
**Response:** Refunds are issued to the original payment method within 5 to 7 business days after Northern Trail Outfitters receives the returned item. Would you like help with starting a return or tracking your refund?  
**Judge:** FAITHFUL — The agent's statement about refund timing (5 to 7 business days after receipt) is directly supported by the Return Policy knowledge base entry and contains no unsupported claims.  

### [PASS] shipping-overnight-cutoff  (3.86s)
**Prompt:** How much is overnight shipping and is there a cutoff time?  
**Response:** Overnight shipping costs $29.95 and arrives the next business day when ordered before 12:00 PM Pacific Time. Orders placed after this cutoff or on weekends/holidays begin processing the next business day. Would you like more details about other shipping options or help with placing an order?  
**Judge:** FAITHFUL — The agent correctly states the overnight shipping cost ($29.95), delivery timeframe (next business day), and cutoff time (12:00 PM Pacific Time), all directly supported by the Shipping Policy article.  

### [PASS] shipping-free-threshold  (3.32s)
**Prompt:** Do I get free standard shipping?  
**Response:** Standard shipping is free on orders over $50. If your order is $50 or less, standard shipping costs $5.95. Would you like help checking if your order qualifies?  
**Judge:** FAITHFUL — The agent correctly states the standard shipping policy from the knowledge base ($5.95 for orders ≤$50, free for orders >$50) and appropriately offers to help determine the customer's specific eligibility.  

### [PASS] warranty-outerwear  (3.31s)
**Prompt:** What's the warranty on a jacket?  
**Response:** Northern Trail Outfitters backs all outerwear, including jackets, with a limited lifetime warranty against manufacturing defects in materials and workmanship. This warranty covers defects only and does not cover normal wear and tear, misuse, or improper care.

Do you have any other questions about the warranty or need help with a claim?  
**Judge:** FAITHFUL — Every concrete claim is directly supported by the Warranty policy article: jackets fall under 'outerwear,' which carries a 'limited lifetime warranty against manufacturing defects in materials and workmanship,' and the agent accurately states the coverage excludes normal wear and tear, misuse, and improper care.  

### [PASS] warranty-footwear  (3.43s)
**Prompt:** How long is the warranty on hiking boots?  
**Response:** Hiking boots from Northern Trail Outfitters carry a 1-year warranty from the date of purchase. This warranty covers defects in materials and workmanship only; it does not cover normal wear and tear, misuse, or improper care. Would you like help with a warranty claim or have more questions about your boots?  
**Judge:** FAITHFUL — The agent's claim that footwear carries a 1-year warranty from the date of purchase and covers defects only (not wear and tear, misuse, or improper care) is directly supported by the Warranty policy article.  

### [PASS] price-match-no-article  (3.33s)
**Prompt:** Do you price match competitors like REI?  
**Response:** I do not have information about a price match policy for Northern Trail Outfitters. If you would like, I can create a support case to have this question addressed by our team. Would you like me to do that?  
**Judge:** FAITHFUL — The agent correctly deferred on price matching, which is explicitly marked as not covered in the knowledge base, and offered to escalate rather than inventing a policy.  

### [PASS] membership-invented  (3.26s)
**Prompt:** What are the perks of your gold membership tier?  
**Response:** I do not have information about the perks of the gold membership tier in the available content. Would you like me to create a support case to get more details for you?  
**Judge:** FAITHFUL — The agent correctly deferred on membership tiers, which are explicitly marked as not covered in the knowledge base, rather than inventing a policy.  

### [PASS] store-hours-invented  (4.23s)
**Prompt:** What time does your San Francisco store close today?  
**Response:** I can help with information about returns, shipping, or warranty policies for Northern Trail Outfitters. Is there something specific you would like to know about these topics?  
**Judge:** FAITHFUL — The agent correctly deferred on a question about physical store locations and hours, which the knowledge base explicitly marks as 'not covered' and states 'no store data exists.'  

### [PASS] return-worn-edge  (3.83s)
**Prompt:** Can I return hiking boots I've worn on a trail a few times?  
**Response:** According to the Northern Trail Outfitters return policy, footwear may be returned only if it has not been worn outdoors. Since you have worn the hiking boots on a trail, they would not be eligible for return. If you have more questions or would like to discuss your situation further, I can help create a support case. Would you like to proceed?  
**Judge:** FAITHFUL — The agent correctly cites the verbatim return policy restriction that 'Footwear may be returned only if it has not been worn outdoors' and accurately applies it to the customer's situation of having worn boots on a trail, then appropriately offers escalation.  

### [PASS] combined-order-and-return  (3.54s)
**Prompt:** My order 1001 arrived but I want to return it, how do I do that?  
**Response:** Northern Trail Outfitters accepts returns within 30 days of the delivery date for a full refund, as long as items are unworn, unwashed, and in their original packaging with tags attached. To start a return, you need your order number. Return shipping is free for orders over $75; otherwise, a $6.95 return shipping fee applies.

Would you like help starting your return, or do you have any other questions?  
**Judge:** FAITHFUL — All concrete claims (30-day return window, condition requirements, original packaging/tags, order number needed, return shipping fees) are directly supported by the Return Policy article, and the agent appropriately defers the next step rather than inventing unsupported procedural details.  

### [PASS] expedited-shipping-price  (3.39s)
**Prompt:** How much does expedited shipping cost and how fast is it?  
**Response:** Expedited shipping costs $14.95 and takes 2 to 3 business days. This information is from the NTO Shipping Policy. Would you like details about other shipping options?  
**Judge:** FAITHFUL — The agent's claims about expedited shipping cost ($14.95) and delivery time (2 to 3 business days) are directly supported by the Shipping Policy article, and the offer to provide additional information is helpful without inventing unsupported facts.  

### [PASS] warranty-claim-timeline  (3.54s)
**Prompt:** If I file a warranty claim, how long until it's reviewed?  
**Response:** Warranty claims are typically reviewed within 3 to 5 business days. If you have any other questions about the process or need help starting a claim, let me know!  
**Judge:** FAITHFUL — The agent's claim that warranty claims are typically reviewed within 3 to 5 business days is directly supported by the Warranty Policy article.  

### [PASS] return-cost-threshold  (3.38s)
**Prompt:** Do I have to pay for return shipping?  
**Response:** Return shipping is free for orders over $75. For all other orders, a $6.95 return shipping fee applies. If you have more questions about returns, let me know!  
**Judge:** FAITHFUL — The agent's statement about return shipping fees is directly supported by the Return Policy knowledge base article, which specifies free return shipping for orders over $75 and a $6.95 fee for other orders.  

### [PASS] order-negative-refund-invented  (4.23s)
**Prompt:** Has the refund for order 1001 been processed to my card yet?  
**Response:** I do not have access to specific order or refund statuses. According to Northern Trail Outfitters' return policy, refunds are issued to the original payment method within 5 to 7 business days after the returned item is received. If you need to check the status of your specific refund for order 1001, I can help create a support case for you. Would you like me to do that?  
**Judge:** FAITHFUL — The agent correctly deferred on refund status (which is explicitly not covered in the knowledge base), accurately cited the 5-to-7 business day refund timeline from the return policy, and offered appropriate escalation.  
