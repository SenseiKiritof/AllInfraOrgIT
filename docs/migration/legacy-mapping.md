# Mapping schema legacy → nuovo

Fonte legacy: MySQL 9.5, schema in `InfraOrgITDocker/legacy/01-schema.sql` e migration EF. Target: MySQL LTS, schema EF Core. Importer: `InfraOrgITApi/tools/LegacyImport`, Fase 7.

## Strategia

- **ID preservati** per tutte le entità: i diagrammi referenziano `EntityId` e non devono essere rimappati.
- Stesso engine (MySQL → MySQL); niente conversione SQL.
- Nomi tabella/colonna invariati salvo le eccezioni elencate.
- Import idempotente per classe, in transazione; rieseguibile in dry-run.
- Nessun dato reale nei repo: fixture sanificate.

## Mapping tabelle

| Legacy | Nuovo | Trasformazione |
|---|---|---|
| `Environments` | `EnvironmentDefinitions` | rinomina tabella/entità; `Id` preservato |
| `Providers` | `Providers` | nessuna |
| `ProviderEnvironments` | `ProviderEnvironments` | `EnvironmentId` → `EnvironmentDefinitionId` |
| `Servers` | `Servers` | + audit; `CredentialId`, `HostKeyFingerprint`, `SshPort` invariati |
| `ServerCredentials` | `ServerCredentials` | + `KeyVersion`, `NeedsReauth`; segreto ricifrato |
| `ServerApplications` | `ServerApplications` | + audit; `ProxyRouteId` preservato |
| `Applications` | `Applications` | + audit |
| `ApplicationVersions` | `ApplicationVersions` | + audit |
| `ApplicationVersionApis` | `ApplicationVersionApis` | `RequestTypeEnum` int → stringa; + audit |
| `ApplicationApiQueryParams` | `ApplicationApiQueryParams` | `ParamType` int → stringa; + audit |
| `Projects` | `Projects` | + audit |
| `ApplicationProject` | `ApplicationProject` | join invariata |
| `ProxyConnections` | `ProxyConnections` | `CreatedAt` preservato; + `UpdatedAt`, `Version` |
| `ProxyRoutes` | `ProxyRoutes` | nessuna; target opzionali preservati |
| `Diagrams` | `Diagrams` | `CreatedAt` preservato; + `UpdatedAt`, `Version`; `IsDefault` invariato |
| `DiagramScopeItems` | `DiagramScopeItems` | `ScopeType`, `EntityId` invariati |
| `DiagramNodes` | `DiagramNodes` | coordinate/handle invariati; + audit |
| `DiagramEdges` | `DiagramEdges` | target/handle/bend invariati; + audit |
| `Users` | `Users` | `Username` normalizzato lowercase; + audit |
| `Groups` | `Groups` | `Name` `longtext` → `varchar(200)`; + audit |
| `Roles` | `Roles` | `ScopeEnum` int → stringa; + audit |
| `GroupUser` | `GroupUser` | join invariata |
| `RoleUser` | `RoleUser` | join invariata |
| `Menus` | `Menus` | + audit; `ParentId` preservato |
| `MenuRole` | `MenuRole` | join invariata |
| `ProviderEnvironmentGroupRoles` | `ProviderEnvironmentGroupRoles` | + audit; deduplica se necessario |
| `CommandTemplates` | `CommandTemplates` | + audit |
| `ApplicationActions` | `ApplicationActions` | `ParameterValues` longtext JSON → JSON; + audit |
| `ReachabilityTests` | `ReachabilityTests` | + audit |
| `CommandExecutions` | `CommandExecutions` | nessuna FK; script/output redatti |
| `__EFMigrationsHistory` | nuova history EF | non importata |

## Enum

| Legacy (int) | Nuovo (string) |
|---|---|
| `QueryParamTypeEnum`: 0,1,2,3,4,5 | `Int`, `String`, `Bool`, `DateTime`, `Double`, `Decimal` |
| `RequestTypeEnum`: 0,1,2,3,4 | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `RoleScopeEnum`: 0,1 | `System`, `Environment` |

Gli enum già stringa (`ProxyDirection`, `CredentialAuthType`, `CommandExecutionKind`, `DiagramScopeType`, `DiagramNodeType`) restano invariati.

## Campi nuovi

- `CreatedAt`/`UpdatedAt`: per le righe importate usare il timestamp legacy se esiste (`Diagrams.CreatedAt`, `ProxyConnections.CreatedAt`, `CommandExecutions.StartedAt`); altrimenti l'istante di import. `UpdatedAt = CreatedAt`.
- `Version = 0`.
- `ServerCredentials.KeyVersion = 1`; `NeedsReauth = false` se il segreto è stato ricifrato.
- `EnvironmentDefinitions` mantiene `Id`, `Name`, `Description`.

## Credenziali

1. La vecchia chiave `ServerAccess:CredentialKey` serve solo all'importer: mai stamparla, mai salvarla nei nuovi repo.
2. Decifrare `EncryptedSecret` e `EncryptedPassphrase` con AES-GCM legacy.
3. Ricifrare con la nuova chiave e `KeyVersion = 1`.
4. Se la decifratura fallisce o la chiave manca: `EncryptedSecret = ''`, `EncryptedPassphrase = NULL`, `NeedsReauth = true`; il server resta importato e l'utente reinserisce il segreto.
5. L'import non logga plaintext, ciphertext o parti di chiave. Il report conta solo `migrated`/`needs_reauth`.

## Diagrammi

- `EntityId` non viene rimappato: ogni nodo/scope/edge punta all'ID legacy preservato.
- `DiagramScopeItem.ScopeType = ProviderEnvironment` porta l'`EnvironmentDefinition.Id` (ex `EnvironmentEntity.Id`), non il `ProviderEnvironment.Id`. Verificare con una query di coerenza.
- La vista globale diventa un diagramma con `IsDefault = true`; nessun id `0`.
- `DiagramNode` e `DiagramEdge` possono riferirsi a entità non più esistenti: l'importer produce un report di orfani; la decisione è bloccare l'import o scartare il nodo, non inventare un ID.
- `ApplicationAction.ParameterValues` può contenere segreti: non loggare i valori; l'audit delle esecuzioni usa lo script redatto.

## Ordine e validazione

1. Riferimento: `EnvironmentDefinitions`, `Providers`, `ProviderEnvironments`, `Menus`, `Roles`.
2. Identità: `Users`, `Groups`, `GroupUser`, `RoleUser`, `ProviderEnvironmentGroupRoles`.
3. Catalogo: `Applications`, `ApplicationVersions`, `ApplicationVersionApis`, `ApplicationApiQueryParams`, `Projects`, `ApplicationProject`, `CommandTemplates`, `ApplicationActions`.
4. Inventario: `ServerCredentials`, `Servers`, `ServerApplications`, `ProxyConnections`, `ProxyRoutes`, `ReachabilityTests`.
5. Diagrammi: `Diagrams`, `DiagramScopeItems`, `DiagramNodes`, `DiagramEdges`.
6. Audit: `CommandExecutions` (redatto).

Validazione bloccante:

- conteggi per tabella uguali al legacy (meno le righe scartate con motivazione);
- FK orfane = 0;
- unique rispettati (username, provider×ambiente, ruolo×gruppo×ambiente);
- ogni `DiagramScopeItem`/`DiagramNode`/`DiagramEdge` ha un target esistente o è nel report;
- render dei diagrammi dopo l'import;
- credenziali: conteggio `migrated` + `needs_reauth` = totale;
- checksum dei campi chiave (nome, IP, hostname, coordinate).

## Cutover

1. Freeze delle scritture legacy.
2. Snapshot e import delta.
3. Smoke test: login, inventario, diagrammi legacy, console su un server di test.
4. Switch DNS / reverse proxy.
5. Vecchio sistema in sola lettura per il rollback; rollback al `versions.lock` precedente se gli smoke falliscono.

## Aperti

- Export affidabile di `the legacy export`: è ignorato da git e può contenere dati rappresentativi; serve un dump approvato, non copiato nel repo.
- Utenti Keycloak: decidere se importare il realm o ricreare gli utenti; mappare per `username` finché il `sub` non è disponibile.
- Audit legacy: definire la redazione di `Script`/`Output` prima dell'import; se non è possibile, importare solo i metadati e marcare il record.
- Duplicati legacy su vincoli nuovi (`UQ*` nel data dictionary): vanno misurati sul export legacy e risolti con una decisione esplicita.
