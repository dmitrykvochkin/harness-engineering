# harness-ai — Pydantic AI agents & data pipeline

Python side of the repo: the Pydantic AI signal classifier from [docs/signal-pipeline-spec.md](../docs/signal-pipeline-spec.md), plus the synthetic dataset and Supabase upload for the [agent-failure-detection PRD](../docs/agent-failure-detection-prd.md).

## Layout

```
ai/
├── pyproject.toml        # uv package manifest (workspace member)
├── classify.py           # signal classifier (see below)
├── src/harness_ai/
│   ├── conversations/    # typed models + loader for recorded traces (traces.jsonl)
│   ├── dataset/          # authored synthetic scenarios + builder for data/conversations/
│   └── db/               # Supabase row models + `harness-upload`
└── tests/
```

## Setup

Requires [uv](https://docs.astral.sh/uv/) (Python 3.14, managed via `.python-version`).

```bash
cd ai
uv sync
```

## Usage

```bash
# Run tests
uv run pytest
```

## Signal classifier (`classify.py`)

A single script that implements [docs/signal-pipeline-spec.md](../docs/signal-pipeline-spec.md). It runs three independent Pydantic AI detectors (`user_frustration`, `task_failure`, `forgetting`) over every trace and writes one JSONL record per trace:

```bash
# NEBIUS_API_KEY in ai/.env (loaded automatically; a shell variable takes precedence)
uv run python classify.py \
  --input ../data/conversations/traces.jsonl \
  --output results.jsonl
```

- **Model.** The default is `nebius:deepseek-ai/DeepSeek-V4.1-Flash` on Nebius AI Studio, which reads `NEBIUS_API_KEY`. `--model` takes any other Pydantic AI `provider:model` string, such as `openai:gpt-6-luna` with `OPENAI_API_KEY` (which goes through the Responses API) or `anthropic:claude-sonnet-5` with `ANTHROPIC_API_KEY`. `--reasoning minimal|low|medium|high|xhigh` sets the reasoning effort on models that support it; without it, each model uses its own default. All three agents use the same model. Nebius responses carry a non-standard `metadata` field that breaks OpenAI schema validation, so `nebius:` models go through a small `NebiusChatModel` subclass that drops it. `--model test` runs offline, but the evidence check rejects its placeholder IDs, so every signal comes back as an error.
- **Input.** The model sees only `run_id` and `events`. Trace metadata (policies, tool semantics, capture status, session note) becomes `ctx-<run_id>-*` context events so detectors can cite it. The script never reads `labels.jsonl` or `split.json`. The whole file is validated before any model call, and a malformed line stops the run with its line number.
- **Evidence check.** This runs as an output validator. If the model cites an ID that isn't in the trace, or gives a `present` verdict without enough evidence, it is asked to fix the output. That uses the single allowed output retry.
- **Output.** Each record is `{run_id, model, signals, errors}`. A failed detector (API error, or output that is still invalid after the one retry) gets `null` in `signals` and a message in `errors`. The output file is overwritten on each run. `max_tokens` is set to 16384 because reasoning models can use up a provider's default limit before they answer.
- **Run metadata.** `results.jsonl` gets a companion `results.meta.json` with the model, start and end time, wall time, and seconds per agent run (mean, p50, p95, max). It also holds token usage (requests, input, output, cache and reasoning tokens), cost, settings, a hash of the prompts, and package versions. Everything is broken down per signal and per trace, so runs with different models or prompts can be compared. Cost comes from [`genai-prices`](https://github.com/pydantic/genai-prices), which ships with Pydantic AI and covers Anthropic, OpenAI and others. It has no Nebius prices, so the `PRICES` dict in `classify.py` holds them for DeepSeek-V4.1-Flash, GLM-5.3-Flash and Qwen3.5-397B-A17B. For any other model, add it there or pass `--input-price` and `--output-price` in USD per 1M tokens (cache discounts are ignored). Without prices, cost is `null`.
- **Exit code.** `0` when every classification completed, `1` when any signal errored, `2` for input or output problems.

Tested with Python 3.14.5, pydantic-ai 2.48.0 and pydantic 2.13.5 against `nebius:deepseek-ai/DeepSeek-V4.1-Flash`.

## Data

Input data lives in [`../data/conversations/`](../data/conversations/) — `traces.jsonl`, `labels.jsonl`, and `split.json` as specified in the PRD. See its [README](../data/conversations/README.md) for fields and labelling rules.

The files are generated from `src/harness_ai/dataset/scenarios_*.py`:

```bash
uv run python -m harness_ai.dataset.build
```

## Uploading to Supabase

The schema lives in [`../supabase/migrations/`](../supabase/migrations/):

- `runs` and `events` hold the traces (detector input). They are readable with the publishable key.
- `run_labels` and `signal_labels` hold the ground truth. They have no row-level-security policy, so only the secret key can read them.
- `signals` and `issues` hold detector output. They start empty and are read by the edge functions.

Row models that mirror these tables are in `src/harness_ai/db/rows.py`.

Apply the migrations once, either in the Supabase SQL editor or with `supabase db push`. Then run:

```bash
uv run harness-upload --dry-run   # validate and count rows, no network
uv run harness-upload             # upsert data/conversations/ into Supabase
```

The uploader reads `SUPABASE_URL` and `SUPABASE_SECRET_KEY` from the environment or from `ai/.env`. Re-running it is safe: it upserts by key and prunes stale rows for this dataset, and it never touches `signals` or `issues`.

Detector output is a separate step. Apply `supabase/migrations/` (the `signals.verdict` check must allow `error`), then:

```bash
uv run harness-upload-results --dry-run
uv run harness-upload-results   # upserts ai/results.jsonl into public.signals
```

A null signal with an `errors` entry is stored as verdict `error`. Re-running replaces rows for the same run, signal, and model.
