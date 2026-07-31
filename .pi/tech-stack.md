# CodeAtlas Tech Stack

Detected and approved on 2026-07-31.

## Architecture

| Area | Technology | Detected version |
|---|---|---|
| Web runtime | Node.js | 26.5.0 |
| Web package manager | npm | 12.0.1 |
| Web framework | Next.js App Router | 16.2.12 |
| UI runtime | React | 19.2.4 |
| Language | TypeScript | 5.9.3 |
| Styling | Tailwind CSS | 4.x |
| Web tests | Vitest | 4.1.10 |
| Web smell analysis | Fallow | 3.10.0 |
| OpenAPI type generator | openapi-typescript | 7.13.0 |
| OpenAPI runtime client | openapi-fetch | 0.17.0 |
| Analysis runtime | Python | 3.12.13 |
| Python package manager | uv | 0.11.32 |
| API framework | FastAPI | 0.141.1 |
| Validation | Pydantic | 2.13.4 |
| Syntax parser | py-tree-sitter | 0.26.0 |
| TypeScript/TSX grammar | tree-sitter-typescript | 0.23.2 |
| ASGI server | Uvicorn | 0.52.0 |
| Python tests | pytest | 9.1.1 |
| Python lint/format | Ruff | 0.16.1 |
| Python types | mypy | 2.3.0 |

## Authoritative manifests

- `web/package.json` and `web/package-lock.json`
- `analysis/pyproject.toml` and `analysis/uv.lock`
- `web/.fallowrc.json`

## Commands

```bash
# Full repository gate
./scripts/verify.sh

# Analysis service
cd analysis
uv run pytest
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests

# Web application
cd web
npm run generate:api
npm run test
npm run lint
npm run typecheck
npm run quality
npm run build
```

## Generated and runtime paths

Do not maintain or commit `.venv/`, `node_modules/`, `.next/`, Python caches, test caches, coverage output, or `.fallow/` runtime state.

## Known setup risk

`npm audit` currently reports 3 high-severity advisories through Next.js, PostCSS and Sharp. The OpenAPI packages were separately audited clean with pinned minimatch and brace-expansion overrides. npm suggests an incompatible Next.js downgrade for the remaining findings, so it was not applied. Reassess upstream fixed releases before publication or deployment.
