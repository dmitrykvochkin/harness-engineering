# harness-ai — Pydantic AI agents & data pipeline

Python side of the repo: typed agents built with [Pydantic AI](https://ai.pydantic.dev) and the agent-failure-detection pipeline from [docs/agent-failure-detection-prd.md](../docs/agent-failure-detection-prd.md).

## Layout

```
ai/
├── pyproject.toml        # uv package manifest (workspace member)
├── src/harness_ai/
│   ├── conversations/    # typed models for recorded traces (traces.jsonl)
│   └── pipeline/
│       ├── importer.py   # load traces.jsonl
│       ├── detect.py     # Pydantic AI detector agent (typed findings)
│       ├── group.py      # findings -> grouped issues
│       ├── evaluate.py   # findings vs human labels -> report
│       └── cli.py        # `harness-ai` entry point
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

# Run the pipeline over a conversations directory (expects traces.jsonl)
uv run harness-ai ../data/conversations

# The detector uses the offline 'test' model by default — no API key needed.
# Swap to a real model in src/harness_ai/pipeline/detect.py when ready.
```

## Data

Input data lives in [`../data/conversations/`](../data/conversations/) — `traces.jsonl`, `labels.jsonl`, and `split.json` as specified in the PRD.
