# NTO Customer Support — Faithfulness Eval

A behavioral-contract eval suite for the NTO Customer Support agent. It drives the
agent over the headless Agent API, scores each response for **accuracy** (did it
surface the right facts?) and **faithfulness** (did it avoid inventing anything and
refuse when it had no grounding?), and produces a scored report.

## Files in this repo

| File | What it is |
|------|-----------|
| `BUILD_GUIDE.md` | Step-by-step guide to build the whole agent from scratch (all six steps). Start here if you want to recreate it. |
| `apex/GetOrderStatus.cls` | The invocable Apex class the agent calls to look up live order data (the Step 3 tool). |
| `apex/README.md` | How the Apex works + the `NTO_Order__c` custom object schema it needs. |
| `scenarios.json` | The test suite — behavioral contracts (data, not code). |
| `run_eval.py` | The eval runner: mints a JWT, drives the agent over the API, scores two ways, records history. |
| `knowledge.md` | Ground-truth knowledge base the LLM judge grades faithfulness against. |
| `dashboard.py` | Reads run history → writes a self-contained `dashboard.html` (KPI cards + trends). |
| `.env.example` | The environment variables you must set (copy to a private file; never commit secrets). |
| `.gitignore` | Excludes secrets, generated reports, the venv. |
| `results.json` / `results.md` | Latest run output (generated). |
| `history.jsonl` | One summary row per run — the dashboard's data source (generated). |
| `dashboard.html` | The generated dashboard (open in a browser). |

## Design: contract-first

Expected behavior lives in `scenarios.json` as data, not code. Each scenario declares:

- `must_include` — facts/phrases that must appear (case-insensitive)
- `must_not_include` — hallucination tripwires that must **not** appear
- `should_refuse` — `true` when the correct behavior is to decline / offer a case

This makes the suite a **regression gate**: run it against any agent version and the
exit code is non-zero if any scenario fails, so it drops straight into CI.

Scenarios span four risk classes: grounded order lookups, grounded policy RAG,
multi-intent routing, and **faithfulness-negative "money tests"** (price match,
membership, store hours, refund status) where the only correct answer is a refusal.

## Run

```bash
# one time, in your shell (secret stays out of the repo):
export NTO_TOKEN_URL='https://<mydomain>/services/oauth2/token'
export NTO_CLIENT_ID='<consumer key>'
export NTO_CLIENT_SECRET='<consumer secret>'
export NTO_AGENT_ID='<BotDefinition Id, 0Xx...>'
export NTO_MY_DOMAIN='https://<mydomain>.my.salesforce.com'

python3 run_eval.py                 # deterministic scoring
python3 run_eval.py --judge         # + LLM-as-judge faithfulness (needs ANTHROPIC_API_KEY)
python3 run_eval.py --only price-match-no-article
```

Outputs `results.md` (human) and `results.json` (machine). Exit code 0 = all pass.

## Two scoring layers

1. **Deterministic** — substring assertions from the contract. Fast, free, no flake.
   Catches the money tests directly (a fabricated date/price is a literal string).
2. **LLM-as-judge** (`--judge`) — Claude grades faithfulness nuance the substring
   checks can't: plausible-but-ungrounded claims phrased in words the tripwire missed.

The deterministic layer is the gate; the judge is the safety net.

## Dashboard (KPIs over time)

Each eval run appends a summary row to `history.jsonl` (accuracy, deflection,
faithfulness, latency, per-category). Generate a self-contained HTML dashboard from
that history — KPI cards, trend sparklines across runs, and the latest run's
per-scenario table:

```bash
python3 run_eval.py --judge --label "v2-guardrail"   # runs eval + records history
python3 dashboard.py                                  # writes dashboard.html
open dashboard.html
```

The four operational KPIs:
- **Deflection rate** — % of questions the agent answered end-to-end without bailing (business ROI).
- **Accuracy** — % passing the deterministic contract checks (right facts).
- **Faithfulness** — % the LLM-as-judge cleared (no ungrounded claims; risk/compliance).
- **Latency** — avg / max response time (customer experience).

Label runs (`--label`) with the agent version to see KPIs trend across versions and
catch regressions (e.g. faithfulness dropping after an instruction edit).

## Prereq

The agent must be reachable over the Agent API: **Service Agent** type, activated,
and the External Client App must issue **JWT** access tokens (Settings → OAuth
Settings → "Issue JSON Web Token (JWT)-based access tokens for named users").
The harness fails fast if the minted token isn't a JWT.
