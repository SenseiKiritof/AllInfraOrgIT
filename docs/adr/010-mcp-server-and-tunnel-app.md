# ADR-010 — MCP server and desktop tunnel app

- Status: accepted
- Date: 2026-11-09

## Context

InfraOrgIT should be usable by AI clients through the Model Context Protocol
and should replace the external XPipe workflow for SSH tunnels. A browser
cannot open a TCP port on the user's machine, so tunnels need a local
component. The full study, tool catalogue and effort ranges are in
`docs/architecture/mcp-server-and-tunnels.md`.

## Decision

- **MCP server in the API.** Streamable HTTP endpoint `/mcp`, JSON-RPC,
  protected-resource metadata at `/.well-known/oauth-protected-resource`.
  Keycloak is the OAuth 2.1 authorization server; personal API keys (hashed in
  `ApiTokens`, scopes, expiry, revocation) are also accepted. Both map to the
  same `Users` row and reuse `EnvironmentAccessService`.
- **Read and action tools.** Read tools expose providers, environments,
  servers, applications, deployments, projects, topology, reachability and
  audit. Action tools (`reachability.run`, `actions.run`) are enabled per
  user/group through `McpGrants`; the environment RBAC remains mandatory. No
  raw shell and no create/update/delete tools in v1.
- **Audit.** A new append-only `AuditEvents` table and `IAuditService` record
  every MCP call (including denied ones) and tunnel start/stop/error.
  `CommandExecutions` stays the SSH command log. Retention defaults to 180
  days, configurable.
- **Desktop app.** A signed cross-platform application (macOS arm64/x64,
  Windows, Linux) that embeds the SPA for **multiple InfraOrgIT instances**
  and manages local tunnels. Tunnels use the user's SSH agent through the
  system `ssh -L`/`-J` process (`SSH_AUTH_SOCK`, `~/.ssh/config`); no private
  key is stored by InfraOrgIT or the app. Targets come from an API allowlist
  derived from the inventory; the app binds `127.0.0.1` only.
- XPipe deep links and copyable `ssh -L` commands are interim shortcuts until
  the app ships.

## Alternatives considered

- **API-host tunnels with a browser WebSocket proxy**: rejected, it turns the
  API into a TCP proxy with SSRF, abuse and resource-exhaustion risks.
- **XPipe only**: rejected as the target because it is a separate desktop app
  with no central audit and no multi-instance integration; kept as interim.
- **MCP with OAuth only**: rejected, desktop/IDE clients often lack OAuth
  discovery; API keys cover them behind the same RBAC.
- **MCP read-only**: rejected, the user wants guarded actions configured per
  user.
- **Extending `CommandExecutions` for MCP/tunnels**: rejected, the table is
  shaped for SSH command runs and feeds the execution log page.
- **One audit table per feature**: rejected, it multiplies pages, filters and
  retention policies for little benefit.

## Consequences

- New API surface and Keycloak client(s), a token table, a grants table and an
  audit table; migrations and OpenAPI updates.
- A new desktop application to build, sign, notarize, distribute and update on
  three operating systems; this is the largest part of the effort.
- Tunnel credentials depend on the user's SSH agent; users without an agent
  cannot open tunnels.
- MCP tools return inventory data to AI clients: tool output is untrusted and
  action tools need confirmation, rate limits and audit.
- Active tunnel state lives in the desktop app; if the web UI must show it, a
  `TunnelSessions` projection is a follow-up.
