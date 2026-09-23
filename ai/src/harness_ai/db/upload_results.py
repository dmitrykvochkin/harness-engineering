"""Upload classifier output into the `signals` table.

    uv run harness-upload-results [results.jsonl] [--dry-run]

Reads one JSONL record per run (the `classify.py` output) and upserts three
signal rows per run. Re-running replaces rows for the same run, signal, and
model, and removes rows for that model whose runs are no longer in the file.
Needs SUPABASE_URL and SUPABASE_SECRET_KEY. Apply supabase/migrations first,
including the verdict `error` migration.
"""

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from postgrest.exceptions import APIError

from harness_ai.db.results import load_result_rows
from harness_ai.db.rows import SignalRow
from harness_ai.db.upload import AI_ROOT, connect

DEFAULT_RESULTS = AI_ROOT / "results.jsonl"
BATCH_SIZE = 250


def _payload(rows: Sequence[SignalRow]) -> list[dict]:
    return [row.model_dump(mode="json", exclude={"id"}) for row in rows]


def upload_results(client, path: Path) -> None:
    rows = load_result_rows(path)
    if not rows:
        raise SystemExit(f"no records in {path}")

    print(f"uploading {len(rows)} signal rows from {path}")
    payload = _payload(rows)
    for start in range(0, len(payload), BATCH_SIZE):
        client.table("signals").upsert(
            payload[start : start + BATCH_SIZE],
            on_conflict="run_id,signal_type,detector_version",
        ).execute()

    by_model: dict[str, set[str]] = {}
    for row in rows:
        by_model.setdefault(row.detector_version, set()).add(row.run_id)
    for model, run_ids in by_model.items():
        stale = (
            client.table("signals")
            .select("run_id")
            .eq("detector_version", model)
            .not_.in_("run_id", sorted(run_ids))
            .execute()
        )
        stale_ids = sorted({item["run_id"] for item in stale.data or []})
        if stale_ids:
            client.table("signals").delete().eq("detector_version", model).in_(
                "run_id", stale_ids
            ).execute()
            print(f"  removed {len(stale_ids)} runs no longer in {path} for {model}")
    print("done")


def _print_dry_run(path: Path) -> None:
    rows = load_result_rows(path)
    counts: Counter[str] = Counter(row.verdict.value for row in rows)
    runs = len({row.run_id for row in rows})
    names = ("present", "absent", "insufficient_evidence", "error")
    summary = ", ".join(f"{name}={counts[name]}" for name in names)
    print(f"{path}: runs={runs} signals={len(rows)} {summary}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--dry-run", action="store_true", help="count rows without connecting")
    args = parser.parse_args(argv)

    if not args.path.is_file():
        raise SystemExit(f"results file not found: {args.path}")

    if args.dry_run:
        try:
            _print_dry_run(args.path)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        return

    try:
        upload_results(connect(), args.path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    except APIError as exc:
        if exc.code in {"PGRST205", "42P01", "23514"}:
            print(
                f"error: {exc.message}\nApply supabase/migrations (including the "
                "verdict=error migration) before uploading results.",
                file=sys.stderr,
            )
            sys.exit(1)
        raise


if __name__ == "__main__":
    main()
