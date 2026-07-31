# Security Policy

## Current status

CodeAtlas is a pre-publication prototype. It has no deployed service, supported release, or public security intake channel. Do not treat the current checkout as a production service.

## Reporting a vulnerability

Before publication, the repository owner must enable GitHub private vulnerability reporting or publish a dedicated security contact. Until that channel exists, do not disclose exploit details in a public issue.

A useful report includes the affected path or endpoint, reproduction steps using non-sensitive data, impact, and any suggested mitigation. Never include real credentials, private repository contents, or third-party personal data.

## Security boundaries

- Only public GitHub repository roots are accepted.
- Source downloads are commit-pinned, HTTPS-only, size-bounded, decoded in memory, and never executed.
- Archive paths, redirects, malformed content, and unsupported source types are controlled boundaries.
- Model, vector-store, persistence, and deployment credentials are not implemented.
- Generated source claims remain separate from future model inference.

## Known pre-release blockers

- `npm audit` currently reports three high-severity transitive advisories through the web stack. npm's proposed resolution is incompatible with the selected Next.js line. Reassess and resolve or explicitly risk-accept them before deployment.
- No public rate limiter, abuse control, durable job system, artifact retention policy, or authentication boundary exists.

Security fixes must pass `./scripts/verify.sh` and include a regression test when the failure is reproducible.
