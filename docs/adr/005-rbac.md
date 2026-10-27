# ADR-005 — RBAC per environment

- Status: accepted
- Date: 2026-10-25
- Decision: D7 = B (tightening per environment)

## Context

The original has three application roles: `SystemAdmin`, `ServerAdmin` and `ServerOperator` per `ProviderEnvironment`. `SystemAdmin` does not imply the per-environment roles. Inventory writes are open to any authenticated user; the matrix is neither documented nor covered by tests. The Phase 1 verification is in `docs/security/permissions.md`.

## Decision

Apply tightening B:

- **Global master data** → `SystemAdmin`: Providers, EnvironmentDefinitions, ProviderEnvironments, Applications, ApplicationVersions, ApplicationVersionApis, ApplicationApiQueryParams, Projects, CommandTemplates, ServerCredentials, Users, Groups, Roles, Menus, assignments, global tests, audit.
- **Resources tied to an environment** → `ServerAdmin` on **all** environments involved: Server, ServerApplication, ProxyConnection, ProxyRoute, diagrams with only `ProviderEnvironment` scopes, deletion of Server/ServerApplication nodes.
- If the operation touches multiple environments (proxy A→B, deploy with route, move of a server), roles are required on all of them.
- **Diagrams** default/global or with `Provider`/`Project` scope → `SystemAdmin`; with only `ProviderEnvironment` scopes → `ServerAdmin` on all scopes.
- **Topology delete**: Provider/ProviderEnvironment → `SystemAdmin`; Server/ServerApplication → `ServerAdmin` on all environments in the cascade.
- **Credentials exception**: SSH assignment, host key reset and changing the address/environment of a server with credentials remain `SystemAdmin`, as in the original; they do not require `ServerAdmin`.
- `SystemAdmin` does **not** imply `ServerAdmin`/`ServerOperator`: servers, console and runs require the environment role.
- Reads unchanged: open to every authenticated user.
- Menu filtered by `MenuRole`; CSRF token on all mutations.

| Capability | SystemAdmin | ServerAdmin (env) | ServerOperator (env) | Other authenticated users |
|---|---|---|---|---|
| Read inventory and menu | yes | yes | yes | yes |
| Write global master data (providers, environments, provider×environment, catalog, projects, templates, credentials, users/groups/roles/menus) | yes | no | no | no |
| Write Server, ServerApplication, ProxyConnection, ProxyRoute | only if also ServerAdmin on the environments involved | yes, on all environments involved | no | no |
| Default/global diagrams or with Provider/Project scope | yes | no | no | no |
| Diagrams with only ProviderEnvironment scopes | only if also ServerAdmin on all scopes | yes, on all scopes | no | no |
| Delete Topology node Provider/ProviderEnvironment | yes | no | no | no |
| Delete Topology node Server/ServerApplication | only if also ServerAdmin on the environments in the cascade | yes, on the environments in the cascade | no | no |
| SSH console | only if also ServerAdmin | yes | no | no |
| Run actions and reachability | only if also Operator | yes | yes | no |
| Global ReachabilityTests | yes | no | no | no |
| Per-server ReachabilityTests (CRUD) | only if also ServerAdmin | yes | no | no |
| Change of address/environment of a server with credentials, host key reset | yes | no | no | no |
| Audit executions | yes | no | no | no |

## Alternatives considered

- **A — Keep writes open**: rejected. A user without roles could delete a subtree with `DELETE /Topology/Nodes/...` and modify any entity.
- **SystemAdmin as superuser also per environment**: rejected, breaks the current separation and makes the boundary between global administration and server operations invisible.

## Consequences

- A policy helper `RequireAdminOnAll(environmentIds)` is needed; multi-environment operations compute the union of the environments touched and reject with 403 if one is missing.
- The matrix must be tested per role and per environment, including multi-environment cases and cascade deletion.
- The UI must hide disallowed actions and menus; the API remains the source of truth.
- No data migration: existing roles remain valid; only authorization changes.

## Phase 1 verification

`SystemAdminWriteFilter` covered only Users, Groups, Roles, Menus and ProviderEnvironmentGroupRoles. Inventory, catalog, proxy, projects, diagrams and topology had no filter. `MenusService.GetMenus` returned all entries and did not use `MenuRole`. The complete legacy matrix is in `docs/security/permissions.md`; D7 = B is the answer.
