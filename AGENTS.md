# AGENTS.md — CodeAtlas Operating Contract

## Project Profile

| Item | Current fact |
|---|---|
| Project | CodeAtlas |
| Purpose | Open-source codebase intelligence web application |
| Product focus | Repository architecture, source-cited questions, and change-impact analysis |
| Portfolio focus | AI engineering with production web-development depth |
| Repository state | Scaffolded Python analysis service and TypeScript web application |
| Primary branch | `main` |

## Product Direction

CodeAtlas helps developers understand unfamiliar repositories. The approved direction is a deployed web product backed by a framework-neutral analysis core. Initial product work should favor public repositories, precise file and symbol evidence, interactive architecture exploration, and useful feature-impact guidance.

Do not silently expand the initial product into autonomous code mutation, pull-request creation, arbitrary-language support, or multi-agent orchestration. Those remain later design choices.

## User Authority

The user's latest explicit instruction controls intent, scope, priorities, and trade-offs. Analysis and planning remain read-only unless implementation or mutation is requested. System, platform-safety, privacy, and legal constraints remain higher authority.

## Safety and Git

- Preserve unrelated and concurrent work. Never stash, reset, restore, rebase away, stage, commit, clean, push, publish, or deploy it.
- Do not delete, move, rename, or discard maintained files without explicit authorization for that scope.
- Do not create branches, worktrees, commits, releases, deployments, or remote changes unless requested.
- Re-read owned paths before editing and stop an overlapping edit if the path changed concurrently.
- Do not add or upgrade dependencies until the user approves the stack or dependency change.
- Before publication, select an explicit open-source license and verify that no credentials, runtime state, private data, or copied material with incompatible terms are included.

## Current Stack

- `analysis/`: Python 3.12, FastAPI, Pydantic, Uvicorn, uv, pytest, Ruff, and strict mypy.
- `web/`: Next.js App Router, React, TypeScript, Tailwind CSS, Vitest, ESLint, and Fallow under npm.
- The FastAPI OpenAPI document is the HTTP contract authority. Generated clients must derive from it rather than maintaining a second handwritten schema.
- Runtime and deployment providers remain unselected adapters.


## Session Bootstrap

At the start of a new session, read `AGENTS.md`, `.pi/state.md`, `.pi/tech-stack.md`, and `.pi/roadmap.md` before proposing or changing code. `.pi/state.md` is the detailed handoff and must distinguish observed facts, approved decisions, proposals, and unresolved questions. Update it after each significant implementation session.

## Architecture Boundaries

Keep these responsibilities separable:

```text
framework-neutral core
  repository model, symbol extraction, retrieval, ranking, citations, evaluation

adapters
  source hosts, model providers, graph stores, vector stores, deployment platforms

web application
  repository explorer, architecture visualization, cited questions, analysis reports
```

A Pi, MCP, model-provider, database, or deployment integration is an adapter unless the user explicitly approves it as a product requirement. Re-check dependencies and platform assumptions before carrying patterns between projects.

Answers about source code must distinguish verified source facts from model inference and cite concrete repository paths or symbols when available.

## Evidence and Reuse

Current target source, tests, and configuration are authoritative. A healthy code graph is a locator, not authority; verify graph hits against source. Search reviewed current-project code before the inspiration library at `<work-root>/inspo`.

When adapting inspiration, preserve the smallest useful invariant and prove it in CodeAtlas. Independently rewritten ideas require no provenance ceremony. If upstream files or substantial expressive material are copied or distributed, identify the exact source, check applicable terms, and retain required notices.

## Editing

Read current source and nearby contracts before changing them. Prefer targeted edits and small verified slices. Do not create backup, duplicate, generated, speculative, or version-suffixed files. Identify generators before editing generated output.

## Code Quality Gates

Code-smell enforcement is executable, not subjective. Python changes must pass Ruff formatting and linting, strict mypy, and pytest. Web changes must pass Vitest, ESLint, TypeScript, Fallow, and a production Next.js build. Fallow blocks dead code, duplicate blocks, cycles, dependency drift, boundary violations, and configured complexity limits. Keep the baseline clean and block new regressions rather than hiding findings.

## Verification

Run the narrowest relevant check first. Before completion, run the repository gate from the root:

```bash
./scripts/verify.sh
```

Inspect owned diffs and report observed exit status and output.

Before reporting repository work complete, report the absolute checkout, branch, HEAD, changed paths, status, verification performed, and remaining risks. Do not claim commit, push, deployment, publication, or release unless it occurred.
