"""Tests for the pipeline stages: importer, grouping, evaluation."""

from harness_ai.conversations.models import Event, Trace
from harness_ai.pipeline.detect import Finding, FindingCategory
from harness_ai.pipeline.evaluate import ExpectedLabel, evaluate
from harness_ai.pipeline.group import group_findings


def _trace(run_id: str) -> Trace:
    return Trace(
        run_id=run_id,
        user_id="usr-alex",
        agent_version="agent-1.4.0",
        events=[
            Event(id="e-001", role="user", content="I want a refund for order 1001"),
            Event(id="e-002", role="agent", content="Processing your refund"),
            Event(
                id="e-003",
                role="tool",
                content="",
                tool_call_id="e-002",
                tool_name="refund",
                tool_result={"status": "pending"},
            ),
        ],
    )


def test_trace_roundtrip_json():
    trace = _trace("run-0001")
    data = trace.model_dump_json()
    assert Trace.model_validate_json(data).run_id == "run-0001"


def test_group_findings_no_double_counting():
    findings = {
        "run-0001": Finding(
            category=FindingCategory.FALSE_COMPLETION,
            verdict="failure",
            evidence_ids=["e-002", "e-003"],
            explanation="Claims completed refund while tool reports pending",
        ),
        "run-0002": Finding(
            category=FindingCategory.FALSE_COMPLETION,
            verdict="failure",
            evidence_ids=["e-002", "e-003"],
            explanation="Same mismatch on another order",
        ),
    }
    issues = group_findings(findings)
    assert len(issues) == 1
    assert sorted(issues[0].affected_run_ids) == ["run-0001", "run-0002"]


def test_evaluate_counts_missed_and_false_alarms():
    findings = {
        "run-0001": Finding(
            category=FindingCategory.UNPRODUCTIVE_LOOP,
            verdict="failure",
            evidence_ids=["e-002"],
            explanation="loop",
        ),
        "run-0002": Finding(
            category=FindingCategory.INSUFFICIENT_EVIDENCE,
            verdict="insufficient_evidence",
            evidence_ids=[],
            explanation="truncated",
        ),
    }
    labels = {
        "run-0001": ExpectedLabel(
            run_id="run-0001", verdict="ok", rationale="productive retry"
        ),
        "run-0002": ExpectedLabel(
            run_id="run-0002", verdict="failure", failure_category=FindingCategory.UNPRODUCTIVE_LOOP
        ),
    }
    report = evaluate(findings, labels)
    by_cat = {r.category: r for r in report.categories}
    assert by_cat["unproductive_loop"].false_alarms == 1
    assert by_cat["unproductive_loop"].missed == 1
