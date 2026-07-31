# Deployment Architecture

This document records deployment requirements. It does not select a provider or authorize a deployment.

## Intended topology

```text
browser
  -> Next.js web service
       -> server actions
            -> private FastAPI analysis service
                 -> GitHub HTTPS API and commit-pinned ZIP archives
```

The browser should not receive analysis-service credentials or a direct unrestricted API origin. `CODEATLAS_ANALYSIS_URL` belongs to the web service environment.

## Current execution model

Architecture, cited-question, and change-impact requests run synchronously within existing acquisition limits. Question and impact requests reacquire and reparse source because persistent artifacts and cache ownership are not selected. This is suitable for a bounded local demonstration, not public traffic.

## Required production controls

Before deployment:

1. Resolve or explicitly risk-accept the recorded npm advisories.
2. Select a license and verify publication contents.
3. Add per-client and per-repository rate limits, a global concurrency cap, request timeouts, and egress budgets.
4. Move repeat analysis behind commit-keyed artifacts. If work can outlive an HTTP request, use a durable queue with cancellation, retries, idempotency, and observable terminal states.
5. Define artifact TTLs and deletion. Never persist downloaded public source longer than required for the documented product behavior.
6. Configure structured logs without source contents, query text that may contain secrets, credentials, or archive bodies.
7. Keep the FastAPI service private to the web service where the provider permits it. Enforce HTTPS and explicit origins at any public boundary.
8. Add health, latency, failure-rate, GitHub quota, archive-limit, queue-depth, and cleanup metrics.

## Secrets

No secret is currently required for public unauthenticated GitHub access. A production GitHub token or future embedding/model key must use the deployment platform's secret store, receive least privilege, never reach browser bundles, and never be logged. CI workflows must reference repository secrets only through environment variables.

## Quotas and cleanup

Existing archive limits cap download size, entry count, selected files, uncompressed bytes, individual file size, path depth, and request duration. Production must add request-rate and concurrency limits above those content limits.

Future stored analysis should use the normalized repository identity plus full commit SHA as its immutable key. Expired artifacts and failed-job payloads require scheduled deletion with observable success and bounded retries.

## Deployment decision still required

Web, API, artifact storage, queue, and observability providers remain replaceable adapters. Select them only after measuring the public demo workload and confirming that the provider supports the controls above.

## First-demo provider recommendation

Railway is the current recommendation for the first bounded demo, but it is not yet selected or deployed. Its official documentation covers [FastAPI deployment](https://docs.railway.com/guides/fastapi), [Next.js deployment](https://docs.railway.com/guides/nextjs), [private service networking](https://docs.railway.com/reference/private-networking), and [configuration as code](https://docs.railway.com/reference/config-as-code). This fits the existing native Python/tree-sitter process and lets the web service call a non-public analysis service without rewriting either runtime.

A two-service Railway project would use `web/` and `analysis/` as independent service roots. Only the web service receives a public domain. The analysis service remains on private networking, binds to the injected `PORT`, and receives no browser traffic directly. `CODEATLAS_ANALYSIS_URL` points to the analysis service's private address.

This recommendation does not authorize deployment. Before selection, validate current plan limits against measured archive latency, confirm request timeout and outbound GitHub access, and resolve or explicitly accept the npm advisories. Cloudflare Workers is not the default because the current FastAPI and native tree-sitter runtime would require a container or a product rewrite rather than a thin adapter.
