# Synthetic support-agent conversation dataset

`kettl-support-synthetic-v1`: 36 fictional customer-support conversations for **Aurora**, the support agent of the fictional EU homeware store Kettl & Co. Each conversation is labelled for three behavioural signals: **User Frustration**, **Task Failure** and **Forgetting**. The dataset is the first deliverable of [the PRD](../../docs/agent-failure-detection-prd.md).

Every trace is synthetic (`"synthetic": true`). All people, e-mail addresses, orders, tracking numbers and references are invented.

| File | Contents | Detector may read? |
|---|---|---|
| `traces.jsonl` | One recorded conversation per line, in the style of a Langfuse or Datadog LLM Observability export | Yes |
| `labels.jsonl` | Human-reviewed verdicts per run and signal, with evidence event IDs | Development runs only |
| `split.json` | Frozen development and held-out run IDs | Yes |

## Regenerating

The files are generated from the scenario sources in `ai/src/harness_ai/dataset/`. Do not edit them by hand.

```bash
cd ai
uv run python -m harness_ai.dataset.build   # rewrites this folder, validates first
uv run pytest tests/test_dataset.py        # fails if these files are stale
```

The build is deterministic because it uses a fixed seed. It refuses to write output if any rule under **Validation** below fails.

## `traces.jsonl` fields

A trace is a Langfuse-style trace header plus an ordered list of observations (spans). The schema is `harness_ai.conversations.models.Trace`.

| Field | Meaning |
|---|---|
| `run_id` | Dataset run ID (`run-0001` … `run-0036`), in shuffled order so it reveals nothing about family |
| `trace_id` | 32-hex OTel-style trace ID |
| `session_id`, `user_id` | Stable pseudonymous IDs (`sess_…`, `usr_…`) |
| `agent_version`, `release` | Agent build, e.g. `support-agent@1.5.0` and `2026.09.1` |
| `environment` | Always `production`, as the traces are meant to look like production traffic |
| `start_time`, `end_time`, `duration_ms` | Wall-clock span of the conversation (UTC) |
| `tags` | `channel:*`, `locale:*`, `topic:*`, agent version, `synthetic` |
| `metadata.policies` | The support-policy clauses that apply to this conversation (`ID-01`, `REF-03`, …). These are the task contract to judge against |
| `metadata.tool_semantics` | What every available tool does and which result values mean done, pending or refused |
| `metadata.capture` | Exporter completeness: `{"status": "complete"}` or `partial` with what was dropped and why |
| `metadata.session` | Present when earlier traces in the same session were not exported |
| `model`, `usage` | LLM provider and model, plus trace-level token and cost totals |
| `events[]` | Ordered observations, described below |

### Events

| Field | Meaning |
|---|---|
| `id` | Stable event ID (`evt-<run>-<nnn>`). Labels and findings cite these |
| `span_id`, `parent_span_id` | Span hierarchy. Generations hang off the trace root, tool calls under the generation that emitted them, and tool results under their call |
| `type` | `system_message`, `user_message`, `generation`, `tool_call` or `tool_result` |
| `role` | `system`, `user`, `agent` or `tool` |
| `name` | Span name, e.g. `agent.generation`, `tool.issue_refund`, `tool.issue_refund.result` |
| `timestamp`, `end_timestamp`, `latency_ms` | Timing. User gaps are human-scale; e-mail threads have gaps of 15 to 90 minutes |
| `content` | Message text, tool arguments as JSON, or tool result as JSON |
| `model`, `usage`, `finish_reason`, `tool_call_ids` | Generation-only fields. `finish_reason` is `tool_calls` when the generation requested tools; an empty-content generation is a pure tool-calling step |
| `tool_name`, `tool_arguments` | On tool calls |
| `tool_call_id`, `tool_result`, `status` | On tool results. `tool_call_id` links to the call event. `status` is transport-level (`ok` or `error`) |
| `level` | Observability severity (`default` or `warning`). **Not a verdict.** A business-level rejection returned with HTTP success is logged at `warning` |

A `tool_call` without a matching `tool_result` means the result was not recorded. Check `metadata.capture` to see whether it was dropped.

## `labels.jsonl` fields

Schema: `harness_ai.dataset.labels.RunLabels`.

| Field | Meaning |
|---|---|
| `run_id` | Joins to `traces.jsonl` |
| `scenario_key` | Scenario variant ID. Kept here and never in traces |
| `primary_family`, `primary_verdict` | The signal the run was written to exercise, and its verdict. Used only for dataset balance |
| `task_expectation` | The reviewer's statement of the requested outcome |
| `signals.<signal>.verdict` | `present`, `absent` or `insufficient_evidence`, labelled independently for all three signals |
| `signals.<signal>.evidence_event_ids` | Every event the reviewer relied on, including for `absent` and `insufficient_evidence` |
| `signals.forgetting.earlier_event_ids` / `later_event_ids` | Where the context was supplied, and where it was later ignored |
| `signals.<signal>.grouping_pattern` | Expected issue bucket for a `present` verdict, e.g. `asks_again_for_supplied_order_number` |
| `signals.<signal>.recovery_note` | Set when the run recovered after the signal occurred. Recovery never downgrades `present` |
| `rationale`, `notes`, `reviewed_by`, `reviewed_at` | Reviewer explanation and provenance |

## Labelling rules

The general rule: a signal is an observation, not a root cause. Sentiment alone never implies Task Failure, and missing records alone never prove failure.

**User Frustration** is `present` when the user expresses dissatisfaction aimed at the agent, its replies, or the interaction, whether explicitly or through clear sarcasm. It stays present even if the agent later resolves the request.
- `absent` covers anger at a carrier or a product, neutral corrections, and praise.
- `insufficient_evidence` applies when the target of the dissatisfaction cannot be determined, for example because the preceding context was dropped or the remark is genuinely ambiguous.

**Task Failure** is `present` when recorded evidence contradicts the expected, permitted outcome. Examples: claiming success while the tool result says `rejected`, acting on the wrong order or line item, promising an escalation with no ticket in a complete trace, or ending with an eligible request unresolved.
- `absent` covers successful actions, accurately described pending operations, correct policy refusals, and prescribed handoffs.
- `insufficient_evidence` applies when the run ends before resolution, or when the relevant result was not captured.

**Forgetting** is `present` when later agent behaviour ignores important context the user supplied earlier in the recorded history, with a meaningful exchange in between. Both the earlier and the later events are cited.
- `absent` covers required re-verification (ID-01), confirmation before an irreversible action, resolving conflicting order numbers, following a revised preference, and immediate instruction noncompliance with no intervening exchange.
- `insufficient_evidence` applies when the alleged earlier context is not in the supplied history.

A recovered failure is still labelled `present`, with a `recovery_note`.

## Counts

Primary-family balance, matching the PRD table:

| Primary family | Present | Absent lookalike | Insufficient | Total |
|---|---:|---:|---:|---:|
| User Frustration | 6 | 4 | 2 | 12 |
| Task Failure | 6 | 4 | 2 | 12 |
| Forgetting | 6 | 4 | 2 | 12 |
| **Total** | 18 | 12 | 6 | 36 |

All verdicts across all 36 runs, counting every signal and not just the primary one:

| Signal | Present | Absent | Insufficient |
|---|---:|---:|---:|
| User Frustration | 9 | 25 | 2 |
| Task Failure | 10 | 23 | 3 |
| Forgetting | 7 | 26 | 3 |

Other properties:
- 7 runs have two or more signals present (3 in the held-out set); one run has all three.
- 12 runs are fully successful, with every signal absent.
- 5 signals carry a recovery note.
- 3 traces are partial captures.
- Several grouping patterns repeat across runs. For example, `asks_again_for_supplied_order_number` occurs in 3 development runs, and `claims_refund_completed_while_tool_rejected` and `promises_escalation_without_creating_ticket` each occur in 2.

Coverage:
- **Topics:** 20 refund, 6 delivery update, 6 address change, 4 cancellation.
- **Agent versions:** `1.4.2` ×12, `1.5.0` ×14, `1.5.1` ×10.
- **Channels:** 33 web chat, 3 e-mail.
- **Locales:** en-GB, en-IE, es-ES, and nl-NL, which includes Dutch-language turns.

## Split

`split.json` holds 24 development runs and 12 held-out runs. For each primary family, the held-out set contains two signal-present runs, one absent lookalike and one insufficient-evidence run. Runs with overlapping signals appear in both splits. The split is by scenario variant: held-out runs are distinct scenarios, not renamed copies of development runs.

Detector authors may read development labels. **Do not read held-out labels or tune prompts on held-out runs.** The split is frozen as of `frozen_at`.

## Validation

The build checks all of the following:
- There are 36 unique runs, and event IDs are unique within each run.
- Events are in timestamp order.
- Every tool result links to a tool call for the same tool.
- Every cited evidence ID exists in its trace.
- Every `present` verdict has a grouping pattern.
- Forgetting's earlier events precede its later events.
- The primary-family table matches exactly.
- Every signal has all three verdicts somewhere in the dataset.
- There are at least 6 overlapping runs, in both splits, and at least 3 fully successful runs.
- The held-out composition matches the rule above.
- No label metadata leaks into any trace.

## Limitations

- **Hand-authored and small.** Results on 36 scenarios show feasibility, not production accuracy. The wording is cleaner and the failures are more clear-cut than in real traffic.
- **Single author, self-reviewed.** Labels have not been independently double-labelled. Borderline calls are explained in `rationale` so a second reviewer can disagree precisely.
- **Simulated telemetry.** Latencies, token counts and costs come from text length plus seeded noise. They look plausible but carry no signal and should not be used for detection. Model names and prices are illustrative.
- **Policy excerpts, not a full policy.** Each trace carries only the clauses that bear on it, which is more help than a real agent log would give.
- **Dates are approximate.** Conversation dates sit around 12–14 September 2026. Relative phrases such as "last Tuesday" or "within 3 days" are only roughly consistent with the timestamps.
- **Narrow domain and language mix.** Mostly English-language e-commerce support, with a few Dutch and Spanish turns.
