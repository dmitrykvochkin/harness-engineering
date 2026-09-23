# Harness Engineering

Find where AI agents fail customers — even when every request succeeds.

Two sub-projects in one repo:

| Folder | Stack | Purpose |
|---|---|---|
| [`ai/`](ai/README.md) | Python 3.14, uv, Pydantic AI | Agents + data pipeline: traces → failure detection → grouped issues → evaluation |
| [`web/`](web/README.md) | Next.js 16, TypeScript, Tailwind v4, pnpm | Dashboard for grouped issues and evaluation reports |

Shared input data (recorded conversation traces) lives in [`data/`](data/) — see [`docs/agent-failure-detection-prd.md`](docs/agent-failure-detection-prd.md) for the product context.

## Quick start

```bash
# Python side (agents + pipeline)
cd ai
uv sync
uv run pytest
uv run harness-ai ../data/conversations

# Web side (dashboard)
cd web
pnpm install
pnpm dev   # http://localhost:3000
```

## Docker Compose (web dev + Postgres)

Starts the Next.js dev server and a Postgres 17 database:

```bash
docker compose up
```

- Web: http://localhost:3000 (override with `WEB_PORT`)
- Postgres: `127.0.0.1:45532` (override with `POSTGRES_PORT`) — an uncommon port, bound to loopback, since other Postgres servers already run on 5432/5438. Copy `.env.example` to `.env` to change ports.
- Inside the compose network the app reaches the DB at `db:5432` via `DATABASE_URL=postgresql://postgres:postgres@db:5432/harness`.
- `node_modules` and `.next` live in named volumes so host/container installs don't conflict.

## Layout

```
harness-engineering/
├── ai/           # Pydantic AI project (uv workspace member)
├── web/          # Next.js App Router project
├── data/         # shared input data (traces, labels, splits)
├── docs/         # PRD and other docs
├── skills/       # agent skills (speckit workflows)
├── .specify/     # spec-driven workflow templates
└── pyproject.toml # uv workspace root (members: ai)
```
