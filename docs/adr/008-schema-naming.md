# ADR-008 — Schema names and audit columns

- Status: accepted
- Date: 2026-10-25

## Context

The legacy schema uses PascalCase names (`Environments`, `ProviderEnvironments`, `ApplicationApiQueryParams`) and has neither timestamps nor optimistic concurrency. The migration must preserve IDs because the diagrams reference them. A full rename to snake_case would add mapping and risk with no requested benefit.

## Decision

- Keep tables and columns in PascalCase, as in the legacy, except:
  - `EnvironmentEntity` → `EnvironmentDefinition`, table `EnvironmentDefinitions`, FK `EnvironmentDefinitionId`.
- Every domain table with its own PK gets `CreatedAt`, `UpdatedAt` (UTC, `datetime(6)`) and `Version` (`int`, default 0, concurrency token). Exceptions: `CommandExecutions` and joins.
- `ServerCredentials` gets `KeyVersion` and `NeedsReauth`.
- Legacy numeric enums converted to strings with check constraints; `ParameterValues` into a `JSON` column.
- Candidate unique constraints: `Users.Username`, `Roles.Name`, `ProviderEnvironments (ProviderId, EnvironmentDefinitionId)`, `ApplicationVersions (ApplicationId, VersionNumber)`, `ProxyRoutes (ProxyConnectionId, Route)`, `ProviderEnvironmentGroupRoles (ProviderEnvironmentId, GroupId, RoleId)`, `DiagramScopeItems/Nodes` per logical key. They must be verified on the legacy export before the import.
- Hard delete; no soft delete in v1. Destructive deletes have an impact preview and audit.
- `CommandExecutions` remains append-only with `ServerId` without FK.

## Alternatives considered

- **snake_case**: more conventional in MySQL, but requires total mapping and does not solve a real problem.
- **Keep `Environments` as a table**: fewer renames, but leaves ambiguity with `ProviderEnvironment` and the `EnvironmentDefinition` entity.
- **RowVersion byte[]**: MySQL has no server-side rowversion; `Version` int is explicit and testable.

## Consequences

- The importer maps a limited number of names.
- The data dictionary is the source for migrations and tests.
- The `UQ*` constraints may fail on duplicate legacy data: the cleanup decision must be made in Phase 7, not silently in the importer.
