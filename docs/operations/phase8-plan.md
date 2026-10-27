# Phase 8 operational plan — hardening and release

Derives from the Musts in `release-audit.md` (2026-10-26 audit). Order chosen by dependency: first the image and the deploy, then auth/session, observability and application security, finally contracts, backup, load test and release.

## Proposed decisions

| Topic | Choice | Reason |
|---|---|---|
| Session store | MySQL table via EF, same application instance | no new service; the deploy stays one host + Compose |
| Observability | Serilog JSON logs + optional OpenTelemetry OTLP from env | works locally without a collector, in production it is enabled via env |
| Deploy | single host, Caddy in front of SPA and API, Keycloak same-host | D4 confirmed |
| Images | explicit tags; digest on the first available registry | the repos are still local |

## Work packages

| WP | Content | Must | Exit |
|---|---|---|---|
| 1 | Multi-stage non-root API `Dockerfile`, `api` service in the `full` profile, healthcheck, `read_only`, `cap_drop`, limits | 1, 8 | `docker compose --profile full up` serves SPA + API |
| 2 | Keycloak `start` with hostname/proxy headers, Caddy forwards `/realms` and `/resources`, client redirect for the real host | 2 | real same-host login |
| 3 | Shared MySQL session store, expiry and per-user limits | 3 | API restart without logout; two instances share the session |
| 4 | Serilog JSON, correlation id, OpenTelemetry traces/metrics, separate liveness/readiness health | 4 | structured logs and `/health/ready` with dependencies |
| 5 | Security headers in API and Caddy, forwarded headers with trusted proxies, rate limit per callback/run/reachability/console, mandatory Origin | 5, 6, 7 | tests on headers, 429 and missing Origin |
| 6 | OpenAPI generation from the backend and drift check in CI; generated `schema.d.ts` | 11 | CI fails on a drifted contract |
| 7 | Migration job separate from API startup, MySQL backup/restore for application and Keycloak with restore test | 9, 10 | runbook + scripts tested locally |
| 8 | Load test on lists, topology and save with thresholds | 12 | latency/throughput report |
| 9 | `make release`, `v0.x` tag, `versions.lock`, E2E cleanup, release checklist | 13, 14 | green release checklist |

## Status

- WP1 done: multi-stage non-root API `Dockerfile`, `migrate` job, read-only `api` service with `cap_drop`/`no-new-privileges`, healthcheck, Caddy waiting for the API. `make full` verified.
- WP2 done on the `full` profile: Keycloak `start` with `KC_HOSTNAME`, proxy headers and dynamic backchannel; Caddy forwards `/realms` and `/resources`; real login tested on an isolated stack (`/api/session` 200 with user `admin`). Note: the existing realm must be updated or recreated because `--import-realm` does not modify already imported redirect URIs.
- WP3 done: `Sessions` tables in MySQL with DataProtection-encrypted payload, keys in the `api-dp-keys` volume, expiry and session limit per user. Test: session visible from a second API instance and limit enforced.
- WP4 done: JSON logs with correlation id, OpenTelemetry OTLP enableable from env, `/health/ready` with MySQL and Keycloak. Verified on containers: readiness `{"status":"Healthy","checks":[{"name":"mysql"...},{"name":"keycloak"...}]}` and JSON logs.
- WP5 done: security headers on API and Caddy, forwarded headers with trusted networks, rate limit per callback/run/reachability/console, mandatory Origin on mutations. Verified via Caddy: HSTS 31536000 with forwarded proto, distinct SPA/API CSP.
- WP6 done: OpenAPI 3.1.1 generated from code in `InfraOrgITApi/openapi/InfraOrgIt.Api.json` (148 operations), `scripts/openapi.sh`, CI step that regenerates and fails on drift. The frontend `schema.d.ts` remains a Should, not yet automated.
- WP7 done: `make backup` (application + Keycloak MySQL dump, manifest), `make restore` with mandatory confirmation, runbook `operations/backup-restore.md`. Test on an isolated stack: valid dumps, restore blocked without confirmation, restore executed with table and realm verified.
- WP8 done: `scripts/loadtest.py` and `make load-test` on lists, topology and create/delete; report in `operations/load-test.md`. Isolated stack, 12 requests per endpoint, no errors, averages 9–26 ms.
- WP9 done: `make release VERSION=0.x.y` with `make ci` gate, `versions.lock`, lock commit and local tags; runbook `operations/release.md`. Guards verified (invalid version exit 2, dirty working tree exit 1). Compose images and .NET base image pinned by digest. `make ci` green and 5 Playwright tests passed on `make dev`; release not executed: repo with uncommitted changes and real Phase 7 still open.
- Review fixes: rate limit after authentication with per-user test, restore with confirmation/service stop/validated dumps, `600` backup, dedicated Docker `auth` network, `make e2e-full` verified on Caddy, OpenAPI with per-operation security, concurrent session lock and readiness without repeated discovery.

## Out of scope for Phase 8

- Rehearsal on a real legacy dump and cutover runbook: still blocked by data, tracked in `migration/phase7-plan.md`.
- Push, `main` protection and remote workflows: require GitHub credentials.
