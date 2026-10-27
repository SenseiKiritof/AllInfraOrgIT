# Permissions matrix

Verified against the legacy backend on 2026-10-25 (`MinimalApis/*`, `ServerAccessService`, `SystemAdminWriteFilter`, `Services/*`).

## Roles

| Role | Scope | Where it lives |
|---|---|---|
| `SystemAdmin` | system | `Users.Roles` |
| `ServerAdmin` | `ProviderEnvironment` | `ProviderEnvironmentGroupRoles` via user group |
| `ServerOperator` | `ProviderEnvironment` | `ProviderEnvironmentGroupRoles` via user group |

`SystemAdmin` **does not** imply `ServerAdmin`/`ServerOperator`. A `ServerAdmin` is also an operator on their own environment (`OperatorEnvironmentIds` includes admins).

## Authentication

- All `/api/*` routes require a token, except `Auth/Login`, `Auth/Token`, `Auth/RefreshToken`, `Auth/Logout`.
- The token comes from an HttpOnly cookie; the WebSocket console also accepts `access_token` in the query string (`/api/socket` only).
- The console checks `Origin` against `FeConn.Host`.
- There is no explicit CSRF token: mutations rely on `SameSite=Strict` and the JSON content type.

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
| SSH console (`/socket/Servers/{id}/Console`) | `ServerAdmin` | — | Origin required; no implicit `SystemAdmin` |
| Auth/CurrentUser | authenticated | — | |

## Verified gaps

1. **Inventory writes open to every authenticated user.** A user without roles can create/modify/delete providers, environments, servers, applications, projects, proxies and diagrams. They can also delete a subtree from the topology (`DELETE /Topology/Nodes/...`). This is the widest gap.
2. **Menu not filtered by role.** `MenusService.GetMenus` returns all entries and does not load `Menu.Roles`; the `MenuRole` table has no effect on the menu. The UI shows admin pages to everyone (writes then fail).
3. **No environment delete.** `EnviromentsApi` exposes GET/POST/PUT, not DELETE; the new CRUD will have to decide whether to add it with an impact preview.
4. **Implicit CSRF.** There is no CSRF token; `SameSite=Strict` protects, but the defense is not explicit and is not tested.
5. **Incomplete audit on inventory writes.** There is no audit for create/update/delete of inventory and diagrams; only remote executions are recorded.

## Target v1 — D7 = B (decided 2026-10-25)

Tightening per environment. Reads remain open to every authenticated user; writes change.

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
| Run ApplicationActions and reachability per server/environment | `ServerOperator` on the environment |
| CRUD ReachabilityTests per server | `ServerAdmin` on the server's environment |
| All reads | authenticated |
| `/auth/login`, `/auth/callback` | anonymous |

`SystemAdmin` does not imply `ServerAdmin`/`ServerOperator`: for a server or a console the environment role is still required. A `ServerAdmin` is also an operator on their own environment.

## Tests to write in Phase 2–6

- `SystemAdmin` without environment roles: provider CRUD ok; server creation 403; console 403; run 403.
- `ServerAdmin` on environment A: server CRUD A ok; provider CRUD 403; server B 403; proxy A→B 403 if not admin on B too; diagram with scope A ok; diagram with scope B 403; Provider diagram 403.
- `ServerOperator` on A: run A ok; console A 403; server CRUD A 403; reachability CRUD A 403.
- Authenticated user without roles: reads ok; every write 403.
- Menu: each role sees only assigned entries.
- CSRF: mutation without token → 403; foreign `Origin` → 403.
