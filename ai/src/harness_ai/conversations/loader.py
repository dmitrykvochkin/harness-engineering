"""Load recorded conversation traces from a `traces.jsonl` file."""

from pathlib import Path

from harness_ai.conversations.models import Trace


def load_traces(path: str | Path) -> list[Trace]:
    """Load traces from a JSONL file, skipping blank lines."""
    return [
        Trace.model_validate_json(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
