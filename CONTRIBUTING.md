# Contributing to CodeAtlas

CodeAtlas is licensed under Apache-2.0 and remains pre-release while its security and deployment blockers are resolved. Contributions are accepted under the same license.

## Development setup

Required runtimes are Python 3.12, uv 0.11.32 or compatible, Node.js 26, and npm 12.

```bash
git clone <repository-url>
cd codeatlas
cd analysis && uv sync --locked && cd ..
npm ci --prefix web
./scripts/verify.sh
```

Run the FastAPI service and Next.js application in separate terminals:

```bash
cd analysis && uv run uvicorn codeatlas_analysis.api:app --reload
cd web && npm run dev
```

The web server uses `CODEATLAS_ANALYSIS_URL` and defaults to `http://127.0.0.1:8000`.

## Change guidelines

- Keep repository, retrieval, citation, and impact logic framework-neutral.
- Keep GitHub, embedding providers, storage, and deployment systems behind adapters.
- Derive web HTTP types from FastAPI OpenAPI with `npm run generate:api`.
- Add observable behavior tests before implementation changes.
- Preserve explicit insufficient-evidence and controlled-failure paths.
- Do not add autonomous code changes, pull-request creation, or unsupported languages to the initial product boundary.

## Before opening a pull request

Run the same command used by CI:

```bash
./scripts/verify.sh
```

Describe the user-visible behavior, controlled failure, tests run, and any remaining limitations. Never include credentials, downloaded repository data, generated runtime state, or private source.

## Security reports

Follow [SECURITY.md](SECURITY.md). Do not disclose an exploitable vulnerability in a public issue.
