# MCP server and local tunnels — feasibility study

- Status: study, not implemented
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

A personal API key (hashed in a new table) is a simpler fallback for local
clients that do not implement OAuth discovery. It should be a feature-flagged
compatibility path, not the primary one, because it bypasses the OAuth
hardening and needs its own revocation/rotation UI.

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
| Action tools (`reachability.run`, `actions.run`) | +5–8 |
| Hardening, observability, client allowlist | +3–4 |
| **Total, read-only production** | **16–22** |
| **Total, read-only + actions** | **22–30** |

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

Recommendation: **A + B now**, **C next** if tunnels must live inside
InfraOrgIT. Do not build D unless there is a strong requirement to work from a
locked-down browser with no local install.

### 4.3 Local agent design (option C)

- Distribution: .NET self-contained binary/tray for macOS (arm64/x64), Linux,
  Windows; signed and notarized on macOS, signed on Windows; auto-update from
  a signed manifest.
- Auth: OAuth 2.1 device authorization grant (RFC 8628) through Keycloak; the
  agent never stores the user's password. Token refresh and revoke.
- Targets: the API returns an allowlist derived from the inventory
  (`ServerId` + target host/port, typically the deployment `ExposedPort` or a
  `HostPort`), never an arbitrary host:port from the client. The agent cannot
  create a tunnel to something the user cannot see.
- Bind: `127.0.0.1` only, ephemeral or requested local port above 1024;
  collision check; max concurrent tunnels; idle timeout.
- SSH: SSH.NET with the same jump-host chain and host-key pinning; credentials
  either from the user's SSH agent/keychain or a short-lived credential issued
  by the API for that server and tunnel (preferred; auditable, no long-lived
  key on disk).
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
| XPipe links + `ssh -L` snippets + docs | 1–2 |
| Agent MVP (macOS, device auth, allowlist, jump hosts, status) | 12–16 |
| Packaging/signing/notarization/auto-update | +5–8 |
| Windows/Linux variants | +5–8 |
| API-host WebSocket proxy (not recommended) | 20–30 |

## 5. Roadmap

1. **Stage 1 — 2–3 weeks**: MCP read-only with Keycloak OAuth and audit; XPipe
   deep links and copyable `ssh -L`; documentation and an MCP test client.
2. **Stage 2 — 3–4 weeks**: MCP action tools with confirmation and rate
   limits; local agent MVP on macOS with allowlisted tunnels and audit.
3. **Stage 3 — hardening**: Windows/Linux agent, signing/auto-update, load
   tests, penetration test of the MCP surface, tunnel abuse cases.

## 6. Decisions needed

1. MCP authentication: OAuth 2.1 only, or also personal API keys for desktop
   clients? (recommended: OAuth first, API keys behind a flag)
2. MCP scope in v1: read-only, or read + reachability/actions?
3. Tunnels: XPipe links first, or invest in the local agent immediately?
4. Which operating systems must the agent support in v1?
5. Credential model for the agent: user's SSH agent, or short-lived credentials
   issued by InfraOrgIT?
6. Audit storage: a new `McpToolCalls`/`TunnelEvents` table, or a generic
   `AuditEvents` table that also replaces/extents `CommandExecutions`?

## 7. Non-goals

- Raw shell access over MCP.
- Browser-to-server TCP tunnels without a local component.
- Replacing XPipe's full feature set (RDP/VNC, file manager, services).
- Multi-tenant MCP clients with per-client environment grants in v1; scopes
  stay coarse and environment rights come from the user's groups.
