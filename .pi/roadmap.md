---
purpose: Outcome-oriented roadmap for CodeAtlas
updated: 2026-08-01
status: complete
---

# CodeAtlas Roadmap

This roadmap gives future sessions direction without turning ordinary work into a mandatory task lifecycle. `.pi/state.md` remains the current-position authority.

## Overview

| Phase | Outcome | Status |
|---|---|---|
| 0. Foundation | Reproducible Python and web scaffold with strict quality gates | Complete |
| 1. Repository intake | Accept and track one bounded public repository | Complete |
| 2. Structural understanding | Build a source-backed repository and symbol model | Complete |
| 3. Cited questions | Answer repository questions with inspectable evidence | Complete |
| 4. Change impact | Explain implementation location and likely blast radius | Complete |
| 5. Public release | Deploy a safe demo and publish a contribution-ready repository | Complete |

## Phase 0: Foundation

**Outcome:** A maintainable full-stack base that proves both services run and blocks obvious quality regressions.

**Completed evidence:**

- [x] Git repository initialized on `main`.
- [x] FastAPI health endpoint and behavior test.
- [x] Next.js App Router landing page and accessibility-oriented component test.
- [x] Python Ruff, strict mypy and pytest gates.
- [x] Web Vitest, ESLint, TypeScript, Fallow and production-build gates.
- [x] Cross-stack `./scripts/verify.sh` command.
- [x] Live HTTP probes for API and homepage.
- [x] Detailed stack and handoff context.

**Deferred:** commit, remote and deployment.

## Phase 1: Repository Intake

**Outcome:** A user can submit one supported public repository and receive a stable identity and observable analysis state.

**Success criteria:**

- [x] Versioned OpenAPI request, success response and typed error response.
- [x] Public GitHub URL normalization and controlled rejection behavior.
- [x] Deterministic repository identity independent of UI or provider implementation.
- [x] Explicit state model such as pending, processing, ready and failed.
- [x] Web form connected to the generated API contract.
- [x] Accessible pending, success and error presentation.
- [x] Tests make no paid API calls and do not require GitHub credentials.

**Boundary:** start with an in-memory adapter. Do not silently add cloning, persistence or background infrastructure.

## Phase 2: Structural Understanding

**Outcome:** CodeAtlas can explain the shape of one TypeScript or JavaScript repository from parsed source evidence.

**Success criteria:**

- [x] Bounded repository acquisition with size, path and file-type limits.
- [x] Repository, file, module and symbol domain model.
- [x] Imports and symbol relationships represented without requiring an LLM.
- [x] Incremental or repeatable analysis with deterministic fixtures.
- [x] Architecture view cites concrete source paths and symbols.
- [x] Parser and acquisition adapters remain replaceable.

**Deferred:** semantic retrieval and model-generated answers until structural evidence is trustworthy.

## Phase 3: Cited Questions

**Outcome:** A developer can ask a repository question and inspect why the answer is supported.

**Success criteria:**

- [x] Semantic and structural retrieval use a shared evidence contract.
- [x] Every source claim cites repository paths or symbols.
- [x] Model inference is labeled separately from verified facts.
- [x] Empty, unsupported and insufficient-evidence cases are explicit.
- [x] Provider adapters keep model choice outside the domain core.
- [x] Evaluation fixtures measure retrieval relevance and citation support.

## Phase 4: Change Impact

**Outcome:** CodeAtlas identifies likely implementation boundaries and affected code without modifying the repository.

**Success criteria:**

- [x] Feature-location analysis names candidate modules with evidence.
- [x] Impact traversal explains direct and transitive relationships.
- [x] Confidence and missing evidence are visible.
- [x] Reports avoid claiming certainty from graph proximity alone.
- [x] Representative open-source repositories demonstrate useful output.

**Out of scope:** autonomous edits and pull-request creation.

## Phase 5: Public Release

**Outcome:** A recruiter or contributor can understand, run, evaluate and safely contribute to CodeAtlas.

**Success criteria:**

- [x] Open-source license selected and added.
- [x] npm audit advisories resolved or explicitly risk-accepted with compensating controls.
- [x] Deployment architecture, secrets, quotas and cleanup documented.
- [x] Live demo uses bounded public data and abuse controls.
- [x] README includes a concise demo, architecture and measured results.
- [x] CONTRIBUTING and SECURITY guidance exist.
- [x] CI runs the same repository verification gate used locally.
- [x] Public `main` reflects the deployed release documentation, configuration, and bounded-control source.

## Roadmap Rules

- Move a phase only when its observable success criteria are proven.
- Update `.pi/state.md` after significant sessions; update this roadmap only when outcomes or ordering change.
- Treat provider, storage and deployment selections as explicit decisions, not defaults inherited from inspiration projects.
- Prefer one complete vertical behavior over parallel unfinished infrastructure.
