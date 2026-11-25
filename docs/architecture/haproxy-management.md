# HAProxy management inside InfraOrgIT

- Status: draft plan, not implemented
- Date: 2026-11-25
- Scope: bring HAProxy Manager capabilities into InfraOrgIT, using the Data
  Plane API and the existing inventory, RBAC, audit and UI.
- Reference: local `HAProxy Manager` repository (`manager/*.cs`,
  `manager/wwwroot/*.js`) and `InfraOrgIT` `ProxyConnection` / `ProxyRoute`
  inventory model.

## 1. Goal

One place to:

1. discover HAProxy on managed servers, propose a candidate and let the user
   choose whether to start monitoring;
2. see frontends, backends, servers, status, certificates and traffic;
3. run runtime actions (ready, drain, maint, checks, forced state, session
   shutdown) with the InfraOrgIT identity and audit;
4. edit routes, backends, servers, parameters and TCP `listen` sections with
   preview, HAProxy validation, reload wait and rollback;
5. link live HAProxy routes and projects to the existing inventory and
   diagrams.

HAProxy Manager remains the reference implementation and lab harness. It is
not run in production next to InfraOrgIT after cutover.

## 2. What already exists

| Area | HAProxy Manager | InfraOrgIT today |
|---|---|---|
| Data Plane API v2/v3 | `Nodes.cs`: per-node `HttpClient`, API auto-detect, v2 path/response normalization, stats-only mode | none |
| TLS | per-node CA file, self-signed flag, hostname always verified | SSH host-key pinning only |
| Runtime | `Program.cs:272-313`: ready/drain/maint via Data Plane API; check/forced state/shutdown through the stats page | none |
| Config | `config.js`: structured route/backend/server/parameter operations, transactions, validation, reload wait, raw `listen` patching | inventory-only `ProxyConnection` / `ProxyRoute` (`ProxyEndpoints.cs`) |
| Metrics | `Collector.cs`: stats/native or stats CSV every 60 s, 7-day retention, increments | none for HAProxy |
| Certificates | not managed; only the TLS CA used to reach the API | none |
| Userlists | masked in raw reads, restored on raw writes, structured writes blocked (`Secrets.cs`) | none |
| Autodiscovery | none; nodes are configured by hand in appsettings/UI | no software discovery. Only OS check via SSH (`ServerOsUpdateChecker`) and tunnel port discovery (`ss -tlnH`); no HAProxy detection |
| UI | vanilla `wwwroot/app.js` + `config.js`, cookie login, own users | React 19, TanStack Query, i18n, Keycloak/BFF, shared table/form components |
| Auth | local users with viewer/operator/admin | `SystemAdmin`, `ServerAdmin`, `ServerOperator` per environment |
| Audit | local `history` table | append-only `AuditEvents` with hash chain; `CommandExecutions` for remote commands |
| Inventory | projects map hostnames to a project name | `Project` has no hosts; applications/deployments have environments and hostnames |

Two route models must not be merged blindly:

- HAProxy Manager route: a live frontend ACL + `use_backend` rule
  (host, path, backend, node).
- InfraOrgIT `ProxyRoute`: an inventory intent attached to a
  `ProxyConnection` and optionally a deployment (`ServerApplication`).

The plan keeps the live HAProxy configuration as its own read model and adds
an explicit binding to the inventory route, instead of rewriting inventory
rows on every HAProxy change.

### 2.1 Reuse of existing entities

| Existing entity | Role in the HAProxy feature | Decision |
|---|---|---|
| `Provider`, `EnvironmentDefinition`, `ProviderEnvironment` | ownership, UI filters, RBAC | no duplicate; an instance reaches its environment through `Server.ProviderEnvironmentId` |
| `Server` | physical HAProxy node | required FK; `JumpServerId` + `CredentialId` are reused by discovery and by the SSH-forward transport |
| `ServerCredential` | SSH access to the node | reused for discovery and `SshForward`; **not** reused for Data Plane API credentials (different protocol and lifetime). API/stats passwords live write-only on the instance, use the same `CredentialCipher` key ring, and follow the SSH credential rule (only `SystemAdmin` sets/rotates them) |
| `ApplicationType` `HAProxy` | catalog type | already seeded (`InfraOrgItDbContext.Seed`); no new type |
| `Application` + `ApplicationVersion` | HAProxy product/deployment identity | optional link for topology and project derivation; the binary version detected by discovery stays on the instance, it does not overwrite the catalog version |
| `ServerApplication` | HAProxy deployment on the node | optional `HaproxyInstance.ServerApplicationId`; gives version, host port, environment and the existing `ProxyRouteId` link |
| `Project` + `ApplicationProject` + `ApplicationEnvironment` | project of a host | **reuse instead of a new project-host table**: normalize `ApplicationEnvironment.Hostname`, match it to HAProxy host ACLs, then derive the project through `Project.Applications`. Unmatched hosts are shown as "non associato" and imported as suggestions |
| `ProxyConnection` / `ProxyRoute` | inventory route intent | binding target for `HaproxyRouteBinding`; live HAProxy routes stay in snapshots, inventory rows are never rewritten by a reload |
| `Server.HaNode`, `ServerApplication.HaRole` | existing HA labels | display only; cluster membership is explicit (section 4.5) |
| `AuditEvents` | audit trail | reuse; one event per instance/action/config apply, no separate history table |
| `CommandExecutions` | remote command audit | not used for config writes; discovery and OS-style checks do not create a row per run |
| `TunnelService` / `TunnelSession` | user/browser tunnels | not used as the API transport; the server-side transport reuses `ISshConnector.OpenForwardAsync` (section 12) |
| `InventoryData` (data transfer) | export/import | add the new entities and cluster/member rows; never export passwords or private keys |
| `Menu` / `MenuRole` | navigation | add one HAProxy menu entry; existing role filtering stays |

`ApplicationEnvironment.Hostname` is an origin used for test calls, not a
free-form host list. Normalize it to a host before comparing; never write a
HAProxy host into it. If a host has no matching application environment, mark
it **"progetto non associato"** and require the user to act: assign an existing
project/application, create the missing application environment, or ignore the
host. The import must show the list and cannot finish silently with unmatched
hosts. A generic `ProjectHost` is a last resort only if the user confirms it;
it is not part of phase 1.

## 3. Recommended approach

Port the **domain and service layer** of HAProxy Manager into the InfraOrgIT
API, and rebuild the UI with the existing React stack.

Rejected alternatives:

- **Embed the manager as a separate service behind Caddy.** Two authentication
  systems, two databases, two audit trails, no shared RBAC.
- **Copy the manager `wwwroot` into InfraOrgIT.** It bypasses the shared
  design, i18n and query patterns, and duplicates its own login.
- **Keep the manager as the only writer and make InfraOrgIT a viewer.** The
  user asked for management inside InfraOrgIT.

Target shape:

```text
Browser (React)
  -> /api/haproxy/*            InfraOrgIT API (session, RBAC, CSRF, audit)
       -> HaproxyDiscovery     SSH read-only detection of HAProxy/Data Plane API
       -> HaproxyClient        typed Data Plane API client, per instance
       -> HaproxyMetrics       live ring + rollups + retention
       -> HaproxyPlanner       preview, diff, transaction, reload, snapshot
       -> InfraOrgIT DB        instances, metrics, plans, snapshots, bindings
  -> HAProxy Data Plane API / stats (central API or local sidecar)
```

The browser never holds Data Plane API credentials. In server mode the central
API calls the proxies. In local mode the desktop sidecar runs the same module
and calls them directly (section 12).

"Browser without credentials" means the React SPA never receives the Data
Plane API username/password, never stores them in JS/localStorage and never
talks to HAProxy directly. It calls `/api/haproxy/*`; the API decrypts the
credential, opens the HTTP/SSH transport, applies RBAC and audit, and returns
only data. This avoids CORS and browser trust of self-signed CAs, keeps
secrets out of devtools and browser storage, and makes the same UI work in
server and local mode (in local mode the caller is the localhost sidecar).

## 4. Discovery and instance registry

### 4.1 Autodiscovery

There is no existing software autodiscovery to reuse. Add a read-only
`HaproxyDiscoveryService`, separate from the OS check:

- triggers: **every hour** by default (same cadence as the OS check), plus
  **Rileva ora** in the UI; only servers with an SSH credential;
- concurrency 4, 20 s command timeout, same SSH connector and jump chain as
  the console;
- read-only script:
  - `command -v haproxy` and `haproxy -v`;
  - `systemctl is-active/is-enabled haproxy`;
  - `ps` for `haproxy` and `dataplaneapi`;
  - `ss -ltnp` to find listening ports (Data Plane API, stats page, proxy
    binds);
  - `/etc/haproxy/haproxy.cfg` readability and includes;
  - `grep` for `stats socket`, `stats listen`, `bind ... ssl crt`, `crt-list`;
  - `curl -k https://127.0.0.1:<port>/v2/info` and `/v3/info` for local
    API probing, without credentials; a `401` is enough to confirm the
    endpoint and its version.
- If the API probe succeeds on loopback, the candidate defaults to
  `Transport=SshForward` and `ApiHost=127.0.0.1`; if it is exposed on a
  reachable hostname, `Transport=Direct`.
- Do not read or store Data Plane API passwords. The API user password is
  not discoverable safely; the admin enters it once.
- Candidate instance is created/updated with `DiscoverySource=Auto`,
  `DiscoveryStatus`, `LastSeenAt`, inferred `BaseUrl`, guessed `ApiVersion`,
  optional `AllowSelfSigned` candidate, and `MonitoringChoice=Undecided`.
  Discovery **never starts monitoring**: no collector, no Data Plane API
  calls, no credentials request until the user explicitly enables it. It stays
  `CredentialsRequired` until an admin completes it.
- The UI surfaces the discovery once: server detail card, HAProxy "Rilevati"
  list and a menu badge. The user chooses **Attiva monitoraggio**,
  **Non ora** or **Ignora**; "Non ora" keeps `Undecided` but stops the prompt,
  "Ignora" sets `Disabled`. The choice can be changed later from the server
  detail or the HAProxy instance list.
- After the first choice, hourly discovery only refreshes metadata
  (`LastSeenAt`, version, endpoint, cluster suggestions). It never re-enables
  monitoring or overwrites `MonitoringChoice`.
- Priority scan: servers already used as `ProxyConnection.SourceServer`, then
  servers with a `ServerApplication` of type `HAProxy`, then all others.
- If HAProxy is installed but stopped, or only a config exists, create a
  candidate with the discovered version/config and no endpoint.
- Deduplicate by `(ServerId, BaseUrl)`; never overwrite an admin-edited
  instance URL or credentials.
- Cluster suggestion: nodes with the same frontend host/path and similar
  binds are listed as candidate members; an admin confirms the cluster.

First successful connection reads the existing configuration and fills
routes, backends, servers, certificates and parameters, so a server that
already has HAProxy is not empty in the UI. Auto-discovery of inventory
bindings is in section 10.

### 4.2 `HaproxyInstance`

All entities derive from `EntityBase` (timestamps + optimistic version).
Secrets use the existing `CredentialCipher` / `ServerAccessOptions` key ring.

| Column | Type | Notes |
|---|---|---|
| `ServerId` | int FK, required | environment/RBAC source |
| `ServerApplicationId` | int FK, nullable | optional HAProxy deployment (type `HAProxy`) |
| `ClusterId` | int FK, nullable | optional `HaproxyCluster` for multi-node apply |
| `Name` | varchar(64), unique | stable key used by metrics and plans |
| `BaseUrl` | varchar(300) | `https://host[:port]`, no userinfo/query/fragment |
| `Transport` | varchar(20) | `Direct`, `SshForward` or `DesktopRelay` |
| `ApiHost` / `ApiPort` | varchar(200)/int | target from the server's point of view when `SshForward` (usually `127.0.0.1:5555/5556`) |
| `ApiVersion` | varchar(10) | `auto`, `v2`, `v3`, `stats` |
| `Username` | varchar(100) | Data Plane API user; empty in `stats` mode |
| `EncryptedPassword` + `KeyVersion` | text/int | same scheme as server credentials |
| `StatsUsername` | varchar(100) | stats page user; optional |
| `EncryptedStatsPassword` + `KeyVersion` | text/int | optional |
| `CaPem` | text, nullable | public CA certificates, no private keys |
| `AllowSelfSigned` | bool | explicit per instance; global default `false` |
| `MonitoringChoice` | varchar(10) | `Undecided`, `Enabled`, `Disabled`; discovery never changes it after the first user choice |
| `MonitoringChangedAt` / `MonitoringChangedBy` | timestamp/text | audit of the last opt-in/opt-out |
| `Enabled` | computed | true only when `MonitoringChoice=Enabled` and credentials/transport are valid |
| `DiscoverySource` / `DiscoveryStatus` / `LastSeenAt` | text/text/timestamp | `Auto`/`Manual`, `Found`/`CredentialsRequired`/`Unreachable`/`Ready` |
| `LastTestAt`, `LastTestStatus`, `LastTestDetail` | timestamp/text | connection test result |

`BaseUrl` must be `https`, hostname verification is always enforced. For SSRF
protection the host must match the linked server address/hostname, unless an
explicit SystemAdmin override is recorded. Do not allow `http`, redirects, or
credentials in the URL.

`HaproxyCluster` (optional): name, environment, members, mode
(`active-active`, `active-passive`). It gives "apply to the cluster" a stable
meaning; without it, multi-node apply is an ad-hoc selection.

### 4.3 Live read models

- `HaproxyRouteSnapshot`: instance, frontend, bind, host, path, backend,
  default flag, raw condition, `ConfigurationVersion`, collected at.
- `HaproxyServerSnapshot`: instance, backend, server, address, status,
  check state, forced state, collected at.
- `HaproxyRouteBinding`: optional link from
  `(InstanceId, Frontend, Host, Path, Backend)` to an existing `ProxyRouteId`,
  with `Status` (`Suggested`, `Confirmed`, `Ignored`) and a note.
- `HaproxyCertificateSnapshot`: instance, storage name, path, domains,
  issuer, not_before, not_after, size, collected at. No key material.

Snapshots are rebuilt on every collection; they are not audit data.

### 4.4 Metrics

The ask is near-real-time data with a 90-day default retention. One row every
5 s for 90 days is not viable (100 series × 17,280 samples/day × 90 =
155 M rows). Use three tiers:

| Tier | Interval | Retention | Storage |
|---|---|---|---|
| Live ring | 5 s (configurable 2–60) | 1 h | memory only, latest snapshot + series |
| Raw rollup | 1 min | 7 days default | DB |
| Long rollup | 5 min | **90 days default, configurable** | DB |

- Collector interval default **5 s** for Data Plane API nodes; stats-only CSV
  nodes default **15 s** (configurable per instance).
- The collector writes one 1-minute bucket (sum of increments, gauges) and one
  5-minute bucket; it does not write a row per poll. This keeps the DB small
  while the UI sees 5 s data from the live ring. Counters are summed; gauges
  keep average/max/last as appropriate; latency averages are weighted by the
  request/session count, not summed.
- Chart resolution: ≤1 h live ring, ≤7 days 1-minute rollups, ≤90 days
  5-minute rollups. Server-side SQL aggregation/downsampling to about 100
  points.
- Storage estimate for 100 series: 1-minute/7 d ≈ 1.0 M rows, 5-minute/90 d
  ≈ 2.6 M rows. Three instances with ~300 series ≈ 11 M rows; MySQL fine.
  SQLite local mode is heavier; keep the same default but allow a lower local
  retention.
- Config: `Haproxy:MetricsIntervalSeconds=5`,
  `Haproxy:StatsOnlyIntervalSeconds=15`,
  `Haproxy:MetricsLiveMinutes=60`,
  `Haproxy:MetricsRawRetentionDays=7`,
  `Haproxy:MetricsRetentionDays=90`,
  `Haproxy:MetricsRollupMinutes=5`.
- Counter resets after reload are handled like `Collector.cs`: if a counter
  decreases, the increment is the current value; first sample after a restart
  is skipped.
- Prune in batches hourly; index `(InstanceId, Kind, Proxy, Server, Timestamp)`.
- Live endpoint serves the collector cache; it does not call the Data Plane
  API per browser client. UI polls it every 5 s while visible.

Protocol data (HTTP/2, HTTP/3, QUIC) uses a separate
`HaproxyProtocolMetricSample` table with the same `(InstanceId, Timestamp,
Kind, Proxy, Server)` key and nullable typed columns for the persisted set.
Rows are written only when protocol collection is enabled; they use the same
1-minute and 5-minute rollups. The live protocol detail is served from the
latest CSV/native cache and is never persisted field-by-field.

Comparison with the current HAProxy Manager:

| Aspect | HAProxy Manager | Proposed InfraOrgIT |
|---|---|---|
| Collection | one sample every 60 s | 5 s live (API nodes), 15 s stats-only |
| Stored detail | raw 60 s for 7 days | 1-minute rollups 7 days; 5-minute rollups 90 days |
| Live view | overview auto-refresh 30 s; metrics up to 60 s old | collector cache, UI refresh 5 s |
| Ranges | 1 h, 6 h, 24 h, 7 d | 1 h, 6 h, 24 h, 7 d, 30 d, 90 d |
| Storage per 100 series | ~1.0 M rows | ~3.6 M rows (90 days) |
| Aggregation | client-side buckets from raw rows | server-side rollups, ~100 points per chart |
| Upstream calls | ~1/min per node | ~12/min per node (API), ~4/min stats-only |
| Restart | first delta skipped | same, plus rollup buckets continue |
| Retention job | prune on each loop | batched prune hourly |

The 5 s raw data is not persisted for 90 days: that would be ~155 M rows per
100 series. The tiering keeps near-real-time live charts and 90-day history
without that cost.

### 4.4.1 What HAProxy and the Data Plane API expose

Measured on the lab (HAProxy 2.8.30, Data Plane API 3.0.28):

| Source | Fields | Notes |
|---|---|---|
| HAProxy stats CSV (`/;csv`) | **206 columns** (2 identifiers `pxname`, `svname` + 204 metrics) | richest surface; includes HTTP/2, HTTP/3/QUIC and agent checks |
| Data Plane API `GET /services/haproxy/stats/native` | **66 distinct fields** per row | strict subset of the CSV; 4 frontend, 45 backend, 56 server rows in the lab |
| Data Plane API `GET /services/haproxy/runtime/info` | **58 process fields** | version, uptime, connections, SSL, tasks, memory, threads |
| Data Plane API `GET /info` | API build/version only | not a metric source |

Native fields by area:

- traffic/sessions: `stot`, `req_tot`, `rate`, `rate_max`, `req_rate`,
  `req_rate_max`, `conn_rate`, `conn_rate_max`, `conn_tot`, `dcon`, `dses`,
  `scur`, `smax`, `slim`, `qcur`, `qmax`, `rate_lim`, `lbtot`, `wretr`,
  `wredis`, `intercepted`;
- responses/errors: `hrsp_1xx`, `hrsp_2xx`, `hrsp_3xx`, `hrsp_4xx`,
  `hrsp_5xx`, `hrsp_other`, `econ`, `eresp`, `dreq`, `dresp`, `cli_abrt`,
  `srv_abrt`;
- timing/health: `ctime`, `rtime`, `ttime`, `qtime`, `downtime`, `lastchg`,
  `lastsess`, `check_status`, `check_duration`, `check_rise`, `check_fall`,
  `check_health`, `check_desc`, `chkfail`, `chkdown`, `last_chk`, `status`,
  `weight`, `act`, `bck`, `addr`;
- bytes/compression: `bin`, `bout`, `comp_in`, `comp_out`, `comp_byp`,
  `comp_rsp`;
- identity/config: `iid`, `pid`, `sid`, `mode`, `algo`.

The other 138 CSV fields are HTTP/2, HTTP/3/QUIC, agent checks, cache,
connection-pool and max-time fields; the native endpoint does not expose
them. The protocol fields are included in the live detail and a selected subset
is persisted (below); agent/cache/max-time fields remain live-only.

Collection decision:

- **Persist a core set**, not all 66: `req_tot`/`stot`, `hrsp_1xx`…`5xx`,
  `hrsp_other`, `bin`, `bout`, `scur`, `smax`, `qcur`, `qmax`, `slim`,
  `rtime`, `ctime`, `ttime`, `qtime`, `econ`, `eresp`, `cli_abrt`,
  `srv_abrt`, `status`, `check_status`, `check_health`, `weight`, `lastsess`;
- **Persist process gauges** once per instance: `uptime`, `curr_conns`,
  `cum_conns`, `curr_ssl_conns`, `cum_ssl_conns`, `max_conn`, `sess_rate`,
  `conn_rate`, `tasks`, `run_queue`, `idle_pct`, `mem_max_mb`, `nbthread`,
  `active_peers`, `connected_peers`, `failed_resolutions`, `dropped_logs`;
- **Live only**: the full 66-field native snapshot is returned by
  `/overview/live` but not persisted;
- **Later**: HTTP/3/QUIC and cache fields, only if the estate uses them.

HAProxy Manager currently stores only 7 numeric metrics per row
(`req/stot`, 4xx, 5xx, `scur`, `rtime`, `bin`, `bout`) plus `status`; the plan
adds queues, timing breakdown, aborts, checks and process gauges without
changing the row count.

#### HTTP/2, HTTP/3 and QUIC (in scope)

These fields exist only in the CSV/runtime output, not in `stats/native`.
Enable protocol collection per instance when a QUIC bind or non-zero `h3sess`
is discovered; fetch the CSV every 15 s while core metrics stay at 5 s from
native. The CSV call is merged with the native snapshot and is not repeated per
browser client.

**Persisted (typed columns, rollup at 1/5 minutes)**

- `h2req`, `h2sess`, `h3req`, `h3sess` — protocol adoption;
- `h2_open_connections`, `h2_backend_open_streams` — HTTP/2 pressure;
- `h2_detected_conn_protocol_errors`, `h2_detected_strm_protocol_errors`;
- `quic_hdshk_fail` — handshake failures;
- `quic_dropped_pkt`, `quic_lost_pkt` — drops/loss;
- `quic_sent_pkt` — denominator for loss rate;
- `quic_retry_error` — Retry token failures;
- `quic_too_short_dgram` — Initial datagrams too short (MTU/PMTUD);
- `quic_rxbuf_full`, `quic_socket_full` — resource pressure;
- `h3_version_fallback` — HTTP/3 downgrade;
- `h3_protocol_errors_total` — aggregate computed from all `h3_*` errors;
- `quic_transp_err_total` — aggregate computed from all `quic_transp_err_*`;
- `qpack_encoder_stream_error`, `qpack_decoder_stream_error`;
- `ssl_failed_handshake`.

**Live detail (not persisted)**

- all 204 CSV fields, including every `h3_*`, `quic_*`, `h2_*`, `h1_*`,
  agent, cache, connection-pool and `*_max` field;
- the full native 66-field snapshot and the 58 process fields;
- the protocol drawer shows the H2/H3/QUIC counters grouped by adoption,
  errors, drops, resources and QPACK; raw CSV is optional for diagnostics.

**Aggregation rules**

- adoption/error/drop counters are summed;
- `h2_open_connections`, `h2_backend_open_streams`, `quic_rxbuf_full` and
  `quic_socket_full` are gauges (last/max);
- `h3_protocol_errors_total` and `quic_transp_err_total` are computed before
  storage from the individual CSV fields, so the scheme does not need 30
  columns for transport errors;
- if the CSV lacks module fields, show "not available" and suggest verifying
  `stats show-modules`; do not change HAProxy config automatically.

**Suggested alerts**

- QUIC handshake failures: ratio over `h3sess` above ~1–2% in 5 minutes, or a
  sustained increase;
- QUIC loss/drop: loss rate over `quic_sent_pkt` above the estate baseline,
  not just an absolute count;
- H3 aggregate protocol errors: sustained increase;
- `quic_rxbuf_full`/`quic_socket_full`: growth, resource saturation;
- `ssl_failed_handshake`: increase, independent of HTTP version.

### 4.5 Cluster

HAProxy is clusterable (active/active or active/passive, normally with
keepalived/VRRP and the same configuration on every node), but the manager
treats every node independently. Add an explicit cluster:

`HaproxyCluster`: id, name, provider environment, mode
(`active-active`/`active-passive`), optional VIP, notes, members
(`HaproxyInstance.ClusterId`).

- The UI can select a cluster for config apply and for bulk runtime actions.
- Config apply to a cluster uses pre-flight + canary + sequential + stop on
  error + best-effort rollback (section 8); the config is intended to be equal
  on all members.
- Runtime actions inside a cluster run independently per member; an
  active-passive cluster can default to the active node.
- Discovery only suggests candidate members (same host/path/binds); it never
  creates a cluster or changes membership automatically.

### 4.6 Monitoring opt-in UI

- Server detail, HAProxy card: when discovery finds HAProxy, show version,
  endpoint/transport and `MonitoringChoice`, with **Attiva monitoraggio**,
  **Non ora**, **Ignora**. The card remains available after the choice.
- HAProxy page, **Rilevati** tab: all candidates for environments where the
  user is `ServerAdmin`, filters by server/environment/choice, and the same
  actions. A menu badge counts `Undecided` candidates.
- HAProxy page, **Istanze** tab: per-instance toggle `Monitoraggio attivo` and
  last change; changing it calls `PUT /instances/{id}/monitoring`.
- `Undecided`: no collector, no Data Plane API calls, no credential prompt
  after "Non ora"; the candidate stays visible and hourly discovery keeps
  refreshing its metadata.
- `Disabled`: no collector/live data and the server is skipped by the hourly
  discovery scan until the user re-enables or clicks "Rileva ora"; stored
  metrics remain readable until retention, with a "monitoraggio disattivato
  dal …" banner; can be re-enabled.
- `Enabled`: if endpoint/credentials/transport are valid the collector starts
  within one interval; otherwise the instance shows `CredentialsRequired` and
  the setup form.
- Discovery never re-enables or changes the choice, and no prompt is repeated
  after the user has answered. Enabling/disabling is audited.

## 5. Permissions

The HAProxy module follows the existing server-management matrix, not a new
global read grant:

| Operation | Required role |
|---|---|
| See instance candidates and their server | `ServerAdmin` on the environment (discovery is automatic; approval is admin) |
| Read overview, routes, servers, metrics, certificate metadata | `ServerOperator` on the instance's environment |
| Runtime actions (ready/drain/maint/check/force/shutdown) | `ServerOperator` |
| Config write, preview/apply/rollback, route binding | `ServerAdmin` |
| Raw config read | `ServerAdmin` (may expose backend addresses and ACL names) |
| Instance endpoint/CA/API version/MonitoringChoice | `ServerAdmin` on the linked environment |
| Data Plane API / stats passwords | `SystemAdmin` (same rule as SSH credentials) |
| Global metrics retention/interval settings | `SystemAdmin` |

`SystemAdmin` still does not imply `ServerAdmin` (D7=B). An instance belongs
to one server/environment; users without a role on that environment see
nothing, even if the generic inventory read model is open.

Audit every mutation: instance create/update/delete/test, discovery approval,
runtime action, config preview/apply/rollback, certificate upload/delete,
binding confirm. Detail includes instance, node, config version, reload id
and result; never a password or private key.

## 6. API surface

All endpoints are under `/api/haproxy`, require the normal session/CSRF, and
return problem details. New rate-limit policies: `haproxy-read` (120/min per
user), `haproxy-action` (30/min), `haproxy-apply` (10/min).

| Method / path | Role | Purpose |
|---|---|---|
| `GET /instances` | `ServerOperator` (env) | list, no secrets |
| `POST /instances`, `PUT /{id}`, `DELETE /{id}` | `ServerAdmin` endpoint, `SystemAdmin` secrets | registry; password fields write-only and SystemAdmin-only |
| `POST /instances/{id}/test` | `ServerAdmin` | test Data Plane API, HAProxy version, stats, `Direct`/`SshForward` |
| `PUT /instances/{id}/monitoring` | `ServerAdmin` | set `Enabled`/`Disabled`/`Undecided`; start/stop collector, keep stored metrics |
| `POST /discovery/run`, `GET /discovery` | `ServerAdmin` | discover/approve candidates |
| `GET /clusters`, `POST /clusters`, `PUT /{id}`, `DELETE /{id}` | `ServerAdmin` | cluster membership and mode |
| `GET /overview/live` | `ServerOperator` | latest stats + 5 s series |
| `GET /instances/{id}/protocol/live` | `ServerOperator` | full H2/H3/QUIC CSV detail, not persisted |
| `GET /overview?range=` | `ServerOperator` | rollup chart series |
| `GET /routes`, `GET /servers` | `ServerOperator` | live snapshots with filters |
| `GET /instances/{id}/config` | `ServerAdmin` | frontends/backends/defaults/listen/raw, secrets masked |
| `GET /instances/{id}/certificates` | `ServerOperator` | metadata only, expiry |
| `POST /instances/{id}/certificates`, `PUT/DELETE /{name}` | `ServerAdmin` | upload/replace/delete combined PEM, write-only |
| `GET /metrics?instanceId=&kind=&proxy=&server=&minutes=` | `ServerOperator` | series |
| `POST /instances/{id}/server-actions` | `ServerOperator` | confirmation + audit |
| `POST /instances/{id}/changes/preview` | `ServerAdmin` | diff, warnings, TTL plan |
| `POST /changes/{planId}/apply` | `ServerAdmin` | version re-check, apply, reload, snapshot; accepts a cluster id |
| `GET /snapshots`, `POST /snapshots/{id}/rollback` | `ServerAdmin` | inspect/restore |
| `PUT /routes/{bindingId}` | `ServerAdmin` | confirm/ignore a suggested binding |
| `GET /import/preview`, `POST /import/apply` | `SystemAdmin` | one-off manager import |

## 7. Data Plane API client

Port `NodeConnection` / `NodeClient` from `manager/Nodes.cs` into
`Infrastructure/Haproxy`:

- one `HttpClient` / `SocketsHttpHandler` per instance, 10 s timeout;
- `Direct`: normal HTTPS handler with optional CA/self-signed;
- `SshForward`: `ConnectCallback` opens `ISshConnector.ConnectAsync(server)` +
  `ISshSession.OpenForwardAsync(apiHost, apiPort)`, keeps the SSH session alive
  per instance, disposes it on removal/shutdown; hostname verification still
  uses the `BaseUrl` certificate name;
- `DesktopRelay` (if enabled): same handler shape over the desktop relay;
- Basic auth, no automatic redirects (stats uses 303 with credentials in the
  URL);
- explicit CA chain or self-signed flag; hostname always verified;
- v3 native paths, v2 path/response normalization, automatic probe/fallback;
  `stats` mode is read-only;
- normalize empty collections (`null` / 404) to `[]`;
- no automatic retries on mutations; GET retries only on transient transport
  errors;
- never log Authorization, passwords, cookies, or raw config with secrets.

Keep the manager's compatibility quirks: v2 `{_version,data}` unwrapping,
flat collections with parent query parameters, runtime server paths and the
multiple-`defaults` validation.

## 8. Config change flow and multi-node

1. **Preview.** Load current config, check `Configuration-Version`, build
   operations and a line diff for every selected instance, store a
   `HaproxyChangePlan` (5 min TTL). Warnings: multiple `defaults` without
   `from`, unused backends, missing servers, changed binds, certificate
   expiry, reload impact.
2. **Pre-flight.** For a cluster/multi-selection, verify every node is
   reachable, same config version as the plan, supports the operation, and
   can validate. Abort before any write if one fails.
3. **Apply.** Re-check the version, reject drift with `409`. Structured
   changes use a Data Plane transaction per node; `listen` and rollback patch
   only the target block in raw config and run `only_validate=true` before
   writing.
4. **Reload.** Capture `Reload-ID`, poll the reload status, verify HAProxy is
   running. Store snapshots before and after.
5. **Canary / stop-on-first-error.** Recommended default: apply to one
   canary node first, wait for reload and a health check (process running,
   stats endpoint answers); then apply the remaining nodes sequentially.
   Stop on the first failure; automatically attempt to roll back the nodes
   already changed to their pre-change snapshots; report every node and any
   rollback failure. There is no distributed transaction: the Data Plane
   transaction is per node. For active-passive clusters the canary is the
   active node; config is still applied to both unless the operator chooses
   otherwise.
6. **Rollback.** Apply a stored raw snapshot with validation; never edit an
   applied snapshot.

Bulk runtime actions (ready/drain/maint/...) are independent per server and
can run in parallel with a per-server result table; config writes use the
canary/sequential rule above. A cluster is defined by `HaproxyCluster`; an
ad-hoc multi-selection shows a warning that nodes are not declared as a
cluster.

Userlist passwords: keep `Secrets.cs` masking. Reads return `********`;
raw writes restore the current password from the node when the value is still
masked. New/changed passwords are typed by an admin in a write-only field.
Structured userlist writes stay blocked. Preview shows the masked value, never
the secret.

## 9. Certificates and userlists

Findings: HAProxy Manager never manages certificates served by HAProxy; it
only uses a CA to call the Data Plane API. The Data Plane API exposes
`/services/haproxy/storage/ssl_certificates` with metadata (domains, issuer,
not_before, not_after, size), upload/replace/delete. Upload expects a combined
PEM containing the private key.

Recommendation:

- **Read-only inventory (phase 1):** list from the storage endpoint and from
  `bind ... ssl crt` / `crt-list`; show name, domains, issuer, expiry and a
  warning at 30/7 days. `GET` metadata does not return the private key.
- **Upload/replace (in scope, phase 5/6):** `POST` multipart combined PEM,
  `PUT` text/plain by storage name, `DELETE` by name, with the current
  `Configuration-Version` and reload wait. Validate before sending: PEM parses,
  contains a certificate and a private key, key matches the certificate, not
  expired, SAN/CN captured, size ≤1 MiB, no password-encrypted key in the
  first release. Never log, return or store the PEM in InfraOrgIT; record only
  metadata and SHA-256. A replace does not change the filename; a new upload is
  not referenced by a bind until a config change adds it.
- **Delete:** explicit confirmation and a warning when the certificate is
  referenced by a `bind`/`crt-list`; block or require a second confirmation.
- **Rollback:** keep certificate metadata, not the private key. Restoring an
  old certificate re-uploads the operator's PEM; an encrypted key backup, if
  required, is a separate secret-management decision.
- **Permissions:** certificate upload/replace/delete follows server config
  write (`ServerAdmin`); the PEM is write-only. Data Plane API passwords keep
  the SSH-credential rule (`SystemAdmin`).
- **Userlists:** keep the manager's masking; no structured userlist endpoint.
  Raw config writes are allowed only with preview/validation and write-only
  passwords. Exclude userlist editing from the first config-write release.

## 10. Inventory and topology binding

- Discovery fills live route/server snapshots automatically, so a server with
  existing HAProxy configuration shows its routes without manual entry.
- For each live route, try an **unambiguous** match against an existing
  `ProxyRoute` by `VirtualHost + Route + ListenPort` and target label; mark it
  `Confirmed`. If no match, create a `Suggested` binding with the best target
  from backend server addresses → inventory servers/deployments; never write
  inventory.
- Project derivation reuses `ApplicationEnvironment.Hostname` and
  `Project.Applications`; do not introduce `ProjectHost` in the first release.
  A host with no match is shown as **"progetto non associato"** and the user
  must assign it, create the missing application environment, or mark it
  ignored. The importer reports the full list; it never creates projects or
  `ProjectHost` rows silently.
- The UI shows "Suggerita" / "Confermata" / "Ignorata"; an admin can bulk
  confirm. `ProxyRoute`/`ProxyConnection`/deployment are created only by an
  explicit **Importa nell'inventario** action with preview, and only when the
  target server/application is unique. Default: suggestions only.
- Diagrams gain HAProxy edges from confirmed bindings and instance → server.
  The live read model never changes diagram edges without a binding.
- `ProxyRoute` remains curated; a HAProxy reload must not silently change
  deployment targets or diagrams.

## 11. Import from HAProxy Manager

One-off CLI under `InfraOrgITApi/tools/HaproxyImport`:

1. read `manager.db` with `--dry-run`;
2. import instances (`nodes`): name, base URL, API version, stats username,
   CA PEM, self-signed flag, transport; link by hostname/IP or explicit
   mapping; do **not** import API/stats passwords (Data Protection key ring) —
   re-enter them;
3. map manager projects/hosts to existing projects through
   `ApplicationEnvironment.Hostname` + `Project.Applications`; every unmatched
   host is listed and must be resolved or ignored by the user before
   `--apply`; `ProjectHost` is a last-resort follow-up only;
4. do not import `history` into `AuditEvents` (append-only hash chain would
   break) and do not import old metrics; export to CSV if needed;
5. preview, then `--apply`; one audit event per imported instance/project.

Cutover: import + test read-only, run in parallel for a full traffic cycle,
enable runtime actions, enable config writes, freeze the manager, retire it.

## 12. Desktop and local mode

- Primary target: the central API reaches the Data Plane API; the browser
  never holds credentials.
- Transport is part of the instance from phase 1, not a later add-on:
  - `Direct`: `BaseUrl` is reachable over HTTPS from the caller.
  - `SshForward`: the API connects through the linked server's SSH session
    (and jump chain) to `ApiHost:ApiPort`, usually `127.0.0.1:5555/5556` on
    the HAProxy node. Reuse `ISshConnector.ConnectAsync` +
    `ISshSession.OpenForwardAsync` and a persistent SSH session per instance;
    `SocketsHttpHandler.ConnectCallback` returns the forwarded stream.
  - `DesktopRelay`: implemented together with `SshForward` for a node
    reachable exclusively from the workstation; reuse the existing desktop
    tunnel relay. The browser still talks only to the API.
- Local mode: the standalone API sidecar runs the same module, does local SSH
  discovery, uses `Direct` or `SshForward` and stores credentials in the local
  encrypted store. Metrics go to SQLite while the app is open. The 90-day
  default applies; local retention is configurable because SQLite grows
  faster.
- If only the workstation can reach a proxy, local mode works; server mode
  uses `SshForward` when the API can SSH, otherwise `DesktopRelay`.
- A `stats`-only instance works without Data Plane API: overview and server
  actions from CSV/stats, no config writes.
- Local mode has no central metrics collector when the app is closed; document
  the gap.

## 13. Phases

| Phase | Deliverable | Exit criteria | Size |
|---|---|---|---|
| 0. Decisions | this plan + ADR for RBAC, clusters, binding, certificates, transport | signed off | S |
| 1. Discovery + foundation | hourly discovery, candidate opt-in UI, instance registry, Direct/SshForward/DesktopRelay client, read-only snapshots | a lab server with existing HAProxy is discovered, monitoring stays off until the user enables it, then routes/servers appear | M |
| 2. Live metrics | 5 s collector, live ring, 1/5-minute rollups, 90-day retention, H2/H3/QUIC protocol metrics and live detail, overview/charts | metrics match HAProxy on 2.4/2.8/3.2 lab; live refresh ≤5 s; protocol counters match CSV | M |
| 3. Runtime actions | ready/drain/maint/check/force/shutdown, confirmation, audit | action matrix matches manager; audit complete | M |
| 4. Config read | config endpoints, params/listen/raw, masking, certificate metadata | raw/listen/params match manager; no secret leak | M |
| 5. Config write | preview, transactions, validation, reload, snapshots, rollback, canary, certificate upload/replace/delete | route/backend/server/listen/cert changes validated; failure leaves a valid config | L |
| 6. Inventory/import | bindings, project derivation, importer, diagrams | imported data matches; suggestions confirmed; inventory not silently changed | M |
| 7. Cutover | parallel run, docs, runbook, flag removal | manager retired; rollback tested | M |

Indicative order of magnitude, one senior full-stack developer with the lab:
10–14 weeks including discovery, metrics, cluster apply and SshForward.
DesktopRelay or an HAProxy version outside the lab adds 30–50%. Not a quote;
refine with a CR after phase 0.

## 14. Testing and verification

- Unit: v2/v3 normalization, route parser, listen block patch/diff, secrets
  masking, defaults trap, server actions, metrics delta, rollup aggregation.
- API integration with a fake `HttpMessageHandler`: 401, 409 version drift,
  transaction rollback, reload timeout, TLS failure, discovery candidates.
- Disposable HAProxy + Data Plane API containers (2.9/v2, 3.0/v3 and 3.2) for
  a smoke suite; separate job if too slow for `make ci`.
- Playwright: discovery approval, overview live refresh, route action
  confirmation, config preview/apply failure, suggested binding, import.
- Migration test on a copy of `manager.db`: counts, project mapping, no
  secret in logs, no history/metrics import.
- Real-target: one lab node, one route add/remove, one runtime action, one
  rollback; verify HAProxy remains valid and serving.

## 15. Decisions and remaining questions

| Question | Decision |
|---|---|
| Read visibility | `ServerOperator` on the instance environment; raw config `ServerAdmin`; no global read |
| Multi-node apply | explicit `HaproxyCluster`; pre-flight all, canary then sequential, stop on error, best-effort rollback, no distributed transaction |
| Cluster selection | yes: select the cluster in UI; ad-hoc multi-selection warns that it is not a declared cluster |
| Inventory binding | auto-suggest from existing config; auto-confirm unambiguous matches; admin confirms the rest; explicit import creates inventory rows |
| Project mapping | reuse `ApplicationEnvironment.Hostname` + `Project.Applications`; unmatched hosts are flagged and the user must resolve or ignore them; no `ProjectHost` initially |
| Certificates | read-only inventory + upload/replace/delete in scope; combined PEM write-only, no key storage; `ServerAdmin` |
| Userlists | masked read; raw write-only password fields; no structured userlist writes |
| Data Plane API passwords | `SystemAdmin` only, same rule as SSH credentials; `ServerAdmin` can test/use but not view or rotate |
| Transport | `Direct`, `SshForward` and `DesktopRelay` from phase 1 |
| Discovery | hourly + manual "Rileva ora"; monitoring starts only after the user opts in; choice changeable later |
| Monitoring opt-in | default `Undecided` and no collector; server detail + "Rilevati" tab + instance toggle; prompted once, never auto-enabled |
| Metrics | 5 s live/1 h, 1-minute/7 d, 5-minute/90 d configurable; core subset of the 66 native fields |
| Import | instances/projects only; re-enter passwords; no history/metrics |

Remaining decisions before phase 1:

1. Confirm alert thresholds for QUIC handshake failures, dropped/lost packets
   and H3 protocol errors once the first week of data exists.
2. Confirm whether agent-check/cache/max-time CSV fields should also get a live
   drawer or stay raw-CSV-only.

## 16. First step

Vertical slice:

1. hourly discovery + `HaproxyInstance` + `HaproxyClient` (`Direct` and
   `SshForward`) + connection test;
2. read-only overview/routes/servers from an existing lab HAProxy;
3. 5 s live metrics + 1/5-minute rollups + 90-day retention;
4. RBAC, audit, i18n and tests.

Then runtime actions, config write, certificate upload and the importer.
