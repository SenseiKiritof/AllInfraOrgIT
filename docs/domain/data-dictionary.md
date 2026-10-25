# Data dictionary

Database: MySQL LTS (8.4), InnoDB, `utf8mb4_0900_ai_ci`. Nomi tabella/colonna in PascalCase come il legacy; JSON API in camelCase.

## Convenzioni

- **PK**: `int AUTO_INCREMENT`; gli ID legacy sono preservati nell'import.
- **Audit**: ogni tabella di dominio con PK propria ha `CreatedAt datetime(6) NOT NULL`, `UpdatedAt datetime(6) NOT NULL`, `Version int NOT NULL DEFAULT 0`. Eccezioni: `CommandExecutions` (storico append-only) e le tabelle di join.
- **Version**: token di concorrenza ottimistica incrementato da `SaveChanges`; MySQL non ha `xmin`.
- **Date**: UTC, ISO 8601 nelle API.
- **Enum**: stringhe con check constraint, salvo diversa indicazione.
- **Delete**: hard delete in v1; anteprima impatti e audit per le operazioni distruttive. I padri con figli sono bloccati (409), non cancellati in cascata: solo le tabelle di join usano `ON DELETE CASCADE`.
- **UQ***: vincolo consigliato, da verificare sui dati legacy prima dell'import.

## Identità e RBAC

### Users

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(100) | no | |
| Surname | varchar(100) | no | |
| Username | varchar(100) | no | UQ; case-insensitive; mappa `preferred_username` |
| CreatedAt / UpdatedAt / Version | audit | no | |

### Groups

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | UQ*; legacy `longtext` |
| audit | | | |

### Roles

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(100) | no | UQ; `SystemAdmin`, `ServerAdmin`, `ServerOperator` |
| Label | varchar(100) | no | |
| ScopeEnum | varchar(20) | no | `System` \| `Environment`; check |
| audit | | | |

### Menus

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(50) | no | |
| Path | varchar(200) | no | |
| IsActive | boolean | no | default true |
| HideBackButton | boolean | no | default false |
| IsVisible | boolean | no | default true |
| Order | int | sì | |
| ParentId | int | sì | FK `Menus.Id`, no cascade; delete bloccata con figli |
| audit | | | |

### GroupUser

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| GroupsId | int | no | PK, FK `Groups.Id` cascade |
| UsersId | int | no | PK, FK `Users.Id` cascade |

### RoleUser

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| RolesId | int | no | PK, FK `Roles.Id` cascade |
| UsersId | int | no | PK, FK `Users.Id` cascade |

### MenuRole

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| MenuId | int | no | PK, FK `Menus.Id` cascade |
| RolesId | int | no | PK, FK `Roles.Id` cascade |

### ProviderEnvironmentGroupRoles

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ProviderEnvironmentId | int | no | FK `ProviderEnvironments.Id` restrict |
| GroupId | int | no | FK `Groups.Id` cascade |
| RoleId | int | no | FK `Roles.Id` cascade |
| audit | | | UQ* (`ProviderEnvironmentId`, `GroupId`, `RoleId`) |

## Inventario

### Providers

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | UQ* |
| audit | | | |

### EnvironmentDefinitions

Tabella nuova; sostituisce `Environments` del legacy. L'entità si chiama `EnvironmentDefinition`.

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK; preserva `Environments.Id` |
| Name | varchar(100) | no | UQ* |
| Description | varchar(250) | no | |
| audit | | | |

### ProviderEnvironments

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ProviderId | int | no | FK `Providers.Id` restrict |
| EnvironmentDefinitionId | int | no | FK `EnvironmentDefinitions.Id` restrict; ex `EnvironmentId` |
| audit | | | UQ* (`ProviderId`, `EnvironmentDefinitionId`) |

### Servers

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ProviderEnvironmentId | int | no | FK `ProviderEnvironments.Id` restrict |
| Name | varchar(200) | no | |
| IpAddress | varchar(200) | no | |
| Hostname | varchar(200) | no | |
| CredentialId | int | sì | FK `ServerCredentials.Id` aggiunta in Fase 5 |
| SshPort | int | no | default 22 |
| HostKeyFingerprint | varchar(100) | sì | SHA256 TOFU |
| audit | | | |

### ServerCredentials

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | |
| Username | varchar(200) | no | |
| AuthType | varchar(20) | no | `Password` \| `PrivateKey` |
| EncryptedSecret | longtext | no | AES-GCM; mai serializzato |
| EncryptedPassphrase | longtext | sì | AES-GCM; mai serializzato |
| KeyVersion | int | no | nuovo, default 1; rotazione chiave |
| NeedsReauth | boolean | no | nuovo, default false; import senza chiave |
| audit | | | |

`HasSecret` è calcolato (`EncryptedSecret != ''`), non memorizzato.

### ServerApplications

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ServerId | int | no | FK `Servers.Id` restrict |
| ApplicationVersionId | int | no | FK `ApplicationVersions.Id` restrict |
| ExposedPort | int | no | |
| ProxyRouteId | int | sì | FK `ProxyRoutes.Id` aggiunta in Fase 4, UQ* (relazione 1-1) |
| audit | | | |

## Catalogo

### Applications

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | UQ* |
| Description | varchar(200) | no | legacy; valutare ampliamento |
| BasePath | varchar(50) | no | |
| ListeningOnPort | int | no | |
| audit | | | |

### ApplicationVersions

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationId | int | no | FK `Applications.Id` restrict |
| VersionNumber | varchar(25) | no | UQ* (`ApplicationId`, `VersionNumber`) |
| audit | | | |

### ApplicationVersionApis

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationVersionId | int | no | FK `ApplicationVersions.Id` restrict |
| Url | varchar(200) | no | |
| RequestTypeEnum | varchar(10) | no | `GET` \| `POST` \| `PUT` \| `PATCH` \| `DELETE` |
| Description | varchar(200) | no | |
| Body | longtext | sì | |
| audit | | | |

### ApplicationApiQueryParams

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationApiId | int | no | FK `ApplicationVersionApis.Id` restrict |
| Name | varchar(200) | no | |
| ParamType | varchar(20) | no | `Int` \| `String` \| `Bool` \| `DateTime` \| `Double` \| `Decimal` |
| audit | | | |

### Projects

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | UQ* |
| Description | varchar(500) | sì | |
| audit | | | |

### ApplicationProject

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| ApplicationsId | int | no | PK, FK `Applications.Id` cascade (solo link) |
| ProjectsId | int | no | PK, FK `Projects.Id` cascade (solo link) |

### CommandTemplates

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | |
| Description | varchar(500) | no | default '' |
| Script | longtext | no | placeholder `{{Name}}` |
| audit | | | |

### ApplicationActions

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ApplicationId | int | no | FK `Applications.Id` restrict |
| Label | varchar(100) | no | |
| Order | int | no | |
| CommandTemplateId | int | sì | FK `CommandTemplates.Id` restrict |
| CustomScript | longtext | sì | solo SystemAdmin |
| ParameterValues | JSON | no | default `{}`; può contenere valori sensibili |
| RequiresConfirmation | boolean | no | |
| audit | | | |

`CommandTemplateId` e `CustomScript` sono alternativi; almeno uno valorizzato (check applicativo).

## Topologia

### ProxyConnections

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| SourceServerId | int | no | FK `Servers.Id` restrict |
| TargetServerId | int | no | FK `Servers.Id` restrict |
| Direction | varchar(20) | no | `Outgoing` \| `Incoming` |
| CreatedAt | datetime(6) | no | preservato dal legacy |
| UpdatedAt / Version | audit | no | |

### ProxyRoutes

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ProxyConnectionId | int | no | FK `ProxyConnections.Id` cascade |
| Route | varchar(200) | no | UQ* (`ProxyConnectionId`, `Route`) |
| MappedTo | varchar(50) | sì | |
| TargetServerApplicationId | int | sì | FK `ServerApplications.Id`, no action |
| TargetProxyConnectionId | int | sì | FK `ProxyConnections.Id`, no action |
| audit | | | |

## Diagrammi

### Diagrams

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Name | varchar(200) | no | |
| Description | varchar(500) | sì | |
| IsDefault | boolean | no | default false; vista globale; invariante applicativo |
| CreatedAt | datetime(6) | no | preservato |
| UpdatedAt / Version | audit | no | |

### DiagramScopeItems

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| DiagramId | int | no | FK `Diagrams.Id` cascade |
| ScopeType | varchar(30) | no | `Provider` \| `ProviderEnvironment` \| `Project` |
| EntityId | int | no | polimorfico; per `ProviderEnvironment` è `EnvironmentDefinition.Id` |
| audit | | | UQ (`DiagramId`, `ScopeType`, `EntityId`) |

### DiagramNodes

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| DiagramId | int | no | FK `Diagrams.Id` cascade |
| NodeType | varchar(30) | no | `Provider` \| `ProviderEnvironment` \| `Server` \| `ServerApplication` |
| EntityId | int | no | polimorfico |
| X / Y | double | no | |
| Width / Height | double | sì | |
| Collapsed | boolean | no | default false |
| audit | | | UQ (`DiagramId`, `NodeType`, `EntityId`) |

### DiagramEdges

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| DiagramId | int | no | FK `Diagrams.Id` cascade |
| ProxyConnectionId | int | no | logico, nessuna FK |
| TargetNodeType | varchar(30) | no | `Server` \| `ServerApplication` |
| TargetEntityId | int | no | polimorfico |
| SourceHandle | varchar(50) | sì | |
| TargetHandle | varchar(50) | sì | |
| BendX / BendY | double | sì | offset dal midpoint |
| audit | | | UQ* (`DiagramId`, `ProxyConnectionId`, `TargetNodeType`, `TargetEntityId`) |

## Gestione remota e audit

### ReachabilityTests

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| ServerId | int | sì | FK `Servers.Id` cascade; `NULL` = test globale |
| Hostname | varchar(200) | no | validato prima della shell |
| Port | int | no | 1–65535 |
| Description | varchar(200) | no | default '' |
| audit | | | |

### CommandExecutions

| Colonna | Tipo | Null | Vincoli / note |
|---|---|---|---|
| Id | int | no | PK |
| Username | varchar(100) | no | snapshot |
| ServerId | int | no | **nessuna FK**; lo storico sopravvive |
| ServerName | varchar(200) | no | snapshot |
| Kind | varchar(20) | no | `Action` \| `Reachability` \| `Console` |
| Label | varchar(200) | no | |
| Script | longtext | no | redatto |
| ExitCode | int | sì | |
| Output | longtext | no | troncato; redatto |
| StartedAt | datetime(6) | no | |
| EndedAt | datetime(6) | sì | |

Indice su `ServerId`. Nessun `Version`: lo storico è append-only.

## Mapping enum legacy → nuovo

| Enum legacy | Tipo legacy | Nuovo |
|---|---|---|
| `QueryParamTypeEnum` | int 0–5 | `Int`, `String`, `Bool`, `DateTime`, `Double`, `Decimal` |
| `RequestTypeEnum` | int 0–4 | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `RoleScopeEnum` | int 0–1 | `System`, `Environment` |
| `ProxyDirection` | varchar | `Outgoing`, `Incoming` (invariato) |
| `CredentialAuthType` | varchar | `Password`, `PrivateKey` (invariato) |
| `CommandExecutionKind` | varchar | `Action`, `Reachability`, `Console` (invariato) |
| `DiagramScopeType` | varchar | `Provider`, `ProviderEnvironment`, `Project` (invariato) |
| `DiagramNodeType` | varchar | `Provider`, `ProviderEnvironment`, `Server`, `ServerApplication` (invariato) |
