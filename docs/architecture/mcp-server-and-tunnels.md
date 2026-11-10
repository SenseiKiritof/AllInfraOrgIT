# MCP server and local tunnels — feasibility study

- Status: stage 1-2 implemented; desktop shell started (stage 3)
- Date: 2026-11-09
- Scope: expose InfraOrgIT as an MCP server; evaluate local SSH tunnels (XPipe today) and how they could live in InfraOrgIT.

## 1. Questions

1. Can InfraOrgIT act as a **Model Context Protocol server**, so an AI client
   (Claude, OpenCode, IDE agents) can read the inventory and, later, run the
   same guarded actions a user can?
2. Can InfraOrgIT replace or complement **XPipe tunnels**? A browser cannot
   open a TCP port on the user's machine, so the tunnel engine must run
   somewhere else: the desktop, a small local agent, or the API host.

## 2. Foundations already in the code

| Area | What exists | Consequence |
|---|---|---|
| API | ASP.NET Core 10, minimal APIs under `/api`, OpenAPI generated | MCP can be a new endpoint in the same process, reusing services |
| Auth (users) | Keycloak + BFF cookie (`SessionAuthenticationHandler`), no token in JS | MCP clients cannot use the cookie: need a bearer/JWT scheme for `/mcp` |
| RBAC | `EnvironmentAccessService`: `SystemAdmin`, `ServerAdmin`, `ServerOperator` per provider environment | Tool calls must re-check the same rules; `SystemAdmin` does not imply server rights (D7=B) |
| SSH | `SshConnector` (SSH.NET) with jump hosts, host-key pinning and `ForwardedPortLocal` for SFTP through a jump host | the same primitive can open local forwards; tunnel code would reuse credential resolution, not invent it |
| Audit | `CommandExecutions` stores action/reachability/console runs, redacted | MCP tool calls and tunnel sessions need their own audit trail or a common one |
| Rate limits | fixed-window policies for remote run, reachability, console, files (`Program.cs:179`) | add a policy per MCP client/tool and per tunnel |
| Front door | Caddy serves `/api/*`, `/auth/*`, `/realms/*`, `/resources/*` | add `/mcp*` and `/.well-known/oauth-protected-resource*` routes |
| API keys | `ApplicationApiKeys` are **outbound** keys used to call external APIs | they are not an inbound authentication mechanism for InfraOrgIT |

## 3. InfraOrgIT as an MCP server

### 3.1 Protocol and transport

MCP is JSON-RPC 2.0. For a server inside a web API the relevant transport is
**Streamable HTTP**: a single `/mcp` endpoint that accepts POST requests,
returns JSON (or an SSE stream when the client asks for progress), optionally
supports GET for server-initiated messages. `stdio` is not usable inside the
container; it is only an option for a local companion process.

Current MCP authorization (spec revision 2026-07-28) expects an HTTP MCP
server to be an **OAuth 2.1 resource server**:

- `401` with `WWW-Authenticate: Bearer resource_metadata="…"`;
- Protected Resource Metadata (RFC 9728) at
  `/.well-known/oauth-protected-resource` (plus the path variant for `/mcp`);
- Keycloak as authorization server (RFC 8414 metadata already exposed);
- resource indicators (RFC 8707) and PKCE for public clients.

Keycloak is already the identity provider, so it can also be the
authorization server for MCP. Two client profiles:

| Client | Flow | Use |
|---|---|---|
| Service/integration | client credentials, audience `infraorgit-mcp`, scopes `mcp:read` / `mcp:operate` | CI, automation, agents without a human |
| Interactive desktop/IDE | authorization code + PKCE, same user as the SPA | Claude Desktop, OpenCode, IDE plugins |

Personal API keys are also in scope (decision D1): a new `ApiTokens` table
stores a hash, name, owner, scopes, expiry and last use, with create/revoke in
the user profile. OAuth stays the primary path for clients that support it;
API keys cover desktop/IDE clients without OAuth discovery. Both map to the
same user and RBAC checks.

### 3.2 Tools and scopes (v1 read-only)

Read tools reuse the existing queries and DTOs; every call takes the caller's
identity and checks access exactly as the HTTP endpoints do.

| Tool | Returns | Permission |
|---|---|---|
| `providers.list` | providers and environments | authenticated |
| `servers.list` / `servers.get` | servers with sizing, OS, HA, operator | authenticated; filtered by environment access |
| `applications.list` / `applications.get` | catalog, types, versions | authenticated |
| `deployments.list` | version on server, runtime, container fields, ports | authenticated |
| `projects.list` / `projects.get` | projects and their servers (integrated/production) | authenticated |
| `topology.get` | the diagram model, proxy routes and virtual hosts | authenticated |
| `reachability.list` | tests and last results | authenticated |
| `executions.list` | audit entries, redacted | authenticated, same filter as the page |

Action tools in a second phase, reusing the existing guarded services:

| Tool | Permission | Extra guard |
|---|---|---|
| `reachability.run` | `ServerOperator` on the target environment | rate limit, explicit `confirm: true` |
| `actions.run` | `ServerOperator` on the target environment | confirmation, idempotency key, existing redaction |
| `tunnels.*` | `ServerOperator` / `ServerAdmin` | see section 4 |

No create/update/delete tools in v1. No raw shell: `commands` would be a
free-form execution tool and defeats the action allowlist. The console stays
interactive-only.

Action tools are enabled per user, not only by scope (decision D2): a new
`McpGrants` table (user or group, allowed read/action tools, optional
environment filter) is checked before the environment RBAC. A user can see the
tools they are granted and nothing more; a grant never overrides a missing
`ServerAdmin`/`ServerOperator` right.

Resources (`infraorgit://servers/{id}`, `infraorgit://applications/{id}`) can
expose the same JSON for clients that prefer resources to tools. Prompts can
ship a few operational templates ("diagnose a server", "which servers run
this application") without adding new permissions.

### 3.3 Authentication and authorization design

- New authentication scheme for `/mcp` only: JWT bearer from Keycloak
  (`Authority` public issuer, `Audience` `infraorgit-mcp`). The SPA keeps the
  cookie scheme; no mixed-mode on `/api`.
- Map the token to `Users.Username` (`preferred_username`) and build a
  `ClaimsPrincipal` the existing `EnvironmentAccessService` accepts. No new
  permission model.
- Tool visibility is filtered per caller (an operator does not see tools they
  cannot run), but the call always re-checks: list filtering is UX, not
  security.
- Scopes are coarse (`mcp:read`, `mcp:operate`); environment-level rights stay
  in the database.
- Per-client rate limits: e.g. 60 read calls/minute, 10 action calls/minute,
  and a global cap per token. Reuse the existing fixed-window approach.
- Every call writes an audit row: client id, user, tool, target ids, duration,
  outcome, error code. Do not log arguments that contain secrets.
- Response size cap and pagination on every list tool; truncate long fields
  with an explicit marker.
- Tool output is untrusted input for the AI client (prompt injection). The
  server only returns inventory data; action tools require an explicit
  confirmation field and never accept arbitrary commands.

### 3.4 Endpoint and deployment

```
POST /mcp                  JSON-RPC (Streamable HTTP)
GET  /mcp                  optional SSE stream
GET  /.well-known/oauth-protected-resource
GET  /.well-known/oauth-protected-resource/mcp
```

Caddy additions:

```caddyfile
handle /mcp* {
    reverse_proxy {$API_UPSTREAM:api:8080}
}
handle /.well-known/oauth-protected-resource* {
    reverse_proxy {$API_UPSTREAM:api:8080}
}
```

Keycloak: a new confidential client `infraorgit-mcp` with the two scopes, a
service account for client credentials, and the SPA client kept separate.
Disable the endpoint with `Mcp:Enabled=false` by default in production until
the feature is approved.

### 3.5 Implementation choice

- Preferred: the official C# MCP SDK (`ModelContextProtocol` package). It
  handles protocol version negotiation, Streamable HTTP and JSON-RPC details;
  pin the version and cover it with contract tests (MCP Inspector + a test
  client).
- Fallback for a read-only MVP: a small JSON-RPC handler for `initialize`,
  `tools/list`, `tools/call`, `resources/list`, `resources/read`. Less code
  than the SDK integration but the protocol surface must be maintained.
- Tests: protocol conformance, 401/metadata discovery, RBAC matrix per tool,
  rate limit, audit row, response truncation, prompt-injection strings kept
  inert.

### 3.6 Effort

| Slice | Days (person) |
|---|---|
| Read-only MVP with a static bearer/API key | 5–7 |
| OAuth 2.1 + protected-resource metadata + Keycloak client | +5–8 |
| Full read tools, filtering, audit, tests, docs | +4–6 |
| Audit foundation (`AuditEvents` + service) | 4–6 |
| Action tools (`reachability.run`, `actions.run`) + `McpGrants` UI | +6–9 |
| Hardening, observability, client allowlist | +3–5 |
| **Total, read-only production (both auth)** | **20–28** |
| **Total, read-only + actions** | **29–42** |

## 4. Local tunnels

### 4.1 What XPipe does today

XPipe is a desktop connection hub, not a web app. Its documentation confirms
local, remote and dynamic SSH tunnels that can be toggled on/off, and the
`xpipe://` URL handler (plus the `xpipe open` CLI) used to launch actions and
connections from other tools. It relies on the user's OpenSSH client and has
no web interface.

Consequence: **the browser cannot open `localhost:PORT`**. Any tunnel engine
must run on the user's machine or on a host they can reach. Installing an app
is not optional for a real local forward; the question is which app.

### 4.2 Options

| Option | How it works | Pros | Cons | Effort |
|---|---|---|---|---|
| **A. XPipe deep links** | InfraOrgIT shows "Apri in XPipe" on a server/deployment, generating an `xpipe://` URL; the user toggles the tunnel in XPipe | no new app, uses the existing XPipe tunnel workflow, no credentials in the browser | manual toggle, XPipe must be installed and its URL handler/CLI available, no central tunnel audit, tunnel licensing to verify | 1–2 days |
| **B. Copyable `ssh -L`** | InfraOrgIT composes the exact command from server, jump host and target port | zero dependencies, transparent | manual, terminal required | 1 day |
| **C. Local InfraOrgIT agent** | small cross-platform CLI/tray app; device login to InfraOrgIT, fetches allowlisted targets, opens SSH local forwards with SSH.NET, reports status and audit | fully integrated, central audit, no XPipe dependency, reuses jump hosts/host-key pinning | new app to install, sign and update; credential handling; 3 OS targets | 15–25 days + packaging |
| **D. API-host tunnel + WebSocket proxy** | API opens the forward, browser tunnels TCP over WebSocket to `/api/tunnels/{id}` | works from any browser, no install | API becomes a TCP proxy: SSRF/abuse/resource exhaustion, latency, complex backpressure; not recommended | 20–30 days |

Decision D3: **C is the target**, with A + B as interim shortcuts until the
app ships. Do not build D unless a browser-only requirement appears later.

### 4.3 Desktop app design (option C)

- Scope (decision D3): a desktop application that offers the browser features
  and the tunnels in one place, and can connect to **several InfraOrgIT
  instances** (name, URL, account per instance, tabs or a switcher).
- Shell: a thin native shell with an embedded webview per instance, so the SPA
  is reused instead of duplicated; the tunnel engine and the instance switcher
  live in the native shell.
- Distribution (decision D4: all modern OS): .NET self-contained app for macOS
  (arm64/x64), Linux and Windows; signed and notarized on macOS, signed on
  Windows; auto-update from a signed manifest.
- Auth: OAuth 2.1 device authorization grant (RFC 8628) through Keycloak; the
  agent never stores the user's password. Token refresh and revoke.
- Targets: the API returns an allowlist derived from the inventory
  (`ServerId` + target host/port, typically the deployment `ExposedPort` or a
  `HostPort`), never an arbitrary host:port from the client. The agent cannot
  create a tunnel to something the user cannot see.
- Bind: `127.0.0.1` only, ephemeral or requested local port above 1024;
  collision check; max concurrent tunnels; idle timeout.
- SSH (decision D5): use the **user's SSH agent**. The first implementation
  spawns the system `ssh -L`/`-J` process, inheriting `SSH_AUTH_SOCK` and the
  user's `~/.ssh/config`; no private key reaches InfraOrgIT or the app. A later
  native SSH.NET path can use an agent connector, but the process approach is
  smaller and matches how XPipe works.
- Audit/status: agent reports start/stop/errors; the API stores tunnel events
  and shows them in the server detail and the audit log.
- UI: server/deployment action "Apri tunnel", list of active local tunnels,
  copy port; requires `ServerOperator`/`ServerAdmin` on the environment.
- Tests: unit for allowlist/bind/port allocation, integration with the
  existing `FakeSsh`, manual E2E against a real jump host, negative tests for
  arbitrary targets and expired tokens.

### 4.4 Effort

| Slice | Days (person) |
|---|---|
| XPipe links + `ssh -L` snippets + docs (interim) | 1–2 |
| Desktop app shell + multi-instance + webview | 10–15 |
| Device auth, keychain token storage, instance accounts | 4–6 |
| Tunnel manager (system ssh, allowlist, ports, status, audit) | 8–12 |
| macOS/Windows/Linux packaging, signing, notarization, auto-update | 8–12 |
| Tests and docs | 4–6 |
| **Total, desktop app** | **34–51** |
| API-host WebSocket proxy (not recommended) | 20–30 |

## 5. Roadmap

1. **Stage 1 — 4–5 weeks**: `AuditEvents` foundation; MCP read-only with
   Keycloak OAuth **and** personal API keys; XPipe deep links and copyable
   `ssh -L` as interim tunnels; MCP test client and docs.
2. **Stage 2 — 3–4 weeks**: MCP action tools with `McpGrants`, confirmation,
   idempotency and rate limits.
3. **Stage 3 — 8–10 weeks**: desktop app on macOS first (multi-instance,
   embedded SPA, tunnels through the user's SSH agent, audit), then Windows and
   Linux, signing/notarization/auto-update.
4. **Stage 4 — hardening**: load tests, penetration test of the MCP surface,
   tunnel abuse cases, retention and audit review.

## 6. Decisions taken

| # | Decision |
|---|---|
| D1 | MCP auth: OAuth 2.1 via Keycloak **and** personal API keys. |
| D2 | MCP exposes actions too, enabled per user/group through `McpGrants`; environment RBAC still applies. |
| D3 | Tunnels live in a desktop app that also offers the browser features and connects to multiple InfraOrgIT instances; XPipe deep links are an interim shortcut. |
| D4 | Desktop app on all modern OS: macOS (arm64/x64), Windows, Linux. |
| D5 | The app uses the user's SSH agent (`ssh -L`/`-J` with `SSH_AUTH_SOCK`); no private key stored by InfraOrgIT. |

**D6 — audit storage (recommended).** A new append-only `AuditEvents` table
plus an `IAuditService`, shared by MCP and tunnels; `CommandExecutions` stays
the SSH-command log and is not reshaped.

- Columns: `Id`, `OccurredAt`, `Kind` (`McpToolCall`, `TunnelStart`,
  `TunnelStop`, `TunnelError`), `ActorUserId`/`ActorUsername` (snapshot, no FK
  cascade), `ClientId`, `Action`, `TargetType`/`TargetId`, `Outcome`
  (`Ok`/`Error`/`Denied`), `ErrorCode`, `DurationMs`, `CorrelationId`,
  `DetailJson` (redacted, capped at 4 KB).
- Tunnel events also carry `ServerId`, `TargetHost`, `TargetPort`, `LocalPort`
  as nullable typed columns; MCP calls leave them null.
- MCP logs every `tools/call`, including denied ones; tunnel logs start, stop,
  error and client disconnect. No tool arguments with secrets and no SSH
  output in `DetailJson`.
- Indexes on `(OccurredAt)`, `(Kind, OccurredAt)`, `(ActorUsername, OccurredAt)`;
  retention configurable, default 180 days, with a purge job.
- Why not extend `CommandExecutions`: its shape is a command run (script,
  exit code, redacted output) and its page is the execution log; MCP calls and
  tunnel sessions would pollute it.
- Why not one table per feature: a generic audit table gives one page, one
  filter, one retention policy and one writer; feature-specific fields go in
  typed nullable columns or `DetailJson`.

## 6b. Implemented slice

- `ApiTokens` + `AuditEvents` tables and `AuditService`.
- Personal API tokens managed from `/tokens` (user menu); SHA-256 hash at rest,
  scopes `mcp:read`/`mcp:operate`, expiry, last use, revoke.
- `/mcp` Streamable HTTP endpoint (MCP C# SDK 2.4.0, stateless) with bearer API
  token authentication and read-only tools: `list_servers`, `get_server`,
  `list_applications`, `list_projects`, `list_deployments`.
- Every tool call writes an `AuditEvents` row; denied/revoked tokens get 401.
- OAuth 2.1 via Keycloak: confidential `infraorgit-mcp` (client credentials)
  and public `infraorgit-mcp-desktop` (PKCE), scopes `mcp:read`/`mcp:operate`,
  audience mapper, discovery document at
  `/.well-known/oauth-protected-resource`.
- The `/mcp` policy requires `mcp:read` or `mcp:operate`; a token without a
  scope gets 403. The desktop client defaults to `mcp:read` with
  `mcp:operate` optional, so a single MCP connection can be read-only or
  read-write by choice. Action tools will additionally require `McpGrants`.
- Caddy routes `/mcp*` and the discovery path to the API.
- Action tools `run_reachability_tests` and `run_application_action`:
  require `mcp:operate`, an `McpGrant` for the user/group (optional
  environment) and `ServerOperator`/`ServerAdmin`; `confirm=true` is
  mandatory; results and denials are audited.
- Grants are managed from `/mcp-grants` (Users page, SystemAdmin) and through
  `/api/mcp/grants`.
- MCP resources: `infraorgit://inventory/summary` (counts),
  `infraorgit://servers/{id}` and `infraorgit://applications/{id}`; reads reuse
  the tool queries and are audited as `read_resource`.
- MCP prompts: `diagnose-server` and `application-impact`, templates that only
  describe which tools to call.
- Desktop shell (`../InfraOrgITDesktop`, .NET 10 + Photino, ADR-011):
  multi-instance manager with a per-user JSON store and one child window per
  open instance.
- Still to do: tunnel engine and packaging in the desktop app.

## 7. Open points

- Keycloak client naming and scopes for MCP; whether the SPA client can be
  reused for the authorization-code flow.
- Agent update channel and signing keys; which OS versions are "modern" for
  support.
- Central visibility of active tunnels: the app owns the sessions; if the web
  UI must show them, add a `TunnelSessions` projection fed by the app.

## 8. Non-goals

- Raw shell access over MCP.
- Browser-to-server TCP tunnels without a local component.
- Replacing XPipe's full feature set (RDP/VNC, file manager, services).
- Multi-tenant MCP clients with per-client environment grants in v1; scopes
  stay coarse and environment rights come from the user's groups.
