# ADR-011 — desktop shell with .NET and Photino

- Status: accepted
- Date: 2026-11-10
- Supersedes: none
- Related: ADR-010 (MCP server and tunnel app), D3/D4/D5

## Context

ADR-010 decided that local SSH tunnels live in a desktop app that also offers
the browser features and connects to several InfraOrgIT instances. This
decision covers the shell stack, not the tunnel engine.

Constraints:

- one codebase for macOS, Windows and Linux;
- an embedded webview per instance, reusing the existing SPA;
- no Chromium bundle if the OS already provides a webview;
- keep the workspace on .NET 10 where possible;
- a small dependency surface, since the app will later spawn `ssh` and handle
  tokens.

## Decision

Use **.NET 10 + [Photino.NET](https://www.tryphotino.io/)** in a new sibling
repository, `InfraOrgITDesktop`.

- A manager window hosts the local HTML UI (instances list) and owns the
  native message loop.
- Each opened instance is a child `PhotinoWindow` pointing at the instance
  URL, created from the manager's web-message handler. Sessions for different
  instances stay isolated in separate windows.
- Instances are stored in a per-user JSON file, validated to `http`/`https`
  and saved atomically.
- Tunnel management will be added in the same process: spawn the system
  `ssh -L`/`-J`, inherit `SSH_AUTH_SOCK`, and only accept targets returned by
  the instance API.

## Consequences

- No bundled browser runtime; rendering depends on WKWebView, WebView2 or
  WebKitGTK, so visual differences are possible.
- Photino has a single message loop. Windows must be created on the UI thread
  from a message handler, not from background threads; the code documents and
  follows this pattern.
- Packaging, signing, notarization and auto-update remain open, as in
  ADR-010; this ADR only fixes the stack.
- The desktop repository is not part of `make` or `versions.lock` yet. Add it
  to the release flow when there is a distributable build.
