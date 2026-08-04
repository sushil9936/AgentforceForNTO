# Build Guide — NTO Customer Support Agent (end to end)

A step-by-step walkthrough to recreate this project from scratch in a free
Salesforce Developer Edition org: a grounded Agentforce customer-service agent
with an Apex tool action, a headless API, a faithfulness eval gate, and a KPI
dashboard. Follow the six steps in order — each builds on the last.

Everything here is buildable for free. Sign up for a Developer Edition org at
https://developer.salesforce.com/signup (personal email is fine).

Notation: values in `<angle brackets>` are yours to fill in. Never commit real
secrets — the OAuth consumer secret stays in your shell only.

---

## Prerequisites (one time)

1. A Developer Edition org with **Agentforce** enabled (Setup → search
   "Agentforce Agents" → toggle Agentforce **On**).
2. Data Cloud provisioned (needed for the Data Library in Step 2). In a Dev org
   this is a self-serve toggle; it can take a little while to provision.
3. `curl`, `python3`, and (optional) `jq` on your machine.

---

## Step 1 — Bare agent + routing

**Concept:** an agent classifies the user's intent and routes to the right
sub-handler. Agentforce structures this as Agent → Subagents → Actions.

1. Setup → **Agentforce Agents** → **New Agent**.
2. Choose the **Agentforce Service Agent** type. This matters: the *Agentforce
   (Default)* type is customer-service-in-UI only and is **NOT reachable by the
   headless Agent API** you'll need in Step 4. Pick **Service Agent**.
3. Start from scratch / skip the templates. Give it a name (e.g. "NTO Customer
   Support"). Note the **API/Developer Name** (e.g. `NTO_Customer_Support`).
4. It comes with utility subagents (Router, Escalation, Off Topic, Ambiguous).
   Leave them; they do the routing.
5. Open **Preview** and confirm it greets and responds. That's Step 1.

The agent runs as the **EinsteinServiceAgent User** — remember this; permissions
in Step 3 are granted to that user, not to you.

---

## Step 2 — Grounding / RAG (answer from knowledge)

**Concept:** the agent answers factual questions from an indexed corpus (vector
search over your content), not from the model's memory.

1. **Enable Lightning Knowledge:** Setup → Knowledge Settings → Enable. This is
   one-way; fine for a practice org.
2. **Add a body field:** Lightning Knowledge ships with NO content field. On the
   Knowledge object, create a custom **Rich Text Area** field (e.g. `Body__c`).
3. **Author + publish articles.** Create a few with deliberately specific facts
   (exact dollar amounts, day counts, cutoff times) — specificity is what makes
   faithfulness testable later. Publish them (PublishStatus = Online).
   This project used three: Return Policy, Shipping Policy, Warranty Policy.
4. **Build a Data Library:** Setup → Agentforce Data Library → New. Point it at
   your Knowledge articles; set the body field as the Content Field and
   Title/Body as Identifying Fields. Wait for Status = **Ready** (it chunks,
   embeds, and indexes into Data Cloud).
5. **Add a Policy Questions subagent** in the Builder. Give it a routing
   description ("use for returns/shipping/warranty, NOT order status") and
   Reasoning Instructions that enforce grounding (see the guardrail note below).
6. **Attach the "Answer Questions with Knowledge" standard action** to that
   subagent. Its input is an AI-generated Query; it retrieves passages and
   returns Citations.
7. **GOTCHA:** the Data Library is an org-level asset but must be **linked
   per-agent** in the Builder (Explorer → Data → Data Library). If you skip this
   you'll get `REQUIRED_FIELD_MISSING` "no data library assigned to this agent".
8. Preview: "What's your return policy?" should return the article facts.

**Grounding guardrail (Reasoning Instructions for the Policy subagent):**
> Answer using only information retrieved from the knowledge base. Only state
> facts that appear in the retrieved passages. Do not add policies, restrictions,
> exclusions, or procedural steps that are not in the retrieved article. If the
> knowledge base doesn't contain the answer, say you don't have that information
> and offer to create a support case.

---

## Step 3 — Apex tool action (ReAct / tool-calling)

**Concept:** the agent calls real code to fetch live data. The code returns
**structured facts (null when a value is absent)**; the LLM writes the prose.
This separation is what prevents hallucination — the model can't invent a
delivery date the code returned as null.

1. **Create the data.** Make a custom object (e.g. `NTO_Order__c`) with fields
   like order number, status, item, delivery date, tracking number. Add a few
   records — and deliberately leave one record's delivery date/tracking **null**
   (this becomes a faithfulness test). Add a "not found" case by simply not
   creating that order number.
2. **Write an invocable Apex class** (e.g. `GetOrderStatus`) with an
   `@InvocableMethod` that takes an order number and returns a structured
   Response (found flag + the fields). Use `with sharing` so it respects the
   running user's permissions. Return nulls honestly — do not default-fill.
   The exact class used in this project is in `apex/GetOrderStatus.cls`, and the
   `NTO_Order__c` object schema it depends on is documented in `apex/README.md`.
3. **Register it as an Agent Action** and add it to an "Order Status" subagent.
   Fill in EVERY input/output Description field — blank required descriptions
   cause validation errors that block activation.
4. **Grant two permission layers** to the EinsteinServiceAgent User (create a
   permission set and assign it):
   - **Apex Class Access** → your class (lets the agent invoke the code).
   - **Object + Field-Level Read** on the custom object (lets it read the data
     the code touches). Object-level Read is a SEPARATE gate from field-level
     Read — you need both. Least privilege: Read only.
5. Preview three cases: a happy path, the null-fields record (agent must say the
   date "isn't available yet", not invent one), and a nonexistent order (agent
   must say it can't find it and offer a case). Trace should show GROUNDED.

---

## Step 4 — Headless Agent API (call it over REST)

**Concept:** make the agent callable machine-to-machine, no UI — this is what
makes it embeddable and testable.

1. **Activate the agent.** In the Builder: Commit Version → Activate. Committed
   versions are immutable; to edit later, make a New Version (draft).
2. **Create an External Client App:** Setup → External Client App Manager → New.
   - Enable OAuth. Scopes: `api`, `refresh_token`/`offline_access`,
     `chatbot_api`, `sfap_api`.
   - **Enable Client Credentials Flow.**
   - **CRITICAL — in the app's Settings → OAuth Settings, check "Issue JSON Web
     Token (JWT)-based access tokens for named users."** The `api.salesforce.com`
     platform gateway ONLY accepts JWT-format tokens. If the app issues opaque
     tokens instead, EVERY Agent API call returns a bare HTTP 404 (empty body,
     only a `date` header) — on every path — which looks like a routing bug but
     is really a token-format rejection at the edge. (Do NOT confuse this with
     "Enable JWT Bearer Flow" — that's a different, inbound-assertion setting.)
3. **Set Run As:** app → Policies → OAuth Policies → Enable Client Credentials
   Flow → Run As = the EinsteinServiceAgent User.
4. **Get the Agent ID.** For new-builder agents, the ID in the Builder URL is
   NOT the API id — query it (Developer Console → Query Editor):
   ```sql
   SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = '<Your_Agent_Dev_Name>'
   ```
   The `Id` (starts with `0Xx`) is your `<AGENT_ID>`.
5. **Mint a token** (the secret stays in your shell — never in a file):
   ```bash
   export CONSUMER_SECRET='<your consumer secret>'
   curl -s -X POST 'https://<mydomain>/services/oauth2/token' \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     --data-urlencode 'grant_type=client_credentials' \
     --data-urlencode 'client_id=<consumer key>' \
     --data-urlencode "client_secret=$CONSUMER_SECRET"
   ```
   The `access_token` should start with `eyJ` (a JWT). If it starts with your
   org id and `!`, JWT issuance is off — go fix step 2 above.
6. **Create a session:**
   ```bash
   curl -s -X POST 'https://api.salesforce.com/einstein/ai-agent/v1/agents/<AGENT_ID>/sessions' \
     -H "Authorization: Bearer <TOKEN>" -H 'Content-Type: application/json' \
     --data '{"externalSessionKey":"<uuid>","instanceConfig":{"endpoint":"https://<mydomain>"},"streamingCapabilities":{"chunkTypes":["Text"]},"bypassUser":true}'
   ```
   You get back a `sessionId` and a greeting. Then POST a message:
   ```bash
   curl -s -X POST 'https://api.salesforce.com/einstein/ai-agent/v1/sessions/<sessionId>/messages' \
     -H "Authorization: Bearer <TOKEN>" -H 'Content-Type: application/json' \
     --data '{"message":{"sequenceId":1,"type":"Text","text":"Where is my order 1001?"}}'
   ```
   A grounded, tool-backed answer over pure REST = Step 4 done.

**Debugging tip:** a bare 404 from an API gateway means "route not matched for
this caller," not "resource missing." Fastest disambiguator: send the same call
WITHOUT the auth header. If you still get 404 (not 401), auth isn't even being
evaluated — the token format/host/route is the problem, not the credential.

---

## Step 5 — Faithfulness eval gate

**Concept:** before trusting the agent, prove it (a) states the right facts and
(b) never invents facts / refuses when it lacks grounding. Two scoring layers.

Files in this repo implement it:
- `scenarios.json` — behavioral contracts (data, not code). Each scenario has
  `must_include`, `must_not_include` (hallucination tripwires), and
  `should_refuse`. Include "money tests": questions with no grounding (price
  match, membership, store hours) where the ONLY correct answer is a refusal.
- `run_eval.py` — mints a JWT, runs each scenario in its own session over the
  Agent API, and scores two ways:
  1. **Deterministic** — substring assertions from the contract. Cheap, no flake,
     great CI gate. Exit code is non-zero if any scenario fails.
  2. **LLM-as-judge** (`--judge`) — a model grades whether every claim is
     supported by the ground-truth knowledge base and refusals happen when they
     should. Catches plausible-but-ungrounded drift the substring checks miss.
- `knowledge.md` — the ground-truth the judge grades against.

Run it:
```bash
export NTO_TOKEN_URL='https://<mydomain>/services/oauth2/token'
export NTO_CLIENT_ID='<consumer key>'
export NTO_CLIENT_SECRET='<consumer secret>'
export NTO_AGENT_ID='<AGENT_ID>'
export NTO_MY_DOMAIN='https://<mydomain>'
python3 run_eval.py            # deterministic
python3 run_eval.py --judge    # + LLM judge (needs a model key; see README)
```

**THE key lesson:** an LLM-as-judge is only as trustworthy as the source-of-truth
you give it. If `knowledge.md` is a lossy paraphrase of your real articles, the
judge will confidently flag CORRECT answers as hallucinations. Ground the judge
against the EXACT article text your retrieval returns — pull it from the org:
```sql
SELECT Title, Body__c FROM Knowledge__kav WHERE PublishStatus = 'Online'
```
Also: "I don't have that, want a case?" is a *faithful* answer — don't score a
refusal as a failure just because it didn't assert a negative policy.

---

## Step 6 — KPI dashboard (observability)

**Concept:** an agent in production is a system you operate. One eval run is a
snapshot; a history of runs is a trend line that catches regressions.

- `run_eval.py` appends one summary row per run to `history.jsonl` (use
  `--label "<version>"` to tag runs by agent version).
- `dashboard.py` reads the history + latest `results.json` and writes a
  self-contained `dashboard.html` (no server, no JS libraries).

```bash
python3 run_eval.py --judge --label "v1"
python3 dashboard.py
open dashboard.html
```

Four KPIs:
- **Deflection rate** — % answered end-to-end without bailing (business ROI).
- **Accuracy** — % passing the deterministic contract checks.
- **Faithfulness** — % the judge cleared (risk / compliance).
- **Latency** — avg / max response time (customer experience).

Label runs by agent version so the trend sparklines show whether an instruction
or model change helped or regressed.

---

## Recap of the arc

1. Routing → 2. Grounding/RAG → 3. Tool-calling (Apex) → 4. Headless API →
5. Faithfulness eval gate → 6. KPI dashboard.

Each step is a distinct agentic-AI building block, and the last two turn "an
agent that works" into "an agent you can prove is safe and operate over time."
