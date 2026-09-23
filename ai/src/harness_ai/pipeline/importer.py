"""Import recorded conversation traces from JSONL files.

Reads one trace per line (see conversations/models.py for the schema)
from a `traces.jsonl` file as described in the PRD.
"""

from pathlib import Path

from harness_ai.conversations.models import Trace


def load_traces(path: str | Path) -> list[Trace]:
    """Load traces from a JSONL file, skipping blank lines."""
    traces = [
        Trace.model_validate_json(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return traces
