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

- [x] **Shell and multi-instance manager**
  .NET 10 + Photino (ADR-011); per-user `instances.json`, one child window per instance, URL validation, unit tests and three-OS CI.
  Verification: `dotnet test InfraOrgITDesktop.slnx` and `ci` green on ubuntu/macos/windows.

- [x] **Tunnel allowlist and audit API**
  `tunnels:operate` token scope; `GET /api/tunnels/targets` (operator environments only, jump host and username from the server, target from the deployment) and `POST /api/tunnels/events` writing `TunnelStart`/`TunnelStop`/`TunnelError`.
  Verification: integration test for scope, RBAC, allowlist and audit rows.

- [x] **Desktop tunnel engine**
  System `ssh -L`/`-J` with `SSH_AUTH_SOCK`, local port allocation, start/stop/status and audit calls; token kept in memory or the OS keychain.
  Verification: local sshd with a test key, negative test on a non-allowlisted target.
  Done with the token in memory; checked against a local sshd container and `ssh-agent` (authenticated, local port listening). Non-allowlisted targets are rejected by the API integration test.

- [x] **Desktop device login**
  RFC 8628 + PKCE with the `infraorgit-mcp-desktop` client, issuer discovery, user code opened in the browser and tunnel targets loaded with the resulting token.
  Verification: full flow against the local realm (device request, consent, access token with `mcp:read tunnels:operate`, refresh token) and 23 desktop tests.

- [x] **Desktop token persistence and refresh**
  Refresh token in macOS Keychain, Windows Credential Manager or `secret-tool` (memory fallback), session restore, refresh within 60s of expiry and once on 401, logout clears the store.
  Verification: 38 desktop tests; platform stores use fake runners in CI, real keychain/signtool behavior still needs a manual run.

- [x] **Central tunnel visibility**
  `TunnelSessions` projection with 30s heartbeats, two-minute staleness cleanup, `GET /api/tunnels/sessions` filtered to operator environments and `/tunnels` page with 15s refresh.
  Verification: API integration tests and desktop heartbeat tests green.

- [x] **Rate limits**
  Dedicated `mcp` and `tunnels` fixed windows (120/min per user or token), with a burst test returning 429.

- [x] **Signing and notarization workflow**
  `publish.yml` imports the macOS certificate, signs, notarizes and staples, signs Windows with signtool, and uploads a GitHub Release on `v*` tags; unsigned builds still work without secrets.
  Verification: actionlint/shellcheck clean and unsigned publish works; real certificates and notarization need the repository secrets.

- [x] **Update check**
  The manager reads GitHub `releases/latest`, compares the assembly version and opens the release page; notes capped, stable tags only.
  Verification: 23 fake-handler tests and three-OS CI; no download/install.

- [ ] **Automatic update install**
  Download the signed artifact, verify it and replace the app; the updater is still manual (release page) and the desktop repo is not in `make release`/`versions.lock`.

## Workspace

- [x] **Rename workspace and subrepositories**
  `AllInfraOrgIT`, `InfraOrgITApi`, `InfraOrgITWeb`, `InfraOrgITDocker` (no legacy prefix, no dots). Updated `Makefile`, `scripts/`, workflows, `versions.lock`, docs, README and GitHub remotes. Legacy copies were archived outside the workspace.
  Compose project `infraorgit`, images `infraorgit-api`/`infraorgit-web` (Docker names must be lowercase).

- [ ] **Validate the Docker images on the first tag**
  Implemented `InfraOrgITWeb/Dockerfile` + `Caddyfile`, image version labels for the API, `docker.yml` workflows in `InfraOrgITApi` and `InfraOrgITWeb` (GHCR, tags `X.Y.Z`, `X.Y`, `sha`, `latest`).
  Missing: first `v*` tag, workflow and push verification, image digests in `versions.lock`, published image usage in the release compose.
  Verification: `gh run list` green, `docker pull` both images, `APP_VERSION`/`VITE_APP_VERSION` visible at runtime.
