# Topologia e diagrammi

Fase 4, 2026-10-26. Il riferimento funzionale è `../InfraOrgIT` (in sola lettura).

## Entità

| Tabella | Ruolo |
|---|---|
| `ProxyConnections` | collegamento source → target con `Direction` (`Outgoing` = il source usa il target come proxy; `Incoming` = il source è proxy del target) |
| `ProxyRoutes` | route di una connessione; target opzionale su una `ServerApplication` **oppure** su un'altra `ProxyConnection` |
| `ServerApplications.ProxyRouteId` | link 1-1 opzionale fra deploy e route, FK `Restrict` |
| `Diagrams` | diagramma; `IsDefault` unico gestito dall'applicazione |
| `DiagramScopeItems` | filtri salvati: `Provider`, `ProviderEnvironment`, `Project` |
| `DiagramNodes` | posizione e dimensione per nodo, chiave (`DiagramId`, `NodeType`, `EntityId`) |
| `DiagramEdges` | ancore e bend per edge, chiave (`DiagramId`, `ProxyConnectionId`, `TargetNodeType`, `TargetEntityId`) |

### IDs: non confonderli

- `DiagramScopeItem` con `ScopeType=ProviderEnvironment` porta **`EnvironmentDefinition.Id`**. È il filtro "ambiente" della vista globale.
- `DiagramNode` con `NodeType=ProviderEnvironment` porta **`ProviderEnvironment.Id`**.
- `DiagramNode` `Provider`/`Server`/`ServerApplication` porta l'ID dell'entità omonima.
- `TopologyEnvironmentDto.Id` è il `ProviderEnvironment.Id`; `EnvironmentId` è `EnvironmentDefinition.Id`.

Questi IDs sono verificati dai test e non vanno cambiati: l'import legacy (Fase 7) li preserva.

## Topologia

`GET /api/topology?providerId=&environmentId=&projectId=` restituisce provider → ambienti → server → applicazioni, più le connessioni proxy con le route.

- `environmentId` filtra su `EnvironmentDefinition.Id`.
- `projectId` filtra i server con almeno un deploy di un'app del progetto e aggiunge i server collegati da proxy, così la vista progetto non perde proxy e WAF.
- Provider e ambienti vuoti restano nella vista globale; con un filtro progetto restano solo i contenitori con server.

`TopologyService` è usato sia dall'endpoint sia dal grafo dei diagrammi.

## Diagrammi

- `GET /api/diagrams`, `/{id}`, `/default`; CRUD su `/api/diagrams`.
- `GET /api/diagrams/{id}/graph` restituisce diagramma, topologia filtrata dagli scope, nodi ed edge **in scope**. Nodi ed edge fuori scope restano salvati e tornano quando lo scope li include.
- `PUT /api/diagrams/{id}/nodes` aggiorna/crea posizioni; ignora chiavi fuori scope.
- `PUT /api/diagrams/{id}/edges` sostituisce gli edge in scope; deduplica per chiave logica, valida gli handle ≤ 50 caratteri.
- `IsDefault` è unico: impostarlo azzera gli altri.
- `GET /api/diagrams/default` restituisce la vista globale predefinita; 404 se non esiste.

## Permessi (D7 = B)

| Operazione | Ruolo |
|---|---|
| Letture topologia, diagrammi, proxy | autenticato |
| Diagramma globale, predefinito, con scope `Provider` o `Project` | `SystemAdmin` |
| Diagramma con soli scope `ProviderEnvironment` | `ServerAdmin` su **tutti** i `ProviderEnvironment` degli ambienti in scope |
| Cambio scope | unione scope vecchi e nuovi |
| Salvataggio nodi/edge | stesso permesso del diagramma |
| Delete nodo `Provider`/`ProviderEnvironment` | `SystemAdmin` |
| Delete nodo `Server`/`ServerApplication` | `ServerAdmin` sull'ambiente del server |
| CRUD connessioni proxy | `ServerAdmin` sugli ambienti di source e target |
| CRUD route proxy | `ServerAdmin` sugli ambienti della connessione e del target (applicazione o connessione) |

`SystemAdmin` non sostituisce `ServerAdmin` per server e diagrammi d'ambiente.

## Delete topologia

`GET /api/topology/nodes/{nodeType}/{id}/delete-preview` riporta l'impatto: ambienti, server, applicazioni, connessioni, route, route che perdono il target, assegnazioni di ruolo.

`DELETE /api/topology/nodes/{nodeType}/{id}` elimina il sottoalbero in transazione. Le route di proxy esterni che puntavano al sottoalbero restano senza target; i deploy collegati alle route rimosse perdono `ProxyRouteId`. Il catalogo (applicazioni, versioni, ambienti globali) non viene toccato.

## Frontend

- `lib/buildGraph.ts` è puro e testato: costruisce nodi React Flow dalla topologia, rispetta le posizioni salvate, instrada ogni route sull'applicazione target o sul server target.
- Canvas `/diagrams/{id}` e `/diagrams/default` con React Flow 12, caricato in un chunk separato.
- Salva posizioni e ancore/bend; "Salva come…" clona gli scope in un nuovo diagramma.
- Pannello nodo con anteprima impatti e delete quando il ruolo lo consente.
- Il disegno delle curve con bend non è modificabile dalla UI: i valori salvati vengono preservati.

## Test

- Integrazione: topologia con filtri, grafo, round-trip nodi/edge, default unico, permessi diagramma d'ambiente, delete server con ruolo d'ambiente, CRUD proxy con doppio ambiente.
- Vitest: `buildGraph` (gerarchia, edge su applicazione/server, posizioni salvate, 500 nodi).
- Playwright: creazione diagramma, apertura canvas, salvataggio layout, ricarica, eliminazione.

## Limiti noti

- Import dei diagrammi legacy: rinviato alla Fase 7; serve un dump sanificato (il catalogo reale è in `the legacy export`, vietato).
- Creazione nodi dal canvas non implementata: si usano le pagine di inventario.
- Bend e handle vengono salvati ma non modificati dalla UI.
