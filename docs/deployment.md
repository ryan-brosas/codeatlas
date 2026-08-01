# Deployment Architecture

This document records the bounded Railway deployment and the controls required before scaling it.

## Deployed topology

```text
browser
  -> Next.js web service
       -> server actions
            -> private FastAPI analysis service
                 -> GitHub HTTPS API and commit-pinned ZIP archives
```

The live demo is https://web-production-f07d2d.up.railway.app. The browser receives neither analysis-service credentials nor a direct analysis API origin. `CODEATLAS_ANALYSIS_URL` belongs only to the web service environment.

## Current execution model

Architecture, cited-question, and change-impact requests run synchronously within existing acquisition limits. Every request resolves the latest GitHub commit. Immutable snapshots are reused only when the normalized repository identity and full commit SHA match a process-local cache entry; parsing then repeats from that bounded snapshot.

The analysis process keeps fixed-name aggregate counters for cache hits, misses, skips, evictions and expirations plus count/total/max durations for revision lookup, archive download and complete analysis. Metrics contain no repository, source, query, client or credential labels; remain process-local; reset on restart; and have no public HTTP endpoint.

The web server-action boundary now enforces process-local demo controls: 12 requests per client and 6 per repository per minute, 2 concurrent analyses, a 30-second execution timeout, and at most 2,000 tracked rate-limit keys. Expired keys are removed during admission. These controls require one web replica and a trusted deployment proxy that appends the client address to `X-Forwarded-For`; unknown clients share one conservative bucket. They are suitable only for the first bounded demo, not horizontally scaled traffic.

## Controls required before scaling

1. If artifacts must survive process restart or horizontal scaling, replace the process-local cache through its adapter boundary. If work can outlive an HTTP request, use a durable queue with cancellation, retries, idempotency, and observable terminal states.
2. Define durable artifact TTLs and deletion before selecting a provider. Never persist downloaded public source longer than required for the documented product behavior.
3. Configure structured logs without source contents, query text that may contain secrets, credentials, or archive bodies.
4. Keep the FastAPI service private to the web service. Enforce HTTPS and explicit origins at any additional public boundary.
5. Export the existing privacy-safe aggregates only after selecting an observability provider. Add failure-rate, GitHub quota, archive-limit, queue-depth, and cleanup metrics when those boundaries exist.

## Secrets

No secret is currently required for public unauthenticated GitHub access. A production GitHub token or future embedding/model key must use the deployment platform's secret store, receive least privilege, never reach browser bundles, and never be logged. CI workflows must reference repository secrets only through environment variables.

## Quotas and cleanup

Existing archive limits cap download size, entry count, selected files, uncompressed bytes, individual file size, path depth, and request duration. The single-replica web adapter adds process-local request-rate, repository-rate, concurrency, timeout, and key-count limits. Horizontal scaling requires a shared limiter or provider-enforced equivalent.

The analysis process caches at most 32 immutable snapshots and 16 MiB of selected source bytes for a fixed five-minute TTL. LRU eviction enforces both limits, oversized snapshots bypass caching, and expired entries are removed on access. Concurrent misses may download independently and converge on the same key. The cache never writes source to disk and disappears on restart.

Future durable analysis should keep the normalized repository identity plus full commit SHA as its immutable key. Expired artifacts and failed-job payloads require scheduled deletion with observable success and bounded retries.

## Scaling decisions remain

Railway hosts the bounded web and analysis processes. Durable artifact storage, queue, and observability providers remain unselected replaceable adapters. Select them only after measuring the public demo workload and confirming that they support the controls above.

## First-demo deployment

Railway hosts the first bounded demo. Its official documentation covers [FastAPI deployment](https://docs.railway.com/guides/fastapi), [Next.js deployment](https://docs.railway.com/guides/nextjs), [private service networking](https://docs.railway.com/reference/private-networking), and [configuration as code](https://docs.railway.com/reference/config-as-code). This fits the existing native Python/tree-sitter process and lets the web service call a non-public analysis service without rewriting either runtime.

The two-service Railway project uses `web/` and `analysis/` as independent service roots. Only the web service receives a public domain. The analysis service remains on private networking, binds to the injected `PORT`, and receives no browser traffic directly. `CODEATLAS_ANALYSIS_URL` points to the analysis service's private address.

Live probes confirmed outbound GitHub access, architecture, cited-question and impact responses, proxy-derived rate limiting, HTTP-to-HTTPS redirection, HSTS and the audit-clean deployed build. Cloudflare Workers is not the default because the current FastAPI and native tree-sitter runtime would require a container or a product rewrite rather than a thin adapter.

## Configuration as code

`analysis/railway.json` and `web/railway.json` use Railway's current RAILPACK schema, explicit start commands, health checks, bounded restart retries, and one replica per service. Each service is deployed from its matching root. Only the web service receives a public domain. `CODEATLAS_ANALYSIS_URL` points to the analysis service's private Railway address.
