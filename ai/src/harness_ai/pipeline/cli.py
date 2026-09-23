"""Command-line entry point: traces -> findings -> issues -> report.

Usage:
    harness-ai <conversations_dir>

Expects `<dir>/traces.jsonl` (and optionally `<dir>/labels.jsonl`) as
described in docs/agent-failure-detection-prd.md. Prints a JSON report.
"""

import asyncio
import json
import sys
from pathlib import Path

from harness_ai.pipeline.detect import Finding
from harness_ai.pipeline.evaluate import ExpectedLabel, evaluate
from harness_ai.pipeline.group import group_findings
from harness_ai.pipeline.importer import load_traces


async def run_pipeline(conversations_dir: Path) -> dict:
    traces = load_traces(conversations_dir / "traces.jsonl")

    findings: dict[str, Finding] = {}
    for trace in traces:
        findings[trace.run_id] = await detect_trace(trace)

    issues = group_findings(findings)

    report: dict = {
        "runs_total": len(traces),
        "issues": [issue.model_dump() for issue in issues],
    }

    labels_path = conversations_dir / "labels.jsonl"
    if labels_path.exists():
        labels = {
            label.run_id: label
            for label in (
                ExpectedLabel.model_validate_json(line)
                for line in labels_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
        evaluation = evaluate(findings, labels)
        report["evaluation"] = evaluation.model_dump()

    return report


async def detect_trace(trace) -> Finding:
    from harness_ai.pipeline.detect import detect

    return await detect(trace)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: harness-ai <conversations_dir>", file=sys.stderr)
        sys.exit(2)

    conversations_dir = Path(sys.argv[1]).resolve()
    if not conversations_dir.is_dir():
        print(f"error: {conversations_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    report = asyncio.run(run_pipeline(conversations_dir))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
