"""Classifier JSONL becomes one signals-table row per signal, including failures."""

import json
from pathlib import Path

from harness_ai.db.results import load_result_rows

RECORD = {
    "run_id": "run-0001",
    "model": "nebius:example-model",
    "signals": {
        "user_frustration": {
            "verdict": "present",
            "reason": "The user said this is ridiculous.",
            "evidence_event_ids": ["evt-0001-012"],
        },
        "task_failure": None,
        "forgetting": {
            "verdict": "absent",
            "reason": "The agent kept the order number.",
            "evidence_event_ids": [],
        },
    },
    "errors": {"task_failure": "evidence cites unknown event ids: evt-010"},
}


def test_null_signal_becomes_an_error_row(tmp_path: Path):
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps(RECORD) + "\n", encoding="utf-8")

    rows = {row.signal_type.value: row for row in load_result_rows(path)}

    assert set(rows) == {"user_frustration", "task_failure", "forgetting"}
    assert rows["user_frustration"].verdict.value == "present"
    assert rows["user_frustration"].evidence_event_ids == ["evt-0001-012"]
    assert rows["user_frustration"].detector_version == "nebius:example-model"
    assert rows["task_failure"].verdict.value == "error"
    assert rows["task_failure"].explanation == "evidence cites unknown event ids: evt-010"
    assert rows["task_failure"].evidence_event_ids == []
    assert rows["forgetting"].verdict.value == "absent"


def test_malformed_line_names_its_line_number(tmp_path: Path):
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps(RECORD) + "\nnot-json\n", encoding="utf-8")

    try:
        load_result_rows(path)
    except ValueError as exc:
        assert f"{path}:2:" in str(exc)
    else:
        raise AssertionError("expected ValueError")
