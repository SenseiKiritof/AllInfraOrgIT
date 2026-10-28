# Data dictionary

Database: MySQL LTS (8.4), InnoDB, `utf8mb4_0900_ai_ci`. Table/column names in PascalCase as in the legacy; API JSON in camelCase.

## Conventions

- **PK**: `int AUTO_INCREMENT`; legacy IDs are preserved during import.
- **Audit**: every domain table with its own PK has `CreatedAt datetime(6) NOT NULL`, `UpdatedAt datetime(6) NOT NULL`, `Version int NOT NULL DEFAULT 0`. Exceptions: `CommandExecutions` (append-only history) and the join tables.
- **Version**: optimistic concurrency token incremented by `SaveChanges`; MySQL has no `xmin`.
- **Date**: UTC, ISO 8601 in the APIs.
- **Enum**: strings with a check constraint, unless stated otherwise.
- **Delete**: hard delete in v1; impact preview and audit for destructive operations. Parents with children are blocked (409), not cascade-deleted: only join tables use `ON DELETE CASCADE`.
- **UQ***: recommended constraint, to be verified against legacy data before import.

## Identity and RBAC

### Users

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(100) | no | |
| Surname | varchar(100) | no | |
| Username | varchar(100) | no | UQ; case-insensitive; maps `preferred_username` |
| CreatedAt / UpdatedAt / Version | audit | no | |

### Groups

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | UQ*; legacy `longtext` |
| audit | | | |

### Roles

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(100) | no | UQ; `SystemAdmin`, `ServerAdmin`, `ServerOperator` |
| Label | varchar(100) | no | |
| ScopeEnum | varchar(20) | no | `System` \| `Environment`; check |
| audit | | | |

### Menus

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(50) | no | |
| Path | varchar(200) | no | |
| IsActive | boolean | no | default true |
| HideBackButton | boolean | no | default false |
| IsVisible | boolean | no | default true |
| Order | int | yes | |
| ParentId | int | yes | FK `Menus.Id`, no cascade; delete blocked with children |
| audit | | | |

### GroupUser

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| GroupsId | int | no | PK, FK `Groups.Id` cascade |
| UsersId | int | no | PK, FK `Users.Id` cascade |

### RoleUser

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| RolesId | int | no | PK, FK `Roles.Id` cascade |
| UsersId | int | no | PK, FK `Users.Id` cascade |

### MenuRole

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| MenuId | int | no | PK, FK `Menus.Id` cascade |
| RolesId | int | no | PK, FK `Roles.Id` cascade |

### ProviderEnvironmentGroupRoles

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ProviderEnvironmentId | int | no | FK `ProviderEnvironments.Id` restrict |
| GroupId | int | no | FK `Groups.Id` cascade |
| RoleId | int | no | FK `Roles.Id` cascade |
| audit | | | UQ* (`ProviderEnvironmentId`, `GroupId`, `RoleId`) |

## Inventory

### Providers

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | UQ* |
| audit | | | |

### EnvironmentDefinitions

New table; replaces the legacy `Environments`. The entity is named `EnvironmentDefinition`.

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK; preserves `Environments.Id` |
| Name | varchar(100) | no | UQ* |
| Description | varchar(250) | no | |
| audit | | | |

### ProviderEnvironments

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ProviderId | int | no | FK `Providers.Id` restrict |
| EnvironmentDefinitionId | int | no | FK `EnvironmentDefinitions.Id` restrict; formerly `EnvironmentId` |
| audit | | | UQ* (`ProviderId`, `EnvironmentDefinitionId`) |

### Servers

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ProviderEnvironmentId | int | no | FK `ProviderEnvironments.Id` restrict |
| Name | varchar(200) | no | |
| IpAddress | varchar(200) | no | |
| Hostname | varchar(200) | no | |
| CredentialId | int | yes | FK `ServerCredentials.Id` added in Phase 5 |
| SshPort | int | no | default 22 |
| HostKeyFingerprint | varchar(100) | yes | SHA256 TOFU |
| JumpServerId | int | yes | FK `Servers.Id` restrict; optional SSH jump host |
| audit | | | |

### ServerCredentials

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | |
| Username | varchar(200) | no | |
| AuthType | varchar(20) | no | `Password` \| `PrivateKey` |
| EncryptedSecret | longtext | no | AES-GCM; never serialized |
| EncryptedPassphrase | longtext | yes | AES-GCM; never serialized |
| KeyVersion | int | no | new, default 1; key rotation |
| NeedsReauth | boolean | no | new, default false; import without key |
| audit | | | |

`HasSecret` is computed (`EncryptedSecret != ''`), not stored.

### ServerApplications

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ServerId | int | no | FK `Servers.Id` restrict |
| ApplicationVersionId | int | no | FK `ApplicationVersions.Id` restrict |
| ExposedPort | int | no | |
| ProxyRouteId | int | yes | FK `ProxyRoutes.Id` added in Phase 4, UQ* (1-1 relationship) |
| audit | | | |

## Catalog

### Applications

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | UQ* |
| Description | varchar(200) | no | legacy; consider widening |
| BasePath | varchar(50) | no | |
| ListeningOnPort | int | no | |
| Hostname | varchar(300) | yes | origin for test calls, `http`/`https` |
| audit | | | |

### ApplicationApiKeys

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationId | int | no | FK `Applications.Id` cascade |
| Name | varchar(200) | no | header or query name from the OpenAPI security scheme; UQ with ApplicationId+Location |
| Location | varchar(10) | no | `Header` \| `Query` |
| EncryptedValue | varchar(1000) | no | AES-GCM via SSecureUtils; empty when the value is not configured |
| KeyVersion | int | no | version of the credential key |
| audit | | | |

### ApplicationVersions

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationId | int | no | FK `Applications.Id` restrict |
| VersionNumber | varchar(25) | no | UQ* (`ApplicationId`, `VersionNumber`) |
| audit | | | |

### ApplicationVersionApis

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationVersionId | int | no | FK `ApplicationVersions.Id` restrict |
| Url | varchar(200) | no | |
| RequestTypeEnum | varchar(10) | no | `GET` \| `POST` \| `PUT` \| `PATCH` \| `DELETE` |
| Description | varchar(200) | no | |
| Body | longtext | yes | |
| audit | | | |

### ApplicationApiQueryParams

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationApiId | int | no | FK `ApplicationVersionApis.Id` restrict |
| Name | varchar(200) | no | |
| ParamType | varchar(20) | no | `Int` \| `String` \| `Bool` \| `DateTime` \| `Double` \| `Decimal` |
| audit | | | |

### Projects

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | UQ* |
| Description | varchar(500) | yes | |
| audit | | | |

### ApplicationProject

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| ApplicationsId | int | no | PK, FK `Applications.Id` cascade (link only) |
| ProjectsId | int | no | PK, FK `Projects.Id` cascade (link only) |

### CommandTemplates

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | |
| Description | varchar(500) | no | default '' |
| Script | longtext | no | `{{Name}}` placeholder |
| audit | | | |

### ApplicationActions

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationId | int | no | FK `Applications.Id` restrict |
| Label | varchar(100) | no | |
| Order | int | no | |
| CommandTemplateId | int | yes | FK `CommandTemplates.Id` restrict |
| CustomScript | longtext | yes | SystemAdmin only |
| ParameterValues | JSON | no | default `{}`; may contain sensitive values |
| RequiresConfirmation | boolean | no | |
| audit | | | |

`CommandTemplateId` and `CustomScript` are mutually exclusive; at least one must be set (application check).

## Topology

### ProxyConnections

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| SourceServerId | int | no | FK `Servers.Id` restrict |
| TargetServerId | int | no | FK `Servers.Id` restrict |
| Direction | varchar(20) | no | `Outgoing` \| `Incoming` |
| CreatedAt | datetime(6) | no | preserved from the legacy |
| UpdatedAt / Version | audit | no | |

### ProxyRoutes

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ProxyConnectionId | int | no | FK `ProxyConnections.Id` cascade |
| Route | varchar(200) | no | UQ* (`ProxyConnectionId`, `Route`) |
| MappedTo | varchar(50) | yes | |
| TargetServerApplicationId | int | yes | FK `ServerApplications.Id`, no action |
| TargetProxyConnectionId | int | yes | FK `ProxyConnections.Id`, no action |
| audit | | | |

## Diagrams

### Diagrams

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | |
| Description | varchar(500) | yes | |
| IsDefault | boolean | no | default false; global view; application invariant |
| CreatedAt | datetime(6) | no | preserved |
| UpdatedAt / Version | audit | no | |

### DiagramScopeItems

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| DiagramId | int | no | FK `Diagrams.Id` cascade |
| ScopeType | varchar(30) | no | `Provider` \| `ProviderEnvironment` \| `Project` |
| EntityId | int | no | polymorphic; for `ProviderEnvironment` it is `EnvironmentDefinition.Id` |
| audit | | | UQ (`DiagramId`, `ScopeType`, `EntityId`) |

### DiagramNodes

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| DiagramId | int | no | FK `Diagrams.Id` cascade |
| NodeType | varchar(30) | no | `Provider` \| `ProviderEnvironment` \| `Server` \| `ServerApplication` |
| EntityId | int | no | polymorphic |
| X / Y | double | no | |
| Width / Height | double | yes | |
| Collapsed | boolean | no | default false |
| audit | | | UQ (`DiagramId`, `NodeType`, `EntityId`) |

### DiagramEdges

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| DiagramId | int | no | FK `Diagrams.Id` cascade |
| ProxyConnectionId | int | no | logical, no FK |
| TargetNodeType | varchar(30) | no | `Server` \| `ServerApplication` |
| TargetEntityId | int | no | polymorphic |
| SourceHandle | varchar(50) | yes | |
| TargetHandle | varchar(50) | yes | |
| BendX / BendY | double | yes | offset from the midpoint |
| audit | | | UQ* (`DiagramId`, `ProxyConnectionId`, `TargetNodeType`, `TargetEntityId`) |

## Remote management and audit

### ReachabilityTests

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| ServerId | int | yes | FK `Servers.Id` cascade; `NULL` = global test |
| Hostname | varchar(200) | no | validated before the shell |
| Port | int | no | 1–65535 |
| Description | varchar(200) | no | default '' |
| audit | | | |

### CommandExecutions

| Column | Type | Null | Constraints / notes |
|---|---|---|---|
| Id | int | no | PK |
| Username | varchar(100) | no | snapshot |
| ServerId | int | no | **no FK**; the history survives |
| ServerName | varchar(200) | no | snapshot |
| Kind | varchar(20) | no | `Action` \| `Reachability` \| `Console` |
| Label | varchar(200) | no | |
| Script | longtext | no | redacted |
| ExitCode | int | yes | |
| Output | longtext | no | truncated; redacted |
| StartedAt | datetime(6) | no | |
| EndedAt | datetime(6) | yes | |

Index on `ServerId`. No `Version`: the history is append-only.

## Legacy → new enum mapping

| Legacy enum | Legacy type | New |
|---|---|---|
| `QueryParamTypeEnum` | int 0–5 | `Int`, `String`, `Bool`, `DateTime`, `Double`, `Decimal` |
| `RequestTypeEnum` | int 0–4 | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `RoleScopeEnum` | int 0–1 | `System`, `Environment` |
| `ProxyDirection` | varchar | `Outgoing`, `Incoming` (unchanged) |
| `CredentialAuthType` | varchar | `Password`, `PrivateKey` (unchanged) |
| `CommandExecutionKind` | varchar | `Action`, `Reachability`, `Console` (unchanged) |
| `DiagramScopeType` | varchar | `Provider`, `ProviderEnvironment`, `Project` (unchanged) |
| `DiagramNodeType` | varchar | `Provider`, `ProviderEnvironment`, `Server`, `ServerApplication` (unchanged) |
