# ADR-004 — Single-host deployment with Docker Compose and Caddy

- Status: accepted
- Date: 2026-10-25
- Decision: D4

## Context

Self-hosted application on a single Linux host. HTTPS is needed, and a single origin for SPA and API: first-party session cookies and no CORS. A existing reverse proxy exists only if the host sits behind it.

## Decision

- Docker Compose on a single host; no Kubernetes in v1.
- Caddy at the edge: serves the SPA `dist/`, reverse-proxies `/api/*` and `/auth/*` to the API and handles automatic TLS (ACME or private CA for the LAN).
- Same origin for SPA and API. In development no Caddy: Vite on :3000 with a proxy to the API on :5298.
- Keycloak on the same host through Caddy (subdomain or path prefix) in Phase 8, together with the production configuration.
- `versions.lock` for releases and rollback.

## Alternatives considered

- **API serves the SPA** (`UseStaticFiles` + Kestrel): fewer containers, but certificate and frontend coupled to the API deployment.
- **nginx/Traefik**: more configuration for automatic TLS.
- **Existing reverse proxy**: Caddy removed; only the edge changes.
- **Kubernetes/cloud**: out of scope for v1.

## Consequences

- One more container and a domain/DNS for the certificates.
- Caddyfile and Compose validated in CI.
- In production Keycloak moves from `start-dev` to `start`, with hostname and proxy headers.
