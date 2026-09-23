"""Row models for the Supabase tables in supabase/migrations/.

One model per table, with the same column names. Each has a constructor from
the in-memory dataset models so the uploader never hand-builds dicts.
Detector-side rows (SignalRow, IssueRow) are defined here too so the detector
and grouping stages write the same shape the dashboard reads.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from harness_ai.conversations.models import Event, Trace
from harness_ai.dataset.labels import RunLabels, Signal, SignalLabel, Split, Verdict

SplitName = Literal["development", "held_out"]

_EVENT_COLUMNS = set(Event.model_fields) | {"finish_reason", "tool_call_ids"}


class DatasetRow(BaseModel):
    name: str
    split_rule: str | None = None
    frozen_at: datetime | None = None

    @classmethod
    def from_split(cls, split: Split) -> DatasetRow:
        return cls(name=split.dataset, split_rule=split.rule, frozen_at=split.frozen_at)


class RunRow(BaseModel):
    run_id: str
    dataset: str
    split: SplitName | None = None
    trace_id: str
    session_id: str | None = None
    user_id: str
    name: str
    agent_version: str
    release: str | None = None
    environment: str
    synthetic: bool = True
    schema_version: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: int | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    model: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None

    @classmethod
    def from_trace(cls, trace: Trace, dataset: str, split: SplitName | None) -> RunRow:
        return cls(
            run_id=trace.run_id,
            dataset=dataset,
            split=split,
            trace_id=trace.trace_id or trace.run_id,
            session_id=trace.session_id,
            user_id=trace.user_id,
            name=trace.name,
            agent_version=trace.agent_version,
            release=trace.release,
            environment=trace.environment,
            synthetic=trace.synthetic,
            schema_version=trace.schema_version,
            start_time=trace.start_time,
            end_time=trace.end_time,
            duration_ms=trace.duration_ms,
            tags=trace.tags,
            metadata=trace.metadata,
            model=trace.model,
            usage=trace.usage.model_dump() if trace.usage else None,
        )


class EventRow(BaseModel):
    id: str
    run_id: str
    seq: int
    span_id: str | None = None
    parent_span_id: str | None = None
    type: str
    role: str
    name: str | None = None
    timestamp: datetime
    end_timestamp: datetime | None = None
    latency_ms: int | None = None
    content: str = ""
    level: str = "default"
    status: str | None = None
    model: str | None = None
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_call_ids: list[str] | None = None
    tool_arguments: dict[str, Any] | None = None
    tool_result: dict[str, Any] | list[Any] | None = None
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="Any extra event fields without a dedicated column"
    )

    @classmethod
    def from_event(cls, event: Event, run_id: str, seq: int) -> EventRow:
        data = event.model_dump()
        extra = event.model_extra or {}
        return cls(
            **{k: v for k, v in data.items() if k in cls.model_fields},
            run_id=run_id,
            seq=seq,
            attributes={k: v for k, v in extra.items() if k not in _EVENT_COLUMNS},
        )


class RunLabelRow(BaseModel):
    run_id: str
    scenario_key: str
    primary_family: Signal
    primary_verdict: Verdict
    task_expectation: str
    synthetic: bool = True
    reviewed_by: str
    reviewed_at: datetime
    notes: str | None = None

    @classmethod
    def from_labels(cls, labels: RunLabels) -> RunLabelRow:
        return cls(**labels.model_dump(exclude={"signals"}))


class SignalLabelRow(BaseModel):
    run_id: str
    signal: Signal
    verdict: Verdict
    rationale: str
    evidence_event_ids: list[str] = Field(default_factory=list)
    earlier_event_ids: list[str] = Field(default_factory=list)
    later_event_ids: list[str] = Field(default_factory=list)
    grouping_pattern: str | None = None
    recovery_note: str | None = None

    @classmethod
    def from_label(cls, run_id: str, signal: Signal, label: SignalLabel) -> SignalLabelRow:
        return cls(run_id=run_id, signal=signal, **label.model_dump())


class IssueRow(BaseModel):
    """A grouped issue written by the grouping stage."""

    id: UUID | None = None
    signal_type: Signal
    pattern: str
    title: str
    description: str | None = None
    root_cause_hypothesis: str | None = None
    affected_run_count: int = 0
    representative_run_ids: list[str] = Field(default_factory=list)


class DetectorVerdict(StrEnum):
    """A detector outcome. `error` means that detector never produced a verdict."""

    PRESENT = "present"
    ABSENT = "absent"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ERROR = "error"


class SignalRow(BaseModel):
    """One detector finding for one signal on one run."""

    id: UUID | None = None
    run_id: str
    signal_type: Signal
    verdict: DetectorVerdict
    explanation: str
    evidence_event_ids: list[str] = Field(default_factory=list)
    pattern: str | None = None
    issue_id: UUID | None = None
    detector_version: str


def dataset_rows(
    traces: list[Trace], labels: list[RunLabels], split: Split
) -> tuple[DatasetRow, list[RunRow], list[EventRow], list[RunLabelRow], list[SignalLabelRow]]:
    """Convert the in-memory dataset into rows for every dataset table."""
    split_of: dict[str, SplitName] = {r: "development" for r in split.development}
    split_of |= {r: "held_out" for r in split.held_out}

    runs = [RunRow.from_trace(t, split.dataset, split_of.get(t.run_id)) for t in traces]
    events = [
        EventRow.from_event(e, t.run_id, seq) for t in traces for seq, e in enumerate(t.events, 1)
    ]
    run_labels = [RunLabelRow.from_labels(lb) for lb in labels]
    signal_labels = [
        SignalLabelRow.from_label(lb.run_id, sig, sl)
        for lb in labels
        for sig, sl in lb.signals.items()
    ]
    return DatasetRow.from_split(split), runs, events, run_labels, signal_labels
