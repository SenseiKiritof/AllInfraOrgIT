# Inventory fields proposal

- Status: implemented (2026-10-29)
- Date: 2026-10-29
- Scope: data model, API, validation, UI and translations. The migration is `InventoryDetails`; the backfill is left to each installation.

An operations inventory needs eight facts that have no column in InfraOrgIT today. They end up as free text in `Servers.Hostname` (public IP, HA node, operator, runtime) or are not recorded at all (host port, image, compose folder, virtual host). This document proposes where each fact goes and why, the impact on API, `Guard` validation, DTOs, UI and translations, the migration to generate and how to backfill existing data.

## Summary

| # | Gap | Proposal | Table |
|---|---|---|---|
| 1 | container or native service | `Runtime`: `Container` \| `Native` | `ServerApplications` |
| 2 | image, container name, compose folder | `ContainerImage`, `ContainerName`, `ComposeDirectory` | `ServerApplications` |
| 3 | host port behind a local reverse proxy | `HostPort` | `ServerApplications` |
| 4 | MySQL/MariaDB, MongoDB, Redis | `Type` values `MySql`, `MongoDb`, `Redis` | `Applications` |
| 5a | public/NAT IP | `PublicIpAddress` | `Servers` |
| 5b | cores, RAM, disk, OS | `CpuCores`, `MemoryGb`, `DiskGb`, `OperatingSystem` | `Servers` |
| 5c | HA role, third-party operator | `HaNode`, `ManagedBy`; `HaRole` per deployment | `Servers`, `ServerApplications` |
| 6 | virtual host and proxy listen port | `VirtualHost`, `ListenPort`, wider unique key | `ProxyRoutes` |

Every new column is nullable. Null means "not known" or "not applicable": existing rows stay valid, the migration moves no data and no default states a fact nobody checked.

## Proposal per gap

Examples use the demo company Acme (`acme.internal`, `acme.example`), its hosts `proxy01`, `web01`, `app01`, `app02`, `db01` and documentation addresses (`203.0.113.0/24`).

### 1. Container or native service

| Column | Type | Null | Constraints / validation |
|---|---|---|---|
| `ServerApplications.Runtime` | varchar(20) | yes | `Container` \| `Native`; check `CK_ServerApplications_Runtime`; empty → null, otherwise `Guard.Enum<DeploymentRuntime>` |

- **Why on the deployment.** The same product can run both ways in one inventory, e.g. MySQL installed from packages on `db01` and in a container on a test host.
- **Why nullable, no default.** Third-party hosts (a partner's SFTP server, a mail relay) can be in the inventory without anyone knowing how they run. A `Container` default would state a false fact on them.
- **Rejected.** On `Applications`: one value per application, wrong as soon as a product runs both ways. Derived from `ContainerName` being set: cannot tell "native" from "not known".

### 2. Image, container name and compose folder

| Column | Type | Null | Constraints / validation |
|---|---|---|---|
| `ServerApplications.ContainerImage` | varchar(300) | yes | repository without tag, e.g. `registry.acme.internal/acme/crm-api`; `Guard.OptionalText` |
| `ServerApplications.ContainerName` | varchar(200) | yes | `container_name` on the host, e.g. `crm-api`; `Guard.OptionalText` |
| `ServerApplications.ComposeDirectory` | varchar(300) | yes | folder of the compose file, e.g. `/opt/acme/crm-api`; `Guard.OptionalText` |

Rule: the three columns are accepted only with `Runtime` = `Container`, otherwise 422. One check keeps container data off native deployments.

- **Why on the deployment.** These are the handles an operator types on the host (`docker logs <ContainerName>`, `cd <ComposeDirectory> && docker compose up -d`). The image sits next to them because the repository name can differ per environment, for instance while an image is being renamed or when environments use different registries.
- **Why no tag.** The tag changes at every release (often a commit hash): stored here it would be stale after the next deploy. `ApplicationVersions.VersionNumber` stays the catalog version.
- **Rejected.** `Applications.ContainerImage` on the catalog: one value per application, wrong in the cases above. Deriving name and folder from the application name: correct only under a naming convention that is never broken, and InfraOrgIT does not impose one. A `Containers` child table (sidecars, several containers per deployment): not needed until a deployment has more than one container.

### 3. Host port behind a local reverse proxy

| Column | Type | Null | Constraints / validation |
|---|---|---|---|
| `ServerApplications.HostPort` | int | yes | port published on the host (`HostPort:ListeningOnPort`); `Guard.Port` when set; equal to `ExposedPort` → stored as null |

The port chain becomes explicit:

```text
client ─▶ web01:9443  local nginx           ServerApplications.ExposedPort
       ─▶ web01:7001  published by Docker   ServerApplications.HostPort
       ─▶ :3000       inside the container  Applications.ListeningOnPort
```

Null means the container publishes directly on `ExposedPort` (`7002:3000`) or the service is native: there is no intermediate port.

- **Why a new column.** `ExposedPort` keeps its meaning (the port reachable from outside the server), so route targets (`MappedTo`), the diagram label `:port`, the `{{ExposedPort}}` placeholder and the existing rows stay correct.
- **Rejected.** Redefining `ExposedPort` as the host port and moving the nginx port elsewhere: changes the meaning of every existing row. Modeling the local nginx as its own deployment plus a route on a server-to-itself connection: `CK_ProxyConnections_DifferentServers` and the API forbid self-connections, the diagram would need self-loop edges and every deployment an extra route. Limit of the chosen option: the virtual host and path of a local nginx are not recorded (open point 4).

### 4. MySQL/MariaDB, MongoDB and Redis types

`Applications.Type` gains three values; the column stays varchar(20), not null, default `Backend`.

| Value | Label | Default port |
|---|---|---|
| `MySql` | MySQL/MariaDB | 3306 |
| `MongoDb` | MongoDB | 27017 |
| `Redis` | Redis | 6379, sentinel 26379 |

Changes: the `ApplicationTypes` array in `ApplicationsEndpoints` (the 422 message lists the values from it), the check `CK_Applications_Type` in `InfraOrgItDbContext`, the `applicationTypes` list in `ApplicationsPage.tsx`, the comment on `Application.Type`. Labels are product names and are not translated, as today.

- **Why product values.** The existing values are products (`RabbitMq`, `Kafka`, `Elastic`, `Kibana`), not categories. MySQL and MariaDB share protocol, port and client tools: the product shows in the application name (`mysql`, `mariadb`) and version.
- **Rejected.** A generic `Database` type: loses the product, unlike the other values. A separate `MariaDb` value: no behavior differs; it can be added later with the same change.
- The API, API key and call sections stay visible for these types: only `Frontend` hides them, as for `Sftp` and `Kafka` today.

### 5a. Public / NAT IP

| Column | Type | Null | Constraints / validation |
|---|---|---|---|
| `Servers.PublicIpAddress` | varchar(45) | yes | IPv4 or IPv6 (45 = longest IPv6 text); new `Guard.OptionalIpAddress`: trim, empty → null, `IPAddress.TryParse` and, for IPv4, four dotted parts (`TryParse` alone reads `1` as `0.0.0.1`), otherwise 422 |

- **Why.** Without a column the public address is written inside `Hostname` (`web01 (portal, public 203.0.113.10)`): it is not a field, and the free text reaches commands through the `{{Hostname}}` placeholder. Format validation keeps the new column from turning into free text again; `IpAddress` keeps its current rule.
- **Rejected.** Keeping it in `Hostname`: the problem itself. A `ServerAddresses` child table (management, public, backup addresses): one public address per server covers the need.

### 5b. Resources and operating system

| Column | Type | Null | Constraints / validation |
|---|---|---|---|
| `Servers.CpuCores` | int | yes | > 0; new `Guard.OptionalPositive` |
| `Servers.MemoryGb` | int | yes | > 0, whole GB |
| `Servers.DiskGb` | int | yes | > 0, total of the disks in GB |
| `Servers.OperatingSystem` | varchar(100) | yes | free text, e.g. `Debian 12`; `Guard.OptionalText` |

- **Why.** Sizing matters for failover (a secondary node with half the cores of the primary cannot take the full load) and comes up in every capacity discussion. Virtual machines are sized in whole GB.
- **Rejected.** A JSON `Specs` column: no validation or sorting, unlike the typed columns elsewhere. Reading the values live over SSH (`nproc`, `free -g`, `lsblk`, `/etc/os-release`): third-party hosts have no credential and the inventory must answer without connecting; a remote action can refresh the columns later. Megabytes or decimals: not needed for whole-GB sizes.

### 5c. HA role and third-party operator

| Column | Type | Null | Constraints / validation |
|---|---|---|---|
| `Servers.HaNode` | varchar(20) | yes | label of the node in a redundant group, e.g. `A`, `B`; `Guard.OptionalText` |
| `ServerApplications.HaRole` | varchar(20) | yes | `Primary` \| `Secondary`; check `CK_ServerApplications_HaRole`; empty → null, otherwise `Guard.Enum<DeploymentHaRole>` |
| `Servers.ManagedBy` | varchar(100) | yes | organisation that operates the server when it is not the owning team, e.g. `Acme Hosting`; `Guard.OptionalText` |

Two levels are needed:

- **Node, on the server.** `app01` and `app02` run the same applications, both active behind `proxy01`, which balances every path: they are nodes A and B of one group. Null means a single instance.
- **Role, on the deployment.** Instances of the same application are not always equivalent: only one runs the scheduled jobs, or only one is registered as a partner's webhook target. `HaRole` marks them `Primary` / `Secondary`; null means equivalent instances or a single one.

- **Rejected.** `Primary`/`Secondary` on the server: false for active-active nodes, and a job or webhook role concerns one application on one node. An `HaPeerServerId` foreign key: groups can have more than two nodes (a three-node cache cluster), and pairs show through the shared deployments. A `HaGroups` table: no use beyond a label yet. Storing the configuration that produces the role (an environment name, a feature switch): application configuration, not inventory; only its effect is needed. `ManagedBy` as a foreign key to `Providers`: providers are hosting providers that scope environments and RBAC; an operator company would show up as a provider without environments in lists, filters and diagrams.

### 6. Virtual host and listen port on proxy routes

| Column | Type | Null | Constraints / validation |
|---|---|---|---|
| `ProxyRoutes.VirtualHost` | varchar(200) | yes | host name matched by the source server of the connection (nginx `server_name`, WAF or gateway host), e.g. `shop.acme.example`; `Guard.OptionalText` |
| `ProxyRoutes.ListenPort` | int | yes | port the source server listens on for the route (`listen`), e.g. `443`; `Guard.Port` when set |

`MappedTo` keeps its meaning (port on the target). The unique key `(ProxyConnectionId, Route)` becomes `(ProxyConnectionId, VirtualHost, ListenPort, Route)`, and the duplicate check in `ProxyEndpoints` (`CreateRouteCoreAsync`, `UpdateRouteAsync`) compares the same four fields; the 409 message names host and port. MySQL treats NULLs as distinct in a unique index: for routes without host and port the API check (EF compares null as equal) remains the guard, and rows written by SQL bypass it.

- **Why on the route.** One connection carries several virtual hosts and ports: `proxy01` listens on 443 for `shop.acme.example` and `admin.acme.example`, which both serve `/app/` from `web01`. With the current key the second `/app/` cannot be stored.
- **Rejected.** On `ProxyConnections`: one value per connection, wrong for the case above. A `ProxyListeners` table (`ServerId`, `VirtualHost`, `ListenPort`) referenced by the routes: normalized, but a new entity with endpoints and UI for a value repeated on a handful of routes; worth it only if virtual hosts get renamed often. Writing the host into `Route` (`shop.acme.example/app`): breaks the path used by labels and test calls.

## Impact

### API and validation

| Area | Change |
|---|---|
| `ServersEndpoints` | `ServerInput` and `ServerDto` + `PublicIpAddress`, `CpuCores`, `MemoryGb`, `DiskGb`, `OperatingSystem`, `HaNode`, `ManagedBy`, set in create and update with the rules above; list search `q` also on `PublicIpAddress` and `ManagedBy`, so values moved out of `Hostname` stay searchable; `EnsureCanWriteAsync` unchanged, the new fields are not connection identity |
| `ServerApplicationsEndpoints` | `ServerApplicationInput` and `ServerApplicationDto` + `Runtime`, `ContainerImage`, `ContainerName`, `ComposeDirectory`, `HostPort`, `HaRole`; container rule and `HostPort` normalization in create and update |
| `ServersEndpoints.CreateApplicationAsync` | `ServerApplicationDeployInput` + the same six fields |
| `ApplicationsEndpoints` | `ApplicationTypes` + `MySql`, `MongoDb`, `Redis` |
| `ProxyEndpoints` | `ProxyRouteInput`, `ProxyRouteDto` and their projection + `VirtualHost`, `ListenPort`; four-field duplicate check |
| `TopologyService` / `TopologyProxyRouteDto` | + `VirtualHost`, `ListenPort` for the diagram label |
| `Guard` | + `OptionalIpAddress`, `OptionalPositive` |
| Enums | `DeploymentRuntime { Container, Native }`, `DeploymentHaRole { Primary, Secondary }`, declared next to their endpoints like `ProxyDirection` |
| RBAC | unchanged: servers and deployments need `ServerAdmin` on the environment, applications `SystemAdmin` |

New record parameters go last with a `null` default, like `ApplicationInput.Type`, so existing callers and tests keep compiling.

**Full-replace PUT.** `PUT /api/servers/{id}` and `PUT /api/server-applications/{id}` assign every field: a form that does not send the new fields clears them. All callers change in the same release: in `ServersPage.tsx` the list form and the detail edit (`saveEntity("/api/servers")`) and the deploy `POST`; in `ApplicationsPage.tsx` the deployment form (`saveEntity("/api/server-applications")`).

### UI

| File | Change |
|---|---|
| `ServersPage.tsx` | master data (create form and detail edit): public IP, cores, RAM, disk, OS, HA node, operator, also shown in the detail panel; deployed applications: table and deploy form + runtime, image, container, compose folder, host port, HA role |
| `ApplicationsPage.tsx` | `applicationTypes` + 3 entries; deployments section + the six deployment fields |
| `src/lib/inventory.ts`, `src/lib/diagrams.ts` | `Server`, `ServerApplication`, `TopologyProxyRoute` types |
| `src/lib/buildGraph.ts` | route label `host:port/path → mappedTo` when host or port are set |

`EntitySection` fields cannot depend on each other: the runtime and HA role selects get an empty option, the container fields stay visible and the API rejects them with a native runtime. The web has no editor for proxy routes, only `/api/proxy-routes` (the Proxy section described in `docs/ux/pages.md` is not implemented): until one exists, `VirtualHost` and `ListenPort` are written through the API or SQL.

### Translations

New keys in both dictionaries of `src/lib/i18n.tsx`; `ApplicationsPage` reuses the `servers.*` keys for the deployment fields, as it already does with `servers.exposedPort`.

| Key | it | en |
|---|---|---|
| `servers.publicIp` | IP pubblico (NAT) | Public IP (NAT) |
| `servers.cpuCores` | Core CPU | CPU cores |
| `servers.memoryGb` | RAM (GB) | RAM (GB) |
| `servers.diskGb` | Disco (GB) | Disk (GB) |
| `servers.operatingSystem` | Sistema operativo | Operating system |
| `servers.haNode` | Nodo HA | HA node |
| `servers.managedBy` | Gestito da | Managed by |
| `servers.runtime` | Esecuzione | Runtime |
| `servers.runtimeContainer` | Container | Container |
| `servers.runtimeNative` | Servizio nativo | Native service |
| `servers.containerImage` | Immagine container | Container image |
| `servers.containerName` | Nome container | Container name |
| `servers.composeDirectory` | Cartella compose | Compose folder |
| `servers.hostPort` | Porta host | Host port |
| `servers.haRole` | Ruolo HA | HA role |
| `servers.haPrimary` | Primario | Primary |
| `servers.haSecondary` | Secondario | Secondary |

### Documents and generated files

- `docs/domain/data-dictionary.md`: new columns, checks, the wider `ProxyRoutes` key and the two enums in the mapping table.
- `docs/ux/pages.md`: server flow fields and the type list of the catalog flow.
- `InfraOrgITApi/openapi/InfraOrgIt.Api.json`: regenerated with `make openapi`, never edited.
- `InfraOrgITDocker/init/mysql/1-InfrastructureApps.sql`: re-exported after the migration.

### Tests

- Integration (`InventoryApiTests` and the proxy route tests): round trip of every new field; 422 on an invalid IP, non-positive sizes, unknown runtime or HA role, container fields with `Native`, ports out of range; `HostPort` equal to `ExposedPort` saved as null; the three types accepted; the same path under two virtual hosts on one connection accepted, the same host, port and path rejected with 409.
- Vitest: route label in `buildGraph.test.ts`.
- `make ci` green before merging.

## Migration

One migration, generated by EF from the model changes, never written or edited by hand. From `AllInfraOrgIT`:

```bash
source scripts/env.sh && dotnet tool restore && dotnet tool run dotnet-ef migrations add InventoryDetails --project ../InfraOrgITApi/src/InfraOrgIt.Api --startup-project ../InfraOrgITApi/src/InfraOrgIt.Api
```

Expected content, to review the generated `Up` against:

| Table | Operations |
|---|---|
| `Servers` | 7 nullable columns |
| `ServerApplications` | 6 nullable columns; checks `CK_ServerApplications_Runtime`, `CK_ServerApplications_HaRole` |
| `Applications` | drop and re-add `CK_Applications_Type` with 11 values |
| `ProxyRoutes` | 2 nullable columns; unique index on `(ProxyConnectionId, Route)` dropped and recreated on `(ProxyConnectionId, VirtualHost, ListenPort, Route)`, about 1.6 KB of key, under the 3072-byte InnoDB limit |

If the generated code differs, fix the model and regenerate. Then `make migrate`, re-export `1-InfrastructureApps.sql`, `make openapi`, `make ci`.

`Down` drops the columns and their data. It fails if rows already use the new types (old check) or if a connection has the same path under two virtual hosts (old unique index): fix those rows before rolling back.

## Backfill

The migration fills nothing: the values belong to an installation, not to the product. After `make migrate` they are entered through the UI or the API, or with SQL reviewed before running it; the installation's `3-CustomData.sql` (git-ignored) is then re-exported so a reset keeps them. Its `REPLACE INTO` statements name their columns, so a snapshot taken before the migration still loads with the new columns null.

Prefer what the hosts report over diagrams and spreadsheets, which drift.

| Field | How to read it on the host |
|---|---|
| `CpuCores`, `MemoryGb`, `DiskGb`, `OperatingSystem` | `nproc`, `free -g`, `lsblk -d -o NAME,SIZE`, `/etc/os-release` |
| `Runtime` | a `systemd` unit for the service → `Native`; listed by `docker ps` → `Container` |
| `ContainerImage`, `ContainerName`, `HostPort` | `docker ps --format '{{.Image}} {{.Names}} {{.Ports}}'`, image without the tag |
| `ComposeDirectory` | the `com.docker.compose.project.working_dir` label from `docker inspect` |
| `VirtualHost`, `ListenPort` | `nginx -T` (`server_name`, `listen`); WAF and API gateway configuration |
| `PublicIpAddress`, `HaNode`, `HaRole`, `ManagedBy` | network and HA documentation; the text now in `Hostname` |

The same pass removes each moved fact from the `Hostname` text. Installation values never go in this repository.

## Open points

1. `Servers.Hostname` still holds role notes after the backfill ("portal front end"). Add `Servers.Description` and keep `Hostname` for the real name? Not part of this proposal; it needs its own backfill.
2. Action placeholders `{{ContainerName}}`, `{{ComposeDirectory}}`, `{{HostPort}}` would let a template run `docker compose` in the right folder. Small follow-up, not included.
3. A proxy route editor in the web: separate change.
4. Virtual host and path of a local nginx in front of containers on the same server: not recorded (gap 3, rejected alternative).
5. Other products, such as Oracle or PostgreSQL: same change as gap 4 when needed.
6. One migration if every gap is approved; one per area if only some are.
