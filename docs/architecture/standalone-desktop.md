# Standalone desktop with a local instance

Status: **study + spike** — 2026-11-18. SQLite/local-host spike completed; desktop packaging and import/export are next.

Goal: InfraOrgIT Desktop must be usable on one machine without Keycloak,
Docker, MySQL or a remote InfraOrgIT installation. The existing remote-instance
mode stays available; the standalone mode adds a local instance that starts and
stops with the desktop app.

## Executive summary

The pragmatic option is a **self-contained .NET API sidecar** started by
Electron, backed by **SQLite** in `userData`, serving the existing Web bundle
from loopback and authenticating one local user without Keycloak. Reuse the
current inventory, SSH/tunnel, audit and MCP code; do not rewrite the product
or embed MySQL/Keycloak.

This keeps feature parity with the Web app and limits the new surface to four
areas:

1. provider-neutral EF model + SQLite migrations;
2. a `Local` host mode (SQLite session store, local session bootstrap, static
   Web files);
3. Electron sidecar lifecycle and packaging;
4. local key storage, backup/restore and migration/import.

Rough effort: **5–8 weeks for one developer** after a 3–5 day spike. Packaging
size grows by roughly 80–120 MB per platform for a self-contained .NET sidecar.
The plan includes a versioned inventory export/import from the start, because
moving existing data into the standalone instance is a first-use requirement,
not a later nice-to-have.

The main risk is not Electron: it is making 30+ MySQL migrations and the
MySQL-specific model mapping portable without changing the production schema.
A spike must prove that before the rest is planned in detail.

## Current architecture and blockers

Today the desktop is a shell around a remote instance:

- `InfraOrgITDesktop` opens a URL in a `WebContentsView` and reuses the BFF
  session (`electron/main.js`).
- `InfraOrgITWeb` is a static SPA served by Caddy; every API call is same-origin
  (`/api`, `/auth`, `/mcp`).
- `InfraOrgITApi` is ASP.NET Core with `MySql.EntityFrameworkCore`, OIDC/JWT,
  the BFF session handler and MySQL-backed sessions.
- Keycloak provides login, roles in tokens and the desktop device flow.
- Docker Compose supplies MySQL, Keycloak, the API and Caddy.

Blocking assumptions for a local instance:

| Area | Current assumption | Needed for standalone |
|---|---|---|
| Database | `ConnectionStrings:MySql`, `UseMySQL` (`Program.cs:49`) | SQLite provider and migrations |
| Sessions | `MySqlSessionStore` uses `GET_LOCK`/`DO RELEASE_LOCK` | SQLite/in-process session store |
| Login | `OidcOptions` validated at startup; `/auth/login` redirects to Keycloak | Local bootstrap session; OIDC optional |
| Web origin | Caddy serves `/srv` and proxies `/api` | API serves the SPA or a local proxy |
| Instance URL | Remote HTTPS; loopback HTTP allowed by `normalizeInstanceUrl` | Local loopback instance is accepted; packaged policy must allow it explicitly |
| Secrets | API credential key from config; desktop uses `safeStorage` | Electron generates/decrypts the key and passes it to the sidecar |
| Data migration | Remote inventory has no portable export | Versioned JSON export/import with dry-run and credential metadata |
| Packaging | Electron only | Sidecar binary plus Web `dist` in the app bundle |
| Updates | Replace the Electron app bundle | Already atomic; sidecar is inside the bundle |

Relevant code:

- `InfraOrgITApi/src/InfraOrgIt.Api/Program.cs` — provider, auth and OIDC
  validation, health checks.
- `InfraOrgITApi/src/InfraOrgIt.Api/Infrastructure/Persistence/InfraOrgItDbContext.cs`
  — MySQL column types (`longtext`, `json`, `datetime(6)`) and check
  constraints.
- `InfraOrgITApi/src/InfraOrgIt.Api/BuildingBlocks/Auth/MySqlSessionStore.cs`
  — MySQL lock and session table.
- `InfraOrgIt.Web` `Caddyfile` — single-origin static + proxy contract.
- `InfraOrgITDesktop/electron/main.js` — instance partitions, tunnel manager,
  credential vault and updater.

## Options

### A. .NET sidecar + SQLite (recommended)

Electron starts a self-contained `InfraOrgIt.Api` binary on `127.0.0.1` with a
random port and a bootstrap secret. The API uses SQLite, serves the Web bundle
and exposes the same endpoints. Electron creates a local instance tab pointing
at that loopback origin.

**Pros:** reuses all domain, RBAC, SSH, tunnel, audit and MCP code; same Web UI;
no Docker; one data file; backup is a file copy; remote mode unchanged.

**Cons:** .NET runtime/binary size; two processes; provider-neutral data layer
work; local auth has to be designed carefully.

### B. Desktop-only local manager

Implement inventory and tunnels in the Electron manager with a JSON/SQLite
store and no Web app.

**Pros:** small runtime, fast start.

**Cons:** duplicates the entire product; loses audit, diagrams, MCP, API tests,
file browser and most UI; divergence grows immediately. Rejected.

### C. Bundle MySQL + Keycloak

Ship both services in Docker or as local binaries.

**Pros:** no code changes.

**Cons:** defeats “standalone”; huge install, ports, upgrades, backups and
security surface; Keycloak still needs a realm and admin bootstrap. Rejected.

### D. Rewrite the API in Node/Electron

Move the domain into the main process.

**Pros:** one process.

**Cons:** rewrite of a tested .NET backend, EF model, migrations, MCP server and
SSH stack. Rejected.

## Recommended architecture

```text
┌──────────────────────────── Electron ────────────────────────────┐
│ manager window + instance tab (WebContentsView)                  │
│   │                                                              │
│   ├─ local instance: http://127.0.0.1:<port> (persist partition)  │
│   ├─ remote instances: existing HTTPS URLs                       │
│   └─ sidecar supervisor: spawn, health, logs, stop, restart      │
│          │                                                       │
│          ▼                                                       │
│   InfraOrgIt.Api --local (self-contained .NET)                   │
│     ├─ SQLite: userData/standalone/infraorgit.db                 │
│     ├─ Web bundle: resources/web (served same-origin)            │
│     ├─ local session bootstrap + CSRF                            │
│     └─ SSH/tunnels/audit/MCP as today                            │
└──────────────────────────────────────────────────────────────────┘
```

Electron owns the process lifecycle and the OS key material. The sidecar owns
the data and never opens a network listener beyond loopback.

### Host mode

Add `Local:Enabled` and `Database:Provider=Sqlite`:

- `Program.cs` selects `UseSqlite(connectionString)` when the provider is
  `Sqlite`; production keeps `UseMySQL`.
- `/api/session`, `/api/session/theme`, menus, roles and the Web UI work
  unchanged once a local session exists.
- `/auth/login` and `/auth/desktop-session` return `404` or a local-mode error;
  the SPA never reaches them because the local session is already present.
- `Mcp:Oidc` stays empty in local mode; personal API tokens continue to work.
  OAuth discovery endpoints are not mapped when no OIDC authority is set.
- Audit anchor and OpenTelemetry stay opt-in; local mode defaults them off.

### Local Web hosting

The sidecar serves the SPA from `Local:WebRoot` (packaged `web/` directory)
with `UseDefaultFiles`, `UseStaticFiles` and a fallback to `index.html` for
client routes. This keeps one origin and avoids CORS, custom protocols and a
second static server. The existing security headers move from Caddy into the
API middleware for local mode (or the API serves the same headers).

Alternative if serving static files in the API is unwanted: an Electron
`protocol.handle("https://app.local")` handler serving the same bundle and
proxying `/api` to the sidecar. It is more moving parts; not preferred for the
first iteration.

### Local authentication and session bootstrap

Single-user local mode does not need a login screen:

1. Electron starts the sidecar with a random `INFRAORGIT_LOCAL_BOOTSTRAP`
   secret (never written to disk) and a loopback-only URL.
2. Electron calls `POST /auth/local/session` through the instance partition with
   that secret. The API creates or extends a session for the fixed local user
   and sets the normal HttpOnly session cookie.
3. The SPA loads; `/api/session` returns the session and CSRF token. All
   existing CSRF and origin checks stay enabled.
4. The local user has `SystemAdmin`, so the initial environment, provider,
   credentials and servers can be created from the UI.

The bootstrap endpoint is anonymous only in the sense that it does not require
a cookie; it must require the per-launch secret, bind to loopback and be rate
limited. The local OS account is the trust boundary. No local password is
stored. If a password is later desired, it can be a local-only unlock screen,
not a Keycloak replacement.

Open design point: whether the local session should be persistent across
restarts (session row in SQLite, cookie in the partition) or recreated on every
launch. Recommendation: persist it, but rotate the bootstrap secret each
launch; revoke it on logout.

### Database and migrations

SQLite is the only realistic embedded store. The domain uses no MySQL-only
queries except `MySqlSessionStore`; the schema does use MySQL column types and
migration DDL.

Plan:

- Move provider-specific mappings out of `OnModelCreating` into conditional
  configuration: `longtext`, `json` and `datetime(6)` become provider-specific
  or generic (`TEXT`, ISO timestamps).
- Add `Microsoft.EntityFrameworkCore.Sqlite` and a second migrations assembly
  or a `Migrations/Sqlite` folder with its own snapshot.
- Keep the MySQL migrations frozen and generate SQLite migrations from the same
  model. Verify schema parity with a table/column diff in CI.
- Replace `MySqlSessionStore` with `LocalSessionStore` (EF + `SemaphoreSlim`)
  selected by provider; keep the same `ISessionStore` contract.
- Enable WAL, `busy_timeout`, foreign keys and a single writer. The desktop is
  single-user, so contention is minimal.
- Store the DB at `userData/standalone/infraorgit.db`. Keep it outside the app
  bundle so updates never touch data.

Do not use `EnsureCreated`: it bypasses migrations, seed data and future
upgrades. If SQLite migrations prove too costly, a fallback is a versioned
schema initializer owned by the sidecar; that is a deliberate compromise, not
the default.

### Credential key and secrets

The API encrypts SSH credentials with AES-GCM keys
(`ServerAccess:CredentialKeys`). In local mode:

- Electron generates a 32-byte key on first run and stores it encrypted with
  `safeStorage` (Keychain/DPAPI/Secret Service).
- On each sidecar start Electron decrypts the key and passes it through the
  child environment (`ServerAccess__CredentialKeys__1`,
  `ServerAccess__CurrentKeyVersion=1`).
- If `safeStorage` is unavailable, the key stays in memory for that run and the
  app warns that credentials will not survive a restart. This mirrors the
  existing token-store behavior.
- Backups contain the encrypted credential ciphertext; the key is not in the
  backup. Exporting to another machine requires a key export or re-entering
  credentials. This must be explicit in the backup UI.

### Backups, export and import

Three different needs must not be confused:

| Need | Contains | Portable | Restore target |
|---|---|---|---|
| **Full local backup** | SQLite DB, encrypted credential ciphertext, local settings, audit | Only with the device key | Same machine/key |
| **Inventory export** | Canonical JSON of inventory, diagrams and projects; credential metadata, no secrets | Yes | Empty or `replace` local DB |
| **Remote-to-local migration** | Inventory export produced by a remote instance | Yes | First standalone import |

#### Inventory export format

Use one JSON document (`.infraorgit.json`, optionally gzip later) with a stable
envelope and synthetic `ref` keys, never database IDs:

```json
{
  "format": "infraorgit.inventory",
  "formatVersion": 1,
  "productVersion": "0.3.15",
  "exportedAt": "2026-11-18T17:00:00Z",
  "source": { "mode": "remote", "name": "Acme" },
  "counts": { "providers": 3, "servers": 42, "applications": 12 },
  "checksum": "sha256:...",
  "data": {
    "providers": [{ "ref": "provider:acme", "name": "Acme", "...": "..." }],
    "environmentDefinitions": [],
    "providerEnvironments": [],
    "servers": [],
    "applications": [],
    "applicationVersions": [],
    "serverApplications": [],
    "projects": [],
    "proxyConnections": [],
    "proxyRoutes": [],
    "tunnelServices": [],
    "commandTemplates": [],
    "diagrams": [],
    "diagramScopes": []
  },
  "credentialRefs": [
    {
      "ref": "credential:acme-deploy",
      "name": "Acme deploy key",
      "username": "deploy",
      "authType": "PrivateKey",
      "owner": "shared"
    }
  ],
  "warnings": []
}
```

Rules:

- `ref` is generated by the exporter (for example `server:prd-app-01`) and is
  unique inside the file. The importer creates new database IDs and maps
  relationships through `ref`.
- `checksum` is SHA-256 over the canonical UTF-8 JSON of `data` and
  `credentialRefs`; the importer verifies it before validation.
- Exported fields follow the public API DTOs; secrets, passwords, passphrases,
  API tokens, sessions, devices, MCP agents/permissions and audit rows are
  **never** included.
- Credential metadata is included so the importer can show unresolved
  references. Imported servers keep `CredentialId=null` and a warning lists
  which credentials must be created/downloaded again. Personal credentials are
  omitted; shared credentials keep name, username and auth type only.
- Menus, roles and the local user are not imported. The standalone host seeds
  its own local SystemAdmin and built-in menu/policy; custom menu labels can be
  a separate settings export later.
- Diagram nodes, positions, scopes and proxy routes are included; layout IDs are
  remapped. File attachments do not exist in the model today.
- The export is audited as `DataExport` with counts and source mode, but the
  audit log itself is not exported.

#### Import modes and validation

Start with two modes:

- **replace** (v1): import into an empty local database or after an explicit
  wipe confirmation. This is the remote-to-standalone path. The sidecar writes
  an automatic SQLite backup before the transaction and rolls back on failure.
- **merge** (post-v1): match by natural keys and update, skip or rename
  conflicts. Keep it out of the first release; a bad merge is harder to undo
  than an empty-database import.

The import flow is always: parse → verify checksum → validate schema and limits →
dry-run summary → confirm → backup → transaction → audit → refresh.

The **export** side is provider-independent and should ship on the current
MySQL API first; it is small, useful on its own and lets users prepare the file
before the standalone build exists. The SQLite importer is then tested against
that same format.

Natural keys for the future merge mode:

| Entity | Key |
|---|---|
| Provider | `Name` |
| Environment definition | `Name` |
| Provider environment | provider + environment |
| Server | environment + `Name` |
| Application | `Name` |
| Application version | application + `VersionNumber` |
| Server application | server + version + exposed/host port |
| Project | `Name` |
| Proxy connection/route | source + target + virtual host + listen port + route |
| Tunnel service | server + `Name` |
| Command template | `Name` (plus server when scoped) |
| Diagram | `Name` + scope |

Validation and safety:

- Only `SystemAdmin`; CSRF and Origin checks stay mandatory; the endpoint is
  rate limited.
- Cap file size (for example 20 MB) and entity counts; reject unknown
  `formatVersion` majors and duplicate refs.
- Validate every string with the same `Guard` limits as the API, reject
  references to missing refs, and never accept absolute paths or URLs that are
  not part of the model.
- Dry-run produces counts, conflicts and unresolved credential refs without
  writing. The UI must show them before the confirm button.
- Import runs in one transaction; the pre-import backup is kept until the next
  successful import.
- Import/export endpoints work in both remote and local modes, so an existing
  installation can produce the file and the standalone app can consume it.
- Full local backup stays a separate action: it copies the SQLite DB (after a
  WAL checkpoint) plus a manifest, and does not pretend to be portable because
  it still needs the device key for credentials.

#### Import/export API surface

- `GET /api/data/export` → JSON download (`Content-Disposition`), SystemAdmin.
- `POST /api/data/import` → dry-run summary and short-lived import token,
  SystemAdmin, multipart file or JSON body; never writes inventory.
- `POST /api/data/import/confirm` with an import token and `mode=replace` →
  applies the validated file after a backup. The token is short-lived (for
  example 10 minutes), one-use, bound to the user and file checksum, and refers
  to a server-side validated payload; the client does not re-upload or edit it.
- `GET /api/data/export/status` optional if exports become asynchronous; v1
  can keep it synchronous with the size cap.
- The Web UI adds **Data** (or **Backup**) under administration with Export,
  Import, dry-run review and the credential-unresolved warning.
- Audit actions: `DataExport`, `DataImport`, `DataImportRejected`.

Testing:

- Golden fictitious export fixture (Acme) round-trips: export → import into an
  empty SQLite DB → canonical counts and relationship hashes match.
- Dry-run writes nothing; malformed checksum, duplicate refs, missing refs,
  oversize files and unknown format versions are rejected.
- No secret fields appear in the export (test asserts absence of password,
  passphrase, token, private key markers).
- Import rolls back on the first failure and leaves the pre-import backup.
- E2E: export from the remote local stack, import into a standalone data
  directory, verify a server, diagram layout and unresolved credential warning.

### Packaging and lifecycle

- Publish the API per target RID:
  `dotnet publish -c Release -r osx-arm64 --self-contained` (and osx-x64,
  win-x64, linux-x64).
- Put the publish output under `Contents/Resources/api/` (macOS) or the
  platform equivalent, and the Web `dist` under `Resources/web/`.
- Electron picks a free loopback port, spawns the sidecar with a per-launch
  bootstrap secret, waits for `/health/live`, then creates/opens the local
  instance. On quit, send SIGTERM/`taskkill` and wait; the updater already
  swaps the whole app bundle atomically.
- Sidecar logs go to `userData/logs/api.log`, rotated by size. A crash restarts
  the sidecar once, then shows an actionable error in the manager.
- The local instance is a normal instance record with a reserved URL/name; it
  cannot be removed while standalone mode is active. Remote instances remain
  unchanged.
- Packaging may need `extraResource` in `@electron/packager`; build time and
  artifact size grow. Verify on all four targets before release.

### Security model

- Bind only `127.0.0.1`; never `0.0.0.0`. No LAN firewall exception.
- Per-launch bootstrap secret; random port; no secret in URLs or logs.
- Keep CSRF, Origin checks, HttpOnly cookie, CSP and frame denial. For loopback
  HTTP set `Auth:SecureCookies=false` only in local mode; production remains
  HTTPS with `__Host-` cookies.
- The local OS account is the authentication boundary. Document that a shared
  OS account or malware running as the same user can read the app data.
- The sidecar must reject non-loopback requests even if a proxy is configured.
- MCP remains local; personal tokens are stored as today. OAuth/Keycloak
  discovery is absent in local mode.
- Code signing is still required for a trustworthy desktop distribution; the
  unsigned build warning remains.

### Migration path from remote to local

Out of scope for the first standalone release. Users can recreate inventory or
use a future JSON import. A direct MySQL-to-SQLite migration would require a
schema/type converter, credential rewrap and ID preservation; estimate it as a
separate item after the local mode is stable.

## Test strategy

- API unit/integration tests run against both providers for the subset that
  touches the DB; keep the existing Testcontainers MySQL suite as the
  production gate.
- Add SQLite integration tests: migrations on an empty file, seed roles/menu,
  session create/expire/revoke, credential encrypt/decrypt, audit chain.
- Desktop unit tests: sidecar supervisor (port, secret, health timeout, crash
  restart, quit), local instance creation, data directory paths.
- Web tests: no changes expected; add a mocked local session bootstrap.
- E2E: start the packaged app (or test harness) with a temporary `userData`,
  create a provider/server, open a console against a fake SSH server, restart
  and verify data + session survive.
- CI: matrix packaging of the sidecar per RID; verify the sidecar starts and
  `/health/live` is 200 from a smoke script.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| MySQL-specific model/migrations resist SQLite | high | Spike first; provider-neutral mappings; separate migrations; schema diff test |
| Sidecar size/startup | medium | Self-contained publish; measure; consider trimming (EF may limit) |
| Local auth/CSRF gaps | high | Bootstrap secret, loopback bind, keep CSRF/Origin, security review |
| Credential key loss | high | safeStorage key + explicit backup warning; never silently regenerate |
| Two-process lifecycle bugs | medium | supervisor state machine + tests; one restart then clear error |
| Packaging/signing complexity | medium | build sidecar per RID in the publish workflow; sign/notarize the whole bundle |
| Feature expectations | medium | publish a scope table: local mode parity, import/export and MCP limitations |

## Phased plan and effort

| Phase | Work | Estimate |
|---|---|---|
| 0. Spike | SQLite provider + conditional mappings + one migration; start API on SQLite; local session bootstrap; serve Web `dist`; one E2E smoke | 3–5 days |
| 1. Data layer | Full SQLite migrations, session store, seed/versioning, backup/restore primitives, dual-provider tests | 5–8 days |
| 2. Local host/auth | `Local` config, bootstrap endpoint, cookie/CSRF, static hosting, health/logging, disable OIDC paths | 4–6 days |
| 3. Desktop integration | Sidecar supervisor, port/secret, local instance, quit/crash handling, settings/data paths | 4–6 days |
| 4. Secrets and backup | safeStorage key handoff, corruption/rotation, full local backup/restore UI, tests | 3–5 days |
| 5. Import/export | versioned JSON format, export from remote, dry-run/confirm, replace import, credential unresolved report, round-trip tests | 4–6 days |
| 6. Hardening/release | Security review, tests, dual-provider CI, packaging all RIDs, docs, clean-machine checks | 4–6 days |
| **Total** | | **27–42 dev days** |

Add signing/notarization and a clean-machine test matrix as release dependencies,
not as part of the estimate.

## Spike acceptance criteria

The spike is successful only if all of these pass on a developer machine:

1. A self-contained API starts with `Database:Provider=Sqlite` on a fresh
   `userData` directory and applies SQLite migrations without MySQL.
2. Roles, menu and connection policy seed correctly; a local session can call
   `/api/session` and create a provider, environment, server and credential.
3. The Web bundle loads from the sidecar origin; login is bypassed with the
   bootstrap secret; CSRF still rejects a mutation without the token.
4. A Client tunnel and an SSH console work from the local instance against the
   fake SSH fixture.
5. The app survives a restart with data and the local session intact; the API
   stops when Electron quits.
6. No production MySQL migration or schema is changed.
7. The packaged macOS arm64 app starts the sidecar from `Resources` and passes
   the same smoke test.

If criterion 1 or 6 fails, stop and revisit the provider strategy before
writing desktop integration code.

## Spike results (2026-11-18)

The API spike is on branch `spike/standalone-sqlite` and proves the core path:

- Added the SQLite provider and a derived `SqliteInfraOrgItDbContext` with its
  own migration set; the MySQL model/schema is unchanged.
- The first generated SQLite migration failed on `CHAR_LENGTH` in the audit
  hash check. The check constraint now uses `length` only for SQLite.
- Runtime registration must resolve the base context to the derived instance
  (`AddDbContext<Sqlite...>` + a scoped `InfraOrgItDbContext` alias); otherwise
  EF looks for the base migration set and applies nothing.
- Local mode starts the API entirely on SQLite, applies the migration, serves
  the Web `dist` from the same origin, creates a local SystemAdmin session with
  the bootstrap secret and accepts a CSRF-protected provider create.
- The static Web root conflicts with the existing `GET /` API info endpoint;
  local mode must leave `/` to the SPA.
- Existing MySQL unit and integration suites (63 + 108) stay green.

Still open from the spike acceptance list:

- Electron sidecar supervisor and packaged app;
- local tunnel/console smoke against the fake SSH fixture;
- import/export implementation and round-trip fixture;
- local mode should skip OIDC option validation and the Keycloak readiness
  check instead of requiring dummy OIDC settings.

## Implementation update (2026-11-18)

The first implementation slice is on the spike branches:

- API: versioned `.infraorgit.json` export and `replace` import with checksum,
  validation, dry-run token, pre-import SQLite backup and credential metadata.
  Tests: three SQLite integration tests cover round-trip, tampered checksum and
  missing data; MySQL suites stay green.
- Desktop: **Impostazioni → Istanza locale** (or `DESKTOP_STANDALONE=1`)
  starts the self-contained API on a free loopback port, stores
  SQLite/backups under `userData/standalone`, injects the local session into
  the instance partition, creates the **InfraOrgIT locale** instance and stops
  the sidecar on quit. The supervisor retries a crashed sidecar once.
- Packaging: `package.js --api-dir --web-dir` copies `Resources/standalone` and
  `Resources/web`; `publish.yml` checks out API/Web sources, publishes the API
  per target RID and builds the Web bundle.
- Verified on a packaged osx-arm64 app with a temporary `userData`: SQLite
  migration, local user/session, SPA served from the sidecar and
  `/api/menus` 200. Uncompressed app ~681 MB, sidecar ~158 MB.
- Local SSH smoke against a disposable sshd from the SQLite API with a password
  credential: reachability returned `reachable=true`; the console-start audit
  path is the same endpoint used by the desktop. Linux and Windows sidecars and
  Web resources were staged successfully in addition to macOS arm64/x64.

**Go/no-go: GO**, conditional on these entry gates for the production slice:

1. local SSH tunnel and console smoke against a disposable SSH target;
2. import/export Web UI and a golden round-trip test (API round-trip now
   covered by three SQLite integration tests; UI still pending);
3. signed/notarized package on a clean machine;
4. four-target package matrix (Linux and Windows staging already packaged
   manually; CI matrix still to run).

No schema or MySQL production path regression was found. The remaining work is
the Electron/API wiring review, security review of the loopback bootstrap and
the release packaging gate.

## Open decisions

- Persist the local session or recreate it on every launch? (Recommendation:
  persist, rotate bootstrap secret.)
- Is the first standalone release single-user only? (Recommendation: yes.)
- When to add **merge** import; v1 ships `replace` into an empty database only.
- Whether a full local backup may export the credential key for cross-machine
  restore, or stays tied to the device key.
- Where to store the credential key when `safeStorage` is unavailable: block
  local credential use or keep it in memory only.
- Whether to ship a reduced MCP surface in local mode or keep it identical.
- Whether to sign the sidecar separately or rely on the signed/notarized app
  bundle.

## References

- `../backlog.md` — standalone desktop item.
- `mcp-server-and-tunnels.md` — existing tunnel/MCP design.
- `../adr/012-electron-desktop-shell.md` — Electron shell decision.
- `../adr/013-connection-policy.md` — transport policy.
- `../../InfraOrgITApi/src/InfraOrgIt.Api/Program.cs`
- `../../InfraOrgITApi/src/InfraOrgIt.Api/Infrastructure/Persistence/InfraOrgItDbContext.cs`
- `../../InfraOrgITWeb/Caddyfile`
- `../../InfraOrgITDesktop/electron/main.js`

## Verification 2026-11-19

- `make ci` green: API 63 unit + 111 integration, Web 228 tests, OpenAPI
  regenerated without drift, Compose config and Redocly valid.
- `make desktop-ci` green (85 unit) and the Electron shell test PASS.
- `make e2e` green against the full stack (10/10).
- Real SSH smoke on the desktop code path: `runCommand`, `openShell` and the
  ssh2 Local tunnel against a disposable sshd with a password credential
  returned `console-ok`, `shell-ok` and the SSH banner through the forwarded
  local port.
- GitHub `publish` workflow run `44423613579` completed on osx-arm64, osx-x64,
  win-x64 and linux-x64; every artifact contains
  `Resources/standalone/InfraOrgIt.Api` and `Resources/web/index.html`.
  The manual run packaged API/Web `main`, so it validates the packaging path,
  not the spike runtime; a functional standalone release still requires the
  API/Web changes to be merged/tagged.
- `v0.3.17` published. The osx-arm64 artifact was launched with a fresh
  `userData`: SQLite sidecar healthy, local user created, SPA loaded, local
  instance tab opened, no crash report. GHCR API/Web `0.3.17` manifests and the
  four desktop release archives are present.
- Still not verifiable here: signed/notarized clean-machine install (no
  certificates configured) and the Web import/export page (not implemented).
