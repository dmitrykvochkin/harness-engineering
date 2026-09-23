# Agent Failure Detection PoC

Hackathon PRD and teammate handoff • 23 September 2026

## Objective

Build a proof of concept that finds behavioural failures in recorded AI agent conversations and groups them into actionable issues with evidence. A run can finish without a technical error while still failing the customer.

Our intended product helps engineering teams understand where agents fail real users, how often those problems occur, and which conversations to investigate. We are adopting the Raindrop-style product model for a niche market; the niche is still to be selected. Customer support is the temporary demo domain, not a final market decision.

## User and value

The initial user is an engineer responsible for a customer-support agent. They need to identify recurring customer problems without manually reading every conversation.

Product promise: “Find where your AI agent fails customers—even when every request succeeds—and show the evidence your team needs to act.”

Evaluation is part of the mechanism: it assesses individual interactions. The product adds discovery, grouping, affected-run counts, and investigation. A discovered failure can later become a regression test to verify a fix.

## PoC requirements

The first milestone is a working pipeline: recorded conversations → failure detection → grouped issues → evaluation report. A JSON output or command-line report is sufficient.

| Requirement | Expected behaviour |
|---|---|
| Input | Read conversations, tool calls/results, timestamps, and agent version from JSON. Include backend outcome evidence when available. |
| Detection | Detect User Frustration, Task Failure, and Forgetting independently; a conversation may match multiple signals. |
| Evidence | Every finding references specific message or tool-event IDs and explains why the signal matches. |
| Uncertainty | Return insufficient evidence when a conclusion cannot be supported. Missing records alone do not prove failure. |
| Grouping | Combine similar observed failures into issues with a title, description, unique affected-run count, and representative examples. Root causes remain hypotheses. |
| Measurement | Compare findings with separate human-reviewed labels; report correct detections, missed failures, false alarms, and abstentions. |

Use an LLM for interpretation and deterministic checks where recorded tool evidence is conclusive. Choose the simplest implementation that supports this pipeline.

## First task for the teammate

Create the scenario dataset and expected outcomes before detector implementation. Timebox the initial version to approximately 45–60 minutes. Deliver 36 short, clearly labelled synthetic conversations using fictional customers and orders.

| Primary signal family | Signal present | Signal absent lookalikes | Insufficient evidence | Total |
|---|---:|---:|---:|---:|
| User Frustration | 6 | 4 | 2 | 12 |
| Task Failure | 6 | 4 | 2 | 12 |
| Forgetting | 6 | 4 | 2 | 12 |
| Total | 18 | 12 | 6 | 36 |

Assign each conversation a primary signal family for dataset balance, but label all three signals independently as `present`, `absent`, or `insufficient_evidence`. The table counts verdicts for the primary signal only, not total signal matches. Include at least six conversations with overlapping signals; these are part of the 36, not additional cases.

### Signal selection

Use **User Frustration**, **Task Failure**, and **Forgetting** to cover the customer's expressed experience, the task outcome, and continuity of context. These are three presets in [Raindrop's Signals documentation](https://www.raindrop.ai/docs/platform/signals/). Their inclusion as presets does not establish a ranking by frequency. The definitions below are our operational rules for the demo, not a claim to reproduce Raindrop's internal classifiers.

A signal is an observation, not necessarily an agent defect. Frustration may occur even when the agent acts correctly. Do not infer task failure from sentiment alone or claim a proven root cause from a signal match.

### Synthetic dataset authoring brief

Write realistic e-commerce support conversations about refunds, delivery updates, cancellations, and address changes. Aim for 6–12 user/assistant messages per conversation, plus relevant tool events. Include earlier context explicitly when it is needed to judge later behaviour. Supply applicable policy and tool semantics, including whether an operation is pending or completed. Use fictional data and varied wording, politeness, and conversation lengths.

**User Frustration**

Definition: the user expresses dissatisfaction directed at the agent, its responses, or the interaction. Detect both explicit complaints and context-supported indirect frustration.

- Present: “You keep asking me the same thing”; “That is not what I asked”; or sarcastic “Great, another answer that doesn't help” after an irrelevant reply. Include frustration that remains present even if the agent later resolves the request.
- Absent lookalikes: anger at a late parcel or damaged product without criticism of the agent; a neutral correction; genuine praise after help. Negative words alone are insufficient.
- Insufficient evidence: “Seriously?” with missing preceding context or an unclear target of dissatisfaction.
- Evidence: cite the user's expression and the surrounding exchange needed to interpret it. Do not require a tool failure or assume the agent caused the frustration.

**Task Failure**

Definition: available evidence shows the agent did not perform an expected, permitted task or produced an outcome inconsistent with the user's request. Judge against the task contract and policy supplied with the trace.

- Present: confirms a refund while its result is rejected; cancels the wrong order; promises escalation but a complete trace and final state show no ticket; or ends a repeated-lookup loop with an eligible request unresolved. Include polite users who never complain.
- Absent lookalikes: a successful action; a pending operation accurately explained within the expected workflow; a correct policy-based refusal; or a valid handoff when escalation is the prescribed outcome.
- Insufficient evidence: the conversation ends before resolution, or the relevant action result is missing. A lack of visible confirmation alone is not proof of failure.
- Evidence: cite the request, applicable task expectation, and contradictory action/result or observable unresolved ending. Record a recovered failure as present if it occurred, with recovery noted separately.

**Forgetting**

Definition: later agent behaviour fails to use important user context explicitly supplied earlier and available in the recorded conversation. This is an observed context-use failure, not proof of an internal memory-system bug.

- Present: asks again for an already provided order number without a reason; returns to an old address after acknowledging a replacement; or forgets an established Dutch-language preference later in the exchange.
- Absent lookalikes: necessary identity verification; confirmation before an irreversible action; resolving two conflicting order numbers; or correctly following the user's latest revised preference.
- Insufficient evidence: “I already told you” when the alleged earlier information is absent from the supplied history.
- Evidence: cite both the earlier context and the later conflicting behaviour. Immediate instruction noncompliance alone does not establish forgetting; include a meaningful intervening exchange.

Include repeated patterns across different conversations for grouping, and cases where signals are independent: frustration despite correct handling, silent task failure, and forgotten context that is corrected before task completion. Add overlapping cases such as forgotten order details causing an unresolved request and an explicit complaint. Include at least three fully successful, unambiguous conversations with all signals absent. Group issues by specific observed pattern, such as “asks again for supplied order number”, rather than creating only three buckets named after the signals.

### Deliverables

1. `traces.jsonl`: one trace per line with run ID, fictional user ID, agent version, and ordered events. Each event needs a stable ID, timestamp, role/type, and content. Link tool calls to their results. Mark traces as synthetic.
2. `labels.jsonl`: a separate verdict for each of the three signals on every run, supporting event IDs, and a short rationale. Include primary family, expected grouping pattern for matched signals, and a recovery note where applicable. For forgetting, reference both earlier and later events.
3. `split.json`: 24 development runs and 12 held-out runs. Reserve two signal-present cases, one absent lookalike, and one insufficient-evidence case per primary family for the held-out set. Include overlapping signals in both splits.
4. `README.md`: field definitions, labelling rules, dataset counts, and synthetic-data limitations.

Keep expected labels and scenario-family metadata out of detector inputs. Split by scenario variant, not just changed customer names; avoid near-duplicate development and held-out conversations. The detector developer may inspect development labels but should not use held-out cases to tune prompts.

### Definition of done for task one

All 36 traces have reviewed labels and valid evidence references. Tool outcomes, agent claims, and labels are internally consistent. The dataset contains all three verdicts in each family, and another teammate can understand the intended decision from the supplied evidence. Freeze the held-out set before detector tuning.

## PoC acceptance and demo

The pipeline must find examples of all three signals, attach valid evidence to every finding, and group repeated patterns without double-counting runs. It must distinguish signal matches from absent lookalikes and abstain when evidence is missing.

For the 12 held-out cases, report raw outcomes per signal, precision, recall, and how often the detector abstains, evaluating all three labels for each run. Count abstentions on known present signals as missed detections. Assess insufficient-evidence labels separately; do not treat them as negatives. The small synthetic set demonstrates feasibility; it does not establish production accuracy. Any false alarms or misses must remain visible in the demo report.

Demo sequence: show a technically successful conversation → reveal the customer failure and evidence → open the grouped issue and affected runs. A proposed fix and rerun is a later extension.

## Delivery boundaries

Budget approximately four hours for the PoC: dataset 45 minutes, importer 30 minutes, detector 75 minutes, grouping 45 minutes, and evaluation 45 minutes. Use the remaining hackathon time for an issue inbox, fresh sample-agent runs, one fix-and-rerun example, and pitch rehearsal.

Production integrations, live monitoring, automatic deployment of fixes, trend significance, authentication, billing, and a polished dashboard are outside the first milestone. The immediate handoff is the dataset task above; detector and interface work follow once its inputs and labels are ready.
