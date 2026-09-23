"""Models for the human-reviewed labels and the dev/held-out split.

Labels live beside the traces but are never handed to a detector: they carry
the expected verdicts, the scenario family used for dataset balance, and the
grouping pattern each matched signal is expected to fall into.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Signal(StrEnum):
    """The three signals labelled independently on every run."""

    USER_FRUSTRATION = "user_frustration"
    TASK_FAILURE = "task_failure"
    FORGETTING = "forgetting"


class Verdict(StrEnum):
    """Per-signal verdict. `insufficient_evidence` is an abstention, not a negative."""

    PRESENT = "present"
    ABSENT = "absent"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class SignalLabel(BaseModel):
    """One reviewed verdict for one signal on one run."""

    verdict: Verdict
    rationale: str = Field(description="Short human explanation of the verdict")
    evidence_event_ids: list[str] = Field(
        default_factory=list,
        description="Every event a reviewer relied on, including absent/abstain verdicts",
    )
    earlier_event_ids: list[str] = Field(
        default_factory=list,
        description="Forgetting only: where the context was supplied",
    )
    later_event_ids: list[str] = Field(
        default_factory=list,
        description="Forgetting only: where the agent failed to use it",
    )
    grouping_pattern: str | None = Field(
        default=None,
        description="Expected issue bucket for a present verdict, e.g. "
        "'asks_again_for_supplied_order_number'",
    )
    recovery_note: str | None = Field(
        default=None,
        description="Set when the run recovered after the signal occurred; "
        "recovery does not downgrade a present verdict",
    )


class RunLabels(BaseModel):
    """All three verdicts for one run, plus dataset bookkeeping."""

    run_id: str
    scenario_key: str = Field(
        description="Stable scenario variant id; distinct variants, not renamed customers"
    )
    primary_family: Signal = Field(description="Family this run was authored for, for balance only")
    primary_verdict: Verdict = Field(description="Verdict of the primary family signal")
    task_expectation: str = Field(
        description="Reviewer's statement of the requested outcome the run is judged against"
    )
    synthetic: bool = True
    reviewed_by: str
    reviewed_at: datetime
    signals: dict[Signal, SignalLabel]
    notes: str | None = None


class Split(BaseModel):
    """Frozen development / held-out partition of the run IDs."""

    dataset: str
    frozen_at: datetime
    rule: str
    counts: dict[str, int]
    development: list[str]
    held_out: list[str]
