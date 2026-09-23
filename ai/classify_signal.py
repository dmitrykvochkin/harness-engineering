"""Classify traces for user-created signals and store the findings in Supabase.

Reads definitions (title + prompt) from public.signal_definitions, runs one Pydantic AI
detector per definition over every trace, and upserts one public.signals row per trace
with signal_type = the definition's slug.

    python classify_signal.py                 # definitions with no findings for --model yet
    python classify_signal.py refund-promises # specific definitions, by slug (re-runs them)
    python classify_signal.py --all           # every definition

Uses the same shared instructions, model input and evidence check as classify.py. Needs
SUPABASE_URL, SUPABASE_SECRET_KEY and the model's API key (env or ai/.env), and the
signals_for_definitions migration.
"""

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from classify import (
    DEFAULT_MODEL,
    ENV_FILE,
    MAX_TOKENS,
    OUTPUT_RETRIES,
    REQUEST_TIMEOUT,
    SHARED_INSTRUCTIONS,
    InputError,
    SignalResult,
    build_model,
    build_model_input,
    describe_error,
    evidence_validator,
    load_env_file,
    load_traces,
)
from postgrest.exceptions import APIError
from pydantic_ai import Agent

from harness_ai.db.rows import DefinitionSignalRow, DetectorVerdict
from harness_ai.db.upload import connect

DEFAULT_INPUT = Path(__file__).parent.parent / "data" / "conversations" / "traces.jsonl"
DEFINITION_COLUMNS = "id,title,prompt,slug"
VERDICTS = [v.value for v in DetectorVerdict]


def fetch_definitions(client, slugs, include_all, model_name):
    query = client.table("signal_definitions").select(DEFINITION_COLUMNS).order("created_at")
    if slugs:
        query = query.in_("slug", slugs)
    definitions = query.execute().data or []
    if slugs:
        missing = sorted(set(slugs) - {d["slug"] for d in definitions})
        if missing:
            raise InputError(f"no signal definition with slug: {', '.join(missing)}")
        return definitions
    if include_all:
        return definitions
    return [d for d in definitions if not has_findings(client, d["id"], model_name)]


def has_findings(client, definition_id, model_name):
    rows = (
        client.table("signals")
        .select("id")
        .eq("signal_definition_id", definition_id)
        .eq("detector_version", model_name)
        .limit(1)
        .execute()
    )
    return bool(rows.data)


def instructions_for(definition):
    return (
        f"{SHARED_INSTRUCTIONS}\n\n"
        f"Your signal: {definition['title'].upper()}.\n\n{definition['prompt']}"
    )


def build_agent(model, model_settings, definition):
    agent = Agent(
        model,
        output_type=SignalResult,
        deps_type=dict,
        instructions=instructions_for(definition),
        retries={"output": OUTPUT_RETRIES},
        model_settings=model_settings,
    )
    agent.output_validator(evidence_validator(definition["slug"]))
    return agent


def finding_row(definition, run_id, model_name, output, error):
    common = {
        "run_id": run_id,
        "signal_type": definition["slug"],
        "signal_definition_id": definition["id"],
        "detector_version": model_name,
    }
    if output is None:
        return DefinitionSignalRow(
            **common, verdict=DetectorVerdict.ERROR, explanation=error or "Detector failed"
        )
    return DefinitionSignalRow(
        **common,
        verdict=DetectorVerdict(output.verdict),
        explanation=output.reason,
        evidence_event_ids=output.evidence_event_ids,
    )


async def classify_one(agent, trace, semaphore):
    model_input = build_model_input(trace)
    async with semaphore:
        try:
            result = await agent.run(json.dumps(model_input, ensure_ascii=False), deps=model_input)
            return trace["run_id"], result.output, None
        except Exception as e:
            return trace["run_id"], None, describe_error(e)


def remove_stale(client, definition, model_name, run_ids):
    """Drop this definition's findings for runs that are no longer in the input."""
    stale = (
        client.table("signals")
        .select("run_id")
        .eq("signal_definition_id", definition["id"])
        .eq("detector_version", model_name)
        .not_.in_("run_id", sorted(run_ids))
        .execute()
    )
    stale_ids = sorted({row["run_id"] for row in stale.data or []})
    if stale_ids:
        client.table("signals").delete().eq("signal_definition_id", definition["id"]).eq(
            "detector_version", model_name
        ).in_("run_id", stale_ids).execute()
        print(f"  removed {len(stale_ids)} findings for runs no longer in the input")


async def classify_definition(client, agent, definition, traces, args):
    counts = Counter()
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [classify_one(agent, trace, semaphore) for trace in traces]
    for next_result in asyncio.as_completed(tasks):
        run_id, output, error = await next_result
        row = finding_row(definition, run_id, args.model, output, error)
        counts[row.verdict.value] += 1
        detail = f" ({error})" if error else ""
        print(f"  {run_id}: {row.verdict.value}{detail}", flush=True)
        if not args.dry_run:
            client.table("signals").upsert(
                row.model_dump(mode="json", exclude={"id"}),
                on_conflict="run_id,signal_type,detector_version",
            ).execute()
    if not args.dry_run and args.limit is None:
        remove_stale(client, definition, args.model, {t["run_id"] for t in traces})
    return counts


async def run(client, definitions, traces, args):
    model = build_model(args.model)
    model_settings = {"max_tokens": MAX_TOKENS, "timeout": REQUEST_TIMEOUT}
    if args.reasoning:
        model_settings["thinking"] = args.reasoning
    totals = {}
    for definition in definitions:
        print(f"\n{definition['slug']} ({definition['title']}): {len(traces)} traces")
        agent = build_agent(model, model_settings, definition)
        totals[definition["slug"]] = await classify_definition(
            client, agent, definition, traces, args
        )
    return totals


def print_summary(totals, args):
    width = max(len(slug) for slug in totals) + 2
    print("\n" + f"{'signal':<{width}}" + "".join(f"{v:>23}" for v in VERDICTS))
    for slug, counts in totals.items():
        print(f"{slug:<{width}}" + "".join(f"{counts[v]:>23}" for v in VERDICTS))
    if args.dry_run:
        print("\nDry run: nothing was written to Supabase.")
    else:
        print(f"\nFindings upserted into public.signals (detector_version={args.model}).")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slugs", nargs="*", help="definition slugs to (re)classify")
    parser.add_argument("--all", action="store_true", help="classify every definition")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="traces JSONL file")
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"Pydantic AI model (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--reasoning",
        choices=["minimal", "low", "medium", "high", "xhigh"],
        help="reasoning effort for models that support it (default: the model's own)",
    )
    parser.add_argument(
        "--concurrency", type=int, default=4, help="traces classified at once (default: 4)"
    )
    parser.add_argument("--limit", type=int, help="only the first N traces (skips pruning)")
    parser.add_argument(
        "--dry-run", action="store_true", help="classify and print, but write nothing"
    )
    args = parser.parse_args()
    if args.slugs and args.all:
        parser.error("pass slugs or --all, not both")
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    load_env_file(ENV_FILE)

    try:
        traces = load_traces(args.input)[: args.limit]
        client = connect()
        definitions = fetch_definitions(client, args.slugs, args.all, args.model)
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not definitions:
        print(f"Every signal definition already has findings for {args.model}.")
        print("Pass slugs or --all to re-run.")
        return 0

    try:
        totals = asyncio.run(run(client, definitions, traces, args))
    except APIError as e:
        print(
            f"error: {e.message}\nApply supabase/migrations (including "
            "signals_for_definitions) and upload the dataset with harness-upload first.",
            file=sys.stderr,
        )
        return 2

    print_summary(totals, args)
    return 1 if any(counts["error"] for counts in totals.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
