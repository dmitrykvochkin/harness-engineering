"""Dataset -> Supabase row conversion, checked offline against the migration's shape."""

import re
from pathlib import Path

from harness_ai.db.rows import (
    EventRow,
    RunLabelRow,
    RunRow,
    SignalLabelRow,
    dataset_rows,
)
from harness_ai.db.upload import DEFAULT_OUT, _payload, load_dataset

MIGRATION = (
    Path(__file__).resolve().parents[2] / "supabase/migrations/20260923100000_traces_and_labels.sql"
)


def _columns(table: str) -> set[str]:
    sql = MIGRATION.read_text(encoding="utf-8")
    body = re.search(rf"create table public\.{table} \((.*?)\n\);", sql, re.S).group(1)
    names = set()
    for line in body.splitlines():
        match = re.match(r'\s+"?([a-z_]+)"?\s+[a-z]', line)
        if match and match.group(1) not in {"unique", "primary"}:
            names.add(match.group(1))
    return names


def test_row_models_match_migration_columns():
    for model, table in [
        (RunRow, "runs"),
        (EventRow, "events"),
        (RunLabelRow, "run_labels"),
        (SignalLabelRow, "signal_labels"),
    ]:
        assert set(model.model_fields) <= _columns(table), table


def test_dataset_rows_cover_everything():
    traces, labels, split = load_dataset(Path(DEFAULT_OUT))
    dataset, runs, events, run_labels, signal_labels = dataset_rows(traces, labels, split)

    assert dataset.name == split.dataset
    assert len(runs) == len(run_labels) == 36
    assert len(events) == sum(len(t.events) for t in traces)
    assert len(signal_labels) == 36 * 3
    assert {r.split for r in runs} == {"development", "held_out"}
    assert sum(r.split == "held_out" for r in runs) == 12

    generation = next(e for e in events if e.type == "generation")
    assert generation.finish_reason in {"stop", "tool_calls"}
    assert generation.tool_call_ids is not None

    ids = {e.id for e in events}
    assert all(e.tool_call_id in ids for e in events if e.tool_call_id)


def test_payload_rows_share_keys_for_bulk_upsert():
    traces, labels, split = load_dataset(Path(DEFAULT_OUT))
    _, _, events, _, _ = dataset_rows(traces, labels, split)
    payload = _payload(events)
    assert len({tuple(sorted(row)) for row in payload}) == 1
