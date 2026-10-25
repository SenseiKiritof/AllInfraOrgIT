# ERD di dominio

Modello verificato sul legacy il 2026-10-25: 26 entità, 4 tabelle di join, `__EFMigrationsHistory` esclusa.

```mermaid
erDiagram
  USER ||--o{ GROUP_USER : "membro"
  GROUP ||--o{ GROUP_USER : "contiene"
  USER ||--o{ ROLE_USER : "ha"
  ROLE ||--o{ ROLE_USER : "assegnato"
  ROLE ||--o{ MENU_ROLE : "vede"
  MENU ||--o{ MENU_ROLE : "visibile a"
  MENU ||--o| MENU : "padre"

  PROVIDER ||--o{ PROVIDER_ENVIRONMENT : "offre"
  ENVIRONMENT_DEFINITION ||--o{ PROVIDER_ENVIRONMENT : "in"
  PROVIDER_ENVIRONMENT ||--o{ SERVER : "contiene"
  PROVIDER_ENVIRONMENT ||--o{ PROVIDER_ENVIRONMENT_GROUP_ROLE : "concede"
  GROUP ||--o{ PROVIDER_ENVIRONMENT_GROUP_ROLE : "riceve"
  ROLE ||--o{ PROVIDER_ENVIRONMENT_GROUP_ROLE : "ruolo"

  SERVER ||--o{ SERVER_APPLICATION : "ospita"
  APPLICATION_VERSION ||--o{ SERVER_APPLICATION : "deployata"
  APPLICATION ||--o{ APPLICATION_VERSION : "versioni"
  APPLICATION_VERSION ||--o{ APPLICATION_VERSION_API : "espone"
  APPLICATION_VERSION_API ||--o{ APPLICATION_API_QUERY_PARAM : "parametri"
  APPLICATION }o--o{ PROJECT : "progetti"

  SERVER ||--o{ PROXY_CONNECTION : "source"
  SERVER ||--o{ PROXY_CONNECTION : "target"
  PROXY_CONNECTION ||--o{ PROXY_ROUTE : "trasporta"
  PROXY_ROUTE }o--o| SERVER_APPLICATION : "target applicazione"
  PROXY_ROUTE }o--o| PROXY_CONNECTION : "inoltra"
  SERVER_APPLICATION }o--o| PROXY_ROUTE : "route"

  DIAGRAM ||--o{ DIAGRAM_SCOPE_ITEM : "scope"
  DIAGRAM ||--o{ DIAGRAM_NODE : "nodi"
  DIAGRAM ||--o{ DIAGRAM_EDGE : "edge"

  APPLICATION ||--o{ APPLICATION_ACTION : "azioni"
  COMMAND_TEMPLATE ||--o{ APPLICATION_ACTION : "template"
  SERVER ||--o{ REACHABILITY_TEST : "test"
  SERVER_CREDENTIAL ||--o{ SERVER : "usata da"
  SERVER ||--o{ COMMAND_EXECUTION : "audit (no FK)"
```

## Aggregati

| Aggregato | Radice | Contenuto |
|---|---|---|
| Inventario | `Provider`, `EnvironmentDefinition` | `ProviderEnvironment`, `Server` |
| Catalogo | `Application` | `ApplicationVersion`, `ApplicationVersionApi`, `ApplicationApiQueryParam` |
| Progetti | `Project` | associazione M-N con `Application` |
| Topologia | `ProxyConnection` | `ProxyRoute`, target applicazione o connessione |
| Diagrammi | `Diagram` | `DiagramScopeItem`, `DiagramNode`, `DiagramEdge` |
| Amministrazione | `User`, `Group`, `Role`, `Menu` | join e `ProviderEnvironmentGroupRole` |
| Gestione remota | `ServerCredential`, `CommandTemplate`, `ApplicationAction`, `ReachabilityTest` | `CommandExecution` (audit) |

## Invarianti

1. `ProviderEnvironment` è la coppia provider × ambiente. Lo scope `ProviderEnvironment` di un diagramma porta l'`EnvironmentDefinition.Id`, **non** il `ProviderEnvironment.Id` (verificato in `DiagramsService.BuildScopedTopologyAsync`).
2. `ProxyConnection.Direction`:
   - `Outgoing`: il source usa il target come proxy.
   - `Incoming`: il source è proxy per il target.
3. `ProxyRoute` punta a una `ServerApplication` **oppure** a un'altra `ProxyConnection`; entrambi i target sono opzionali.
4. `ServerApplication.ProxyRouteId` e `ProxyRoute.TargetServerApplicationId` formano un riferimento circolare nullable: l'import e le delete devono azzerare i riferimenti esterni prima di rimuovere le righe.
5. `ServerCredential` è condivisa da più server. Il segreto è cifrato, versionato e non serializzato.
6. `CommandExecution` non ha FK verso `Server`: lo storico sopravvive alla cancellazione del server.
7. `DiagramNode`/`DiagramEdge`/`DiagramScopeItem` hanno `EntityId` polimorfico senza FK. La validazione avviene nel servizio, non nel DB.
8. `Diagram.IsDefault` è un invariante applicativo: al massimo un diagramma default. MySQL non ha indici unici parziali; l'app lo garantisce in transazione.
9. `SystemAdmin` non implica `ServerAdmin`/`ServerOperator`: sono scope diversi.
10. Gli ID legacy sono preservati nell'import, perché i diagrammi li referenziano.

## Differenze rispetto al legacy

- `EnvironmentEntity` diventa `EnvironmentDefinition`; tabella `EnvironmentDefinitions`.
- Ogni tabella di dominio con PK propria riceve `CreatedAt`, `UpdatedAt`, `Version` (eccetto `CommandExecutions`).
- `ServerCredentials` riceve `KeyVersion` e `NeedsReauth`.
- Gli enum numerici (`QueryParamTypeEnum`, `RequestTypeEnum`, `RoleScopeEnum`) diventano stringhe.
- `ApplicationActions.ParameterValues` passa da `longtext` JSON a colonna `JSON`.
- I nomi di tabella/colonna restano PascalCase, come il legacy, per ridurre il mapping dell'importer.
