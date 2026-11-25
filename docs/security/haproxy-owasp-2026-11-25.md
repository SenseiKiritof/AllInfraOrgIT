# OWASP review — HAProxy module — 2026-11-25

| | |
|---|---|
| **Date** | 2026-11-25 |
| **Target** | HAProxy feature on `feature/haproxy-monitoring`: discovery, opt-in monitoring, metrics (Data Plane API and stats-only), runtime actions, certificates, clusters, inventory route matching |
| **Scope** | `InfraOrgITApi` HAProxy feature, `InfraOrgITWeb` HAProxy pages, `InfraOrgITDocker` runtime images |
| **Method** | OWASP Top 10 2021 checklist, source review, unit and integration tests, live lab HAProxy 2.8.30 + Data Plane API 3.0.28, Trivy image scans, dependency audits |
| **Status** | 5 findings fixed in this pass; residuals documented |

## 1. Executive summary

The HAProxy module keeps the platform controls and adds no new unauthenticated
surface:

- Reads require `ServerOperator` on the instance environment, configuration and
  monitoring changes require `ServerAdmin`, Data Plane API and stats passwords
  require `SystemAdmin`.
- Passwords are stored with `CredentialCipher`, are write-only in the API and
  are never returned; the instance DTO exposes only `hasCredentials`.
- Certificate PEMs (including the private key) are sent only to the Data Plane
  API; they are never stored, audited or returned by InfraOrgIT.
- Outbound `Direct` connections accept only the linked server (IP, hostname or
  public IP) unless a `SystemAdmin` performs the change; credentials, query and
  fragment in a URL are rejected.
- TLS hostname verification is always enforced, redirects and proxies are
  disabled, and self-signed certificates require an explicit per-instance flag.
- Every mutation is CSRF-protected, rate-limited and audited.

`make ci` is green (105 unit, 116 integration, 237 Web tests, Biome, `tsc`,
build, OpenAPI drift, Redocly).

## 2. OWASP Top 10 2021 status

| Category | Status | Evidence |
|---|---|---|
| **A01 Broken Access Control** | Pass | List and detail reads use `OperatorEnvironmentIds`; settings/monitoring/certificates/clusters require `ServerAdmin`; secrets require `SystemAdmin`; server actions require `ServerOperator`; discovery requires admin on the server or `SystemAdmin` for a full scan |
| **A02 Cryptographic Failures** | Pass | AES-GCM `CredentialCipher` for API and stats passwords; write-only secrets; `CaPem` holds public certificates only; HTTPS for `Direct`; hostname verification and strict CA chain when a CA is set; no certificate key storage |
| **A03 Injection** | Pass | EF Core parameterized queries; React escapes text; no raw SQL, shell, `eval` or `dangerouslySetInnerHTML`; backend/server names escaped in URLs and form bodies; certificate names restricted to `[A-Za-z0-9._-]` |
| **A04 Insecure Design** | Pass | Monitoring never starts automatically; explicit `Undecided`/`Enabled`/`Disabled`; URL restrictions; 1 MiB PEM limit; 16 MiB response cap; no config writes in this phase |
| **A05 Security Misconfiguration** | Pass | Downstream certificate failures return 502 instead of a generic 500; CSRF middleware applies to all mutations; `remote-run` rate limit on every write; audit on every change |
| **A06 Vulnerable Components** | Pass for application code | NuGet and npm audits clean; API image clean after the base-image bump; Caddy, Keycloak and MySQL findings are upstream, see section 4 |
| **A07 Authentication** | Pass | OIDC BFF session; secrets require `SystemAdmin`; no token or password in URLs; stats and Data Plane credentials are optional/required per mode |
| **A08 Software and Data Integrity** | Pass | Certificate upload validates a combined PEM with certificate and key; CSV parsing is bounded and typed; no unsigned artifact is installed by this module |
| **A09 Logging and Monitoring** | Pass | Audit events for settings, secrets (booleans only), monitoring choice, connection test, refresh, server actions, certificate upload/replace/delete and cluster CRUD |
| **A10 SSRF** | Pass | `Direct` targets must match the linked server; URLs reject user info, query and fragment; redirects and system proxies are disabled; SshForward reaches endpoints from the managed server |

## 3. Findings fixed in this pass

### F-01 — Medium (A10) — `Direct` endpoints could target any host

`ServerAdmin` could set `BaseUrl` or `StatsBaseUrl` to an arbitrary host and
make the API issue authenticated requests from its network. The client now
requires the URL host to match the linked server IP, hostname or public IP; a
non-matching host requires `SystemAdmin`. URL credentials, query strings and
fragments are rejected for both URLs.

### F-02 — Low (A01) — Instance list was restricted to `ServerAdmin`

`GET /api/haproxy/instances` filtered on admin environments while every detail
endpoint required only `ServerOperator`, so an operator could read an instance
by id but saw an empty list. The list now uses the operator environment set,
matching the documented read model.

### F-03 — Low (A05) — Certificate write failures returned a generic 500

Upload, replace and delete called the Data Plane API without an error boundary;
a downstream failure produced an empty 500 with a trace id. They now return 502
with the Data Plane API message, like test and refresh.

### F-04 — Medium (A09/A04, availability) — Transient DB errors stopped the API

The metrics, protocol-metrics and refresh background services ran their first
query outside any `try`; a transient MySQL I/O timeout propagated to the host,
which is configured to stop on unhandled background exceptions (observed on the
local stack during load). Each tick now logs a warning and continues.

### F-05 — Medium (A06) — API image had 5 HIGH findings

Trivy reported 2 HIGH in the Ubuntu base (`apt`, `lib` packages) and 3 HIGH in
the pinned ASP.NET runtime 10.0.14. The Dockerfile now pins the 10.0.15
`aspnet` and `sdk` digests; the rebuilt `infraorgit-api:local` reports 0
HIGH/CRITICAL with `--ignore-unfixed`.

Also fixed: retention days now honour `Haproxy:MetricsRawRetentionDays` and
`Haproxy:MetricsRetentionDays` instead of hard-coded 7/90, and both HAProxy
clients cap buffered responses at 16 MiB.

## 4. Residual risks

- **SshForward targets:** `ApiHost` and `StatsBaseUrl` are reached from the
  managed server, so a `ServerAdmin` can point them at other hosts reachable
  from that server. This is the same trust as the SSH credential already used
  for discovery; accepted for this phase.
- **DNS rebinding:** the server match is checked on the URL hostname before
  resolution. A compromised DNS could return a different address for a matching
  name. Low residual on managed infrastructure.
- **Certificate private key in transit:** the combined PEM contains the key and
  is sent to HAProxy over the Data Plane API TLS connection; it is never stored
  or returned by InfraOrgIT.
- **Caddy HIGH:** `golang.org/x/net` v0.60.0 in `caddy:2-alpine`
  (CVE-2026-78661, fixed 0.62.0); the current upstream image still ships the
  vulnerable version, so the Web image keeps 1 HIGH until Caddy rebuilds.
- **Keycloak CRITICAL:** OpenJDK 21.0.12 in `keycloak:26.8.1`
  (CVE-2026-114938, fixed 21.0.13); needs a newer Keycloak image.
- **MySQL CRITICAL:** `gosu` Go stdlib (CVE-2025-68121) and bundled `certifi`
  (GHSA-6q48-6c7w-9gw2) in `mysql:8.4`; needs an upstream image refresh.
- **D7 inventory reads** and optional MFA are unchanged from the platform
  review of 2026-11-19.

## 5. Verification performed

- `make ci`: 105 unit, 116 integration, Biome, `tsc --noEmit`, 237 Vitest,
  production build, `jq versions.lock`, OpenAPI regeneration without drift,
  Redocly lint.
- `dotnet list package --vulnerable --include-transitive`: no vulnerable
  packages. `yarn audit --level high`: 0 vulnerabilities.
- Trivy 0.76.2, `--scanners vuln --severity HIGH,CRITICAL --ignore-unfixed`:
  - `infraorgit-api:local`: 5 HIGH before, 0 after the digest bump.
  - `infraorgit-web:local`: 1 HIGH (Caddy `golang.org/x/net`).
  - `quay.io/keycloak/keycloak:26.8.1`: 1 CRITICAL (OpenJDK).
  - `mysql:8.4`: 2 CRITICAL (`gosu`, `certifi`).
- Live lab, HAProxy 2.8.30 and Data Plane API 3.0.28:
  - `Direct` with self-signed certificate: test 200, 56 routes, 56 servers,
    5 s live samples, protocol counters from `;csv`.
  - stats-only: test 105 rows, refresh 0 routes / 56 servers, metrics and
    protocol buckets persisted, `drain`/`ready` through the stats page verified
    as `admin_state` on the node.
  - certificates: metadata read, upload/replace/delete 204, list reflects each
    step; an invalid EC PEM is rejected with 502 and the Data Plane API message.
  - `SystemAdmin` can save a non-matching `Direct` host; the unit tests cover
    host matching, IPv6 brackets, trailing dots and unsafe URLs.
  - cluster created, assigned and displayed on the instance card.
- `make security-smoke` was not run: it needs disposable personal MCP tokens.
  The module adds no MCP tools; the existing 2026-11-19 smoke result stands.
