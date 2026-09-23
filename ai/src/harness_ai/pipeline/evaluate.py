"""Evaluate detector findings against human-reviewed labels.

Implements the PRD's measurement requirement: compare findings with
separate labels, reporting correct detections, missed failures, false
alarms, and abstentions per category.

Attribution rules:
- correct/missed stats belong to the label's expected category
- false alarms belong to the category the detector claimed
- abstaining on a known failure counts as a missed detection (PRD)
"""

from collections import Counter

from pydantic import BaseModel, Field

from harness_ai.pipeline.detect import Finding, FindingCategory


class ExpectedLabel(BaseModel):
    """One human-reviewed label from `labels.jsonl` (PRD deliverable 2)."""

    run_id: str
    verdict: str = Field(examples=["failure", "ok", "insufficient_evidence"])
    failure_category: FindingCategory | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class CategoryReport(BaseModel):
    category: str
    correct: int = 0
    missed: int = 0
    false_alarms: int = 0
    abstentions: int = 0


class EvaluationReport(BaseModel):
    """Per-category outcomes for a set of runs (PRD acceptance section)."""

    runs_evaluated: int = 0
    categories: list[CategoryReport] = Field(default_factory=list)


def evaluate(
    findings: dict[str, Finding], labels: dict[str, ExpectedLabel]
) -> EvaluationReport:
    """Compare detector findings with expected labels per run."""
    stats: dict[str, Counter] = {c.value: Counter() for c in FindingCategory}
    evaluated = 0

    for run_id, label in labels.items():
        if run_id not in findings:
            continue
        evaluated += 1
        finding = findings[run_id]
        label_key = label.failure_category.value if label.failure_category else "overall"

        def bump(category: str, outcome: str) -> None:
            stats.setdefault(category, Counter())[outcome] += 1

        if label.verdict == "failure":
            if finding.verdict == "failure":
                if finding.category == label.failure_category:
                    bump(label_key, "correct")
                else:
                    # Claimed a failure, but the wrong kind: false alarm
                    # attributed to the category the detector claimed.
                    bump(finding.category.value, "false_alarms")
            else:
                # Not detected, or abstained — both count as missed (PRD).
                bump(label_key, "missed")
                if finding.verdict == "insufficient_evidence":
                    bump(label_key, "abstentions")
        elif label.verdict == "ok":
            if finding.verdict == "failure":
                bump(finding.category.value, "false_alarms")
        elif label.verdict == "insufficient_evidence":
            if finding.verdict == "insufficient_evidence":
                bump(label_key, "correct")
            elif finding.verdict == "failure":
                bump(finding.category.value, "false_alarms")

    categories = [
        CategoryReport(category=name, **counter) for name, counter in stats.items()
    ]
    return EvaluationReport(runs_evaluated=evaluated, categories=categories)
