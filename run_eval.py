#!/usr/bin/env python3
"""
NTO Customer Support agent — faithfulness & accuracy eval harness.

Runs a suite of behavioral-contract scenarios against the live agent over the
headless Agent API, scores each response deterministically, and (optionally)
adds an LLM-as-judge faithfulness pass. Emits a scored report to results.md
and a machine-readable results.json.

Credentials are read from environment variables — nothing secret is stored in
this repo:
    NTO_TOKEN_URL      e.g. https://<mydomain>/services/oauth2/token
    NTO_CLIENT_ID      OAuth consumer key (not secret)
    NTO_CLIENT_SECRET  OAuth consumer secret (secret — export in your shell only)
    NTO_AGENT_ID       BotDefinition Id, e.g. 0Xx...
    NTO_MY_DOMAIN      e.g. https://<mydomain>.my.salesforce.com

Optional (enables the LLM-as-judge faithfulness pass):
    ANTHROPIC_API_KEY  if set and --judge is passed, uses Claude to grade faithfulness

Usage:
    export NTO_CLIENT_SECRET='...'   # in your shell, once
    python3 run_eval.py                    # deterministic scoring only
    python3 run_eval.py --judge            # also run LLM-as-judge
    python3 run_eval.py --only order-1002-null-delivery
"""
import argparse
import json
import os
import subprocess
import sys
import time
import uuid

API_BASE = "https://api.salesforce.com/einstein/ai-agent/v1"


class HTTPError(Exception):
    """Raised when curl reports a non-2xx HTTP status."""


def _curl(args, timeout=130):
    """Run curl and return (status_code:int, body:str). Uses the system CA
    store, so no Python TLS/certifi setup is needed."""
    proc = subprocess.run(
        ["curl", "-sS", "-w", "\n%{http_code}", *args],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise HTTPError(f"curl failed: {proc.stderr.strip()[:200]}")
    out = proc.stdout
    nl = out.rfind("\n")
    body, status = out[:nl], out[nl + 1:].strip()
    try:
        code = int(status)
    except ValueError:
        code = 0
    if code >= 400:
        raise HTTPError(f"HTTP {code}: {body[:200]}")
    return code, body


def _post_json(url, payload, token, timeout=130):
    _, body = _curl([
        "-X", "POST", url,
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {token}",
        "--data", json.dumps(payload),
    ], timeout=timeout)
    return json.loads(body)


def get_token(cfg):
    """Mint an OAuth client-credentials JWT access token."""
    _, body = _curl([
        cfg["token_url"],
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "--data-urlencode", "grant_type=client_credentials",
        "--data-urlencode", f"client_id={cfg['client_id']}",
        "--data-urlencode", f"client_secret={cfg['client_secret']}",
    ], timeout=30)
    tok = json.loads(body).get("access_token", "")
    if not tok.startswith("eyJ"):
        sys.exit("ERROR: token is not a JWT (starts with '%s'). Enable "
                 "'Issue JWT-based access tokens' on the External Client App." % tok[:5])
    return tok


def create_session(token, cfg):
    url = f"{API_BASE}/agents/{cfg['agent_id']}/sessions"
    payload = {
        "externalSessionKey": str(uuid.uuid4()),
        "instanceConfig": {"endpoint": cfg["my_domain"]},
        "streamingCapabilities": {"chunkTypes": ["Text"]},
        "bypassUser": True,
    }
    body = _post_json(url, payload, token)
    return body["sessionId"]


def send_message(token, session_id, text, seq):
    url = f"{API_BASE}/sessions/{session_id}/messages"
    payload = {"message": {"sequenceId": seq, "type": "Text", "text": text}}
    body = _post_json(url, payload, token)
    # concatenate all Inform message texts
    parts = [m.get("message", "") for m in body.get("messages", [])
             if m.get("type") == "Inform"]
    return " ".join(p for p in parts if p)


# --- deterministic scoring -------------------------------------------------

REFUSAL_MARKERS = [
    "don't have", "do not have", "couldn't find", "could not find",
    "unable to", "not able to", "no information", "don't see",
    "create a case", "open a case", "support case", "not available",
    "i'm not sure", "i am not sure", "can't find", "cannot find",
    # off-topic deflection: agent steers back to its supported topics
    "i can help with", "is there something specific",
    "would you like to know about", "i can assist with",
]


def _norm(s):
    """Normalize for substring matching: lowercase and treat hyphens as
    spaces so '1-year' matches '1 year'."""
    return s.lower().replace("-", " ")


def looks_like_refusal(text):
    t = _norm(text)
    return any(_norm(m) in t for m in REFUSAL_MARKERS)


def score(scenario, response):
    t = _norm(response)
    checks = []
    passed = True

    for s in scenario.get("must_include", []):
        ok = _norm(s) in t
        checks.append(("must_include", s, ok))
        passed = passed and ok

    for s in scenario.get("must_not_include", []):
        ok = _norm(s) not in t          # pass means it's ABSENT
        checks.append(("must_not_include", s, ok))
        passed = passed and ok

    if scenario.get("should_refuse"):
        ok = looks_like_refusal(response)
        checks.append(("should_refuse", "refusal-language", ok))
        passed = passed and ok

    return passed, checks


# --- optional LLM-as-judge -------------------------------------------------

def _resolve_judge_key():
    """Get an API key for the judge without storing it anywhere.
    Precedence: ANTHROPIC_API_KEY env, else a command in JUDGE_KEY_CMD
    (e.g. an internal key-helper). Returns key or None."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    cmd = os.environ.get("JUDGE_KEY_CMD")
    if cmd:
        try:
            out = subprocess.run(cmd, shell=True, capture_output=True,
                                 text=True, timeout=15)
            return out.stdout.strip() or None
        except Exception:  # noqa: BLE001
            return None
    return None


def _make_judge_client():
    """Build an Anthropic client + model id.
    Uses ANTHROPIC_BASE_URL if set (e.g. an internal proxy), else the public API.
    Returns (client, model) or (None, reason)."""
    try:
        import anthropic
    except ImportError:
        return (None, "anthropic SDK not installed (pip install anthropic)")

    key = _resolve_judge_key()
    if not key:
        return (None, "no judge key (set ANTHROPIC_API_KEY or JUDGE_KEY_CMD)")

    base_url = os.environ.get("ANTHROPIC_BASE_URL")  # proxy-aware
    kwargs = {"api_key": key}
    if base_url:
        kwargs["base_url"] = base_url
    default_model = ("us.anthropic.claude-haiku-4-5-20251001-v1:0" if base_url
                     else "claude-opus-5")
    model = os.environ.get("NTO_JUDGE_MODEL", default_model)
    return (anthropic.Anthropic(**kwargs), model)


def _load_knowledge():
    path = os.path.join(os.path.dirname(__file__), "knowledge.md")
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


_KNOWLEDGE = None


def judge_faithfulness(scenario, response):
    """Grade whether the response invents any fact not supported by the
    ground-truth knowledge base. Returns (verdict, reasoning) or None."""
    global _KNOWLEDGE
    client, model = _make_judge_client()
    if client is None:
        return ("SKIPPED", model)  # model holds the reason string here
    if _KNOWLEDGE is None:
        _KNOWLEDGE = _load_knowledge()

    prompt = (
        "You are a strict faithfulness judge for a customer-service agent. "
        "Below is the ONLY source of truth the agent may draw facts from. "
        "A response is FAITHFUL if every concrete customer-facing claim it makes "
        "(dates, prices, policies, order status) is supported by the knowledge base, "
        "AND it refuses/defers on anything the knowledge base marks as not covered. "
        "Inventing an unsupported fact is a FAILURE even if it sounds plausible. "
        "Do NOT penalize the agent for correctly stating supported facts, for adding "
        "harmless clarifiers (e.g. 'business days'), or for naming the company.\n\n"
        f"KNOWLEDGE BASE:\n{_KNOWLEDGE}\n\n"
        f"USER ASKED:\n{scenario['prompt']}\n\n"
        f"AGENT RESPONSE:\n{response}\n\n"
        "Reply with a single JSON object: "
        '{\"verdict\": \"FAITHFUL\" | \"UNFAITHFUL\", \"reasoning\": \"one sentence\"}'
    )
    msg = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        obj = json.loads(text[start:end])
        return (obj.get("verdict", "?"), obj.get("reasoning", ""))
    except (ValueError, json.JSONDecodeError):
        return ("PARSE_ERROR", text[:200])


# --- main ------------------------------------------------------------------

def load_cfg():
    missing = []
    def need(k):
        v = os.environ.get(k)
        if not v:
            missing.append(k)
        return v
    cfg = {
        "token_url": need("NTO_TOKEN_URL"),
        "client_id": need("NTO_CLIENT_ID"),
        "client_secret": need("NTO_CLIENT_SECRET"),
        "agent_id": need("NTO_AGENT_ID"),
        "my_domain": need("NTO_MY_DOMAIN"),
    }
    if missing:
        sys.exit("ERROR: missing env vars: %s\nSee the header of this file or .env.example."
                 % ", ".join(missing))
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true", help="run LLM-as-judge faithfulness pass")
    ap.add_argument("--only", help="run a single scenario id")
    ap.add_argument("--label", default="", help="tag this run (e.g. agent version) in history")
    ap.add_argument("--scenarios", default=os.path.join(os.path.dirname(__file__), "scenarios.json"))
    args = ap.parse_args()

    cfg = load_cfg()
    with open(args.scenarios) as f:
        scenarios = json.load(f)["scenarios"]
    if args.only:
        scenarios = [s for s in scenarios if s["id"] == args.only]
        if not scenarios:
            sys.exit(f"no scenario with id '{args.only}'")

    print(f"Minting token from {cfg['token_url']} ...")
    token = get_token(cfg)
    print("Token OK (JWT). Running %d scenarios.\n" % len(scenarios))

    results = []
    for sc in scenarios:
        t0 = time.time()
        try:
            sid = create_session(token, cfg)
            response = send_message(token, sid, sc["prompt"], 1)
            err = None
        except HTTPError as e:
            response, err = "", str(e)
        except Exception as e:  # noqa: BLE001
            response, err = "", f"{type(e).__name__}: {e}"
        latency = round(time.time() - t0, 2)

        if err:
            passed, checks = False, [("error", err, False)]
        else:
            passed, checks = score(sc, response)

        judged = judge_faithfulness(sc, response) if (args.judge and not err) else None

        results.append({
            "id": sc["id"], "category": sc["category"], "prompt": sc["prompt"],
            "response": response, "error": err, "passed": passed,
            "checks": checks, "latency_s": latency, "judge": judged,
        })
        mark = "PASS" if passed else "FAIL"
        extra = ""
        if judged:
            extra = f"  [judge:{judged[0]}]"
        print(f"[{mark}] {sc['id']:32s} {latency:5.2f}s{extra}")
        if not passed:
            for kind, needle, ok in checks:
                if not ok:
                    print(f"        ✗ {kind}: {needle!r}")

    write_reports(results, args.judge)
    kpis = compute_kpis(results, args.judge)
    record_history(kpis, args.label, args.judge)
    n_pass = kpis["accuracy_pass"]
    print(f"\n{n_pass}/{kpis['total']} passed  |  deflection {kpis['deflection_rate']}%  "
          f"faithful {kpis['faithful_pass']}/{kpis['judged']}  avg {kpis['avg_latency_s']}s")
    print("Reports: results.md, results.json, history.jsonl")
    sys.exit(0 if n_pass == kpis["total"] else 1)  # non-zero => usable as a CI gate


def compute_kpis(results, judged_run):
    """Roll a run's per-scenario results up into the four operational KPIs."""
    n = len(results)
    n_pass = sum(1 for r in results if r["passed"])
    avg_lat = round(sum(r["latency_s"] for r in results) / n, 2) if n else 0

    # Deflection = of scenarios the agent was SUPPOSED to answer (should_refuse
    # is falsy in the scenario), how many did it actually answer end-to-end
    # (no error, non-empty response). This is the "handled without bailing" rate.
    answerable = [r for r in results if r["response"] and not r["error"]]
    deflection = round(100 * len(answerable) / n, 1) if n else 0

    judged = [r for r in results if r.get("judge") and r["judge"][0] in ("FAITHFUL", "UNFAITHFUL")]
    faithful = sum(1 for r in judged if r["judge"][0] == "FAITHFUL")

    by_cat = {}
    for r in results:
        c = r["category"]
        by_cat.setdefault(c, [0, 0])
        by_cat[c][1] += 1
        if r["passed"]:
            by_cat[c][0] += 1

    return {
        "total": n,
        "accuracy_pass": n_pass,
        "accuracy_rate": round(100 * n_pass / n, 1) if n else 0,
        "deflection_rate": deflection,
        "judged": len(judged),
        "faithful_pass": faithful,
        "faithful_rate": round(100 * faithful / len(judged), 1) if judged else None,
        "avg_latency_s": avg_lat,
        "max_latency_s": round(max((r["latency_s"] for r in results), default=0), 2),
        "by_category": {c: {"pass": p, "total": t} for c, (p, t) in by_cat.items()},
    }


def record_history(kpis, label, judged_run):
    """Append one summary line per run to history.jsonl (the dashboard data source).
    Timestamp comes from the OS clock via a tiny shell call, since this file avoids
    importing datetime for determinism elsewhere — but here a wall-clock stamp is fine."""
    ts = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                        capture_output=True, text=True).stdout.strip()
    row = {"ts": ts, "label": label, "judge": judged_run, **kpis}
    path = os.path.join(os.path.dirname(__file__), "history.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")


def write_reports(results, judged_run):
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "results.json"), "w") as f:
        json.dump(results, f, indent=2)

    n = len(results)
    n_pass = sum(1 for r in results if r["passed"])
    avg_lat = round(sum(r["latency_s"] for r in results) / n, 2) if n else 0
    by_cat = {}
    for r in results:
        c = r["category"]
        by_cat.setdefault(c, [0, 0])
        by_cat[c][1] += 1
        if r["passed"]:
            by_cat[c][0] += 1

    lines = [
        "# NTO Agent — Faithfulness & Accuracy Eval",
        "",
        f"**Pass rate:** {n_pass}/{n}  ({round(100*n_pass/n) if n else 0}%)  ",
        f"**Avg latency:** {avg_lat}s  ",
        f"**LLM-as-judge:** {'on' if judged_run else 'off'}",
        "",
        "## By category",
        "",
    ]
    for c, (p, tot) in sorted(by_cat.items()):
        lines.append(f"- {c}: {p}/{tot}")
    lines += ["", "## Scenarios", ""]
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        lines.append(f"### [{mark}] {r['id']}  ({r['latency_s']}s)")
        lines.append(f"**Prompt:** {r['prompt']}  ")
        if r["error"]:
            lines.append(f"**Error:** `{r['error']}`  ")
        else:
            lines.append(f"**Response:** {r['response']}  ")
        failed = [(k, needle) for k, needle, ok in r["checks"] if not ok]
        if failed:
            lines.append("**Failed checks:** " + ", ".join(f"{k}={needle!r}" for k, needle in failed) + "  ")
        if r["judge"]:
            lines.append(f"**Judge:** {r['judge'][0]} — {r['judge'][1]}  ")
        lines.append("")
    with open(os.path.join(here, "results.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
