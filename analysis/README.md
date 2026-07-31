# CodeAtlas Analysis

FastAPI service for repository structure, retrieval, evidence, and change-impact analysis.

```bash
uv sync --locked
uv run uvicorn codeatlas_analysis.api:app --reload
```

Run its checks with:

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests
uv run pytest
```

The service exposes `GET /v1/health`, network-free `POST /v1/repositories`, and synchronous `POST /v1/architecture`. The architecture endpoint validates one public GitHub URL, acquires a bounded commit-pinned snapshot, parses structural evidence, and returns modules, exported symbols, relationships and explicit limitations. Acquisition limits return HTTP 413; controlled upstream failures return HTTP 502. OpenAPI documentation is available at `/docs`.

## Bounded repository acquisition

The framework-neutral acquisition core reads GitHub ZIP snapshots in memory and keeps only UTF-8 TypeScript, JavaScript and JSON files. Default limits are 20 MiB downloaded, 10,000 archive entries, 5,000 selected files, 50 MiB uncompressed, 512 KiB per source file, 20 path components and 10 seconds per request. Unsafe paths, duplicate paths, symbolic links, unsupported encodings, untrusted redirects and over-limit input are controlled failures.

The GitHub adapter first resolves the latest default-branch commit, then requests the archive by its full commit SHA for repeatable contents. It uses public unauthenticated REST endpoints and only follows HTTPS responses from `api.github.com` and `codeload.github.com`. Repository intake does not invoke this adapter yet.

References: [GitHub source archives](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives) and [repository archive REST endpoints](https://docs.github.com/en/rest/repos/contents#download-a-repository-archive-zip).

## Structural source model

`repository_structure.py` defines immutable repository, file, module, symbol, dependency, source-span and parse-diagnostic evidence. `tree_sitter_parser.py` extracts top-level TypeScript, TSX, JavaScript and JSX declarations, static imports and re-exports without an LLM. Lines and UTF-8 byte columns are one-based. Syntax errors produce partial status and source-located diagnostics while valid neighboring declarations remain available.

Repository assembly keeps JSON files as file evidence without parsing them as TypeScript. Relative module specifiers resolve only when one acquired source path matches. Package imports remain external, missing paths remain unresolved and ambiguous paths are not guessed. Default, named, aliased and namespace imports plus named and wildcard re-exports become source-located symbol relationships. Relationships connect only through verified exported names; re-export surfaces are computed to a fixed point so barrels and cycles remain deterministic. Parser injection is a small callable protocol, so the framework-neutral model does not depend on tree-sitter.

The selected adapter uses [py-tree-sitter](https://tree-sitter.github.io/py-tree-sitter/) and the official [tree-sitter TypeScript grammar](https://github.com/tree-sitter/tree-sitter-typescript). The pinned compatible ranges were exercised together on Python 3.12 and queried against OSV with no advisories observed on 2026-08-01.

## Architecture API

`RepositoryAnalysis` composes acquisition, parsing, relationship resolution and architecture projection behind one injected application boundary. `POST /v1/architecture` runs that bounded pipeline synchronously and returns the domain dataclass contract directly through FastAPI, avoiding a duplicate handwritten response schema. Responses cite the resolved repository revision, module paths, exported symbol names and lines, and relationship source and target evidence. Partial parses, external packages, unresolved or ambiguous modules, and unresolved symbols remain explicit limitation records.

The initial synchronous execution choice keeps the local and portfolio slice deployable without pretending an in-memory background task is durable. It is suitable for the current bounded limits; durable jobs, persistence, quotas and cancellation remain required before a public deployment with larger workloads.

## Deterministic retrieval

`retrieval.py` defines a framework-neutral verified-source evidence contract and deterministic lexical/structural ranking over repository modules, symbols and relationships. Queries are normalized across paths and camel-case names, common question words are ignored, and every result carries a concrete path, line range, optional symbol, matched terms and score. Results are explicitly labeled `verified_source`; empty or unmatched queries return `insufficient_evidence` instead of generating an answer.

The initial retriever deliberately uses no embeddings, vector database, model provider or generated prose. Representative evaluation fixtures require the expected function, class and interface citation to rank first. Graph and inspiration searches found no coherent target precedent, so the implementation uses CodeAtlas source spans and relationship vocabulary directly rather than adapting a generic document-retrieval schema.

## Deterministic cited questions

`cited_answers.py` converts ranked evidence into fixed verified-source fact templates. `CitedAnswer` separates `facts`, underlying `evidence`, and a future `inference` channel. Answer status is `answered`, `insufficient_evidence`, or `unsupported`; no evidence produces no fact. Every fact carries one or more `SourceCitation` values.

`RepositoryAnalysis.answer` composes bounded acquisition, parsing, retrieval and cited facts. `POST /v1/questions` exposes that contract with the same typed URL and source failures as architecture analysis. The generated web action and accessible question form present citations and explicitly state “No model inference used.” A live probe against `sindresorhus/yocto-queue` cited `Queue` at `index.d.ts:1` and `index.js:15` with an empty inference list.

Question requests currently reacquire and reparse the repository because persistence and cache ownership remain unselected. This is bounded and honest for the local slice but should move behind stored revision artifacts or durable jobs before deployment-scale use.

## Semantic retrieval and change impact

`semantic_retrieval.py` accepts an injected batch `TextEmbedder`, validates fixed finite vectors, applies cosine similarity and a threshold, and returns the same `RetrievedEvidence` contract used by lexical retrieval. The domain core selects no provider. GraphMCP located injected cosine-ranking examples in Ragas and Chonkie; CodeAtlas independently retains only the model-neutral injection and threshold invariants, while preserving explicit insufficient evidence instead of their fallback behavior.

`change_impact.py` retrieves one implementation candidate and traverses resolved reverse module relationships with depth and module caps. Reports carry source citations, direct/transitive depth, location confidence, unresolved/partial evidence warnings, truncation, and an unconditional proximity-is-not-certainty warning. Its bounded visited-set traversal was independently adapted to CodeAtlas relationships after GraphMCP located the `pi-code-review-graph` impact-radius implementation; no plugin data model or naming was copied.

A live `sindresorhus/p-map` probe returned `pMap` at `index.js:1`, then cited `index.test-d.ts:2`, `test-multiple-pmapskips-performance.js:4`, and `test.js:7` as direct dependents. That probe exposed a native tree-sitter Point lifetime crash on a large declaration. Source positions now derive from precomputed byte offsets, and a generated 500-line subprocess regression fixture guards the original segmentation failure without copying upstream source.
