---
purpose: Detailed current state and cross-session handoff for CodeAtlas
updated: 2026-08-01
status: phase-5-complete-live-public
---

# CodeAtlas State and Session Handoff

## One-Minute Brief

CodeAtlas is a new codebase-intelligence product intended to demonstrate AI-engineering depth and production web-development skill. It will help developers understand unfamiliar repositories through navigable architecture, source-cited answers, and change-impact guidance.

Phases 0–4 are implemented. CodeAtlas analyzes bounded public TypeScript and JavaScript repositories into commit-pinned architecture, deterministic cited answers, an injected semantic-retrieval seam, and source-backed change-impact reports. Impact reports locate an implementation candidate, traverse direct and transitive reverse dependencies, cite import lines, expose confidence and missing evidence, and warn that proximity is not certainty. The web exposes all three verticals. Phase 5 is complete. Apache-2.0, CI, contribution and security guidance, an audit-clean dependency graph, bounded abuse controls, and a two-service Railway deployment are public and verified. The public web service uses private networking to analysis; live architecture, cited-question, impact, HTTPS hardening, canonical repository limiting, and rate-limit behavior passed. Public `main` contains the deployed release documentation, configuration, tests, and bounded-control source.

## Current Position

| Item | Current value |
|---|---|
| Checkout | `<repository-root>` |
| Branch | `main` |
| HEAD | `main` tracks `origin/main`; use `git rev-parse HEAD` for the current commit |
| Worktree | Modified by the approved Phase 5 release-readiness slice; no commit requested |
| Current phase | Phase 5 complete; live deployment and public source verified |
| Last full verification | `./scripts/verify.sh`, exit 0 on 2026-08-01 with 82 Python and 12 web tests |
| Publication status | Source public at `https://github.com/ryan-brosas/codeatlas` under Apache-2.0 and synchronized with the live demo at `https://web-production-f07d2d.up.railway.app` |

The bounded Railway demo and matching public source are live. The demo is not a production SLA-backed service.

## Approved Product Decisions

1. Position the portfolio around **full-stack AI engineering / AI product engineering**.
2. Build CodeAtlas as a public-facing web product rather than making Pi configuration the portfolio centerpiece.
3. Use a **Python AI core plus TypeScript web application**.
4. Use **FastAPI + Pydantic** for the analysis API and **Next.js App Router + React + TypeScript** for the product interface.
5. Keep the analysis core framework-neutral. GitHub, model providers, graph stores, vector stores, and deployment systems are adapters.
6. Treat the FastAPI-generated OpenAPI document as the HTTP contract authority. Do not maintain a conflicting handwritten schema.
7. Support public TypeScript and JavaScript repositories first.
8. Separate verified source facts from model inference and attach concrete file or symbol evidence to source claims.
9. Keep autonomous code mutation, pull-request creation, arbitrary-language support, and multi-agent orchestration outside the initial boundary.
10. Enforce code quality through executable gates rather than subjective review alone.
11. Acquire public source through GitHub REST ZIP archives pinned to a resolved full commit SHA; keep HTTP and source-host behavior replaceable.
12. Parse TypeScript and JavaScript through a Python tree-sitter adapter while keeping repository structure and parser injection framework-neutral.
13. Run the initial bounded architecture analysis synchronously through `POST /v1/architecture`; defer durable jobs until deployment workload and persistence requirements are selected.
14. Establish deterministic verified-source facts and citations before introducing semantic retrieval or model-generated prose.
15. Keep embedding/model choice outside the core through injected retrieval and embedding protocols; no provider dependency is selected without measured value and approval.
16. Model change impact as bounded reverse traversal over resolved source relationships, with confidence and explicit uncertainty rather than certainty from proximity.

## Current Architecture

```text
web/                         Next.js product interface
  src/app/                   App Router shell and landing page
  src/features/landing/      Cohesive landing-page sections
  src/features/repository-intake/  Analysis, question and impact forms with generated actions
  src/lib/api/generated.d.ts OpenAPI-generated HTTP contract
  .fallowrc.json             Dead-code, duplication, cycle and complexity policy

analysis/                    Python analysis and evidence service
  src/codeatlas_analysis/    FastAPI package, intake core and bounded snapshot reader
  src/codeatlas_analysis/github_repository_source.py  GitHub REST/archive adapter
  src/codeatlas_analysis/repository_structure.py       Repository/file/module/symbol evidence
  src/codeatlas_analysis/tree_sitter_parser.py         TypeScript/JavaScript syntax adapter
  src/codeatlas_analysis/architecture_view.py           Source-cited architecture projection
  src/codeatlas_analysis/repository_analysis.py         Acquisition-to-view application service
  src/codeatlas_analysis/retrieval.py                   Deterministic verified-source retrieval
  src/codeatlas_analysis/cited_answers.py                Fixed cited fact contract
  src/codeatlas_analysis/semantic_retrieval.py            Injected semantic evidence ranking
  src/codeatlas_analysis/change_impact.py                 Bounded reverse impact traversal
  tests/                     Public behavior and failure-contract tests
  pyproject.toml             Runtime and strict quality configuration

scripts/generate-api-client.sh  Deterministic FastAPI-to-TypeScript generation
scripts/verify.sh            Cross-stack completion gate
.github/workflows/verify.yml  Pull-request and main-branch CI gate
docs/deployment.md           Provider-neutral production controls
CONTRIBUTING.md / SECURITY.md  Pre-publication contribution and security guidance
.pi/tech-stack.md            Exact detected versions and commands
.pi/roadmap.md               Outcome-oriented project phases
AGENTS.md                    Operating contract and safety boundaries
```

The intended future responsibility split is:

```text
framework-neutral analysis core
  repository model, symbol extraction, retrieval, ranking, citations, evaluation

adapters
  source hosts, model providers, graph stores, vector stores, deployment platforms

web application
  repository explorer, architecture visualization, cited questions, reports
```

## Verified Current Behavior

### Analysis service

Source: `analysis/src/codeatlas_analysis/api.py`

- A FastAPI application exists with title `CodeAtlas Analysis API` and version `0.1.0`.
- `GET /v1/health` returns HTTP 200 with:

```json
{
  "service": "codeatlas-analysis",
  "status": "ok"
}
```

- The response is validated through a Pydantic `HealthResponse` model.
- `POST /v1/repositories` accepts `{ "repository_url": string }` and returns HTTP 202.
- Public GitHub URLs are normalized to lowercase `github.com/owner/repository` identities; `.git`, `www.github.com`, and a trailing slash normalize to the same identity.
- Non-HTTPS, unsupported-host, credentialed (including empty userinfo), port-bearing, query, fragment, ASCII-control-bearing, malformed and ambiguous paths return stable typed HTTP 400 errors. Missing request fields return the same typed envelope with HTTP 422.
- New submissions enter the explicit `pending` state; the domain vocabulary also defines `processing`, `ready`, and `failed`.
- `InMemoryRepositoryIntake` stores records without GitHub calls, credentials, persistence or background jobs.
- The endpoints are tested through FastAPI/Starlette `TestClient` in `analysis/tests/test_health.py` and `analysis/tests/test_repository_intake.py`.
- Generated OpenAPI at `/docs` describes repository intake plus `POST /v1/architecture`, its `ArchitectureView` success schema, and shared typed 400/413/422/502 errors; focused contract tests cover both endpoint families.
- `POST /v1/architecture` validates a public GitHub URL and synchronously composes bounded acquisition, parsing, relationship resolution and architecture projection through an injected `RepositoryAnalysis` service.
- Architecture responses cite the exact 40-character revision, module paths, exported symbol names and source lines, relationships, and explicit limitations.
- Acquisition-limit failures map to HTTP 413; controlled GitHub/archive failures map to HTTP 502 without leaking stack traces.
- A deterministic injected-source API test requires no network. A live full-path probe returned HTTP 200 for `sindresorhus/yocto-queue` at `b07eac099753833b29d06c614149904445739776` with 4 modules, 4 relationships and 2 explicit limitations.

### Deterministic retrieval

- `retrieval.py` defines immutable `SourceCitation`, `RetrievedEvidence` and `RetrievalResult` contracts independent of FastAPI, embeddings and model providers.
- Evidence kinds cover modules, symbols and relationships. Every returned item is labeled `verified_source` and carries a concrete path, line range, optional symbol, matched query terms and deterministic score.
- Query normalization splits path and camel-case words, removes common question terms and applies one narrow `-ing` normalization so questions such as “account load function” match `loadAccount` without fuzzy model behavior.
- Ranking prefers stronger term coverage, then symbols, relationships and modules, followed by stable path/line/symbol ordering. A caller-provided limit bounds output.
- Empty, stop-word-only, non-positive-limit and unmatched queries return `insufficient_evidence` with no fabricated evidence.
- Representative pytest evaluation fixtures require the expected function, class and interface citation to rank first. No paid API, embedding or model call is used.

### Deterministic cited questions

- `cited_answers.py` defines immutable cited facts and answers. Facts use fixed templates over retrieved module, symbol or relationship evidence; they do not summarize source or invent behavior.
- `CitedAnswer` separates verified `facts`, raw ranked `evidence`, and a future `inference` tuple. The inference tuple is empty in every current path.
- Blank questions are `unsupported`; unmatched questions are `insufficient_evidence`; neither produces facts or evidence. Matched questions are `answered`, and each fact includes its source citation.
- `RepositoryAnalysis.answer` composes bounded acquisition, parsing, retrieval and fact construction. `POST /v1/questions` exposes the generated `RepositoryQuestionRequest` and `CitedAnswer` schemas with typed 400/413/422/502 errors.
- The generated web action posts questions after architecture analysis. The accessible UI shows loading, typed errors, insufficient/unsupported messages, verified facts, path/line citations and “No model inference used.”
- A live full-path question probe for `sindresorhus/yocto-queue` returned HTTP 200 and cited `Queue` at `index.d.ts:1` and `index.js:15` with an empty inference list.
- Question requests currently reacquire and reparse source. This avoids hidden persistence but is not suitable for deployment-scale rate limits without stored revision artifacts or caching.

### Repository acquisition

- `repository_acquisition.py` defines immutable acquisition limits, repository snapshots and source files without FastAPI or GitHub coupling.
- ZIP snapshots are decoded in memory. Only UTF-8 `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs` and `.json` files are retained in deterministic path order.
- Defaults cap downloads at 20 MiB, entries at 10,000, selected files at 5,000, declared uncompressed content at 50 MiB, individual files at 512 KiB, paths at 20 components and requests at 10 seconds.
- Absolute, traversal and backslash paths are rejected; duplicate paths and malformed archives are rejected; symbolic links are ignored. No archive content is written to disk or executed.
- `github_repository_source.py` resolves the latest default-branch commit, validates a full 40-character SHA and requests the ZIP by that SHA.
- The urllib adapter permits only HTTPS `api.github.com` and `codeload.github.com` origins, validates redirects before following them, checks declared and streamed byte lengths, and sends an explicit user agent and GitHub API version.
- Network transport and GitHub source behavior are replaceable protocols. Unit tests use deterministic in-memory archives and fake transports; a live probe acquired five files from `sindresorhus/yocto-queue` at commit `b07eac099753833b29d06c614149904445739776`.
- Acquisition is intentionally not wired into `POST /v1/repositories` until the execution/job boundary is selected.

### Structural source model

- `repository_structure.py` defines immutable repository, file, module, symbol, module-dependency, source-span and parse-diagnostic contracts without tree-sitter, FastAPI or model-provider concepts.
- Repository assembly preserves JSON as file evidence and invokes the injected parser only for TypeScript, TSX, JavaScript and JSX modules.
- Top-level classes, enums, functions, interfaces, type aliases and simple variable declarations carry export visibility and one-based source lines/UTF-8 byte columns.
- Static imports and re-exports carry source spans. Relative paths resolve only when exactly one acquired source candidate matches; bare imports are external, missing paths are unresolved and multiple matches are explicitly ambiguous.
- Default, named, aliased and namespace imports plus named and wildcard re-exports become `SymbolRelationship` evidence with source and target paths, target names and explicit resolution states.
- Relationships connect only to verified exported symbols. Default exports expose `default` separately from their declaration names, and named/wildcard re-export surfaces are computed to a fixed point so barrels and cycles resolve deterministically without recursion or an LLM.
- Tree-sitter syntax errors return partial module evidence with source-located diagnostics instead of discarding valid neighboring declarations.
- Parser injection is a callable protocol. The production adapter uses `tree-sitter` 0.26.x and `tree-sitter-typescript` 0.23.x, while deterministic tests use both the real grammar and a recording parser. Equal snapshots produce equal structure values.
- TypeScript, JavaScript and TSX grammar behavior is covered. JSON at the parser boundary is a controlled error.
- The selected package versions were executed together on Python 3.12, have compatible binary wheels and MIT licenses, and returned no OSV advisories when checked on 2026-08-01.

### Web application

Primary sources:

- `web/src/app/page.tsx`
- `web/src/features/landing/landing-sections.tsx`
- `web/src/app/layout.tsx`
- `web/src/app/globals.css`

Observed behavior:

- The homepage renders the product statement “Understand a codebase before you change it.”
- It presents a public GitHub repository URL field and an “Analyze repository” button.
- It communicates the architecture, evidence, and impact product pillars.
- The page is a server-component composition with no broad client boundary.
- The repository form submits through `web/src/features/repository-intake/submit-repository.ts`, a narrow server action backed by `openapi-fetch` and generated `paths` types.
- `npm run generate:api` exports `app.openapi()` and regenerates `web/src/lib/api/generated.d.ts`; web verification runs generation before tests and build.
- Submission displays a disabled submitting state, normalized pending identity, and typed API errors through status/alert semantics.
- The interactive client boundary is limited to `RepositoryIntakeForm`; the surrounding landing composition remains server-rendered.
- `web/src/app/page.test.tsx` covers the idle form, submitting/pending success flow, and typed error announcement.
- The generated server action calls `POST /v1/architecture` rather than merely creating a pending intake record.
- The form announces `Analyzing repository…`, disables controls during the request, presents typed errors through a named `alert`, and renders success in a labeled `status` region.
- `ArchitectureSummary` displays the normalized repository identity, pinned revision prefix, module/relationship/limitation counts, module paths, exported symbol names, kinds and source lines.
- Component tests cover idle, in-flight, architecture success and typed error behavior without GitHub calls. Earlier live Chromium intake verification remains valid for the form mechanics; the architecture result is additionally verified through component behavior and a live FastAPI end-to-end probe.

## Semantic retrieval

- `retrieval.py` now exposes neutral `EvidenceDocument`, `EvidenceRetriever`, `RetrievalMethod` and shared ranking contracts. Lexical results are explicitly marked `lexical`.
- `semantic_retrieval.py` accepts a batch `TextEmbedder` protocol, validates one finite fixed-dimension vector per text, handles zero vectors as no similarity, applies cosine similarity and a configurable threshold, and emits the same `RetrievedEvidence` contract marked `semantic`.
- A paraphrase fixture proves that “Where do users sign in?” can retrieve `validateSession` when a provider maps those concepts, while lexical retrieval correctly remains insufficient. Invalid provider batches fail with `EmbeddingContractError`; below-threshold queries remain insufficient.
- `RepositoryAnalysis` receives an `EvidenceRetriever`; the default remains lexical. Provider/model selection therefore stays outside repository, citation and impact logic. No dependency or production embedding provider was added.

## Change impact

- `change_impact.py` retrieves one implementation candidate and performs stable, bounded breadth-first traversal over resolved reverse module relationships.
- Reports include candidate evidence, direct/transitive impacted modules with relationship citations, high/medium/low location confidence, unresolved and partial-source warnings, truncation, and an unconditional proximity warning.
- `POST /v1/impact` exposes the generated `ChangeImpactReport` schema and shared typed acquisition failures. The web renders loading, controlled failure, candidate location, confidence, impact depth, citations and limitations.
- A live `sindresorhus/p-map` probe located `pMap` at `index.js:1` and cited `index.test-d.ts:2`, `test-multiple-pmapskips-performance.js:4`, and `test.js:7` as direct dependents. Two unresolved internal relationships were reported rather than hidden.

## Release readiness

- Apache-2.0 was selected after the user continued with the recommended release choice. `LICENSE` is the unmodified official Apache 2.0 text (apart from removal of one leading blank line); README, roadmap, contribution and security guidance now agree. No NOTICE file is required because no upstream file or substantial expressive implementation was copied into CodeAtlas. GitHub repository metadata links directly to the verified live demo.
- `.github/workflows/verify.yml` runs `./scripts/verify.sh` for pull requests and pushes to `main` with read-only contents permission, concurrency cancellation, lockfile-keyed npm caching, pinned uv 0.11.32, Python 3.12 and Node 26.
- A local production-runtime browser probe used the built Next.js server and a deterministic analysis stub. Six same-repository submissions returned architecture, while the seventh rendered the controlled public-demo rate-limit error. Temporary servers and Chromium were stopped afterward.
- Publication review found zero high-confidence secret patterns across 69 tracked/untracked candidate files, no files over 1 MiB, no tracked runtime directories, Apache-2.0 repository metadata, GitHub secret scanning and push protection enabled, and expected permissive or data licenses in the production lock graph. Optional Sharp/libvips packages retain their upstream LGPL metadata and are installed from registries rather than committed or republished.
- Both Railway start boundaries were exercised locally: the production Next.js command served the built homepage, and the configured Uvicorn command returned the expected `/v1/health` payload with an injected `PORT`. All temporary processes were stopped.
- `CONTRIBUTING.md`, `SECURITY.md`, and `docs/deployment.md` document setup, contribution boundaries, current security status, deployed topology, secrets, quotas, retention, cleanup and scaling limits.
- Railway project `codeatlas` (`af286454-d14e-4f03-9954-6fe0a410f832`) is deployed in `production` with one `web` and one `analysis` replica. Only `https://web-production-f07d2d.up.railway.app` is public; analysis uses private networking and has no public domain.
- Live Chromium journeys passed architecture and cited-question analysis for `sindresorhus/yocto-queue`, change impact for `sindresorhus/p-map`, and controlled rate limiting. An adversarial review found that accepted `www.github.com` aliases initially used a different repository key; a regression assertion failed first, the key was canonicalized, and deployment `ff912c42-0a23-424f-a2fc-b66d86437df4` then accepted six alternating canonical/www requests and rejected the seventh from their shared bucket. Railway logs exposed a distinct proxy-derived `srcIp`, proving the client admission key does not collapse all traffic into the unknown bucket.
- The public boundary redirects HTTP to HTTPS and emits HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy`. The final web deployment was `ff912c42-0a23-424f-a2fc-b66d86437df4`; the final analysis deployment using `uv run --no-dev` was `df7fe77c-6940-402c-b73d-49e42d3388d3`. Both currently report `SUCCESS`.
- Exact PostCSS 8.5.25 and Sharp 0.35.3 overrides resolve the audited transitive findings. `npm audit` reports zero vulnerabilities, and the unchanged test, lint, type, Fallow and production-build gates pass.
- The workflow exists on public `main`. GitHub Actions run `30677631563` completed successfully for release commit `cfe0b521a0ea46a6e03a7690b1fe685cfbf9d7d1`. All 15 release paths were then fetched at that exact SHA and matched the local bytes.
## Post-release evaluation

- Direct TestClient probes against current public source hosts measured `developit/mitt` architecture at 920 ms, cited questions at 606 ms, an unsupported billing question at 617 ms, `sindresorhus/yocto-queue` cited questions at 858 ms, and `sindresorhus/p-map` impact at 883 ms. These are single observed local timings, not performance guarantees.
- Mitt and yocto-queue questions returned concrete source citations with empty inference. The unsupported billing question returned `insufficient_evidence` with no facts, evidence, or inference.
- The p-map impact query exposed a deterministic ranking defect: related `pMapSkip` in `index.d.ts` tied exact `pMap` and won by path order, hiding the useful reverse dependencies. A parsed regression fixture failed first.
- Lexical symbol scoring now adds a bounded 0.25-weight precision component based on matched symbol terms over total symbol terms. Query coverage remains dominant; exact `pMap` now scores 2.25 and related `pMapSkip` scores lower without a path- or language-specific heuristic.
- Re-evaluation selected `index.js:1` for pMap, reported medium confidence, restored three direct dependent modules, preserved two unresolved-relationship warnings, and completed in 943 ms. The full repository gate passes with 82 Python and 12 web tests. Fix commit `8624ce7eaadbdae69114e3b19dba79cebac0edc2` passed GitHub Actions run `30678051346`.
- Private analysis deployment `b0e8a6fa-f24d-420e-afe7-fb229f351f05` reached `SUCCESS`. A fresh live Chromium journey through the public web service rendered pMap at `index.js · L1`, three direct impacted modules at their import lines, medium confidence, and both uncertainty warnings.
- Three repeated mitt question requests at the same revision returned identical status and citations in 632, 578, and 573 ms (578 ms median). Every question still follows the source reacquisition and reparsing path, so commit-keyed artifacts are justified as the next scaling design boundary, but no persistence provider or dependency is selected.
- Mitt architecture initially projected eight limitations because one unresolved or external import produced one warning per imported symbol. A regression case with default and named imports failed first. Exact duplicate `(code, path, line, subject)` records are now collapsed in first-source order; re-evaluation returned five distinct limitations in 867 ms without hiding either unresolved entry point or any distinct external dependency. Fix commit `6091ae672b827170003e3d812170b64d585fab42` passed GitHub Actions run `30678298746`; analysis deployment `df7fe77c-6940-402c-b73d-49e42d3388d3` reached `SUCCESS`, and a fresh public Chromium journey rendered 3 modules, 8 relationships, and 5 retained limitations.

## Quality and Verification Contract

Run the repository gate from the project root:

```bash
./scripts/verify.sh
```

It currently runs:

### Python

```bash
uv sync --locked
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests
uv run pytest
```

Configured policy includes strict mypy, Ruff bug/complexity/import/simplification rules, maximum McCabe complexity 10, strict pytest configuration, and Python 3.12 targeting.

### Web

```bash
npm run test
npm run lint
npm run typecheck
npm run quality
npm run build
```

`npm run quality` uses Fallow to block new dead code, duplication, dependency drift, cycles, configured complexity breaches, and architecture-boundary findings. Current Fallow result is zero issues.

### Last observed evidence

- Python: 82 tests passed; Ruff formatting and lint passed; strict mypy passed.
- Web: 12 tests across 4 files passed; ESLint passed; TypeScript passed; Fallow reported 0 issues in maintained code; Next.js production build passed.
- Local and Railway live probes: `sindresorhus/yocto-queue` verified architecture and cited questions; `sindresorhus/p-map` verified change impact with one candidate and three direct dependents. The public Railway service also verified proxy-derived rate limiting, HTTPS redirection and security headers.

Child-agent claims do not replace rerunning these commands in a new session.

## Important Source and Tooling Decisions

- Next.js was generated with the current official `create-next-app` App Router TypeScript scaffold.
- FastAPI testing follows its TestClient pattern, but installed Starlette 1.3.1 deprecated `httpx` in favor of `httpx2`; the project uses `httpx2` as required by the installed source.
- Fallow initially identified the generated landing component as oversized. It was split into cohesive landing sections, after which the complexity report became clean.
- Fallow treats Tailwind as a production dependency because CSS imports it. The project records Tailwind as an intentional build-tool exception in `web/.fallowrc.json` rather than moving it into runtime dependencies.
- Vitest did not resolve the Next.js `@/*` alias without added configuration. The page uses a direct relative feature import instead of adding another resolver dependency.
- Repository URL policy was adapted from reviewed inspiration behavior but rewritten in the Python core: accept only unambiguous HTTPS GitHub repository roots and reject credentials, ports, queries, fragments and deeper paths.
- The deterministic repository identity is the normalized `github.com/owner/repository` key. This avoids coupling identity to an API client or persistence provider.
- The initial intake adapter is in memory and every accepted record starts `pending`; no transition runner exists yet.
- The OpenAPI document remains the client contract authority. `openapi-typescript` 7.13.0 generates path/schema types and `openapi-fetch` 0.17.0 consumes them without handwritten duplicate HTTP types.
- Latest and legacy generator candidates initially failed isolated advisory checks. The selected latest generator/client graph audits clean with exact minimatch 10.2.6 and brace-expansion 5.0.9 overrides.
- The browser calls a server action rather than the analysis service directly, avoiding a broad client-side API URL and CORS boundary. `CODEATLAS_ANALYSIS_URL` configures the server adapter and defaults to local FastAPI.
- GitHub ZIP archives were selected over cloning because structural analysis needs a bounded source snapshot, not history or Git execution. The adapter resolves and pins the full commit before download because GitHub documents branch/tag archives as movable while commit archive contents are stable.
- The generic contents API was not selected because per-file traversal increases API calls and couples acquisition to provider pagination. Archive decoding remains framework-neutral; the GitHub REST and urllib details stay in the adapter.
- Python tree-sitter was selected over a Node/TypeScript compiler subprocess for the initial structural slice. It keeps analysis in one runtime, has Python 3.12 wheels, parses incomplete source, and needs no filesystem execution or module installation. The core receives a callable parser protocol, so richer compiler-semantic adapters can replace it later.
- Initial architecture execution is synchronous and bounded. This gives the local product one honest end-to-end behavior without presenting FastAPI background tasks or in-memory queues as durable. Durable jobs remain a deployment decision when cancellation, retries, persistence and user-scale quotas are required.
- FastAPI uses the immutable `ArchitectureView` dataclass directly as its response model, keeping OpenAPI authoritative without a second handwritten mirror of the structural schema.
- Phase 3 starts with deterministic lexical and structural retrieval rather than embeddings. This makes ranking behavior inspectable and gives later semantic retrieval a measurable baseline.
- The retrieval contract uses CodeAtlas-native paths, symbol spans and relationships. Current-project and inspiration graph searches found no coherent reusable retrieval slice; generic document citation schemas were not copied because they discard code-symbol semantics.
- Deterministic cited facts precede generated prose. Fixed templates ensure every current statement is inspectably derived from one evidence kind and citation; future model inference has a separate field rather than sharing the verified-fact channel.
- The question endpoint reuses the bounded synchronous `RepositoryAnalysis` service. Reacquisition is accepted only for the current local slice and is documented rather than obscured behind an in-memory cache with undefined ownership.
- GraphMCP health-probed the exact broad `<work-root>` index and located current CodeAtlas retrieval seams plus Ragas/Chonkie embedding injection examples. CodeAtlas rewrote only the provider-injection, fixed-dimension, cosine and threshold invariants; it rejected fallback-to-unrelated-results behavior.
- GraphMCP located `pi-code-review-graph/src/graph/impact.ts`. CodeAtlas independently adapted its bounded visited-set traversal invariant to reverse only resolved repository relationships, preserve source citations, report direct/transitive depth, and warn that proximity is not certainty.
- The live p-map probe exposed a tree-sitter native crash caused by Point access on large declarations. Source locations now derive from one precomputed byte-offset map; a generated 500-line subprocess regression test guards the original segmentation fault.
- Direct `tree-sitter` plus `tree-sitter-typescript` dependencies were selected instead of a many-language bundle because the approved boundary is TypeScript and JavaScript only. No inspiration implementation was copied; graph searches found no relevant current-project or inspiration precedent.

## Known Risks and Blockers

### Dependency overrides

`npm audit` reports zero vulnerabilities after exact PostCSS 8.5.25 and Sharp 0.35.3 overrides. The unchanged web tests, lint, type check, Fallow gate and production build pass. Next.js 16.2.12 still declares older transitive ranges, so retain the audit and complete web gate until upstream adopts patched versions.

### Open-source publication

Apache-2.0 is selected, the source repository is public, GitHub private vulnerability reporting is enabled, and the publication-content review found no credential, runtime-artifact, private-data, oversized-file, or dependency-license blocker. Public `main` contains the verified release source and guidance.

### Code graph

The existing `<work-root>` CodeGraphContext index was discovered, but establishing directory watching failed during initialization. Use `pi.read`, `pi.grep`, and `pi.find` as authoritative fallback. If graph results are used later, verify every result against actual source.

### Git state

The repository is on `main`, tracking `origin/main`. Release commit `cfe0b521a0ea46a6e03a7690b1fe685cfbf9d7d1` is public and verified; use `git rev-parse HEAD` for the current completion-receipt commit. Preserve unrelated work and do not create later commits or pushes without a request.

## Open Questions

| Question | Why it matters | Blocking now? |
|---|---|---|
| When should bounded synchronous analysis move to a durable job? | Determines cancellation, quotas, retries and persistence for deployment-scale workloads | Not for the current bounded local slice |
| What persistence should hold repository metadata and analysis artifacts? | Affects local development and deployment portability | Not for a minimal in-memory contract |
| Which embedding/model providers should be supported first? | Affects cost, privacy and adapter shape | No; retrieval is later |
| When will Next.js adopt the patched PostCSS and Sharp ranges? | Allows removal of tested transitive overrides | No; the current graph audits clean |

## Proposed Next Slice

This is a proposal, not an approved implementation contract.

**Goal:** specify a provider-neutral, commit-keyed analysis artifact lifecycle before adding persistence.

Candidate acceptance boundary:

1. Key immutable artifacts by normalized repository identity plus resolved full commit SHA.
2. Define capacity, TTL, deletion, failure, and concurrent-request behavior without adding a storage dependency.
3. Preserve the current framework-neutral `RepositoryAnalysis` boundary and keep source-host/storage details in adapters.
4. Measure the proposed cache against the deterministic repeated-analysis baseline before selecting an in-memory or durable provider.
5. Keep generated wiki prose, autonomous edits, and pull-request creation outside scope unless explicitly approved.

## New-Session Bootstrap

A new session should execute this sequence:

1. Enter the repository root.
2. Read `AGENTS.md` completely.
3. Read `.pi/state.md`, `.pi/tech-stack.md`, and `.pi/roadmap.md`.
4. Run `git status --short --branch --untracked-files=all` and preserve unrelated work.
5. Run `./scripts/verify.sh` before changing behavior.
6. Re-read the exact files owned by the next slice.
7. Implement any approved next slice in small RED → GREEN → refactor increments.
8. Update this state file with new observed evidence, decisions, risks and next priority.

## Copy-Paste Handoff Prompt

```text
Continue CodeAtlas from the repository root.

First read AGENTS.md, .pi/state.md, .pi/tech-stack.md, and .pi/roadmap.md completely. Treat .pi/state.md as the current handoff, but verify its claims against source and commands. Preserve unrelated work; do not commit or push unless requested.

Run git status --short --branch --untracked-files=all and ./scripts/verify.sh before editing. Phases 0–5 are complete, public, and verified. Phase 5 added audit-clean PostCSS and Sharp overrides, process-local public request controls, one-replica Railway configs, security headers, canonical repository limiter keys, and synchronized release guidance. The full gate passes 82 Python tests and 12 web tests; npm audit reports zero vulnerabilities.

The bounded demo is live at https://web-production-f07d2d.up.railway.app with private analysis networking. The proposed next slice is evidence-led post-release evaluation focused on source-verifiable change planning; it is not yet approved.

After work, update .pi/state.md with exact files, observed verification, unresolved risks, and the next-session priority.
```

---

Update this file after each significant implementation session. It is the canonical “you are here” marker, not a substitute for source or verification.
