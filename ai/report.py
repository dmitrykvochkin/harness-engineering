"""Compare classify.py runs against the human labels and write a simple HTML report.

    python report.py runs/*.jsonl --output runs/report.html [--notes runs/notes.html]

Cost, time and tokens come from <name>.meta.json next to each results file. A run that
is still going has no meta file yet: it is scored on the traces written so far, and an
extra table compares every model on just those traces. This script reads labels.jsonl to
score results; classify.py itself never sees the labels.
"""

import argparse
import html
import json
from pathlib import Path

SIGNALS = ["user_frustration", "task_failure", "forgetting"]
DATA = Path(__file__).parent.parent / "data" / "conversations"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_meta(results_path):
    path = results_path.with_suffix(".meta.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def f1(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, score


def score_run(results_path, labels, held_out, run_ids=None):
    meta = load_meta(results_path)
    records = load_jsonl(results_path)
    if run_ids is not None:
        records = [r for r in records if r["run_id"] in run_ids]
    per_signal = {}
    correct = {"all": 0, "held_out": 0}
    total = {"all": 0, "held_out": 0}
    evidence_hits = true_positives = 0
    for signal in SIGNALS:
        tp = fp = fn = hits = 0
        for record in records:
            gold = labels[record["run_id"]]["signals"][signal]
            predicted = record["signals"][signal]
            verdict = predicted["verdict"] if predicted else "error"
            match = verdict == gold["verdict"]
            for part in ["all", "held_out"] if record["run_id"] in held_out else ["all"]:
                total[part] += 1
                correct[part] += match
            if verdict == "present" and gold["verdict"] == "present":
                tp += 1
                hits += bool(set(predicted["evidence_event_ids"]) & set(gold["evidence_event_ids"]))
            elif verdict == "present":
                fp += 1
            elif gold["verdict"] == "present":
                fn += 1
        precision, recall, score = f1(tp, fp, fn)
        per_signal[signal] = {
            "precision": precision,
            "recall": recall,
            "f1": score,
            "false_alarms": fp,
            "misses": fn,
        }
        evidence_hits += hits
        true_positives += tp
    usage = meta["usage"] if meta else {}
    return {
        "name": results_path.stem,
        "model": meta["model"] if meta else records[0]["model"],
        "reasoning": meta["settings"].get("reasoning") if meta else None,
        "partial": meta is None,
        "run_ids": {r["run_id"] for r in records},
        "traces": len(records),
        "accuracy": correct["all"] / total["all"],
        "held_out_accuracy": correct["held_out"] / total["held_out"] if total["held_out"] else None,
        "macro_f1": sum(s["f1"] for s in per_signal.values()) / len(SIGNALS),
        "evidence_hit_rate": evidence_hits / true_positives if true_positives else None,
        "errors": sum(len(r["errors"]) for r in records),
        "cost_usd": meta["cost_usd"] if meta else None,
        "duration_seconds": meta["duration_seconds"] if meta else None,
        "p50": meta["seconds_per_agent_run"]["p50"] if meta else None,
        "p95": meta["seconds_per_agent_run"]["p95"] if meta else None,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_tokens": usage.get("details", {}).get("reasoning_tokens"),
        "signals": per_signal,
    }


def pct(value):
    return "–" if value is None else f"{value * 100:.0f}%"


def money(value):
    return "–" if value is None else f"${value:.3f}"


def num(value, fmt):
    return "–" if value is None else format(value, fmt)


def bar(value, best, lower_is_better=False):
    """A CSS bar scaled to the best value in the column."""
    if value is None or not best:
        return ""
    width = (best / value if lower_is_better else value / best) * 100 if value else 0
    return f'<div class="bar" style="width:{width:.0f}%"></div>'


def label(r):
    text = r["model"] + (f" ({r['reasoning']} reasoning)" if r["reasoning"] else "")
    return html.escape(text) + (" <i>(partial)</i>" if r["partial"] else "")


def same_traces_table(rows, subset_rows):
    """Every model scored on only the traces all runs have finished."""
    if not subset_rows:
        return ""
    count = subset_rows[0]["traces"]
    heads = "".join(
        f"<th>{s.replace('_', ' ').title()}<br>false alarms / misses</th>" for s in SIGNALS
    )
    body = "".join(
        f"<tr><td>{label(r)}</td><td>{pct(r['accuracy'])}</td>"
        f"<td>{pct(r['held_out_accuracy'])}</td><td>{r['macro_f1']:.2f}</td>"
        + "".join(
            f"<td>{r['signals'][s]['false_alarms']} / {r['signals'][s]['misses']}</td>"
            for s in SIGNALS
        )
        + f"<td>{r['errors']}</td></tr>"
        for r in subset_rows
    )
    partial = ", ".join(label(r) for r in rows if r["partial"])
    return f"""<h2>Head to head on the same {count} traces</h2>
<p class="small">{partial} is still running, so here every model is scored on only the
{count} traces that all runs have finished.</p>
<table><tr><th>Model</th><th>Accuracy</th><th>Held-out accuracy</th><th>Macro F1</th>
{heads}<th>Errors</th></tr>
{body}</table>"""


def render(rows, notes, labels_count, subset_rows):
    best_acc = max(r["accuracy"] for r in rows)
    best_f1 = max(r["macro_f1"] for r in rows)
    costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
    best_cost = min(costs) if costs else None
    times = [r["duration_seconds"] for r in rows if r["duration_seconds"] is not None]
    best_time = min(times) if times else None

    def summary_row(r):
        cost, seconds = r["cost_usd"], r["duration_seconds"]
        per_1k = cost / r["traces"] * 1000 if cost is not None else None
        minutes = seconds / 60 if seconds is not None else None
        return (
            f"<tr><td>{label(r)}</td><td>{r['traces']} / {labels_count}</td>"
            f"<td>{pct(r['accuracy'])}{bar(r['accuracy'], best_acc)}</td>"
            f"<td>{pct(r['held_out_accuracy'])}</td>"
            f"<td>{r['macro_f1']:.2f}{bar(r['macro_f1'], best_f1)}</td>"
            f"<td>{pct(r['evidence_hit_rate'])}</td>"
            f"<td>{r['errors']}</td>"
            f"<td>{money(cost)}{bar(cost, best_cost, True)}</td>"
            f"<td>{money(per_1k)}</td>"
            f"<td>{num(minutes, '.1f')} min{bar(seconds, best_time, True)}</td>"
            f"<td>{num(r['p50'], '.1f')} / {num(r['p95'], '.1f')} s</td>"
            f"<td>{num(r['input_tokens'], ',')} / {num(r['output_tokens'], ',')}</td></tr>"
        )

    summary = "".join(summary_row(r) for r in rows)
    per_signal = "".join(
        f"<tr><td>{label(r)}</td>"
        + "".join(
            f"<td>{r['signals'][s]['f1']:.2f}</td>"
            f"<td>{pct(r['signals'][s]['precision'])} / {pct(r['signals'][s]['recall'])}</td>"
            f"<td>{r['signals'][s]['false_alarms']} / {r['signals'][s]['misses']}</td>"
            for s in SIGNALS
        )
        + "</tr>"
        for r in rows
    )
    signal_heads = "".join(f'<th colspan="3">{s.replace("_", " ").title()}</th>' for s in SIGNALS)
    signal_sub = "<th>F1</th><th>Precision / recall</th><th>False alarms / misses</th>" * 3
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Signal detector model comparison</title>
<style>
body {{ font: 15px/1.5 system-ui, sans-serif; max-width: 1150px; margin: 2rem auto; padding: 0 1rem;
  color: #1f2328; }}
h1 {{ margin-bottom: .2rem; }} .sub {{ color: #656d76; margin-top: 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0 2rem; font-size: 14px; }}
th, td {{ border-bottom: 1px solid #d0d7de; padding: .45rem .6rem; text-align: left;
  vertical-align: top; }}
th {{ background: #f6f8fa; }}
.bar {{ height: 4px; background: #2f81f7; border-radius: 2px; margin-top: 3px; }}
.notes {{ background: #f6f8fa; border-left: 4px solid #2f81f7; padding: .5rem 1.2rem; }}
.small {{ color: #656d76; font-size: 13px; }}
</style></head><body>
<h1>Signal detector: model comparison</h1>
<p class="sub">Same prompts, same {labels_count} synthetic support traces, 3 detectors per trace
({labels_count * 3} classifications per model). Scored against the human labels.</p>
{f'<div class="notes">{notes}</div>' if notes else ""}
<h2>Summary</h2>
<table><tr><th>Model</th><th>Traces</th><th>Accuracy</th><th>Held-out accuracy</th>
<th>Macro F1</th><th>Evidence hit</th><th>Errors</th><th>Cost (run)</th><th>Cost / 1k traces</th>
<th>Wall time</th><th>Per call p50 / p95</th><th>Tokens in / out</th></tr>
{summary}</table>
{same_traces_table(rows, subset_rows)}
<h2>Per signal</h2>
<table><tr><th rowspan="2">Model</th>{signal_heads}</tr><tr>{signal_sub}</tr>
{per_signal}</table>
<p class="small"><b>Accuracy</b>: the share of verdicts (present / absent / insufficient
evidence) that exactly match the label; an execution error counts as wrong. <b>Held-out</b>: the
same measure on the frozen held-out runs only. <b>F1, precision, recall</b>: detecting
<i>present</i> against everything else. <b>Evidence hit</b>: of the correctly detected
<i>present</i> signals, the share that cite at least one event the reviewer cited. A
<i>partial</i> run is still going: it is scored on the traces finished so far and has no cost
or time yet. Cost uses list prices per 1M tokens (Nebius prices in classify.py, OpenAI via
genai-prices). Wall time is the sequential run of 3 agent calls per trace. The prompts were
not tuned against these labels.</p>
</body></html>
"""


def main():
    parser = argparse.ArgumentParser(description="Compare classify.py runs in an HTML report.")
    parser.add_argument("results", nargs="+", type=Path, help="results JSONL files")
    parser.add_argument("--output", required=True, type=Path, help="HTML report path")
    parser.add_argument("--notes", type=Path, help="HTML snippet shown above the tables")
    args = parser.parse_args()

    labels = {label["run_id"]: label for label in load_jsonl(DATA / "labels.jsonl")}
    held_out = set(json.loads((DATA / "split.json").read_text(encoding="utf-8"))["held_out"])
    rows = [score_run(path, labels, held_out) for path in args.results]
    subset_rows = []
    if any(r["partial"] for r in rows):
        common = set.intersection(*(r["run_ids"] for r in rows))
        subset_rows = [score_run(path, labels, held_out, common) for path in args.results]
    notes = args.notes.read_text(encoding="utf-8") if args.notes else ""
    args.output.write_text(render(rows, notes, len(labels), subset_rows), encoding="utf-8")
    for heading, group in [("all traces", rows), ("same traces", subset_rows)]:
        if group:
            print(f"-- {heading}")
        for r in group:
            print(
                f"{r['name']:<28} n {r['traces']:>2}  acc {pct(r['accuracy']):>4}"
                f"  held-out {pct(r['held_out_accuracy']):>4}  macro-F1 {r['macro_f1']:.2f}"
                f"  errors {r['errors']:>2}  cost {money(r['cost_usd'])}"
            )
    print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
