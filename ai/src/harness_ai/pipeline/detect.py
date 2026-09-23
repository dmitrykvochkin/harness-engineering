"""Failure-detection agent built with Pydantic AI.

Detects behavioural failures (false completion, ignored instructions,
unproductive loops) in a single conversation trace, or abstains when
the evidence is insufficient — the three failure families from the PRD.
"""

from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from harness_ai.conversations.models import Trace


class FindingCategory(StrEnum):
    FALSE_COMPLETION = "false_completion"
    IGNORED_INSTRUCTIONS = "ignored_instructions"
    UNPRODUCTIVE_LOOP = "unproductive_loop"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Finding(BaseModel):
    """A finding must reference concrete evidence IDs (PRD requirement)."""

    category: FindingCategory
    verdict: str = Field(examples=["failure", "ok", "insufficient_evidence"])
    evidence_ids: list[str] = Field(
        description="Message/tool event IDs that support the verdict"
    )
    explanation: str = Field(description="What the mismatch is and why it matters")


detector_agent = Agent(
    # No API key needed during development: the built-in 'test' model runs
    # offline. Swap to a real model (e.g. 'openai:gpt-5.6' or
    # 'anthropic:claude-fable-5') by setting it here or via env config.
    "test",
    output_type=Finding,
    instructions=(
        "You analyse recorded customer-support agent conversations for "
        "behavioural failures. For each trace: (1) check whether agent claims "
        "match recorded tool outcomes (false completion), (2) check whether "
        "explicit feasible customer instructions were followed (ignored "
        "instructions), (3) check whether repeated actions made progress "
        "(unproductive loops). Every finding must cite specific event IDs as "
        "evidence. If the recorded evidence cannot support a conclusion, "
        "return insufficient_evidence rather than guessing."
    ),
)


async def detect(trace: Trace) -> Finding:
    """Run the detector agent over one trace and return its typed finding."""
    result = await detector_agent.run(f"Analyse this trace:\n{trace.model_dump_json()}")
    return result.output
