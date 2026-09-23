"""Classifier JSONL becomes one signals-table row per signal, including failures."""

import json
from pathlib import Path
from uuid import UUID

from harness_ai.db.results import load_result_rows
from harness_ai.db.rows import DefinitionSignalRow, DetectorVerdict

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


def test_definition_finding_uses_the_slug_as_signal_type():
    definition_id = UUID("7d3c1a52-8f0e-4b8e-9d65-2f1f6c0a9b11")
    row = DefinitionSignalRow(
        run_id="run-0001",
        signal_type="refund-promises",
        signal_definition_id=definition_id,
        verdict=DetectorVerdict.PRESENT,
        explanation="The agent promised a refund the tool rejected.",
        evidence_event_ids=["evt-0001-008"],
        detector_version="nebius:example-model",
    )

    payload = row.model_dump(mode="json", exclude={"id"})

    assert payload["signal_type"] == "refund-promises"
    assert payload["signal_definition_id"] == str(definition_id)
    assert payload["verdict"] == "present"


def test_malformed_line_names_its_line_number(tmp_path: Path):
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps(RECORD) + "\nnot-json\n", encoding="utf-8")

    try:
        load_result_rows(path)
    except ValueError as exc:
        assert f"{path}:2:" in str(exc)
    else:
        raise AssertionError("expected ValueError")
