"""Render the authored scenarios into the committed dataset files.

    uv run python -m harness_ai.dataset.build [out_dir]

Writes `traces.jsonl`, `labels.jsonl` and `split.json` (default
`data/conversations/` at the repo root). Output is deterministic: IDs,
timings and token counts come from seeded RNGs, so rebuilding produces
byte-identical files unless a scenario changes.

Traces are shaped like an LLM-observability export (Langfuse trace plus
observations, Datadog LLM Obs spans): OTel-style trace/span IDs, per-span
latency, model and token usage on generations, and tool spans nested under
the generation that requested them. Labels, scenario keys and primary
families never appear in a trace.
"""

import hashlib
import json
import random
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from harness_ai.conversations.models import Event, Trace, Usage
from harness_ai.dataset.authoring import POLICIES, POLICY_VERSION, TOOL_SEMANTICS, Scenario
from harness_ai.dataset.labels import RunLabels, Signal, Split, Verdict
from harness_ai.dataset.scenarios_forgetting import SCENARIOS as FORGETTING
from harness_ai.dataset.scenarios_frustration import SCENARIOS as FRUSTRATION
from harness_ai.dataset.scenarios_task_failure import SCENARIOS as TASK_FAILURE

DATASET_NAME = "kettl-support-synthetic-v1"
SEED = 20260923
REVIEWED_AT = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)
FROZEN_AT = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)
DEFAULT_OUT = Path(__file__).resolve().parents[4] / "data" / "conversations"

SCENARIOS: list[Scenario] = [*FRUSTRATION, *TASK_FAILURE, *FORGETTING]

# Per family: two signal-present cases, one absent lookalike, one abstention.
HELD_OUT: frozenset[str] = frozenset(
    {
        "uf-present-sarcasm-after-link-dump",
        "uf-present-unrequested-cancellation",
        "uf-absent-insults-the-product",
        "uf-unclear-ambiguous-target",
        "tf-present-address-update-rejected",
        "tf-present-lookup-loop-unresolved",
        "tf-absent-cancellation-refused-after-shipping",
        "tf-unclear-abandoned-before-resolution",
        "fg-present-drops-dutch-preference",
        "fg-present-forgets-stated-return-reason",
        "fg-absent-resolves-conflicting-order-numbers",
        "fg-unclear-mid-trace-gap",
    }
)

# Start times pinned where the conversation content refers to "today" or a clock time.
START_OVERRIDES: dict[str, datetime] = {
    "uf-absent-neutral-correction": datetime(2026, 9, 12, 9, 58, 12, tzinfo=UTC),
    "uf-absent-praise-after-damage": datetime(2026, 9, 12, 11, 21, 40, tzinfo=UTC),
    "uf-present-effort-complaint-despite-refund": datetime(2026, 9, 13, 8, 31, 5, tzinfo=UTC),
    "tf-present-refund-rejected-card-expired": datetime(2026, 9, 13, 14, 2, 51, tzinfo=UTC),
    "tf-present-refund-rejected-fraud-hold": datetime(2026, 9, 13, 9, 47, 30, tzinfo=UTC),
    "tf-absent-cancellation-refused-after-shipping": datetime(2026, 9, 13, 10, 40, 9, tzinfo=UTC),
    "tf-unclear-missing-refund-result": datetime(2026, 9, 13, 9, 10, 44, tzinfo=UTC),
    "fg-present-reverts-to-superseded-address": datetime(2026, 9, 12, 13, 37, 2, tzinfo=UTC),
    "fg-present-ignores-availability-window-corrected": datetime(
        2026, 9, 14, 7, 55, 18, tzinfo=UTC
    ),
}

# agent version -> (provider, model, USD per 1M input tokens, USD per 1M output tokens, release)
MODELS: dict[str, tuple[str, str, float, float, str]] = {
    "support-agent@1.4.2": ("openai", "gpt-4o-2024-08-06", 2.5, 10.0, "2026.08.3"),
    "support-agent@1.5.0": ("openai", "gpt-4.1-2025-04-14", 2.0, 8.0, "2026.09.1"),
    "support-agent@1.5.1": ("openai", "gpt-4.1-2025-04-14", 2.0, 8.0, "2026.09.2"),
}

# Tool schemas and policy excerpts sent with every generation.
PROMPT_OVERHEAD_TOKENS = 1240
READ_TOOLS = {
    "lookup_order",
    "lookup_orders_by_email",
    "get_customer_profile",
    "get_tracking",
    "check_refund_eligibility",
}


def _tokens(text: str) -> int:
    return max(1, round(len(text) / 3.8))


def _hex(rng: random.Random, n: int) -> str:
    return f"{rng.getrandbits(n * 4):0{n}x}"


def _ms(dt: datetime) -> datetime:
    return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha1(value.encode()).hexdigest()[:12]}"


def _usage(input_tokens: int, output_tokens: int, version: str) -> Usage:
    _, _, price_in, price_out, _ = MODELS[version]
    cost = input_tokens / 1e6 * price_in + output_tokens / 1e6 * price_out
    return Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=round(cost, 6),
    )


def render(scenario: Scenario, run_id: str) -> tuple[Trace, dict[str, str]]:
    """Render one scenario into a trace and return it with its tag -> event-id map."""
    rng = random.Random(f"{SEED}:{scenario.key}")
    version = scenario.agent_version
    provider, model_name, *_, release = MODELS[version]
    run_num = run_id.split("-")[1]

    start = START_OVERRIDES.get(scenario.key) or datetime(
        2026, 9, 12, rng.randint(9, 19), rng.randint(0, 59), rng.randint(0, 59), tzinfo=UTC
    )
    start = start.replace(microsecond=rng.randint(0, 999) * 1000)
    clock = start

    events: list[Event] = []
    tags: dict[str, str] = {}
    history_tokens = PROMPT_OVERHEAD_TOKENS
    generation: Event | None = None
    call: Event | None = None
    root_span = _hex(rng, 16)
    turns = scenario.turns

    def next_id() -> str:
        return f"evt-{run_num}-{len(events) + 1:03d}"

    def generate(content: str, finish_reason: str) -> Event:
        nonlocal clock, history_tokens
        out = _tokens(content) if content else rng.randint(12, 30)
        latency = 420 + out * 21 + rng.randint(0, 450)
        ts = _ms(clock + timedelta(milliseconds=rng.randint(20, 60)))
        end = ts + timedelta(milliseconds=latency)
        event = Event(
            id=next_id(),
            span_id=_hex(rng, 16),
            parent_span_id=root_span,
            type="generation",
            role="agent",
            name="agent.generation",
            timestamp=ts,
            end_timestamp=end,
            latency_ms=latency,
            content=content,
            model=model_name,
            usage=_usage(history_tokens, out, version),
            finish_reason=finish_reason,
            tool_call_ids=[],
        )
        events.append(event)
        history_tokens += out
        clock = end
        return event

    for i, turn in enumerate(turns):
        following = turns[i + 1].kind if i + 1 < len(turns) else None

        if turn.kind == "system":
            event = Event(
                id=next_id(),
                span_id=_hex(rng, 16),
                parent_span_id=root_span,
                type="system_message",
                role="system",
                name="system_prompt",
                timestamp=_ms(clock),
                content=turn.content,
            )
            events.append(event)
            history_tokens += _tokens(turn.content)
            clock += timedelta(milliseconds=5)

        elif turn.kind == "user":
            if turn.gap_s is not None:
                gap = turn.gap_s
            elif not events or events[-1].type == "system_message":
                gap = rng.uniform(0.2, 0.6)
            elif scenario.channel == "email":
                gap = rng.uniform(900, 5400)
            else:
                gap = 8 + len(turn.content) / 4 + rng.uniform(5, 30)
            clock += timedelta(seconds=gap)
            event = Event(
                id=next_id(),
                span_id=_hex(rng, 16),
                parent_span_id=root_span,
                type="user_message",
                role="user",
                name="user.message",
                timestamp=_ms(clock),
                content=turn.content,
            )
            events.append(event)
            history_tokens += _tokens(turn.content)
            generation = None

        elif turn.kind == "agent":
            event = generate(turn.content, "tool_calls" if following == "tool_call" else "stop")
            generation = event if following == "tool_call" else None

        elif turn.kind == "tool_call":
            if generation is None:
                generation = generate("", "tool_calls")
            args = json.dumps(turn.tool_arguments, ensure_ascii=False)
            arg_tokens = _tokens(args) + 8
            generation.usage = _usage(
                generation.usage.input_tokens,
                generation.usage.output_tokens + arg_tokens,
                version,
            )
            has_result = following == "tool_result"
            base = (60, 350) if turn.tool_name in READ_TOOLS else (250, 1400)
            latency = rng.randint(*base)
            ts = _ms(clock + timedelta(milliseconds=rng.randint(5, 25)))
            event = Event(
                id=next_id(),
                span_id=_hex(rng, 16),
                parent_span_id=generation.span_id,
                type="tool_call",
                role="agent",
                name=f"tool.{turn.tool_name}",
                timestamp=ts,
                end_timestamp=ts + timedelta(milliseconds=latency) if has_result else None,
                latency_ms=latency if has_result else None,
                content=args,
                tool_name=turn.tool_name,
                tool_arguments=turn.tool_arguments,
            )
            events.append(event)
            generation.tool_call_ids.append(event.id)
            history_tokens += arg_tokens
            call = event
            clock = event.end_timestamp or ts
            if not has_result:
                generation = None

        elif turn.kind == "tool_result":
            if call is None:
                raise ValueError(f"{scenario.key}: tool_result without a preceding tool_call")
            content = json.dumps(turn.tool_result, ensure_ascii=False)
            event = Event(
                id=next_id(),
                span_id=_hex(rng, 16),
                parent_span_id=call.span_id,
                type="tool_result",
                role="tool",
                name=f"tool.{call.tool_name}.result",
                timestamp=call.end_timestamp,
                content=content,
                level=turn.level,
                status=turn.status,
                tool_name=call.tool_name,
                tool_call_id=call.id,
                tool_result=turn.tool_result,
            )
            events.append(event)
            history_tokens += _tokens(content)
            call = None
            generation = None
            clock += timedelta(milliseconds=rng.randint(5, 20))

        else:
            raise ValueError(f"{scenario.key}: unknown turn kind {turn.kind!r}")

        if turn.tag:
            if turn.tag in tags:
                raise ValueError(f"{scenario.key}: duplicate turn tag {turn.tag!r}")
            tags[turn.tag] = events[-1].id

    end_time = max(e.end_timestamp or e.timestamp for e in events)
    gens = [e for e in events if e.usage]
    in_tokens = sum(e.usage.input_tokens for e in gens)
    out_tokens = sum(e.usage.output_tokens for e in gens)

    session_id = _stable_id("sess", f"{scenario.key}:{scenario.customer}")
    metadata: dict = {
        "channel": scenario.channel,
        "locale": scenario.locale,
        "customer_tier": scenario.customer_tier,
        "policy_version": POLICY_VERSION,
        "policies": {pid: POLICIES[pid] for pid in scenario.policies},
        "tool_semantics": TOOL_SEMANTICS,
        "capture": scenario.capture or {"status": "complete"},
    }
    if scenario.session_continues_from:
        metadata["session"] = {
            "earlier_traces_in_session": 1,
            "earlier_traces_exported": False,
            "note": "Earlier traces in this session fall outside the export window.",
        }

    user_seed = scenario.customer if scenario.customer != "unknown" else f"anon:{scenario.key}"
    trace = Trace(
        run_id=run_id,
        trace_id=_hex(rng, 32),
        session_id=session_id,
        user_id=_stable_id("usr", user_seed),
        agent_version=version,
        release=release,
        environment="production",
        synthetic=True,
        start_time=_ms(start),
        end_time=end_time,
        duration_ms=int((end_time - start).total_seconds() * 1000),
        tags=[
            f"channel:{scenario.channel}",
            f"locale:{scenario.locale}",
            f"topic:{scenario.topic}",
            version,
            "synthetic",
        ],
        metadata=metadata,
        model={"provider": provider, "name": model_name},
        usage=_usage(in_tokens, out_tokens, version),
        events=events,
    )
    return trace, tags


def build() -> tuple[list[Trace], list[RunLabels], Split]:
    """Render every scenario, shuffle run order, and resolve labels to event IDs."""
    keys = [s.key for s in SCENARIOS]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate scenario keys")

    ordered = list(SCENARIOS)
    random.Random(SEED).shuffle(ordered)

    traces: list[Trace] = []
    labels: list[RunLabels] = []
    for n, scenario in enumerate(ordered, start=1):
        run_id = f"run-{n:04d}"
        trace, tags = render(scenario, run_id)
        if set(scenario.labels) != set(Signal):
            raise ValueError(f"{scenario.key}: must label all three signals")
        signals = {sig: scenario.labels[sig].resolve(tags, scenario.key) for sig in Signal}
        traces.append(trace)
        labels.append(
            RunLabels(
                run_id=run_id,
                scenario_key=scenario.key,
                primary_family=scenario.primary,
                primary_verdict=signals[scenario.primary].verdict,
                task_expectation=scenario.requested_outcome,
                reviewed_by="dataset-author (synthetic; self-reviewed)",
                reviewed_at=REVIEWED_AT,
                signals=signals,
                notes=scenario.notes,
            )
        )

    held_out = sorted(lb.run_id for lb in labels if lb.scenario_key in HELD_OUT)
    development = sorted(lb.run_id for lb in labels if lb.scenario_key not in HELD_OUT)
    split = Split(
        dataset=DATASET_NAME,
        frozen_at=FROZEN_AT,
        rule=(
            "Held-out: per primary family, two signal-present runs, one absent lookalike and one "
            "insufficient-evidence run, chosen by scenario variant. Do not inspect or tune on "
            "held-out runs."
        ),
        counts={"development": len(development), "held_out": len(held_out)},
        development=development,
        held_out=held_out,
    )
    return traces, labels, split


def validate(traces: list[Trace], labels: list[RunLabels], split: Split) -> list[str]:
    """Check the dataset against the PRD's structural and labelling requirements."""
    errors: list[str] = []
    by_run = {t.run_id: t for t in traces}
    label_by_run = {lb.run_id: lb for lb in labels}

    if len(traces) != 36 or len(by_run) != 36:
        errors.append(f"expected 36 unique traces, got {len(traces)}")
    if set(by_run) != set(label_by_run):
        errors.append("trace and label run IDs differ")

    for trace in traces:
        ids = [e.id for e in trace.events]
        if len(set(ids)) != len(ids):
            errors.append(f"{trace.run_id}: duplicate event IDs")
        if not trace.synthetic:
            errors.append(f"{trace.run_id}: not marked synthetic")
        stamps = [e.timestamp for e in trace.events]
        if stamps != sorted(stamps):
            errors.append(f"{trace.run_id}: events are not in timestamp order")
        calls = {e.id: e for e in trace.events if e.type == "tool_call"}
        for e in trace.events:
            if e.type == "tool_result":
                linked = calls.get(e.tool_call_id or "")
                if linked is None or linked.tool_name != e.tool_name:
                    errors.append(f"{trace.run_id}/{e.id}: tool_result not linked to its call")
        blob = trace.model_dump_json()
        run_label = label_by_run.get(trace.run_id)
        leaks = ["scenario_key", "primary_family", "grouping_pattern", "verdict"]
        if run_label:
            leaks.append(run_label.scenario_key)
        for leak in leaks:
            if leak in blob:
                errors.append(f"{trace.run_id}: trace leaks label metadata ({leak})")

    for lb in labels:
        trace = by_run.get(lb.run_id)
        if trace is None:
            continue
        position = {e.id: i for i, e in enumerate(trace.events)}
        for sig, sl in lb.signals.items():
            where = f"{lb.run_id}/{sig}"
            missing = [x for x in sl.evidence_event_ids if x not in position]
            if missing:
                errors.append(f"{where}: evidence cites unknown events {missing}")
            if not sl.evidence_event_ids:
                errors.append(f"{where}: no evidence cited")
            if sl.verdict == Verdict.PRESENT and not sl.grouping_pattern:
                errors.append(f"{where}: present verdict without grouping pattern")
            if sig == Signal.FORGETTING and sl.verdict == Verdict.PRESENT:
                if not sl.earlier_event_ids or not sl.later_event_ids:
                    errors.append(f"{where}: forgetting needs earlier and later events")
                elif max(position[x] for x in sl.earlier_event_ids) >= min(
                    position[x] for x in sl.later_event_ids
                ):
                    errors.append(f"{where}: earlier context does not precede later behaviour")

    table = Counter((lb.primary_family, lb.primary_verdict) for lb in labels)
    for family in Signal:
        for verdict, want in (
            (Verdict.PRESENT, 6),
            (Verdict.ABSENT, 4),
            (Verdict.INSUFFICIENT_EVIDENCE, 2),
        ):
            if table[(family, verdict)] != want:
                errors.append(f"{family}/{verdict}: {table[(family, verdict)]} runs, want {want}")
        seen = {lb.signals[family].verdict for lb in labels}
        if seen != set(Verdict):
            errors.append(f"{family}: not all three verdicts occur")

    def present_count(lb: RunLabels) -> int:
        return sum(sl.verdict == Verdict.PRESENT for sl in lb.signals.values())

    overlaps = {lb.run_id for lb in labels if present_count(lb) >= 2}
    if len(overlaps) < 6:
        errors.append(f"only {len(overlaps)} overlapping runs, need 6")
    all_absent = [
        lb for lb in labels if all(s.verdict == Verdict.ABSENT for s in lb.signals.values())
    ]
    if len(all_absent) < 3:
        errors.append(f"only {len(all_absent)} fully successful runs, need 3")

    if len(split.development) != 24 or len(split.held_out) != 12:
        errors.append("split must be 24 development / 12 held-out")
    if set(split.development) & set(split.held_out):
        errors.append("split sets overlap")
    held = Counter(
        (label_by_run[r].primary_family, label_by_run[r].primary_verdict) for r in split.held_out
    )
    for family in Signal:
        for verdict, want in (
            (Verdict.PRESENT, 2),
            (Verdict.ABSENT, 1),
            (Verdict.INSUFFICIENT_EVIDENCE, 1),
        ):
            if held[(family, verdict)] != want:
                errors.append(
                    f"held-out {family}/{verdict}: {held[(family, verdict)]}, want {want}"
                )
    if not overlaps & set(split.held_out) or not overlaps & set(split.development):
        errors.append("overlapping runs must appear in both splits")

    return errors


def write(out_dir: Path) -> None:
    traces, labels, split = build()
    errors = validate(traces, labels, split)
    if errors:
        raise SystemExit("dataset validation failed:\n  " + "\n  ".join(errors))

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "traces.jsonl").write_text(
        "".join(t.model_dump_json(exclude_none=True) + "\n" for t in traces), encoding="utf-8"
    )
    (out_dir / "labels.jsonl").write_text(
        "".join(lb.model_dump_json(exclude_none=True) + "\n" for lb in labels), encoding="utf-8"
    )
    (out_dir / "split.json").write_text(split.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(traces)} traces, {len(labels)} labels and split.json to {out_dir}")


if __name__ == "__main__":
    write(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT)
