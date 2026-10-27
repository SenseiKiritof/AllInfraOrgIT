# Phase 8 release audit

2026-10-26 verification on code and configuration, not only on the plan. Status: **not ready**.

## Must — block the release

| # | Problem | Evidence | Action |
|---|---|---|---|
| 1 | No API `Dockerfile`; Caddy points to a nonexistent `api:8080` | `compose.yaml`, `Caddyfile` | non-root API image + service in the full profile |
| 2 | Keycloak `start-dev`, hostname/proxy not configured, Caddy does not forward `/realms`/`/resources`, realm redirect only localhost | `compose.yaml`, `Caddyfile`, realm | production mode, hostname, proxy headers, real redirects |
| 3 | In-memory session store: restart = logout, no multi-instance, no limit | `InMemorySessionStore.cs` | shared store + limits |
| 4 | No observability: no Serilog/OTel, non-JSON logs | `Program.cs`, csproj | structured logs, correlation, metrics/traces |
| 5 | Missing security headers (CSP/HSTS/nosniff/referrer/frame) | `Program.cs`, `Caddyfile` | headers in API and Caddy |
| 6 | Missing forwarded headers behind Caddy: wrong IP/scheme | `Program.cs` | `UseForwardedHeaders` + trust proxy |
| 7 | Rate limit only login and global, no limit on callback/run/reachability/console | `Program.cs` | policies partitioned per IP/user/action |
| 8 | Images without digest, without `user`/`read_only`/`cap_drop`/limits | `compose.yaml` | hardening and pinning |
| 9 | Migrations only in Development, no deploy job | `Program.cs` | separate migration job + runbook |
| 10 | No backup/restore | `docs/operations/` | scripts and restore test |
| 11 | OpenAPI not generated and driftable; CI does not verify it | `docs/api/openapi.yaml`, workflow | contract generation/verification |
| 12 | No load test | test | latency/throughput on lists/topology/save |
| 13 | `make release` exits 1, no tag | `Makefile` | release checklist, tag, lock |
| 14 | Phase 7 verified only on a fake dump: missing rehearsal on a real sanitized dump and cutover/rollback runbook | `docs/migration/phase7-plan.md` | sanitized dump, rehearsal and signed runbook |

## Should

- Mandatory Origin on mutations (today a missing header passes).
- Console: idle timeout and per-user session limit.
- Reachability: rate limit and destination allowlist; do not expose the SSH `exception.Message` to the client.
- EF logs at `Warning` in production (today SQL parameters end up in the logs).
- Explicit `AllowedHosts`; `BootstrapAdminUsername` forbidden outside Development.
- Keycloak password policy and password reset.
- CI: actions pinned by SHA, Dependabot/audit, images and Redocly pinned.
- E2E: cleanup of the child process, not only of the `make` PID.
- Generated TypeScript contract (`schema.d.ts`) instead of manual types.
- Audit of admin mutations.
- `/health/ready` with Keycloak dependency or liveness/readiness distinction.

## Nice

- Caddy access log with rotation; `SECURITY.md`/`CODEOWNERS`/`LICENSE`.
- Coverage gate (coverlet already present).
- Truncation marker in the audit output.
- Update the "Phase 2" comment in the Caddyfile.

## Declared debt — actual state

- Session store: shared MySQL with DataProtection-encrypted payload and per-user limit (Phase 8 WP3).
- `full` Compose: confirmed incomplete (missing API, Keycloak routing).
- Phase 7 import: importer, MySQL adapter and fake dump present; the rehearsal on a representative dataset is missing.

## Not verified

Remote workflows and restore test (not executable in this environment). The full profile was started and login verified on clean volumes; load test, backup/restore and verification on a host with a real domain remain.

## Phase 8 update (2026-10-26)

- Must #1 resolved: multi-stage non-root API image, `migrate` job, read-only `api` service with `cap_drop` and healthcheck.
- Must #2 resolved on the `full` profile: Keycloak `start`, hostname/proxy headers/dynamic backchannel, Caddy forwards `/realms` and `/resources`; real login verified on a clean stack.
- Must #3 resolved: sessions in MySQL encrypted with persistent DataProtection keys; API restart without logout and per-user limit tested.
- Must #4 resolved: JSON logs with correlation id, optional OpenTelemetry OTLP, readiness with MySQL and Keycloak.
- Must #5, #6, #7 resolved: security headers on API and Caddy, forwarded headers with trusted networks, rate limits partitioned per callback/run/reachability/console; mandatory Origin on authenticated mutations.
- Must #8 partial: hardening and limits present on the API; MySQL/Keycloak images and digest pinning still to be hardened.
- Must #11 resolved: OpenAPI generated from code and CI step that fails on drift; frontend `schema.d.ts` remains Should.
- Must #9 resolved: separate and idempotent `migrate` job before the API; API startup without migrations in Production.
- Must #10 resolved: `make backup` / `make restore` with confirmation, runbook `operations/backup-restore.md` and restore test on an isolated stack.
- Must #12 resolved: `scripts/loadtest.py` / `make load-test` on lists, topology and create/delete; results in `operations/load-test.md`.
- Must #13 resolved as a process: `make release VERSION=0.x.y` runs the gates, updates `versions.lock` and creates local tags; manual push. Guards verified, release not yet executed.
- Must #14 remains open: rehearsal on a real legacy dump and cutover runbook not executable without sanitized data.
- Must #8 resolved for digest and API hardening: MySQL, Keycloak and Caddy pinned by digest, .NET base images pinned; API non-root/read-only/cap_drop. Upstream DB images keep the standard entrypoint.
- E2E: `make e2e` does not start child processes, requires an external `make dev`; `make e2e-full` runs the same 5 tests against Caddy/HTTPS. Traces in `test-results/` ignored.
