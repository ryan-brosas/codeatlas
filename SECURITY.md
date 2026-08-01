# Security Policy

## Current status

CodeAtlas has a public source repository and a bounded public demo, but remains a pre-release prototype rather than a production service. GitHub private vulnerability reporting is enabled for confidential security intake.

## Reporting a vulnerability

Use GitHub's private vulnerability-reporting form for this repository. Do not disclose exploit details in a public issue.

A useful report includes the affected path or endpoint, reproduction steps using non-sensitive data, impact, and any suggested mitigation. Never include real credentials, private repository contents, or third-party personal data.

## Security boundaries

- Only public GitHub repository roots are accepted.
- Source downloads are commit-pinned, HTTPS-only, size-bounded, decoded in memory, and never executed. Matching snapshots may remain in the single analysis process for up to five minutes under a 32-entry and 16 MiB selected-source budget; they are never written to disk.
- Archive paths, redirects, malformed content, and unsupported source types are controlled boundaries.
- The product stores no model, vector-store, persistence, source-host, or deployment credentials.
- Generated source claims remain separate from future model inference.

## Known pre-release limitations

- `npm audit` is clean with exact PostCSS 8.5.25 and Sharp 0.35.3 overrides. Next.js 16.2.12 still declares older transitive ranges, so keep the complete web gate and audit as release checks until upstream catches up.
- Process-local rate, repository, concurrency, timeout, and key-count controls protect the verified single-replica web boundary. They are not a distributed limiter. No durable job system, durable artifact persistence, or authentication boundary exists.
- The Railway web domain redirects HTTP to HTTPS and emits HSTS, MIME-sniffing, framing, referrer, and permissions-policy headers. The analysis service has no public domain.

Security fixes must pass `./scripts/verify.sh` and include a regression test when the failure is reproducible.
