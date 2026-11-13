# ADR-012 — Electron desktop shell

- Status: accepted
- Date: 2026-11-13
- Supersedes: ADR-011
- Related: ADR-010 (MCP server and tunnel app), ADR-003 (Keycloak BFF), ADR-011

## Context

ADR-011 chose .NET 10 + Photino.NET for `InfraOrgITDesktop`: a manager window
with one child `PhotinoWindow` per instance, rendering on the OS webview
(WKWebView, WebView2 or WebKitGTK), with the tunnel engine in the same
process.

That stack reached its limits:

- the OS webviews diverge in rendering and in cookie/session behavior, and the
  one-message-loop model makes multi-window state harder to reason about;
- packaging, signing, notarization and update had to be built separately for
  each runtime;
- the native token store passed the refresh token to the macOS `security`
  helper in `argv` (pentest PT-16);
- the workspace already has a working Electron shell with isolated Chromium
  partitions, BFF/device authentication and tunnel projection.

The shell stays a desktop wrapper around the existing SPA; it is not a second
frontend.

## Decision

Use **Electron** as the desktop shell, in
`InfraOrgITDesktop/electron/` (sibling npm project, Node 24).

- One manager window hosts the landing page (instance cards) and the instance
  tabs. A tab is a `WebContentsView`, so the shell chrome stays local while the
  SPA keeps its navigation state.
- Each instance URL gets its own persistent Chromium partition
  (`persist:instance-<hash>`). Cookies, the BFF session and storage never cross
  instances.
- Authentication reuses the instance BFF session. Without one, the main process
  runs the RFC 8628 device flow with PKCE against the public
  `infraorgit-mcp-desktop` client, opens the verification URL in the default
  browser and keeps the device code, PKCE verifier and access token in the main
  process. The refresh token is encrypted with Electron `safeStorage`; renderers
  never receive a token.
- The tunnel engine spawns the system `ssh` with the user's `SSH_AUTH_SOCK`,
  accepts only targets returned by `GET /api/tunnels/targets`, binds loopback
  ports and projects start/stop/error plus 30-second heartbeats to
  `POST /api/tunnels/events` and `POST /api/tunnels/sessions`. No private key is
  stored by the app.
- Downloads use Chromium's native download for attachments and the desktop blob
  bridge for generated results. The signed-ticket `/api` download endpoints
  remain a compatibility path but are not used by this client.
- The renderer boundary is narrow: `contextIsolation`, `nodeIntegration: false`,
  `sandbox: true`, and a preload bridge exposed only on the instance origin.
- GitHub Actions builds the packages on a `v*` tag for macOS arm64
  (`osx-arm64`), macOS Intel (`osx-x64`), Windows x64 (`win-x64`) and Linux x64
  (`linux-x64`), and creates or updates the GitHub Release with the archives and
  their checksums. Packages are unsigned until a macOS/Windows signing setup is
  added.

## Alternatives considered

- **Stay on .NET + Photino (ADR-011)**: rejected. OS webview divergence, the
  single message loop, per-platform packaging work and the keychain `argv`
  exposure outweigh the smaller binary.
- **Tauri**: rejected. It would rewrite the existing Electron main process and
  tunnel projection in Rust without removing the need to bundle a webview.
- **Browser-only Web app**: rejected. It cannot spawn `ssh` with the user's
  agent, manage several instances in one shell or project process-level tunnel
  state.
- **One native window per instance** (the Photino model): rejected. A single
  manager window with tabs keeps the instance list, tunnel drawer and command
  palette in one place while still isolating sessions per partition.

## Consequences

- The app bundles Chromium: larger installers than a native webview shell, and
  Electron upgrades are part of maintenance.
- The desktop toolchain is npm/Node 24; the meta repo gate is
  `make desktop-ci` (`npm ci` plus `npm run test:unit`), not `dotnet`.
- `safeStorage` depends on the OS keyring. On Linux without a Secret Service it
  refuses to persist and keeps the session in memory for that run.
- Signing, notarization, auto-update and installers are follow-up work; the
  publish workflow ships unsigned packages until then.
- ADR-011 is superseded. Historical references to the Photino build in the
  pentest report stay as evidence and are not current state.
