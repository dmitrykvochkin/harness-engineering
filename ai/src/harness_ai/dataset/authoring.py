"""Authoring primitives for the synthetic scenario set.

Scenarios are written as a short list of turns plus three signal verdicts.
Turns reference each other by *tag* rather than by event ID, so the builder
can assign stable IDs, span IDs, timings and token usage and then resolve
every label's evidence tags to real event IDs. A label that cites a tag no
turn defines is a build error, which is how the "valid evidence references"
requirement is enforced mechanically.
"""

from dataclasses import dataclass, field

from harness_ai.dataset.labels import Signal, SignalLabel, Verdict

# --- Support policy supplied with every trace -------------------------------
# Excerpts are attached to the traces that they bear on, so a detector can
# judge a refusal or a pending operation against the same rules a reviewer did.

POLICY_VERSION = "support-policy-2026-08"

POLICIES: dict[str, str] = {
    "ID-01": (
        "Verify the account postcode or e-mail once before disclosing order details. "
        "Re-verification is required only after a 30-minute gap or when the customer "
        "switches to a different order."
    ),
    "REF-01": (
        "Refunds are auto-approved for unopened items returned within 30 days of delivery."
    ),
    "REF-02": (
        "Final-sale items are not refundable. Offer store credit of equal value instead."
    ),
    "REF-03": (
        "Refunds above EUR 250 require supervisor approval: create a ticket in queue "
        "'refunds-approval' and tell the customer it is pending approval."
    ),
    "REF-04": (
        "Original outbound shipping is refunded only when the return is caused by a "
        "defect or a picking error."
    ),
    "CAN-01": (
        "An order can be cancelled while its status is 'processing'. Once the status is "
        "'shipped' or later, cancellation is impossible; offer a return instead."
    ),
    "ADR-01": (
        "The shipping address can be changed while order status is 'processing' or "
        "'label_created'. After carrier handover the address is immutable."
    ),
    "DEL-01": (
        "A parcel with no carrier scan for 10 days is treated as lost; issue a "
        "replacement at no cost to the customer."
    ),
    "DEL-02": (
        "Redelivery must be scheduled inside a window the customer has confirmed they "
        "are available for."
    ),
    "ESC-01": (
        "When the customer asks for a human, or a permitted action cannot be completed, "
        "call escalate_to_human AND create_ticket. A promise of escalation without both "
        "calls leaves the request unhandled."
    ),
    "LNG-01": (
        "Once the customer states a language preference, reply in that language for the "
        "rest of the conversation unless they revise it."
    ),
}

# --- Tool semantics supplied with every trace -------------------------------
# What each tool does and, crucially, which result values mean "done" versus
# "accepted but not yet done" versus "refused".

TOOL_SEMANTICS: dict[str, str] = {
    "lookup_order": "Read-only. Returns order status, items and carrier data.",
    "lookup_orders_by_email": "Read-only. Returns recent orders for an e-mail address.",
    "get_customer_profile": "Read-only. Returns tier and stored language preference.",
    "get_tracking": "Read-only. Returns carrier scans; days_since_last_scan drives DEL-01.",
    "check_refund_eligibility": (
        "Read-only. eligible=true means a refund is permitted under REF-01/REF-02."
    ),
    "issue_refund": (
        "Write. result.status is 'completed' (money moved), 'pending' (accepted, settles "
        "later) or 'rejected' (nothing happened). Only 'completed' may be described as done."
    ),
    "issue_store_credit": "Write. result.status 'issued' means the credit is usable now.",
    "cancel_order": "Write. result.status 'cancelled' or 'rejected' with a reason_code.",
    "update_shipping_address": (
        "Write. result.status 'updated' or 'rejected'. A rejected update leaves the old "
        "address in place."
    ),
    "schedule_redelivery": "Write. result.status 'scheduled' returns the booked slot.",
    "send_return_label": "Write. result.status 'sent' means the label reached the customer.",
    "create_ticket": "Write. Returns ticket_id; absence of this call means no ticket exists.",
    "escalate_to_human": "Write. Returns handoff_id and queue position for a live agent.",
}

# --- Turn DSL ---------------------------------------------------------------


@dataclass(frozen=True)
class Turn:
    """One authored turn, rendered into exactly one trace event."""

    kind: str  # system | user | agent | tool_call | tool_result
    content: str = ""
    tag: str | None = None
    tool_name: str | None = None
    tool_arguments: dict | None = None
    tool_result: dict | None = None
    status: str | None = None
    level: str = "default"
    gap_s: float | None = None  # override the default think/latency gap before this turn


def S(content: str, *, tag: str | None = None) -> Turn:
    """System prompt turn."""
    return Turn("system", content, tag=tag)


def U(content: str, *, tag: str | None = None, gap_s: float | None = None) -> Turn:
    """User message turn."""
    return Turn("user", content, tag=tag, gap_s=gap_s)


def A(content: str, *, tag: str | None = None) -> Turn:
    """Agent generation turn."""
    return Turn("agent", content, tag=tag)


def C(tool_name: str, tool_arguments: dict, *, tag: str | None = None) -> Turn:
    """Tool call turn, emitted by the preceding agent generation."""
    return Turn("tool_call", "", tag=tag, tool_name=tool_name, tool_arguments=tool_arguments)


def R(
    tool_result: dict,
    *,
    tag: str | None = None,
    status: str = "ok",
    level: str = "default",
) -> Turn:
    """Tool result turn, linked to the most recent tool call."""
    return Turn("tool_result", "", tag=tag, tool_result=tool_result, status=status, level=level)


# --- Label DSL --------------------------------------------------------------


@dataclass(frozen=True)
class SignalSpec:
    """A verdict written against turn tags instead of event IDs."""

    verdict: Verdict
    rationale: str
    evidence: tuple[str, ...] = ()
    earlier: tuple[str, ...] = ()
    later: tuple[str, ...] = ()
    grouping_pattern: str | None = None
    recovery_note: str | None = None

    def resolve(self, tags: dict[str, str], scenario_key: str) -> SignalLabel:
        """Turn tag references into event IDs, failing loudly on a bad reference."""

        def ids(names: tuple[str, ...]) -> list[str]:
            missing = [n for n in names if n not in tags]
            if missing:
                raise ValueError(f"{scenario_key}: label cites unknown turn tags {missing}")
            return [tags[n] for n in names]

        evidence = ids(self.evidence) + ids(self.earlier) + ids(self.later)
        return SignalLabel(
            verdict=self.verdict,
            rationale=self.rationale,
            evidence_event_ids=list(dict.fromkeys(evidence)),
            earlier_event_ids=ids(self.earlier),
            later_event_ids=ids(self.later),
            grouping_pattern=self.grouping_pattern,
            recovery_note=self.recovery_note,
        )


def present(
    rationale: str,
    *,
    pattern: str,
    evidence: tuple[str, ...] = (),
    earlier: tuple[str, ...] = (),
    later: tuple[str, ...] = (),
    recovery: str | None = None,
) -> SignalSpec:
    return SignalSpec(
        Verdict.PRESENT,
        rationale,
        evidence,
        earlier,
        later,
        grouping_pattern=pattern,
        recovery_note=recovery,
    )


def absent(rationale: str, *, evidence: tuple[str, ...] = ()) -> SignalSpec:
    return SignalSpec(Verdict.ABSENT, rationale, evidence)


def unclear(rationale: str, *, evidence: tuple[str, ...] = ()) -> SignalSpec:
    return SignalSpec(Verdict.INSUFFICIENT_EVIDENCE, rationale, evidence)


# --- Scenario ---------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """One authored conversation variant and its three reviewed verdicts."""

    key: str
    primary: Signal
    topic: str
    customer: str
    customer_tier: str
    locale: str
    channel: str
    agent_version: str
    policies: tuple[str, ...]
    requested_outcome: str
    turns: list[Turn]
    labels: dict[Signal, SignalSpec]
    capture: dict | None = None
    session_continues_from: bool = False
    notes: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def tools_used(self) -> list[str]:
        seen = {t.tool_name for t in self.turns if t.tool_name}
        return sorted(seen)
