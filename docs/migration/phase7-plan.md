# Phase 7 operational plan — legacy migration

2026-10-26 analysis of the new schema and the legacy schema (`../InfraOrgITDocker/legacy/01-schema.sql`, definitions only). No production data read or copied.

## Implementation status

`tools/LegacyImport` is now present:

- legacy-shaped JSON input, mapping in `ImportPlans.cs`, JSON report, atomic `--apply` in a single transaction;
- IDs preserved; an existing row is skipped only if the natural key matches, otherwise blocking collision and rollback;
- two phases for `Menus.ParentId` and `ServerApplications.ProxyRouteId`, in the same transaction;
- credentials re-encrypted with old/new key and `--new-key-version`; `NeedsReauth` requires `--allow-reauth`;
- redacted audit, dry-run with collision check on the target if `LEGACY_IMPORT_CONNECTION` is set;
- secrets only from env (never argv); `make legacy-dry-run` and 6 importer tests on MySQL Testcontainers.
- read-only MySQL adapter (`LEGACY_SOURCE_CONNECTION`): reads the `ImportPlans` tables and produces the same JSON rows as the fixture;
- fake legacy dump in Docker (`mysql-legacy`, `legacy` profile) with a reduced schema and all data types: one machine, one proxy, one service, one diagram and one execution;
- MySQL source → target integration test: apply, credential re-encryption, idempotency, audit redaction.

Points 3–14 on a representative dataset and the rehearsal with a sanitized dump remain to be done: the fake dump validates the adapter, not the legacy collisions.

## Blockers to close before the importer

1. ~~`tools/LegacyImport` does not exist~~: implemented for JSON fixtures and for legacy MySQL; `--classes`/`--batch-size`/`--fresh` are missing.
2. **Sanitized fixtures** for all classes: the fake dump in `InfraOrgITDocker/legacy/` covers all entity types with invented data; the values and duplicates of the real sanitized dump are still missing.
3. **Duplicate preflight**: the new schema has uniques the legacy did not have (username, provider/environment/application/project names, version per application, route per connection, nodes/edges per key, PEGR, `ServerApplications.ProxyRouteId`). The preflight checks the uniques inside the fixture; collisions with rows already in the target (including seed data) are blocking in apply and, with the connection, also in dry-run.
4. **Orphans and legacy defaults**: `ProviderEnvironmentId=0`, `ProxyRoutes.ProxyConnectionId=0`, orphan FKs, `ReachabilityTests.Port` out of range, proxy with source=target. Blocking preflight.
5. **Cycle `ServerApplications.ProxyRouteId` ↔ `ProxyRoutes.TargetServerApplicationId`**: two-phase import (deploy without link → route → update link), without disabling FKs if possible.
6. **Keycloak `sub`**: the new `User` has no `ExternalId`; import by username and report the unmatched ones. Add the column in Phase 7 if stability is needed.
7. **Credentials**: legacy decryption separate from the new key; if the old `ServerAccess:CredentialKey` is missing or the record is invalid → `NeedsReauth=true`, `EncryptedSecret=''`. Count `migrated + needs_reauth = total`.
8. **Audit**: redaction policy. Prudent default: import metadata, `Script=''`, `Output=''`, count redacted records. Never plaintext/ciphertext in reports.
9. **Timestamps**: the DbContext `SaveChanges` overrides `UpdatedAt`; to preserve timestamps use controlled raw SQL. `Version=0` unless otherwise.
10. **Diagrams**: verify every scope/node/edge against existing entities; at most one `IsDefault`; legacy id 0 is the virtual view, not a row.

## Import order

1. Reference: `EnvironmentDefinitions`, `Providers`, `ProviderEnvironments`; `Roles`, `Menus` skipped only if the natural key matches, otherwise blocking collision; `MenuRole` merged.
2. Identity: `Users`, `Groups`, `GroupUser`, `RoleUser`, `MenuRole`, `ProviderEnvironmentGroupRoles`.
3. Catalog: `Projects`, `Applications`, `ApplicationVersions`, `ApplicationVersionApis`, `ApplicationApiQueryParams`, `ApplicationProject`, `CommandTemplates`, `ApplicationActions`.
4. Inventory: `ServerCredentials`, `Servers`, `ProxyConnections`, `ServerApplications` (null link), `ProxyRoutes`, update link, `ReachabilityTests`.
5. Diagrams: `Diagrams`, `DiagramScopeItems`, `DiagramNodes`, `DiagramEdges`.
6. Audit: `CommandExecutions` (last, no FK on server).

Joins after the parents; self-FK (`Menus.ParentId`, `ProxyRoutes.TargetProxyConnectionId`) with parents first. `SET FOREIGN_KEY_CHECKS=0` only as a last resort, local session, then orphan verification. Do not use `SET UNIQUE_CHECKS=0`.

## Importer requirements

- Input: legacy connection string **read-only**, target, old key from env/secret, report path.
- Dry-run: reads, validates, computes the plan; no writes; same report/exit code as the run.
- Report: per class read/inserted/updated/skipped/rejected; PK and reason; credential counts; checksum; no secrets.
- Idempotency: insert if absent, skip or `--force`; joins `INSERT IGNORE`; `--fresh` only with explicit confirmation.
- Transaction per class; inventory and route/deploy cycle in the same transaction; checkpoint to resume.
- IDs always preserved; no remap of `Diagram*.EntityId`.
- Final `AUTO_INCREMENT > MAX(Id)` check on every table.

## Blocking validation

- Counts: `read - rejected = target`.
- Orphan FKs: zero, excluding `CommandExecutions.ServerId` (no FK by design).
- Uniques: zero duplicates on every new constraint or explicit decision.
- Checks: enum, `AuthType`, `Kind`, port, source≠target, non-zero dates.
- Checksum ordered by ID on key fields (name, IP, hostname, coordinates, handle, bend, route).
- Credentials: in-memory roundtrip, new `KeyVersion`, consistent `needs_reauth`.
- Diagrams: existing targets, single `IsDefault`, render of every diagram.
- Audit: count, empty or redacted script/output, no secret patterns.
- Users: match with Keycloak and list of missing ones.
- Smoke: login, inventory, legacy diagram, console on a test server.

## Cutover

The legacy has no `UpdatedAt` on most tables: a reliable "delta import" is not possible. During the freeze, a full idempotent re-import or CDC/binlog is needed. Rollback = checkout of the previous `versions.lock` and restore of the pre-cutover DB.

The signed runbook remains to be written: the fake schema does not prove freeze times, volumes or rollback on a representative dataset.

## Risks

- Local exports are not committed in the repos: read-only snapshots and sanitized fixtures.
- Loss of the old credential key.
- Legacy host key considered trusted: evaluate a reset for critical servers.
- Large `longtext`: small batches and `max_allowed_packet`.
- Duplicates/checks may stop the import mid-class: blocking preflight.
- Keycloak without aligned users: broken login after the cutover.
