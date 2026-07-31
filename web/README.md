# CodeAtlas Web

Next.js interface for repository architecture, source-cited questions, and change-impact reports.

```bash
npm ci
npm run dev
```

Quality checks:

```bash
npm run verify
```

The landing form analyzes a public repository through a server action backed by the OpenAPI-generated contract. It presents accessible loading and typed error states, then renders the analyzed revision, module paths, exported symbols, relationship counts and explicit limitation counts. After analysis, generated server actions support cited questions and change-impact reports. The UI presents deterministic verified-source facts, concrete path/line citations, insufficient-evidence states, explicit “No model inference used” labeling, candidate implementation locations, confidence, direct/transitive dependent modules, and proximity warnings. Run `npm run generate:api` after changing the FastAPI contract. The analysis service defaults to `http://127.0.0.1:8000`; override it with `CODEATLAS_ANALYSIS_URL`.
