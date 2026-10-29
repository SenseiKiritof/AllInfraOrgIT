# UX map and pages

Verified against the legacy frontend (`infra-org-it-fe/app`, Next.js) on 2026-10-25. Target: Vite + React Router, same flows, corrected routes (`/environments`, not `/enviroments`).

## Shell

- **Login**: `/api/auth/*` (BFF). Public page `/login-error`. No token readable from JavaScript.
- **Side menu**: loaded from `GET /api/menus`; in legacy it is not filtered by role. Target: filtered by `MenuRole`. Labels come from the database and are not translated.
- **Language**: Italian (default) and English in the user dropdown; the choice is stored in `localStorage` and applies immediately. Database-driven labels (menu names, role labels) are translated through the `Translations` table; a new language is a new `Language` code plus its rows (and the frontend dictionary). API error messages stay Italian.
- **Header**: fixed. Back button on detail routes, the name of the open entity centred, page actions on the right (e.g. Console SSH), then theme and user dropdown with the language selector and Logout.
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
| `/applications/{id}` | Application detail | versions, APIs, linked projects, deployed servers | all |
| `/projects` | Projects | list: id, name, description; create/edit/delete | all |
| `/projects/{id}` | Project detail | name, description, linked applications with base path, port and servers (open) | all |
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

1. **Master data**: name, IP, hostname, public IP (NAT), CPU cores, RAM GB, disk GB, operating system, HA node, managed by, environment (select `ProviderEnvironments`), and the SSH credential (SystemAdmin only, also when creating); save. Changing IP, SSH port or jump host while a console is open asks for confirmation and closes that console. If the server has a credential and the address/environment changes, the API requires SystemAdmin.
2. **Deployed applications**: `ServerApplications` list with runtime, host port and HA role; add application version, exposed port, runtime (`Container`/`Native`), container image, container name, compose folder, host port (`null` when equal to the exposed port) and HA role (`Primary`/`Secondary`); container fields require `Container`; delete deployment.
3. **Proxy**: incoming/outgoing connection list; create connection (source/target/direction); delete.
4. **SSH** (`SshBlock`): credential select, port; save; console if `ServerAdmin`; reset host key. The console dock at the bottom is always visible: sessions become tabs, the chevron minimizes the open panels like Riduci, and a session can be reopened from its tab.
5. **Reachability** (`ReachabilityBlock`): global and server tests with a checkbox each; **Effettua selezionati** (disabled until one is checked) or **Effettua tutti i test**; create/edit/delete server tests if `ServerAdmin`, run if `ServerOperator`.
6. **Deploy actions** (`DeployActions`): application buttons; confirmation if required; run; output; visible to `ServerOperator`.

## Catalog flow `/applications/{id}`

Sections follow the population order: a version is needed to deploy a server, and the environments come from the deployments.

1. **Application**: name, description, base path, listening port, type (`Backend`, `Frontend`, `SFTP`, `RabbitMQ`, `NGINX`, `Elastic`, `Kibana`, `Kafka`, `MySQL/MariaDB`, `MongoDB`, `Redis`); save; delete. `Frontend` hides the API, API key and call sections.
2. **Versions**: list, create, edit, delete; each version has a number.
3. **Version APIs**: verb, URL, description, body; CRUD; **Chiama** picks the environment, runs the call server-side with hostname, API keys and query params, shows status, time, size, body with copy/download (cap 10 MiB); saving is opt-in and puts the call in **Chiamate** (own history, open/delete, **Ripeti** reopens it with the same environment, query and body). History keeps 1 MiB per call, pruned after 30 days. SystemAdmin only.
4. **API query params**: name, type; CRUD.
5. **Servers**: deployments of the application (`ServerApplications`) with IP, environment, version, exposed port, runtime, host port and HA role; add server + version + exposed port + deployment details (runtime, container image, container name, compose folder, host port, HA role), change the server of a deployment, delete; link to the server detail. The server select shows name, IP and environment, and typing filters on any of them.
6. **Environments**: only the environments where the application is deployed on a server, with hostname and SSL-ignore (`ApplicationEnvironments`); the call uses the selected environment. Changing the deployments refreshes the list. SystemAdmin only.
7. **API keys**: name + location (`Header` or `Query`) from the OpenAPI security schemes, environment (empty = every environment), write-only value; import fills the definitions, the secret is entered here. SystemAdmin only.
8. **Linked projects**: multi-select; add/remove.
9. **Application actions** (`ActionsBlock`): label, order, template or custom script, placeholder values, confirmation; SystemAdmin only. Operators see only the buttons.

Form selects (server, version, project, menu, location) are searchable: type to filter the option label, arrows and Enter to pick.

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
