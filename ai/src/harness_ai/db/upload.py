"""Upload the conversation dataset into Supabase Postgres.

    uv run harness-upload [conversations_dir] [--dry-run]

Reads `traces.jsonl`, `labels.jsonl` and `split.json` (default
`data/conversations/`), converts them to rows and upserts them with the
secret key. Re-running is safe: rows are upserted by primary key and events
or signal labels that no longer exist in the files are deleted per run.
Detector output in `signals` / `issues` is never touched.

Needs SUPABASE_URL and SUPABASE_SECRET_KEY, read from the environment or
from `ai/.env`. The schema comes from supabase/migrations/ and must be
applied first.
"""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from dotenv import load_dotenv
from postgrest.exceptions import APIError
from pydantic import BaseModel
from supabase import Client, create_client

from harness_ai.conversations import load_traces
from harness_ai.dataset.build import DEFAULT_OUT, validate
from harness_ai.dataset.labels import RunLabels, Split
from harness_ai.db.rows import dataset_rows

BATCH_SIZE = 250
AI_ROOT = Path(__file__).resolve().parents[3]


def load_dataset(directory: Path) -> tuple[list, list[RunLabels], Split]:
    traces = load_traces(directory / "traces.jsonl")
    labels = [
        RunLabels.model_validate_json(line)
        for line in (directory / "labels.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    split = Split.model_validate_json((directory / "split.json").read_text(encoding="utf-8"))
    return traces, labels, split


def _payload(rows: Sequence[BaseModel]) -> list[dict]:
    # PostgREST bulk writes require every object in a batch to have the same keys.
    return [row.model_dump(mode="json") for row in rows]


def _upsert(client: Client, table: str, rows: Sequence[BaseModel], on_conflict: str) -> None:
    payload = _payload(rows)
    for start in range(0, len(payload), BATCH_SIZE):
        batch = payload[start : start + BATCH_SIZE]
        client.table(table).upsert(batch, on_conflict=on_conflict).execute()
    print(f"  {table}: {len(payload)} rows")


def connect() -> Client:
    load_dotenv(AI_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SECRET_KEY must be set (env or ai/.env)")
    return create_client(url, key)


def upload(client: Client, directory: Path) -> None:
    traces, labels, split = load_dataset(directory)
    errors = validate(traces, labels, split)
    if errors:
        raise SystemExit("refusing to upload an invalid dataset:\n  " + "\n  ".join(errors))

    dataset, runs, events, run_labels, signal_labels = dataset_rows(traces, labels, split)
    print(f"uploading {dataset.name} from {directory}")

    _upsert(client, "datasets", [dataset], "name")
    _upsert(client, "runs", runs, "run_id")
    _upsert(client, "events", events, "id")
    _upsert(client, "run_labels", run_labels, "run_id")
    _upsert(client, "signal_labels", signal_labels, "run_id,signal")

    for run in runs:
        keep = [e.id for e in events if e.run_id == run.run_id]
        client.table("events").delete().eq("run_id", run.run_id).not_.in_("id", keep).execute()

    stale = (
        client.table("runs")
        .select("run_id")
        .eq("dataset", dataset.name)
        .not_.in_("run_id", [r.run_id for r in runs])
        .execute()
    )
    if stale.data:
        stale_ids = [row["run_id"] for row in stale.data]
        client.table("runs").delete().in_("run_id", stale_ids).execute()
        print(f"  removed {len(stale_ids)} runs no longer in the dataset")
    print("done")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", nargs="?", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and count rows without connecting"
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        traces, labels, split = load_dataset(args.directory)
        errors = validate(traces, labels, split)
        if errors:
            raise SystemExit("invalid dataset:\n  " + "\n  ".join(errors))
        dataset, *tables = dataset_rows(traces, labels, split)
        names = ["runs", "events", "run_labels", "signal_labels"]
        counts = ", ".join(f"{n}={len(t)}" for n, t in zip(names, tables, strict=True))
        print(f"{dataset.name}: {counts}")
        return

    try:
        upload(connect(), args.directory)
    except APIError as exc:
        if exc.code in {"PGRST205", "42P01"}:
            print(
                f"error: {exc.message}\nApply the schema first: run the SQL files in "
                "supabase/migrations/ in the Supabase SQL editor, or `supabase db push`.",
                file=sys.stderr,
            )
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
