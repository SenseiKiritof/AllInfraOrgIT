# Permissions matrix

Verified against the legacy backend on 2026-10-25 (`MinimalApis/*`, `ServerAccessService`, `SystemAdminWriteFilter`, `Services/*`). The current BFF session and read-model behaviour is recorded in [Current implementation](#current-implementation-bff-2026-11-11) and [Read model](#read-model-pt-05); the legacy matrix is kept as the Phase 1 baseline.

## Roles

| Role | Scope | Where it lives |
|---|---|---|
| `SystemAdmin` | system | `Users.Roles` |
| `ServerAdmin` | `ProviderEnvironment` | `ProviderEnvironmentGroupRoles` via user group |
| `ServerOperator` | `ProviderEnvironment` | `ProviderEnvironmentGroupRoles` via user group |

`SystemAdmin` **does not** imply `ServerAdmin`/`ServerOperator`. A `ServerAdmin` is also an operator on their own environment (`OperatorEnvironmentIds` includes admins).

## Current implementation (BFF, 2026-11-11)

- All `/api/*` routes require an authenticated server-side session, except
  `GET /auth/login` and `GET /auth/callback`.
- The session cookie is `__Host-infraorgit_session` in production: `HttpOnly`,
  `Secure`, `Path=/`, `SameSite=Lax`, with a max-age tied to the refresh window
  (about 30 minutes). The access and refresh tokens are never readable from
  JavaScript.
- `SameSite=Lax` is required by the OIDC login: the callback from Keycloak is a
  top-level cross-site GET navigation. With `Strict` the browser would omit the
  short-lived login cookie that carries `state` and `code_verifier`, and the
  login would fail. Lax still blocks cross-site subrequests and cross-site
  POSTs.
- CSRF is explicit and is the primary control: `GET /api/session` returns a
  per-session token, and every mutating `/api/*` request and `/auth/logout`
  must send it in `X-CSRF-Token` (fixed-time comparison) together with an
  allowed `Origin`. A missing or wrong token returns `403 csrf_failed`; a
  missing or foreign Origin returns `403 origin_failed`. The console WebSocket
  checks `Origin`.
- Do not describe the BFF session cookie as `SameSite=Strict`: that was the
  legacy JWT-cookie behaviour, not the current session. See PT-15 in
  [`pentest-2026-11.md`](pentest-2026-11.md).

## Authentication (legacy backend)

- All `/api/*` routes require a token, except `Auth/Login`, `Auth/Token`, `Auth/RefreshToken`, `Auth/Logout`.
- The token comes from an HttpOnly cookie; the WebSocket console also accepts `access_token` in the query string (`/api/socket` only).
- The console checks `Origin` against `FeConn.Host`.
- There is no explicit CSRF token: the legacy backend relied on `SameSite=Strict` and the JSON content type. The BFF replaces this with the explicit token and Origin check above.

## Effective matrix (legacy)

| Area / route | Read | Write | Verified notes |
|---|---|---|---|
| Providers, Enviroments, ProviderEnvironments | authenticated | **authenticated** | no filter; `Enviroments` is the legacy typo |
| Servers | authenticated | **authenticated** | `PUT /Servers/{id}` requires SystemAdmin only if the server has a credential and the IP/hostname/environment changes; `MoveServer` likewise |
| ServerApplications, ProxyConnections, ProxyRoutes, Projects | authenticated | **authenticated** | no filter |
| Applications, ApplicationVersions, ApplicationVersionApis, ApplicationApiQueryParams | authenticated | **authenticated** | no filter |
| Diagrams | authenticated | **authenticated** | no filter; unique `IsDefault` handled by the service |
| Topology (`GET`, node delete, delete preview) | authenticated | **authenticated** | the delete removes the subtree: destructive surface left open |
| Users, Groups, Roles, Menus, ProviderEnvironmentGroupRoles | authenticated | `SystemAdmin` | `SystemAdminWriteFilter` on POST/PUT/DELETE |
| ServerCredentials (including `/Servers/{id}/Ssh`, `/HostKey`) | `SystemAdmin` | `SystemAdmin` | reads and writes protected |
| CommandTemplates | `SystemAdmin` | `SystemAdmin` | reads and writes protected |
| ApplicationActions config (`GET/POST` per application, `PUT/DELETE`) | `SystemAdmin` | `SystemAdmin` | operators do not see scripts/parameters |
| ApplicationActions deploy (`GET` buttons, `POST .../Run`) | `ServerOperator` | `ServerOperator` | `ServerAdmin` included |
| Global ReachabilityTests (`/ReachabilityTests`) | `SystemAdmin` | `SystemAdmin` | the run is only per server or environment |
| ReachabilityTests per server | `ServerOperator` | `ServerAdmin` | `GET` and run = Operator; CRUD = Admin |
| Reachability run per environment | — | `ServerOperator` | `POST /ProviderEnvironments/{id}/ReachabilityTests/Run` |
| CommandExecutions (audit) | `SystemAdmin` | — | server-side filter and pagination |
| ServerAccess (`/ServerAccess/Me`) | authenticated | — | returns admin/operator environments |
| Connection policy (`GET /api/connection-policy`) | authenticated | — | the desktop needs it before opening a tunnel; BFF or `tunnels:operate` token |
| Connection policy (`PUT /api/connection-policy`) | — | `SystemAdmin` | installation-wide, stored in the shared `ConnectionPolicies` row |
| Server tunnel relay (`GET /api/tunnels/relay`) | `ServerOperator` | — | Local service or deployment only; Origin and `tunnels:operate`/BFF required |
| Direct remote target (`GET /api/remote/targets/{id}`) | `ServerAdmin` | — | Host, jumps, username and host-key fingerprint; never a secret |
| Direct console audit (`POST /api/remote/console-sessions…`) | `ServerAdmin` | — | Creates/completes the `CommandExecution`; owner check on completion |
| Direct action intent/complete (`/intent`, `/api/remote/actions/{id}/complete`) | `ServerOperator` | — | Intent renders the script and creates the execution; completion checks the owner |
| Direct file events (`POST /api/remote/file-events`) | `ServerAdmin` | — | Writes the `FileTransfer` audit kind |
| Direct host key (`POST /api/remote/host-key`) | `ServerAdmin` | — | Stores first-use fingerprint; mismatch is 409 |
| SSH console (`/socket/Servers/{id}/Console`) | `ServerAdmin` | — | Origin required; no implicit `SystemAdmin` |
| File browser (`/Servers/{id}/Files...`) | `ServerAdmin` | — | same environment role as the console |
| Auth/CurrentUser | authenticated | — | |

## Verified gaps

1. **Inventory writes open to every authenticated user.** A user without roles can create/modify/delete providers, environments, servers, applications, projects, proxies and diagrams. They can also delete a subtree from the topology (`DELETE /Topology/Nodes/...`). This is the widest gap.
2. **Menu not filtered by role.** `MenusService.GetMenus` returns all entries and does not load `Menu.Roles`; the `MenuRole` table has no effect on the menu. The UI shows admin pages to everyone (writes then fail).
3. **No environment delete.** `EnviromentsApi` exposes GET/POST/PUT, not DELETE; the new CRUD will have to decide whether to add it with an impact preview.
4. **Implicit CSRF (legacy).** The legacy backend had no CSRF token and relied on `SameSite=Strict`; the BFF adds the explicit token and Origin check described above.
5. **Incomplete audit on inventory writes.** There is no audit for create/update/delete of inventory and diagrams; only remote executions are recorded.

## Target v1 — D7 = B (decided 2026-10-25)

Tightening per environment. Inventory reads remain open to every authenticated
user by design; writes change, and privilege metadata becomes `SystemAdmin`-only.

### Read model (PT-05)

D7 keeps **inventory** reads open to any authenticated account: providers and
environments, servers, deployments, applications and versions, projects,
topology and reachability tests. This is a deliberate single-team policy, not an
oversight. The UI filters menus, but the API is the security boundary and still
returns every environment.

Accepted consequences for the HTTP UI:

- an auto-provisioned account with no application roles can map the whole
  infrastructure, including server addresses, deployments and ports;
- an MCP token with `mcp:read` — including the `infraorgit-mcp` service account
  — is a whole-inventory read grant, not a per-environment grant;
- reconnaissance is easier, but the data is read-only and every write still
  needs the environment role.

Privilege metadata is different and is being restricted: reads of
`/api/users`, `/api/groups`, `/api/roles` and
`/api/provider-environment-group-roles` are moving to `SystemAdmin`, matching
the existing write rule. The UI already hides those pages from non-admins. This
supersedes the “reads unchanged” sentence in ADR-005 for those four resources;
the write model in ADR-005 still applies.

Open decision: if the deployment serves more than one team, or MCP is exposed to
accounts that should not see every environment, replace the global read model
with per-environment filtering for HTTP, MCP tools and resources. Until that
decision is recorded and implemented, treat every authenticated account and
every `mcp:read` token as trusted with the whole inventory.

General rules:

- **Global master data** → `SystemAdmin`.
- **Resources tied to one or more environments** → `ServerAdmin` on **all** environments involved. `SystemAdmin` alone is not enough: role separation per environment stays.
- If an operation touches entities in different environments (proxy source→target, deploy with route, move of a server), the roles are required on all environments involved.
- **Credentials exception**: SSH assignment, host key reset and address/environment change of a server with a credential remain `SystemAdmin`, as in the original; they do not require `ServerAdmin`.
- The UI hides actions that are not allowed; the API remains the source of truth (403, not 404, for existing resources).
- **Menu filtered** by `MenuRole` and **explicit CSRF** on all mutations, in addition to `Origin` and `SameSite`.

### Target matrix

| Operation | Required role |
|---|---|
| CRUD Providers, EnvironmentDefinitions, ProviderEnvironments | `SystemAdmin` |
| CRUD Applications, ApplicationVersions, ApplicationVersionApis, ApplicationApiQueryParams, Projects | `SystemAdmin` |
| CRUD Users, Groups, Roles, Menus, ProviderEnvironmentGroupRoles | `SystemAdmin` |
| CRUD ServerCredentials; SSH assignment; host key reset | `SystemAdmin` |
| File transfer configuration (`PUT /api/servers/{id}/file-transfer`) | `SystemAdmin` |
| CRUD CommandTemplates; ApplicationActions config | `SystemAdmin` |
| Global ReachabilityTests (CRUD and run) | `SystemAdmin` |
| Read CommandExecutions (audit) | `SystemAdmin` |
| Server create/edit/delete | `ServerAdmin` on the server's environment |
| Move Server between environments | `ServerAdmin` on source and target; `SystemAdmin` if the server has a credential |
| IP/hostname change of a server with a credential | `SystemAdmin` |
| CRUD ServerApplications | `ServerAdmin` on the server's environment; if the target route is in another environment, `ServerAdmin` there too |
| CRUD ProxyConnections | `ServerAdmin` on the source and target environments |
| CRUD ProxyRoutes | `ServerAdmin` on the environments of the connection and of the target (ServerApplication or ProxyConnection) |
| CRUD Diagrams and node/edge save, default or global diagram | `SystemAdmin` |
| CRUD Diagrams with only `ProviderEnvironment` scopes | `ServerAdmin` on all environments in scope |
| Diagram scope change | union of old/new scopes; if `Provider`, `Project` or default appears → `SystemAdmin` |
| Delete Topology node `Provider` or `ProviderEnvironment` | `SystemAdmin` |
| Delete Topology node `Server` or `ServerApplication` | `ServerAdmin` on all environments touched by the cascade |
| SSH console | `ServerAdmin` on the server's environment |
| SFTP/FTP file browser (`/api/servers/{id}/files...`) | `ServerAdmin` on the server's environment |
| Run ApplicationActions and reachability per server/environment | `ServerOperator` on the environment |
| CRUD ReachabilityTests per server | `ServerAdmin` on the server's environment |
| Read connection policy | authenticated | — | the desktop needs it before opening a tunnel |
| Update connection policy | `SystemAdmin` | — | one row shared by every API node in the cluster |
| Server-side tunnel relay | `ServerOperator` on the server's environment | — | `Local` service or deployment only; fixed target host/port |
| Direct console/files/actions | `ServerAdmin` (console/files), `ServerOperator` (actions) | — | `Client`/reachable `Auto`; target metadata and audit stay in the API |
| Read inventory: providers, environments, servers, deployments, applications/versions, projects, topology, reachability tests | authenticated (D7 read model) |
| Read Users, Groups, Roles, ProviderEnvironmentGroupRoles | `SystemAdmin` |
| Other reads: session, server access, menus | authenticated |
| `/auth/login`, `/auth/callback` | anonymous |

`SystemAdmin` does not imply `ServerAdmin`/`ServerOperator`: for a server or a console the environment role is still required. A `ServerAdmin` is also an operator on their own environment.

## Tests to write in Phase 2–6

- `SystemAdmin` without environment roles: provider CRUD ok; server creation 403; console 403; run 403.
- `ServerAdmin` on environment A: server CRUD A ok; provider CRUD 403; server B 403; proxy A→B 403 if not admin on B too; diagram with scope A ok; diagram with scope B 403; Provider diagram 403.
- `ServerOperator` on A: run A ok; console A 403; server CRUD A 403; reachability CRUD A 403.
- Authenticated user without roles: inventory reads ok; users/groups/roles/provider-environment-group-roles 403; every write 403.
- Menu: each role sees only assigned entries.
- CSRF: mutation without token → 403; foreign `Origin` → 403.
