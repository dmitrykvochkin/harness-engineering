"""The synthetic dataset satisfies the PRD rules and the committed files are current."""

from pathlib import Path

from harness_ai.conversations import load_traces
from harness_ai.dataset.build import DEFAULT_OUT, build, validate


def test_dataset_passes_validation():
    traces, labels, split = build()
    assert validate(traces, labels, split) == []


def test_committed_files_match_build():
    traces, labels, split = build()
    out = Path(DEFAULT_OUT)
    expected_traces = "".join(t.model_dump_json(exclude_none=True) + "\n" for t in traces)
    expected_labels = "".join(lb.model_dump_json(exclude_none=True) + "\n" for lb in labels)
    assert (out / "traces.jsonl").read_text(encoding="utf-8") == expected_traces, (
        "traces.jsonl is stale: run `uv run python -m harness_ai.dataset.build`"
    )
    assert (out / "labels.jsonl").read_text(encoding="utf-8") == expected_labels
    assert (out / "split.json").read_text(encoding="utf-8") == split.model_dump_json(
        indent=2
    ) + "\n"


def test_importer_reads_committed_traces():
    traces = load_traces(Path(DEFAULT_OUT) / "traces.jsonl")
    assert len(traces) == 36
    assert all(t.synthetic for t in traces)
