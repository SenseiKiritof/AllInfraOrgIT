# MCP and tunnel hardening

Practical checklist for the MCP surface (`/mcp`) and the desktop tunnel API
(`/api/tunnels/*`). It covers auth and revocation, RBAC, the tunnel allowlist,
rate limits, audit retention, untrusted output, response caps, the 429/load
procedure and tunnel abuse cases.

Verified against the API code on 2026-11-11. Evidence paths are workspace
relative: `InfraOrgITApi/...`, `InfraOrgITWeb/Caddyfile`,
`InfraOrgITDesktop/...`. Architecture and decisions:
[`../architecture/mcp-server-and-tunnels.md`](../architecture/mcp-server-and-tunnels.md).

## 1. Auth and scope revocation

| Control | Implementation | Verify |
|---|---|---|
| Personal token | `itk_` prefix, 32 random bytes, SHA-256 hash at rest; raw value returned once | create one in `/tokens`, call `/mcp`, then list `/api/api-tokens` and confirm no raw token is returned |
| Scopes | `mcp:read`, `mcp:operate`, `tunnels:operate`; default `mcp:read` | `POST /api/api-tokens` with no scopes; response has `mcp:read` |
| Revocation | `DELETE /api/api-tokens/{id}` sets `RevokedAt`; validation rejects revoked and expired tokens with 401 | call `/mcp` before and after revoke |
| Expiry | `ExpiresInDays` 1-3650; expired tokens are rejected with 401 | create `ExpiresInDays=1`, inspect `expiresAt` |
| OAuth clients | Keycloak `infraorgit-mcp` (client credentials) and `infraorgit-mcp-desktop` (PKCE); scopes `mcp:read`/`mcp:operate`, desktop also `tunnels:operate` | discovery on `/.well-known/oauth-protected-resource` |
| MCP switch | `Mcp:Enabled=false` skips `MapMcp("/mcp")`; Compose maps `MCP_ENABLED` | set `MCP_ENABLED=false`, restart API, `/mcp` is no longer mapped |
| Route exposure | Caddy serves `/mcp`, `/mcp/*` and `/.well-known/oauth-protected-resource*`; `/api/*` covers audits and tunnels | `InfraOrgITWeb/Caddyfile` |

Authentication results:

- missing, malformed, expired or revoked token -> **401**;
- valid token without `mcp:read` or `mcp:operate` -> **403**;
- valid token without `tunnels:operate` on `/api/tunnels/*` -> **403**;
- `Mcp:Enabled=false` -> endpoint not mapped (404).

Personal tokens are per token in the rate limiter (`api_token_id` claim).
OAuth access tokens have no `api_token_id`, so they share the `preferred_username`
budget. Two personal tokens for the same user therefore get two independent
120/min budgets, while two OAuth tokens for that user share one.

Create the raw token from the user menu (`/tokens`) and keep it out of shell
history. For a fully scripted token, the personal-token API needs the browser
session cookie and CSRF header (`POST /api/api-tokens`); the Keycloak client
credentials flow is simpler for automation:

```bash
export KEYCLOAK=https://localhost:8443
export MCP_CLIENT_SECRET='...'          # from the secret manager, not git
TOKEN=$(curl -sS -X POST \
  "$KEYCLOAK/realms/infraorgit/protocol/openid-connect/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode 'client_id=infraorgit-mcp' \
  --data-urlencode "client_secret=$MCP_CLIENT_SECRET" \
  | jq -r .access_token)
test -n "$TOKEN" && test "$TOKEN" != null
```

Do not paste the token into the command line of a shared host: it is visible in
the process list. Use `MCP_TOKEN` in the environment or the desktop keychain.

The desktop stores the refresh token in the OS secret store. On macOS the
current `security` invocation passes the value with `-w <token>`, so it is
visible in the process argument list to other local processes while the command
runs. This is a short local exposure, not a network one (PT-16): do not run the
desktop on a host with untrusted local users, and treat the argv limitation as
accepted until the store uses stdin or the native Keychain API. See
[`../security/transport.md`](../security/transport.md).

## 2. RBAC matrix

`SystemAdmin` does **not** imply `ServerAdmin`/`ServerOperator` (D7 = B). The
same rule applies to MCP and tunnels: a grant or a scope never replaces the
environment role. See [`../security/permissions.md`](../security/permissions.md).

| Surface | Auth / scope | Environment right | Result |
|---|---|---|---|
| Read tools (`list_servers`, `get_server`, `list_providers`, `list_applications`, `get_application`, `list_projects`, `get_project`, `list_deployments`, `list_reachability_tests`, `get_topology`) | `mcp:read` or `mcp:operate` | none checked today | all inventory rows, not filtered by environment; accepted D7 read model (see gaps) |
| `list_executions` | `mcp:read` or `mcp:operate` | `SystemAdmin` | tool error (`isError`) for other users |
| `run_reachability_tests`, `run_application_action` | `mcp:operate` + `McpGrant` | `ServerOperator` or `ServerAdmin` on the target environment | runs with `confirm=true`; otherwise denied |
| `GET /api/tunnels/targets` | `tunnels:operate` | operator on the server environment | only operator servers with a credential and at least one deployment |
| `POST /api/tunnels/events` | `tunnels:operate` | operator on the server environment | writes `TunnelStart`/`TunnelStop`/`TunnelError` |
| `POST /api/tunnels/sessions` | `tunnels:operate` | operator on the server environment | upserts a live projection (204) |
| `GET /api/tunnels/sessions` | browser session (not a bearer route) | `SystemAdmin` sees all, others operator environments | active rows from the last two minutes, max 200 |
| `GET /api/audit-events` | browser session + `SystemAdmin` | system | paged audit rows |
| `/api/mcp/grants`, `/mcp-grants` | browser session + `SystemAdmin` | system | manage grants |

Grant actions are `reachability.run`, `actions.run` or `*`, optionally limited
to one environment definition (`InfraOrgITApi/src/InfraOrgIt.Api/Features/Mcp/McpGrantService.cs`).
A grant without the matching environment role still produces a denied call
(`forbidden`) and an audit row.

Quick negative checks:

```bash
# Read scope only: an action tool must return isError, with a Denied audit row.
curl -sS "$MCP_BASE_URL/mcp" \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"run_reachability_tests","arguments":{"serverId":1,"testIds":[1],"confirm":true}}}'

# Tunnel scope on the API: targets are filtered to operator environments.
curl -sS "$MCP_BASE_URL/api/tunnels/targets" \
  -H "Authorization: Bearer $TUNNEL_TOKEN" | jq
```

## 3. Tunnel allowlist

`GET /api/tunnels/targets` builds the only list the desktop should use. A server
is included only when it has a credential and at least one deployment, and only
for environments where the caller is an operator. The target port is
`hostPort ?? exposedPort`; the jump host comes from the server, never from the
client. The desktop proposes `SuggestedLocalPort` only for target ports at or
above 1024 and binds `127.0.0.1`
(`InfraOrgITDesktop/src/InfraOrgIt.Desktop/Tunnels/SshTunnel.cs`).

Controls to keep:

- The desktop must open `ssh -L`/`-J` only for `TunnelTargetDto` entries, with
  the returned SSH host, port, username and jump host. No free-form target
  dialog.
- Bind loopback only. The desktop rejects ports below 1024 and collisions; a
  concurrent-tunnel cap is still a recommendation, not an implemented limit.
- Use the user's SSH agent (`SSH_AUTH_SOCK`); no private key is stored by
  InfraOrgIt.
- `POST /api/tunnels/events` and `POST /api/tunnels/sessions` validate the
  server, deployment and operator right, then record the event. They do **not**
  open a network connection: the API is not a TCP proxy, so an arbitrary
  `targetHost` cannot make the server connect anywhere.
- Treat the recorded `TargetHost`/`TargetPort` as client-reported audit data,
  not proof of the real connection. Keep the desktop build signed and use the
  allowlist code path; reconcile sessions against the desktop logs when
  investigating.

## 4. Rate limits

All limits are fixed one-minute windows, queue 0, rejection `429`
(`InfraOrgITApi/src/InfraOrgIt.Api/Program.cs:203-218`). `mcp` and `tunnels`
are partitioned by `api_token_id`, otherwise by username.

| Policy | Limit | Partition |
|---|---|---|
| `auth-login` | 120/min | global fixed window |
| `auth-callback` | 30/min | client IP |
| `remote-run` | 30/min | user |
| `reachability` | 10/min | user |
| `console` | 5/min | user |
| `files` | 60/min | user |
| `mcp` | 120/min | token id or username |
| `tunnels` | 120/min | token id or username |

Implications:

- A single MCP load run must stay under 120 HTTP requests per minute. The load
  script reports measured requests only; warm-up is one `initialize` per worker
  plus one `tools/list` per worker when `--tool` is used. A run with
  `REQUESTS=100`, concurrency 5 and a tool sends about 110 POSTs.
- 429 is immediate and is not retried by the load script: the script counts it,
  prints `Retry-After` when present and exits non-zero. Wait for the next
  one-minute window before retrying.
- For a capacity test above 120/min, use separate personal tokens (separate
  `api_token_id` budgets) or test a different surface. Do not disable the
  limiter in a shared environment.
- A 429 from `mcp` affects only that token/username; another user is unaffected.
  `tunnels` uses the same actor-key function but has its own counter.

## 5. Audit retention and purge

MCP tool handlers write an `AuditEvents` row on success, denial and handled
error (including denied action calls); the desktop reports tunnel
start/stop/error and each report writes a row. Rows carry `Kind`, `Action`,
`Outcome` (`Ok`/`Error`/`Denied`), actor, token id, target, duration, error
code, correlation id and `DetailJson` capped at 4096 characters. See
`InfraOrgITApi/src/InfraOrgIt.Api/BuildingBlocks/Audit/AuditService.cs`.

Retention:

- `Audit:RetentionDays` defaults to **180** in
  `InfraOrgITApi/src/InfraOrgIt.Api/appsettings.json`.
- The purge job runs after one minute, then every six hours, deleting rows
  older than the cutoff in batches of 500
  (`Features/Audit/AuditRetentionService.cs`).
- The value is clamped to 1-3650 days.
- `CommandExecutions` is a separate log and is not deleted by this service.
- The standard ASP.NET configuration key is `Audit__RetentionDays`. Compose
  currently exposes `MCP_ENABLED` but not the audit retention: set
  `Audit__RetentionDays` in the API environment (add it to `compose.yaml`) or in
  the deployment configuration when a shorter retention is required.

Verify rows and age:

```bash
docker compose -f ../InfraOrgITDocker/compose.yaml exec -T mysql \
  sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" infraorgit -e "
    SELECT Kind, Outcome, COUNT(*) AS Rows, MIN(OccurredAt) AS Oldest
    FROM AuditEvents GROUP BY Kind, Outcome;
    SELECT COUNT(*) AS OlderThan180d
    FROM AuditEvents
    WHERE OccurredAt < UTC_TIMESTAMP() - INTERVAL 180 DAY;"'
```

Expected after a healthy purge: `OlderThan180d = 0`. To prove the purge without
waiting six hours, set the retention to one day, insert or keep a row older than
the cutoff and restart the API; the first pass starts after one minute. Never
shorten retention on a production instance without checking the backup and
investigation policy.

`GET /api/audit-events` (SystemAdmin, cookie session) filters by `kind`,
`outcome`, `serverId`, `q`, `page` and `pageSize` (max 200); `/audit` is the
same view in the UI. Authentication failures (401) do not reach the audit
writer: use the API/Caddy access logs to count them.

## 6. Prompt injection, untrusted output and agency

The MCP server is a data/tool provider for an external model: it does not run
an agent, keep memory or accept instructions from tool output. Treat every
string returned by a tool as untrusted data, never as an instruction.

- Inventory fields (names, hostnames, OS, application versions, execution
  output) can contain text controlled by an administrator or by a managed
  server. A server named `IGNORE PREVIOUS INSTRUCTIONS ...` must remain a
  string in the client, not a command.
- `list_executions` is the highest-risk read tool (it returns command output);
  it is SystemAdmin-only. Still treat its text as untrusted.
- `run_reachability_tests` and `run_application_action` never accept a raw
  shell command. They require `mcp:operate`, an `McpGrant`, the environment
  operator right and `confirm=true`; results are allowlisted actions only.
- Do not log tool arguments that contain secrets. `McpToolAudit` records IDs,
  counts and exit codes, not command output; `DetailJson` is capped.
- MCP prompts (`diagnose-server`, `application-impact`) only describe which
  tools to call; they add no permissions. Their arguments are inserted into the
  prompt text, so a client must not treat a prompt argument as trusted
  instruction.

### `confirm` is model-supplied

`confirm=true` is a boolean chosen by the MCP client (the model). It proves
that the request contained the field, not that a human approved the action; the
server cannot distinguish the two. Scope, `McpGrant` and the environment role
are the security boundary, and `confirm` is only a stumble guard.

- Do not auto-approve action tools. Configure the client to ask before every
  `run_reachability_tests` / `run_application_action` call and to show the
  server, action and arguments before approval.
- Disable "yolo"/auto-run modes for tokens with `mcp:operate`; use a
  read-only `mcp:read` token for exploration and connect with operate rights
  only for an approved task.
- A denied action call is audited. Treat repeated denials as a signal of
  prompt injection, a stale grant or an over-broad client policy.
- A human-only approval channel or signed intent is still an open remediation
  item (PT-18); until it exists, the client's approval prompt is the only
  human factor.

### Review grants

Grants are managed from `/mcp-grants` (Users page, `SystemAdmin`) or
`GET/POST /api/mcp/grants`:

1. List every grant and map it to a person or group with a current need.
2. Keep the action narrow (`reachability.run` or `actions.run`, not `*`) and
   limit it to one environment where possible.
3. Check that the holder still has the matching `ServerOperator`/`ServerAdmin`
   right; a grant never replaces the environment role.
4. Remove grants and tokens when the integration or person leaves; revoke
   personal tokens in `/tokens`.

OWASP mapping: LLM01 prompt injection, LLM02 sensitive information disclosure,
LLM05 improper output handling, LLM06 excessive agency, ASI01 agent goal
hijack, ASI02 tool misuse, ASI06 memory/context poisoning and ASI09
human-agent trust exploitation. Findings PT-03/PT-13/PT-18 in
[`../security/pentest-2026-11.md`](../security/pentest-2026-11.md).

Practical test: create a server whose name starts with a prompt-injection
sentence, call `list_servers` through the client, and verify the model quotes
the name as data and does not call an action tool. Then call an action tool
without `confirm=true` and verify the tool error plus a `Denied`/`Error` audit
row.

## 7. Response caps

There is no separate HTTP byte cap on tool responses; the row limits and field
truncation below are the effective bounds:

| Tool / endpoint | Cap |
|---|---|
| `list_servers`, `list_providers`, `list_applications` | `limit` clamped 1-200, default 50 |
| `list_deployments`, `list_reachability_tests` | `limit` clamped 1-200, default 100 |
| `get_topology` | `maxServers` 1-1000, default 100; a larger topology is rejected with `too_large` |
| `list_executions` | `limit` 1-100, default 50; each `output` truncated to 4000 chars |
| `run_application_action` | `output` truncated to 4000 chars |
| `GET /api/tunnels/sessions` | 200 rows |
| `GET /api/audit-events` | `pageSize` max 200 |
| Audit `DetailJson` | 4096 chars |

Clients should also cap what they render and page large inventories. Do not
raise a limit to work around a slow client; add a narrower query.

## 8. 429 and load test procedure

The script is stdlib only and read-only by default. It sends `initialize` and
`tools/list`, and `tools/call` only when `--tool` is set. Action tools
(`run_reachability_tests`, `run_application_action`) are rejected so a load run
cannot mutate the inventory. It accepts JSON and SSE, parses the final JSON-RPC
response, reports p50/p95/p99 and req/s and exits non-zero on HTTP, auth, 429,
JSON-RPC, tool, protocol or network errors.

Self-test, no live instance:

```bash
cd AllInfraOrgIT
python3 -m py_compile scripts/loadtest-mcp.py
python3 scripts/loadtest-mcp.py --self-test
make -n loadtest-mcp
```

Live run against `make full` (Caddy, self-signed certificate):

```bash
cd AllInfraOrgIT
read -rs MCP_TOKEN; echo; export MCP_TOKEN   # paste a token with mcp:read
export MCP_BASE_URL=https://localhost:8443
MCP_INSECURE_TLS=1 python3 scripts/loadtest-mcp.py --requests 30 --concurrency 5
MCP_INSECURE_TLS=1 MCP_TOOL=list_servers MCP_ARGUMENTS='{"limit":10}' \
  python3 scripts/loadtest-mcp.py --requests 60 --concurrency 6
```

Against `make dev` the API is direct on `:5298`; the Vite proxy does not forward
`/mcp`:

```bash
MCP_BASE_URL=http://localhost:5298 MCP_TOKEN="$MCP_TOKEN" \
  python3 scripts/loadtest-mcp.py --requests 30 --concurrency 5
```

Or through the safe Make default (30 requests, concurrency 5, no tool call):

```bash
MCP_TOKEN="$MCP_TOKEN" MCP_INSECURE_TLS=1 make loadtest-mcp
```

Procedure:

1. Run the self-test and a 30/5 baseline; record p50/p95/p99 and req/s.
2. Ramp to 60/6 and 100/10, waiting at least one minute between runs so the
   fixed window resets.
3. Keep a single run below 120 HTTP POSTs, counting warm-up
   (`workers` initialize + `workers` `tools/list` when `--tool` is set).
4. Confirm the limit explicitly:

   ```bash
   MCP_INSECURE_TLS=1 MCP_TOKEN="$MCP_TOKEN" MCP_TOOL=list_servers \
     REQUESTS=140 CONCURRENCY=10 make loadtest-mcp
   ```

   Expected: a non-zero exit, `rate_limited` greater than zero and at least one
   `429` line with `Retry-After`. Wait 60 seconds before the next run.
5. For capacity above one token budget, repeat with different personal tokens;
   report each token separately. Do not use one user's OAuth token for all
   workers if you need independent budgets.
6. Never run the script against production without an approved window: it
   writes `LastUsedAt` per request, creates audit rows and consumes the rate
   budget of the token's user.

Acceptance for a release: no 5xx, no 429 below the documented budget, no
auth/JSON-RPC errors, stable p95 across two consecutive runs and a recorded
baseline. There is no fixed latency SLO yet; compare with
[`load-test.md`](load-test.md) and the deployment host.

## 9. Tunnel abuse cases

| Case | Expected control | Check |
|---|---|---|
| Arbitrary `host:port` target | API never dials; desktop only opens targets from `/api/tunnels/targets` | negative desktop test with a manually edited target; `POST /api/tunnels/events` still needs valid server/deployment IDs |
| Non-operator user | targets filtered; events/sessions return 403 | token without operator environment -> empty list, 403 on event |
| Stolen `tunnels:operate` token | revoke in `/tokens`; audit by `ClientId`; short expiry; separate from `mcp:*` | call targets before/after revoke (401 after) |
| Bind on all interfaces | desktop binds `127.0.0.1` only | `lsof -nP -iTCP -sTCP:LISTEN` while a tunnel is open |
| Local port collision / low port | allocator picks a free port >= 1024; reject explicit low ports | start two tunnels on the same requested port |
| Too many tunnels | `tunnels` 120/min; stale cleanup; add a desktop concurrent cap | open many tunnels and confirm the resource impact; there is no desktop cap today |
| Stale/ghost session | heartbeat every 30s; cleanup marks `Stale` after 2 minutes; `/tunnels` hides non-active | stop the desktop without stop event, wait 2 minutes |
| Forged session row | `POST /api/tunnels/sessions` requires operator right and validates server/deployment; row is a projection, not a connection | post a session for another user's server -> 403 |
| Event replay | events only append audit rows; no action is triggered | repeat a `start` event, verify two audit rows and no tunnel |
| Jump host confusion | jump host and username come from the server, not the request | inspect `/targets` and the desktop command line |
| Token in process list/history | use keychain or `MCP_TOKEN`; never `--token` on shared hosts | `ps` while the desktop/script runs |
| Cleartext desktop instance | HTTPS for non-loopback URLs; `INFRAORGIT_INSECURE_TLS=1` is development-only | set an `http://` instance and inspect the token/data path; see [`../security/transport.md`](../security/transport.md) |

Run the negative tests on a local `make full` stack, not production. The API
integration tests already cover scope, RBAC, allowlist and audit for the tunnel
endpoints (`InfraOrgITApi/tests/InfraOrgIt.IntegrationTests/TunnelApiTests.cs`).

## 10. Release checklist

- [ ] All test/load tokens revoked; production tokens have an expiry and only
      the scopes they need.
- [ ] `mcp:read` holders reviewed: read tools return the whole inventory under
      the D7 read model (see gaps); confirm each holder is trusted with every
      environment.
- [ ] RBAC matrix checked with a `SystemAdmin` who is not an operator and an
      operator who is not `SystemAdmin`.
- [ ] `McpGrant` rows reviewed (`/mcp-grants`); no `*` grant without a reason.
- [ ] Tunnel allowlist negative test passed; desktop binds loopback only.
- [ ] 429 confirmed for `mcp` and `tunnels`; the alert/dashboard watches 429 and
      401/403 on `/mcp`.
- [ ] `AuditEvents` rows present for allowed and denied MCP calls and for tunnel
      start/stop/error; `Audit:RetentionDays` matches policy; purge leaves no
      rows older than the cutoff.
- [ ] Load baseline recorded (`scripts/loadtest-mcp.py`) and no 5xx/429 below
      budget.
- [ ] Prompt-injection sample reviewed; output truncation and row caps
      confirmed.
- [ ] `MCP_ENABLED` matches the environment decision; Caddy exposes only
      `/mcp`, `/mcp/*`, `/.well-known/oauth-protected-resource*` and `/api/*`.
- [ ] `make security-smoke` run on a test instance; temp tokens revoked after
      the run.

## 11. Security smoke test

`scripts/security-smoke.py` is the repeatable negative-check pass for a
running instance. It is stdlib only, read-only by default and prints one
`PASS`/`FAIL`/`SKIP` line per control; any `FAIL` exits non-zero. It is not in
`make ci`: it needs real tokens, and the optional burst writes audit rows and
consumes the token rate budget.

Checks:

- no auth -> 401 on `/mcp`, `/api/servers`, `/api/tunnels/targets` and
  `/api/audit-events`;
- `/.well-known/oauth-protected-resource` is public and advertises an absolute
  resource, an authorization server and the `mcp:read`/`mcp:operate` scopes;
- the `/mcp` 401 `WWW-Authenticate` challenge points at that metadata
  (`resource_metadata`, RFC 9728);
- a `mcp:read` token can call `tools/list` but is denied
  `run_reachability_tests`;
- an operate token without `McpGrant` or the environment operator right is
  denied the action;
- `/api/tunnels/targets` returns 200 with only the allowlisted DTO fields for a
  tunnel token, and 403 for a read-only token;
- `/api/audit-events` denies a non-admin token (403; the route accepts browser
  sessions only, so a bearer token gets 401 first, which is accepted as denial);
- `X-Content-Type-Options: nosniff` and `Referrer-Policy` are present;
- CORS/preflight for `/api` does not echo an arbitrary origin (PASS with no
  CORS headers, which is the current API behavior);
- optional burst: at least one `429` on `/mcp` (off by default).

Inputs are `--base-url`, `--token` (`mcp:read`), optional `--operate-token`
(`mcp:operate` + `tunnels:operate`), optional `--outsider-token` (any
low-privilege user), `--insecure-tls` and `--self-test`. The Make target reads
`MCP_TOKEN` and `MCP_OPERATE_TOKEN` from the environment, so the raw values do
not appear in the process list; the script never prints them and redacts them
from every detail line.

```bash
cd AllInfraOrgIT
read -rs MCP_TOKEN; echo; export MCP_TOKEN              # mcp:read
read -rs MCP_OPERATE_TOKEN; echo; export MCP_OPERATE_TOKEN  # mcp:operate tunnels:operate
make security-smoke
```

Direct run and self-test:

```bash
python3 -m py_compile scripts/security-smoke.py
python3 scripts/security-smoke.py --self-test
MCP_TOKEN=... MCP_OPERATE_TOKEN=... \
  python3 scripts/security-smoke.py --base-url https://localhost:8443 --insecure-tls
make -n security-smoke
```

Expected output (local `make full`, 2026-11-11). The `WWW-Authenticate` line is
the one current finding, see gap 5 below:

```text
security smoke: https://localhost:8443
  read=mcp:read operate=provided outsider=absent timeout=15s
PASS unauthenticated POST /mcp -> 401: 401
PASS unauthenticated GET /api/servers -> 401: 401
PASS unauthenticated GET /api/tunnels/targets -> 401: 401
PASS unauthenticated GET /api/audit-events -> 401: 401
PASS oauth protected-resource is public: 200, public JSON
PASS oauth metadata advertises resource, server and scopes: ...
FAIL mcp 401 challenge points to metadata: Bearer challenge lacks resource_metadata (RFC 9728): ...
PASS read token can call tools/list: 13 tools
PASS read token cannot call an action tool: denied: ... Serve lo scope mcp:operate.
PASS operate token without grant is denied the action: denied: ... Nessun grant MCP ...
PASS tunnels targets with tunnel token: 200, allowlisted fields, 25 targets
PASS tunnels targets with read-only token -> 403: 403
PASS audit-events with non-admin token -> denied: 401 (read token): route accepts browser sessions ...
PASS security headers present: /health/live: nosniff and no-referrer
PASS CORS does not allow an arbitrary origin: no CORS headers (HTTP 405)
SKIP mcp rate limit burst -> 429: disabled (...)
result: FAIL (14 passed, 1 failed, 1 skipped)
```

Enable the burst explicitly. It runs last and leaves the token rate-limited for
the rest of the one-minute window:

```bash
SECURITY_SMOKE_RATE_REQUESTS=121 make security-smoke
```

The action checks pass `testIds: [-1]`: if a token is wrongly authorized, the
grant and operator checks run but no reachability probe matches, so the smoke
test does not touch a server. Revoke the temp tokens after the run.

What this does not cover:

- **Full penetration test.** No exploit chains, auth-bypass fuzzing, OAuth/OIDC
  redirect or token-substitution attacks, CSRF/session fixation, IDOR/BOLA
  beyond the listed endpoints, injection, SSRF, TLS/cipher review or
  dependency/container CVE scanning. Commission a dedicated assessment for
  those.
- **Load, capacity and DoS.** One optional burst proves the limiter returns
  429; it does not measure throughput, latency, soak behavior, DB/SSH
  contention or a distributed flood. Use `scripts/loadtest-mcp.py` for the
  baseline described in section 8.
- **Infrastructure.** Caddy/Compose/Keycloak configuration, network exposure,
  edge certificate chain and HSTS, DNS, host/OS hardening, secret manager,
  backup/restore, audit retention purge and monitoring/alerting are out of
  scope. The security headers are checked on the API response, not on every
  edge route.
- **Browser and desktop flows.** Cookie flags, CSP behavior in a real browser,
  the tunnel process (`ssh -L`/`-J`, loopback bind, keychain) and the UI RBAC
  are covered by the manual checklist and the integration tests, not here.
- **Positive RBAC matrix.** Only the supplied personas are exercised; a
  `SystemAdmin` who is not an operator, a revoked/expired token and
  `Mcp:Enabled=false` (404) remain manual checks in sections 1-3.
- **Idempotence and side effects.** The run writes `LastUsedAt`, audit rows and
  the rate-limit budget. Do not point it at production outside an approved
  window.

## Known gaps to track

These are current-code observations, not claims that the control exists:

1. **Read tools are not environment-filtered.** `InfraOrgITApi/src/InfraOrgIt.Api/Features/Mcp/InventoryTools.cs`
   queries the full inventory for `list_servers`, `get_server`,
   `list_applications`, `get_application`, `list_projects`, `get_project`,
   `list_deployments`, `list_reachability_tests` and `get_topology`; only
   `list_executions` checks `SystemAdmin`. This matches the D7 read model
   (inventory reads are open to every authenticated user; see
   [`../security/permissions.md#read-model-pt-05`](../security/permissions.md#read-model-pt-05)),
   but it makes every `mcp:read` token a whole-inventory read grant. Privilege
   metadata (`/api/users`, `/api/groups`, `/api/roles`,
   `/api/provider-environment-group-roles`) is being restricted to
   `SystemAdmin`. Per-environment read filtering remains an open decision for
   multi-team or externally shared MCP clients.
2. **Tunnel audit target is client-reported.** `POST /api/tunnels/events` and
   `POST /api/tunnels/sessions` validate IDs and the operator right, but accept
   `TargetHost`/`TargetPort` from the desktop. They cannot prove what the local
   `ssh` process connected to. The allowlist is enforced by the desktop.
3. **No audit row for authentication failures.** A 401 on `/mcp` is rejected
   before the tool handler, so `AuditEvents` has no row. Monitor API/Caddy logs
   for 401/403/429 spikes.
4. **Audit retention is not exposed in Compose.** The default 180 days lives in
   `appsettings.json`; changing it requires the `Audit__RetentionDays`
   configuration key.
5. **MCP 401 metadata pointer — fixed 2026-11-11.** `/mcp` 401 responses now
   set `WWW-Authenticate: Bearer resource_metadata=".../.well-known/oauth-protected-resource"`
   (RFC 9728); covered by an integration test and `make security-smoke`.

## Baseline locale

Misurato l'11/11/2026 sullo stack `make full` locale (macOS arm64), token
`mcp:read`, endpoint `https://localhost:8443/mcp`:

```bash
MCP_TOKEN=itk_... MCP_INSECURE_TLS=1 MCP_REQUESTS=60 MCP_CONCURRENCY=10 \
  make loadtest-mcp
```

Risultato: 60/60 richieste OK, 0 errori/429, p50 20.5 ms, p95 41.8 ms,
p99 48.2 ms, ~387 req/s. Usare questo dato come riferimento per la regressione,
non come capacità di produzione: è un ambiente locale con un solo processo API.

## Security smoke locale

`make security-smoke` con token `mcp:read` e `mcp:operate tunnels:operate`:

- 15 controlli PASS, 1 SKIP (burst disabilitato di default).
- Con `--rate-limit-requests 121`: **16 PASS, 0 FAIL**; il 429 arriva dopo 107
  richieste (budget 120/min già parzialmente consumato).
- Coperti: 401 senza auth, metadata pubblica e scopes, challenge RFC 9728,
  separazione read/operate, denial senza grant, allowlist tunnel, 403 con token
  read-only, audit negato, header e CORS.
- Non coperti: pentest completo, carico/capacità, infrastruttura e
  configurazione dei secret.
