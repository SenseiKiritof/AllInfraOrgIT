# UX map and pages

Verified against the legacy frontend (`infra-org-it-fe/app`, Next.js) on 2026-10-25. Target: Vite + React Router, same flows, corrected routes (`/environments`, not `/enviroments`).

## Shell

- **Login**: `/api/auth/*` (BFF). Public page `/login-error`. No token readable from JavaScript.
- **Side menu**: loaded from `GET /api/menus`; in legacy it is not filtered by role. Target: filtered by `MenuRole`.
- **Header**: route title, Back button (except Home), user dropdown with Logout.
- **Detail route**: the menu contains parent (`/servers`) and child (`/servers/{id}`) entries with `HideBackButton=false`; the layout shows the sidebar only when the current route has `HideBackButton=true` (top-level entries).
- **Error handling**: centralized popup; 401 → refresh or login; API errors shown to the user.
- **Tables**: `DataTable` with filters, server-side pagination (`/Paginated`), per-entity columns, edit/delete actions.
- **Forms**: `CrudModal` + `Input`/`MultiSelect`; no React Hook Form in legacy; target RHF + Zod.

## Pages

| Route | Page | Content and actions | Legacy UI access |
|---|---|---|---|
| `/` | Home | placeholder "Landing page" | all |
| `/environments` | Environments | list: id, name, description, provider; create/edit; **no delete** | all |
| `/environments/{id}` | Environment detail | name, description, linked providers; save | all |
| `/providers` | Providers | list: id, name, environments; create/edit/delete | all |
| `/providers/{id}` | Provider detail | name, linked environments; save | all |
| `/servers` | Servers | list: id, name, environment; create/edit/delete | all |
| `/servers/{id}` | Server detail | see server flow | all; remote blocks conditional |
| `/applications` | Applications | list: id, name, description, base path, port; create/edit/delete | all |
| `/applications/{id}` | Application detail | see catalog flow | all |
| `/projects` | Projects | list: id, name, description; create/edit/delete | all |
| `/projects/{id}` | Project detail | name, description, linked applications | all |
| `/diagrams` | Diagrams | list: id, name, description; open, create, delete | all |
| `/diagrams/{id}` | Diagram canvas | see diagrams flow; `id=0` = global view | all |
| `/users` | Users | list: id, username, first name, last name; create/edit/delete | all (SystemAdmin write) |
| `/users/{id}` | User detail | username, first name, last name, groups, roles | all |
| `/groups` | Groups | list and name CRUD | all (SystemAdmin write) |
| `/roles` | Roles | list and CRUD of name, label, scope | all (SystemAdmin write) |
| `/menu` | Menu | list and CRUD of entries, path, order, visibility | all (SystemAdmin write) |
| `/credentials` | Credentials | list: name, SSH user, type, server; CRUD with write-only secret | all (SystemAdmin API) |
| `/commands` | Base commands | list and template CRUD; highlights `{{Name}}` placeholders | all (SystemAdmin API) |
| `/reachability` | Network tests | global tests; per-environment tests; run | all (SystemAdmin/Operator API) |
| `/executions` | Execution log | paginated list: date, user, server, type, command, exit; output detail | all (SystemAdmin API) |
| `/login-error` | Login error | message and retry | public |

## Server flow `/servers/{id}`

1. **Master data**: name, IP, hostname, environment (select `ProviderEnvironments`); save. If the server has a credential and the address/environment changes, the API requires SystemAdmin.
2. **Deployed applications**: `ServerApplications` list; add application version + exposed port; delete deployment.
3. **Proxy**: incoming/outgoing connection list; create connection (source/target/direction); delete.
4. **SSH** (`SshBlock`): credential select, port; save; console if `ServerAdmin`; reset host key.
5. **Reachability** (`ReachabilityBlock`): server tests; create/edit/delete if `ServerAdmin`; run if `ServerOperator`.
6. **Deploy actions** (`DeployActions`): application buttons; confirmation if required; run; output; visible to `ServerOperator`.

## Catalog flow `/applications/{id}`

1. **Application**: name, description, base path, listening port; save; delete.
2. **Versions**: list, create, edit, delete; each version has a number.
3. **Version APIs**: verb, URL, description, body; CRUD.
4. **API query params**: name, type; CRUD.
5. **Linked projects**: multi-select; add/remove.
6. **Application actions** (`ActionsBlock`): label, order, template or custom script, placeholder values, confirmation; SystemAdmin only. Operators see only the buttons.

## Diagrams flow `/diagrams/{id}`

- Toolbar: diagram selector, **Global view** (`id=0`), Save, Save as…, Export PNG, Fit, Re-layout, zoom, Node.
- Global view filters: provider, environment, project; "Save as…" converts them into `DiagramScopeItem` (`Provider`, `ProviderEnvironment`, `Project`).
- React Flow canvas: provider/environment/server/server-application nodes; proxy edges with handle and bend; persisted layout.
- Node actions: create/edit provider, environment, server, application; delete with impact preview (`Topology/Nodes/{type}/{id}/DeletePreview`).
- Proxy: connect servers; manage routes (`Route`, `MappedTo`, application or connection target).
- Saving: `PUT /Diagrams/{id}/Nodes` and `/Edges`; `GET /Diagrams/{id}/Graph` returns diagram + topology + nodes/edges in scope.
- Client-side PNG export. Diagram import not present in legacy; the legacy import is the Phase 7 importer.

## Target differences

| Legacy | Target |
|---|---|
| Next.js App Router, JS | Vite + React Router 7, TypeScript |
| `/enviroments` (API) | `/api/environments` |
| Menu not filtered | menu filtered by role |
| `id=0` for global view | `Diagram.IsDefault` + explicit route `/diagrams/default` (no magic id) |
| `Enviroments` typo in calls | no alias in v1; alias only for external clients (D10) |
| Tables with `totalCount/results` | `{items,total,page,pageSize}` |
| No environment delete | evaluate DELETE with impact preview |
| Server state with `useServerAccess` | same model, data from `/api/server-access/me` |
| Forms without schema | RHF + Zod, RFC 7807 errors |

## Target visibility (D7 = B)

- **SystemAdmin**: global master data (providers, environments, provider×environment, catalog, projects, templates, credentials, users/groups/roles/menu), global diagrams or diagrams with Provider/Project scope, audit.
- **ServerAdmin on the environment**: servers, deployments, proxies, diagrams with environment-only scope, console; multi-environment writes require the role on all environments involved.
- **ServerOperator on the environment**: run actions and reachability.
- **All authenticated users**: reads; the menu shows only assigned entries.
- **SystemAdmin alone is not enough** for server/console/run: the environment role is also required.

## Pages the target can simplify

- Home: dashboard with recent diagrams or environment status; the legacy placeholder is not needed.
- Provider/environment detail: the relation is already handled by `ProviderEnvironment`; avoid two forms editing the same pair.
- Diagrams: separate `buildGraph`/layout (pure, testable functions) from the canvas.
- Admin: one users page with inline groups/roles; no separate navigation if not needed.
