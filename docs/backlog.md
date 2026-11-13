# Backlog

Opened on 2026-10-27. Each item is work not done yet: tick only after its verification passes.

## Frontend — `InfraOrgITWeb`

- [x] **Menu item icons**
  `@heroicons/react` + `path → icon` mapping in `src/lib/icons.ts` (fallback for unknown paths, detail routes mapped to their list). Tests in `src/lib/icons.test.ts`.

- [x] **User and theme icons in the header**
  Theme toggle with `SunIcon`/`MoonIcon`, user in a `details` element with `UserCircleIcon` and logout with `ArrowRightOnRectangleIcon`.

- [x] **Detail header: back + fullscreen**
  In `Shell`: “Back” button to the list when the path is `/<section>/<id>` and fullscreen toggle (`documentElement.requestFullscreen`, state synced on `fullscreenchange`).
  Still to evaluate: use the menu `HideBackButton` instead of path matching, if exceptions are needed later.

- [x] **Servers page UI bugs**
  Sidebar made scrollable (`min-h-0 overflow-y-auto`) and shell `overflow-hidden`; tables already inside `overflow-x-auto`. The residual overlay from the screenshot is not reproducible after refresh: if it comes back, note the route and menu state.

## MCP

- [x] **Read tools and audit**
  Remaining read tools (`list_providers`, `get_application`, `get_project`, `list_reachability_tests`, `get_topology`, `list_executions`), `AuditEvents` retention (180 days) and `GET /api/audit-events` + `/audit` page for SystemAdmin.
  Verification: MCP/audit integration tests and API CI green.

## Desktop — `InfraOrgITDesktop`

- [x] **Electron shell and multi-instance manager**
  Electron (ADR-012); one manager window with an isolated Chromium partition per instance, per-user `instances.json`, URL validation, BFF session reuse, device-flow fallback and tunnel projection.
  Verification: `npm --prefix InfraOrgITDesktop/electron run test:unit` green.

- [x] **Tunnel allowlist and audit API**
  `tunnels:operate` token scope; `GET /api/tunnels/targets` (operator environments only, jump host and username from the server, target from the deployment) and `POST /api/tunnels/events` writing `TunnelStart`/`TunnelStop`/`TunnelError`.
  Verification: integration test for scope, RBAC, allowlist and audit rows.

- [x] **Desktop tunnel engine**
  System `ssh -L`/`-D`/`-R` with `SSH_AUTH_SOCK`, multi-hop `-J`, local port allocation, start/stop/status, audit and heartbeats; refresh token in `safeStorage`.
  Verification: local sshd with a test key, negative test on a non-allowlisted target, Electron unit tests for the argument builder and port guard.

- [x] **XPipe-style tunnel services**
  Server services (Local/Dynamic/Remote, Tcp/Http/Https, openPath), `ss -tlnH` port discovery, ServerAdmin CRUD and the allowlist in the desktop. The API still stores `autoStart`, but the Electron client does not auto-start services.
  Verification: API integration tests for CRUD/discovery/jumps/remote visibility, Electron tests for every mode.

- [x] **Desktop release flow**
  Desktop in `REPOS`, `make desktop-ci` gate (npm unit tests), five-repo `versions.lock`, release docs and push list; `publish.yml` builds the Electron packages and checks the tag is on `main`; `Version tags` ruleset immutable.
  Verification: `make desktop-ci`, `make -n release`, shellcheck and workflow checks.

- [x] **Desktop device login**
  RFC 8628 + PKCE with the `infraorgit-mcp-desktop` client, issuer discovery, user code opened in the browser, tunnel targets loaded with the resulting token and the refresh token encrypted with `safeStorage`.
  Verification: full flow against the local realm (device request, consent, access token with `mcp:read tunnels:operate`, refresh token) and Electron unit tests.

- [x] **Central tunnel visibility**
  `TunnelSessions` projection with 30s heartbeats, two-minute staleness cleanup, `GET /api/tunnels/sessions` filtered to operator environments and `/tunnels` page with 15s refresh.
  Verification: API integration tests and desktop heartbeat tests green.

- [x] **Rate limits**
  Dedicated `mcp` and `tunnels` fixed windows (120/min per user or token), with a burst test returning 429.

- [x] **Security smoke**
  `scripts/security-smoke.py` + `make security-smoke`: 401 matrix, metadata/challenge RFC 9728, scope split, grant/RBAC denial, tunnel allowlist, audit denial, headers, CORS and optional 429 burst.
  Verification: 16/16 PASS locally; the missing `resource_metadata` finding was fixed in the API and covered by a test.

- [ ] **Electron packaging release**
  Run the Electron publish workflow and verify the four packages on clean machines: osx-arm64, osx-x64, win-x64 and linux-x64, with artifacts and GitHub Release assets present.
  Verification: workflow run green, each package installs and opens.

- [ ] **Signing and notarization**
  Add an Electron signing/notarization setup (macOS Developer ID, Windows Authenticode) and verify Gatekeeper, stapled ticket and Authenticode on a clean machine; packages stay unsigned until then.

- [ ] **Penetration test**
  Full external pentest of the MCP surface, tunnel abuse and the web app; the security smoke only covers the automated baseline.

## Security

- [x] **Pentest 2026-11 high findings**
  Deploy secrets/network/templating (PT-01), API-key history redaction + scrub (PT-02), deploy MCP scope/secret (PT-03), cross-environment jump host and proxy route guards (PT-04/PT-06).
  Verification: API integration tests, deploy preflight/compose config, local full stack healthy; report section 10.

- [x] **Pentest 2026-11 medium fixes**
  RBAC metadata reads restricted to SystemAdmin (PT-05); session revocation on role/group changes (PT-07); SSH/SFTP host-key pinning (PT-09); audit rows for file transfer/inventory/tunnel services (PT-10); signed checksum manifest for desktop installs (PT-11); HTTP/SPA action confirmation (PT-13); tunnel-session target validation (PT-14); SameSite/transport/MCP prompt-injection docs (PT-15/16/18); deploy password policy, optional/configurable TOTP (`KEYCLOAK_MFA`) and plain FTP off (PT-08/16/17).
  Verification: API integration tests, Web 101 tests, desktop 153 tests, deploy preflight/compose config, disposable Keycloak 26.8.1 logins with `KEYCLOAK_MFA` false and true, publish manifest signature `Verified OK`.

- [ ] **Pentest 2026-11 accepted/operational residual**
  Inventory/environment reads stay open to authenticated users by design (D7); per-environment filtering is a product decision. The audit chain anchor is implemented (HMAC webhook) but needs a real append-only SIEM/WORM sink. Existing Keycloak realms need the MFA flow recreated and enabled explicitly (`KEYCLOAK_MFA=true`; `--import-realm` does not update them); master realm/brokered IdPs remain operational. Plain FTP is off in deploy and only a dev/legacy opt-in. Images are signed with cosign, SBOM/provenance are published on non-PR builds.

## Workspace

- [x] **Rename workspace and subrepositories**
  `AllInfraOrgIT`, `InfraOrgITApi`, `InfraOrgITWeb`, `InfraOrgITDocker` (no legacy prefix, no dots). Updated `Makefile`, `scripts/`, workflows, `versions.lock`, docs, README and GitHub remotes. Legacy copies were archived outside the workspace.
  Compose project `infraorgit`, images `infraorgit-api`/`infraorgit-web` (Docker names must be lowercase).

- [ ] **Validate the versioned Docker images**
  The `v0.2.0` tag and multi-arch GHCR images exist; `main`/`dev` images are
  signed with cosign, with SBOM and build provenance verified. The release
  compose uses explicit `API_TAG`/`WEB_TAG` and accepts a digest.
  Missing: a new version tag after the signing change (`0.2.0`/`latest` predate
  it), image digests in `versions.lock`, and a release-compose run pinned to a
  digest.
  Verification: `docker manifest inspect`, `cosign verify` and
  `gh attestation verify` on `main`; `gh run list` green.
