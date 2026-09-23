"""Group similar failure findings into actionable issues.

Implements the PRD's grouping requirement: similar observed failures
become one issue with a title, description, unique affected-run count,
and representative examples. Root causes remain hypotheses.
"""

from collections import defaultdict

from pydantic import BaseModel, Field

from harness_ai.pipeline.detect import Finding, FindingCategory


class Issue(BaseModel):
    """A grouped set of similar failures affecting one or more runs."""

    title: str
    description: str
    category: FindingCategory
    affected_run_ids: list[str] = Field(description="Unique runs, no double-counting")
    representative_examples: list[Finding] = Field(
        description="A few findings that best illustrate the issue"
    )


def group_findings(findings: dict[str, Finding]) -> list[Issue]:
    """Group findings (keyed by run ID) into issues by category.

    The initial grouping key is the failure category — each family from
    the PRD (false completion, ignored instructions, unproductive loops)
    becomes one issue whose affected runs are counted uniquely.
    """
    by_category: dict[FindingCategory, dict[str, Finding]] = defaultdict(dict)
    for run_id, finding in findings.items():
        if finding.verdict == "failure":
            by_category[finding.category][run_id] = finding

    issues: list[Issue] = []
    for category, runs in by_category.items():
        if not runs:
            continue
        examples = sorted(runs.values(), key=lambda f: f.explanation)[:3]
        issues.append(
            Issue(
                title=f"{category.replace('_', ' ').title()} in support agent",
                description=(
                    f"Observed {category.replace('_', ' ')} behaviour in "
                    f"{len(runs)} run(s). Root cause is a hypothesis pending "
                    "investigation."
                ),
                category=category,
                affected_run_ids=sorted(runs),
                representative_examples=examples,
            )
        )
    return issues
