"""Pydantic models for recorded agent conversations.

These model the `traces.jsonl` format described in
docs/agent-failure-detection-prd.md: one trace per line with a run ID,
user ID, agent version, and ordered events. Tool calls link to their
results by event ID.

The shape deliberately mirrors what an LLM-observability tool exports
(Langfuse traces/observations, Datadog LLM Observability spans): a trace
header with identifiers, tags, metadata and rolled-up usage, plus an
ordered list of span-like events carrying their own timings and usage.
Detectors only ever read these models, so anything a detector is not
allowed to see (expected labels, scenario family) lives in `labels.jsonl`
instead.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EventType = Literal[
    "system_message",
    "user_message",
    "generation",
    "tool_call",
    "tool_result",
    "event",
]

Level = Literal["default", "warning", "error"]


class Usage(BaseModel):
    """Token and cost accounting for one generation or a whole trace."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class Event(BaseModel):
    """One ordered event inside a conversation trace.

    Equivalent to a Langfuse observation or a Datadog LLM Obs span. `id` is
    the stable reference used by labels and detector findings; `span_id` and
    `parent_span_id` carry the tracing hierarchy (tool spans nest under the
    generation that requested them).
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(examples=["e-0001"])
    span_id: str | None = Field(default=None, examples=["00f067aa0ba902b7"])
    parent_span_id: str | None = None
    type: EventType = "event"
    role: str = Field(
        description="Message author: 'system', 'user', 'agent', or 'tool'",
        examples=["user", "agent", "tool"],
    )
    name: str | None = Field(
        default=None,
        description="Span name, e.g. 'agent.generation' or 'tool.issue_refund'",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_timestamp: datetime | None = None
    latency_ms: int | None = None
    content: str = ""
    level: Level = Field(
        default="default", description="Observability severity, not a failure verdict"
    )
    status: str | None = Field(
        default=None, description="Transport-level outcome of a tool span: 'ok' or 'error'"
    )
    model: str | None = None
    usage: Usage | None = None
    tool_name: str | None = None
    # Tool events only: the result event links back to its call event.
    tool_call_id: str | None = Field(
        default=None, description="Set on tool results; the ID of the call they answer"
    )
    tool_arguments: dict | None = None
    tool_result: dict | list | None = Field(
        default=None, description="Structured outcome evidence for tool events"
    )


class Trace(BaseModel):
    """One recorded conversation run."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0"
    run_id: str = Field(examples=["run-0001"])
    trace_id: str | None = Field(
        default=None, description="32-hex tracing id, as emitted by OTel-based exporters"
    )
    session_id: str | None = Field(
        default=None, description="Groups runs belonging to the same customer session"
    )
    user_id: str = Field(examples=["usr-alex"])
    name: str = "support_agent.conversation"
    agent_version: str = Field(examples=["support-agent@1.4.2"])
    release: str | None = None
    environment: str = "production"
    synthetic: bool = Field(
        default=True, description="Marks trace as synthetic (PRD requires marking)"
    )
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: int | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Channel, locale, applicable policy, tool semantics, capture status",
    )
    model: dict[str, Any] | None = None
    usage: Usage | None = None
    events: list[Event] = Field(default_factory=list)

    def event(self, event_id: str) -> Event | None:
        """Look up one event by its stable ID."""
        return next((e for e in self.events if e.id == event_id), None)
