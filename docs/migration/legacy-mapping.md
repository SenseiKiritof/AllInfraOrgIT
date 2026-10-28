# Legacy → new schema mapping

Legacy source: MySQL 9.5, legacy schema and EF migration. Target: MySQL LTS, EF Core schema. Importer: `InfraOrgITApi/tools/LegacyImport`, Phase 7.

## Strategy

- **IDs preserved** for all entities: the diagrams reference `EntityId` and must not be remapped.
- Same engine (MySQL → MySQL); no SQL conversion.
- Table/column names unchanged except for the listed exceptions.
- Idempotent import per class, in a transaction; re-runnable in dry-run.
- No production data in the repos: sanitized fixtures.

## Table mapping

| Legacy | New | Transformation |
|---|---|---|
| `Environments` | `EnvironmentDefinitions` | table/entity rename; `Id` preserved |
| `Providers` | `Providers` | none |
| `ProviderEnvironments` | `ProviderEnvironments` | `EnvironmentId` → `EnvironmentDefinitionId` |
| `Servers` | `Servers` | + audit; `CredentialId`, `HostKeyFingerprint`, `SshPort` unchanged |
| `ServerCredentials` | `ServerCredentials` | + `KeyVersion`, `NeedsReauth`; secret re-encrypted |
| `ServerApplications` | `ServerApplications` | + audit; `ProxyRouteId` preserved |
| `Applications` | `Applications` | + audit |
| `ApplicationVersions` | `ApplicationVersions` | + audit |
| `ApplicationVersionApis` | `ApplicationVersionApis` | `RequestTypeEnum` int → string; + audit |
| `ApplicationApiQueryParams` | `ApplicationApiQueryParams` | `ParamType` int → string; + audit |
| `Projects` | `Projects` | + audit |
| `ApplicationProject` | `ApplicationProject` | join unchanged |
| `ProxyConnections` | `ProxyConnections` | `CreatedAt` preserved; + `UpdatedAt`, `Version` |
| `ProxyRoutes` | `ProxyRoutes` | none; optional targets preserved |
| `Diagrams` | `Diagrams` | `CreatedAt` preserved; + `UpdatedAt`, `Version`; `IsDefault` unchanged |
| `DiagramScopeItems` | `DiagramScopeItems` | `ScopeType`, `EntityId` unchanged |
| `DiagramNodes` | `DiagramNodes` | coordinates/handle unchanged; + audit |
| `DiagramEdges` | `DiagramEdges` | target/handle/bend unchanged; + audit |
| `Users` | `Users` | `Username` normalized to lowercase; + audit |
| `Groups` | `Groups` | `Name` `longtext` → `varchar(200)`; + audit |
| `Roles` | `Roles` | `ScopeEnum` int → string; + audit |
| `GroupUser` | `GroupUser` | join unchanged |
| `RoleUser` | `RoleUser` | join unchanged |
| `Menus` | `Menus` | + audit; `ParentId` preserved |
| `MenuRole` | `MenuRole` | join unchanged |
| `ProviderEnvironmentGroupRoles` | `ProviderEnvironmentGroupRoles` | + audit; dedupe if necessary |
| `CommandTemplates` | `CommandTemplates` | + audit |
| `ApplicationActions` | `ApplicationActions` | `ParameterValues` longtext JSON → JSON; + audit |
| `ReachabilityTests` | `ReachabilityTests` | + audit |
| `CommandExecutions` | `CommandExecutions` | no FK; script/output redacted |
| `__EFMigrationsHistory` | new EF history | not imported |

## Enums

| Legacy (int) | New (string) |
|---|---|
| `QueryParamTypeEnum`: 0,1,2,3,4,5 | `Int`, `String`, `Bool`, `DateTime`, `Double`, `Decimal` |
| `RequestTypeEnum`: 0,1,2,3,4 | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `RoleScopeEnum`: 0,1 | `System`, `Environment` |

Enums already stored as strings (`ProxyDirection`, `CredentialAuthType`, `CommandExecutionKind`, `DiagramScopeType`, `DiagramNodeType`) remain unchanged.

## New fields

- `CreatedAt`/`UpdatedAt`: for imported rows use the legacy timestamp if it exists (`Diagrams.CreatedAt`, `ProxyConnections.CreatedAt`, `CommandExecutions.StartedAt`); otherwise the import instant. `UpdatedAt = CreatedAt`.
- `Version = 0`.
- `ServerCredentials.KeyVersion = 1`; `NeedsReauth = false` if the secret was re-encrypted.
- `EnvironmentDefinitions` keeps `Id`, `Name`, `Description`.

## Credentials

1. The old `ServerAccess:CredentialKey` key is only used by the importer: never print it, never store it in the new repos.
2. Decrypt `EncryptedSecret` and `EncryptedPassphrase` with legacy AES-GCM.
3. Re-encrypt with the new key and `KeyVersion = 1`.
4. If decryption fails or the key is missing: `EncryptedSecret = ''`, `EncryptedPassphrase = NULL`, `NeedsReauth = true`; the server stays imported and the user re-enters the secret.
5. The import does not log plaintext, ciphertext or key fragments. The report only counts `migrated`/`needs_reauth`.

## Diagrams

- `EntityId` is not remapped: every node/scope/edge points to the preserved legacy ID.
- `DiagramScopeItem.ScopeType = ProviderEnvironment` carries the `EnvironmentDefinition.Id` (formerly `EnvironmentEntity.Id`), not the `ProviderEnvironment.Id`. Verify with a consistency query.
- The global view becomes a diagram with `IsDefault = true`; no id `0`.
- `DiagramNode` and `DiagramEdge` may reference entities that no longer exist: the importer produces an orphan report; the decision is to block the import or drop the node, not to invent an ID.
- `ApplicationAction.ParameterValues` may contain secrets: do not log the values; the execution audit uses the redacted script.

## Order and validation

1. Reference: `EnvironmentDefinitions`, `Providers`, `ProviderEnvironments`, `Menus`, `Roles`.
2. Identity: `Users`, `Groups`, `GroupUser`, `RoleUser`, `ProviderEnvironmentGroupRoles`.
3. Catalog: `Applications`, `ApplicationVersions`, `ApplicationVersionApis`, `ApplicationApiQueryParams`, `Projects`, `ApplicationProject`, `CommandTemplates`, `ApplicationActions`.
4. Inventory: `ServerCredentials`, `Servers`, `ServerApplications`, `ProxyConnections`, `ProxyRoutes`, `ReachabilityTests`.
5. Diagrams: `Diagrams`, `DiagramScopeItems`, `DiagramNodes`, `DiagramEdges`.
6. Audit: `CommandExecutions` (redacted).

Blocking validation:

- per-table counts equal to legacy (minus the rows dropped with a reason);
- orphan FKs = 0;
- uniques respected (username, provider×environment, role×group×environment);
- every `DiagramScopeItem`/`DiagramNode`/`DiagramEdge` has an existing target or is in the report;
- diagram render after the import;
- credentials: `migrated` + `needs_reauth` count = total;
- checksum of key fields (name, IP, hostname, coordinates).

## Cutover

1. Freeze legacy writes.
2. Snapshot and delta import.
3. Smoke test: login, inventory, legacy diagrams, console on a test server.
4. DNS / reverse proxy switch.
5. Old system read-only for rollback; rollback to the previous `versions.lock` if the smoke tests fail.

## Open points

- Reliable export of the legacy dataset: it is git-ignored and is kept outside the repository; an approved dump is needed, not copied into the repo.
- Keycloak users: decide whether to import the realm or recreate the users; map by `username` until `sub` is available.
- Legacy audit: define the redaction of `Script`/`Output` before the import; if not possible, import only the metadata and flag the record.
- Legacy duplicates on new constraints (`UQ*` in the data dictionary): must be measured on the legacy export and resolved with an explicit decision.
