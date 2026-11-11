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
  System `ssh -L`/`-D`/`-R` with `SSH_AUTH_SOCK`, multi-hop `-J`, local port allocation, start/stop/status, audit and heartbeats; token in the OS keychain.
  Verification: local sshd with a test key, negative test on a non-allowlisted target, 93 desktop tests.

- [x] **XPipe-style tunnel services**
  Server services (Local/Dynamic/Remote, Tcp/Http/Https, openPath, autoStart), `ss -tlnH` port discovery, ServerAdmin CRUD, allowlist in the desktop, autoStart and open-in-browser for Local HTTP(S).
  Verification: API integration tests for CRUD/discovery/jumps/remote visibility, desktop tests for all modes and autoStart.

- [x] **Auto-reconnect**
  AutoStart custom services retry up to 3 times with a 5s delay after an unexpected ssh exit; user stop, panel change, logout and exit cancel retries, and token/auth failures do not retry.
  Verification: 101 desktop tests, including retry budget, busy fixed port and new session ids.

- [x] **Tunnel persistence across restarts**
  `tunnels.json` stores only identity (instance/server/service or deployment, mode, requested port), atomic and secret-free; startup restore refreshes the keychain token, loads the allowlist, prunes deleted/disabled services and skips active ones; clear action.
  Verification: 117 desktop tests covering restore, missing token, pruning, stop/logout removal.

- [x] **Windows GUI smoke**
  `gui-smoke-windows` on `windows-latest` starts the app, waits 8s and fails on early exit; window handle logged. Linux job unchanged.
  Verification: run 43004152371 green, negative path tested.

- [x] **Desktop release flow**
  Desktop in `REPOS`, `make desktop-ci` gate, five-repo `versions.lock`, release docs and push list; `publish.yml` refuses tags not on `main`; `Version tags` ruleset immutable.
  Verification: `make desktop-ci`, `make -n release`, shellcheck and workflow checks.

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

- [x] **Update check, download and install**
  The manager reads GitHub `releases/latest`, compares the assembly version, downloads the matching archive and verifies SHA-256; macOS/Linux/Windows replace the published app through a detached helper and restart. Stable tags only; missing checksum requires explicit confirmation.
  Verification: 144+ desktop tests, real mac/Linux helpers and Windows script checks, three-OS CI; signature verification beyond SHA-256 still open.

- [x] **Platform integration tests**
  Real macOS Keychain, Windows Credential Manager, `secret-tool` when available, and macOS/Linux install helpers executed on disposable fake apps; Linux/macOS/Windows CI runs with OS guards.
  Verification: 147/146/145 passed with only OS/tool skips.

- [x] **Security smoke**
  `scripts/security-smoke.py` + `make security-smoke`: 401 matrix, metadata/challenge RFC 9728, scope split, grant/RBAC denial, tunnel allowlist, audit denial, headers, CORS and optional 429 burst.
  Verification: 16/16 PASS locally; the missing `resource_metadata` finding was fixed in the API and covered by a test.

- [x] **Packaging artifacts**
  Manual `publish` dispatch for `0.0.0-test` built and uploaded all four RIDs (osx-arm64, osx-x64, win-x64, linux-x64).
  Verification: run 43010389019, artifacts present.

- [ ] **Real signing and notarization**
  Run the publish workflow with the Apple/Windows certificates and notarization secrets; verify Gatekeeper, stapled ticket and Authenticode on a clean machine.

- [ ] **Penetration test**
  Full external pentest of the MCP surface, tunnel abuse and the web app; the security smoke only covers the automated baseline.

## Security

- [x] **Pentest 2026-11 high findings**
  Deploy secrets/network/templating (PT-01), API-key history redaction + scrub (PT-02), deploy MCP scope/secret (PT-03), cross-environment jump host and proxy route guards (PT-04/PT-06).
  Verification: API integration tests, deploy preflight/compose config, local full stack healthy; report section 10.

- [ ] **Pentest 2026-11 medium/low findings**
  Environment-filtered reads or accepted-risk decision (PT-05), session role revocation (PT-07), MFA/password policy (PT-08), file-transfer host-key pinning (PT-09), audit coverage/tamper evidence (PT-10), signed updater trust (PT-11), per-token rate limits (PT-12), HTTP confirmation enforcement (PT-13), tunnel session target validation (PT-14), SameSite/doc alignment (PT-15), transport hardening (PT-16), resource limits (PT-17), MCP prompt-injection guidance (PT-18).
  Partial in the deploy stack: password policy + bootstrap preflight (PT-08), transport guidance (PT-16), service resource limits (PT-17). MFA enforcement, FTP/TLS client support and the remaining container rootfs gaps stay open.

## Workspace

- [x] **Rename workspace and subrepositories**
  `AllInfraOrgIT`, `InfraOrgITApi`, `InfraOrgITWeb`, `InfraOrgITDocker` (no legacy prefix, no dots). Updated `Makefile`, `scripts/`, workflows, `versions.lock`, docs, README and GitHub remotes. Legacy copies were archived outside the workspace.
  Compose project `infraorgit`, images `infraorgit-api`/`infraorgit-web` (Docker names must be lowercase).

- [ ] **Validate the Docker images on the first tag**
  Implemented `InfraOrgITWeb/Dockerfile` + `Caddyfile`, image version labels for the API, `docker.yml` workflows in `InfraOrgITApi` and `InfraOrgITWeb` (GHCR, tags `X.Y.Z`, `X.Y`, `sha`, `latest`).
  Missing: first `v*` tag, workflow and push verification, image digests in `versions.lock`, published image usage in the release compose.
  Verification: `gh run list` green, `docker pull` both images, `APP_VERSION`/`VITE_APP_VERSION` visible at runtime.
