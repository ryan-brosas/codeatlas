# CodeAtlas

CodeAtlas is an open-source codebase intelligence product for understanding unfamiliar repositories before changing them.

The product direction combines:

- navigable repository architecture;
- questions answered with concrete file and symbol evidence;
- explicit separation between verified source facts and model inference;
- feature-location and change-impact guidance.

## Repository structure

```text
analysis/   Python repository-analysis and evidence API
web/        Next.js product interface
scripts/    Cross-stack project checks
.pi/        Detected project context for Pi
```

The framework-neutral analysis core stays separate from GitHub, model-provider, graph-store, vector-store, and deployment adapters.

## Live demo

[Open the bounded CodeAtlas demo](https://web-production-f07d2d.up.railway.app). The public web service calls a private analysis service and supports public TypeScript and JavaScript repositories.

## Development

### Analysis API

```bash
cd analysis
uv sync --locked
uv run uvicorn codeatlas_analysis.api:app --reload
```

The current API exposes `GET /v1/health`, `POST /v1/repositories`, synchronous `POST /v1/architecture`, `POST /v1/questions`, `POST /v1/impact`, and generated OpenAPI documentation at `/docs`.

### Web application

```bash
cd web
npm ci
npm run dev
```

Open `http://localhost:3000`. The web server calls the analysis service at `http://127.0.0.1:8000` by default; set `CODEATLAS_ANALYSIS_URL` to override it. Regenerate the OpenAPI client contract with `npm run generate:api`.

## Verification

Run every current check from the repository root:

```bash
./scripts/verify.sh
```

This covers Python formatting, linting, strict typing and tests, plus web tests, ESLint, TypeScript, deterministic code-smell analysis, and the production build.

## Project status

Phase 2 structural understanding, Phase 3 cited questions, and Phase 4 change impact are implemented. A user can analyze a bounded public TypeScript or JavaScript repository, inspect commit-pinned architecture, ask deterministic cited questions, and trace candidate change locations into direct and transitive dependent modules. Semantic retrieval uses the same evidence contract through an injected embedding protocol; no model or embedding provider dependency is selected. Reports expose confidence, unresolved evidence, traversal limits, and the warning that dependency proximity is not certainty.

A live `sindresorhus/p-map` impact probe located `pMap` at `index.js:1` and cited three direct dependents at their import lines. The complete local gate currently covers 89 Python tests and 12 web tests. The web dependency graph now audits clean through tested PostCSS and Sharp overrides. Process-local request, repository, concurrency, timeout, memory, and five-minute commit-keyed snapshot-cache bounds protect the deployed single-replica demo. Railway serves only the web publicly; live architecture, cited-question, impact, HTTPS hardening, and rate-limit behavior have been verified.

## License

CodeAtlas is licensed under the [Apache License 2.0](LICENSE).


## Contribution and deployment guidance

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Deployment architecture and blockers](docs/deployment.md)

CI is defined in `.github/workflows/verify.yml` and runs the same `./scripts/verify.sh` gate on pull requests and pushes to `main`.
