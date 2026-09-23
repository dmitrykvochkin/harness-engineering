# web — Next.js dashboard

Next.js side of the repo (App Router, TypeScript, Tailwind CSS v4). Will host the UI for the agent-failure-detection pipeline: grouped issues, affected runs, and evaluation reports.

## Setup

Requires Node 20+ and [pnpm](https://pnpm.io) (pinned via `packageManager`).

```bash
cd web
pnpm install
```

## Usage

```bash
pnpm dev    # development server at http://localhost:3000
pnpm build  # production build
pnpm start  # serve the production build
pnpm lint   # eslint
```

## Notes

- `AGENTS.md`/`CLAUDE.md` are auto-managed by `next dev` — commit them with your work; removing them from a diff just re-creates the change.
- `pnpm-workspace.yaml` holds pnpm config for this folder only (it is not a monorepo workspace root).
- The Python agents/pipeline live in [`../ai`](../ai/README.md); shared input data in [`../data`](../data/).
