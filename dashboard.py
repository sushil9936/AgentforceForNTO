#!/usr/bin/env python3
"""
Generate a self-contained dashboard.html from eval run history.

Reads:
    history.jsonl   one summary row per eval run (appended by run_eval.py)
    results.json    the latest run's per-scenario detail

Writes:
    dashboard.html  KPI cards + trend chart (inline SVG, no dependencies) +
                    per-scenario table. Open in any browser; no server needed.

Usage:
    python3 dashboard.py
"""
import html
import json
import os

HERE = os.path.dirname(__file__)


def load_history():
    path = os.path.join(HERE, "history.jsonl")
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def load_latest():
    path = os.path.join(HERE, "results.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def kpi_card(label, value, sub=""):
    sub_html = f'<div class="sub">{html.escape(sub)}</div>' if sub else ""
    return (f'<div class="card"><div class="label">{html.escape(label)}</div>'
            f'<div class="value">{html.escape(str(value))}</div>{sub_html}</div>')


def sparkline(values, width=520, height=90, pad=8):
    """Inline SVG line chart for a list of numeric values (0-100 scale)."""
    if not values:
        return '<div class="muted">No history yet — run the eval to populate trends.</div>'
    if len(values) == 1:
        values = values * 2  # a single point → flat line
    n = len(values)
    xs = [pad + i * (width - 2 * pad) / (n - 1) for i in range(n)]
    def y(v):
        return height - pad - (max(0.0, min(100.0, v)) / 100.0) * (height - 2 * pad)
    pts = " ".join(f"{x:.1f},{y(v):.1f}" for x, v in zip(xs, values))
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y(v):.1f}" r="2.5" fill="#2b6cb0"/>'
                   for x, v in zip(xs, values))
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
            f'preserveAspectRatio="none">'
            f'<polyline fill="none" stroke="#2b6cb0" stroke-width="2" points="{pts}"/>'
            f'{dots}</svg>')


def trend_block(title, values):
    latest = values[-1] if values else None
    latest_txt = f"{latest}%" if latest is not None else "—"
    return (f'<div class="trend"><div class="trend-head">{html.escape(title)}'
            f'<span class="trend-latest">{latest_txt}</span></div>'
            f'{sparkline(values)}</div>')


def scenario_rows(latest):
    out = []
    for r in latest:
        passed = r.get("passed")
        mark = "PASS" if passed else "FAIL"
        cls = "ok" if passed else "bad"
        judge = r.get("judge")
        jtxt = ""
        if judge:
            jv = judge[0]
            jcls = "ok" if jv == "FAITHFUL" else ("bad" if jv == "UNFAITHFUL" else "muted")
            jtxt = f'<span class="badge {jcls}">{html.escape(jv)}</span>'
        resp = r.get("response") or (r.get("error") or "")
        out.append(
            f'<tr><td><span class="badge {cls}">{mark}</span></td>'
            f'<td>{html.escape(r.get("id",""))}</td>'
            f'<td>{html.escape(r.get("category",""))}</td>'
            f'<td class="prompt">{html.escape(r.get("prompt",""))}</td>'
            f'<td>{jtxt}</td>'
            f'<td>{r.get("latency_s","")}s</td>'
            f'<td class="resp">{html.escape(resp[:220])}</td></tr>'
        )
    return "\n".join(out)


def build():
    history = load_history()
    latest = load_latest()
    last = history[-1] if history else None

    if last:
        acc = f'{last["accuracy_pass"]}/{last["total"]}'
        acc_sub = f'{last["accuracy_rate"]}% accuracy'
        defl = f'{last["deflection_rate"]}%'
        faith = (f'{last["faithful_pass"]}/{last["judged"]}'
                 if last["judged"] else "judge off")
        faith_sub = (f'{last["faithful_rate"]}% faithful'
                     if last.get("faithful_rate") is not None else "run with --judge")
        lat = f'{last["avg_latency_s"]}s'
        lat_sub = f'max {last["max_latency_s"]}s'
        run_label = last.get("label") or "(unlabeled)"
        run_ts = last.get("ts", "")
    else:
        acc = acc_sub = defl = faith = faith_sub = lat = lat_sub = "—"
        run_label = run_ts = "no runs yet"

    acc_series = [h["accuracy_rate"] for h in history]
    defl_series = [h["deflection_rate"] for h in history]
    faith_series = [h["faithful_rate"] for h in history if h.get("faithful_rate") is not None]

    cards = "".join([
        kpi_card("Deflection rate", defl, "answered without bailing"),
        kpi_card("Accuracy", acc, acc_sub),
        kpi_card("Faithfulness", faith, faith_sub),
        kpi_card("Avg latency", lat, lat_sub),
    ])

    trends = "".join([
        trend_block("Accuracy % over runs", acc_series),
        trend_block("Deflection % over runs", defl_series),
        trend_block("Faithfulness % over runs", faith_series),
    ])

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NTO Agent — KPI Dashboard</title>
<style>
  :root {{ --bg:#f7f8fa; --card:#fff; --ink:#1a202c; --muted:#718096;
           --line:#e2e8f0; --ok:#2f855a; --bad:#c53030; --accent:#2b6cb0; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
          font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:1000px; margin:0 auto; padding:28px 20px 60px; }}
  h1 {{ font-size:22px; margin:0 0 2px; }}
  .meta {{ color:var(--muted); font-size:13px; margin-bottom:22px; }}
  .cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
           padding:16px; }}
  .card .label {{ color:var(--muted); font-size:12px; text-transform:uppercase;
                  letter-spacing:.04em; }}
  .card .value {{ font-size:30px; font-weight:650; margin-top:6px; }}
  .card .sub {{ color:var(--muted); font-size:12px; margin-top:2px; }}
  .trends {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-top:22px; }}
  .trend {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
            padding:14px; }}
  .trend-head {{ font-size:13px; color:var(--muted); display:flex;
                 justify-content:space-between; align-items:baseline; margin-bottom:8px; }}
  .trend-latest {{ color:var(--accent); font-weight:650; font-size:15px; }}
  h2 {{ font-size:16px; margin:30px 0 10px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
           border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
  th, td {{ text-align:left; padding:9px 11px; border-bottom:1px solid var(--line);
            font-size:13px; vertical-align:top; }}
  th {{ background:#fafbfc; color:var(--muted); font-weight:600; }}
  tr:last-child td {{ border-bottom:none; }}
  .prompt {{ max-width:220px; color:var(--ink); }}
  .resp {{ max-width:280px; color:var(--muted); }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:20px; font-size:11px;
            font-weight:650; }}
  .badge.ok {{ background:#e6fffa; color:var(--ok); }}
  .badge.bad {{ background:#fff5f5; color:var(--bad); }}
  .badge.muted {{ background:#edf2f7; color:var(--muted); }}
  .muted {{ color:var(--muted); font-size:13px; }}
</style></head>
<body><div class="wrap">
  <h1>NTO Customer Support — Agent KPI Dashboard</h1>
  <div class="meta">Latest run: <b>{html.escape(str(run_label))}</b> &middot; {html.escape(str(run_ts))} &middot; {len(history)} run(s) recorded</div>
  <div class="cards">{cards}</div>
  <div class="trends">{trends}</div>
  <h2>Latest run — per-scenario detail</h2>
  <table>
    <tr><th>Result</th><th>Scenario</th><th>Category</th><th>Prompt</th>
        <th>Judge</th><th>Latency</th><th>Response</th></tr>
    {scenario_rows(latest)}
  </table>
</div></body></html>"""

    out = os.path.join(HERE, "dashboard.html")
    with open(out, "w") as f:
        f.write(doc)
    print(f"Wrote {out}  ({len(history)} run(s) in history, {len(latest)} scenarios in latest)")


if __name__ == "__main__":
    build()
