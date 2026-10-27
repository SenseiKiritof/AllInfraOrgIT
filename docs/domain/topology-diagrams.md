# Topology and diagrams

Phase 4, 2026-10-26. The functional reference is the legacy system (read-only).

## Entities

| Table | Role |
|---|---|
| `ProxyConnections` | source → target link with `Direction` (`Outgoing` = the source uses the target as a proxy; `Incoming` = the source is a proxy for the target) |
| `ProxyRoutes` | route of a connection; optional target on a `ServerApplication` **or** on another `ProxyConnection` |
| `ServerApplications.ProxyRouteId` | optional 1-1 link between deploy and route, FK `Restrict` |
| `Diagrams` | diagram; single `IsDefault` enforced by the application |
| `DiagramScopeItems` | saved filters: `Provider`, `ProviderEnvironment`, `Project` |
| `DiagramNodes` | position and size per node, key (`DiagramId`, `NodeType`, `EntityId`) |
| `DiagramEdges` | anchors and bends per edge, key (`DiagramId`, `ProxyConnectionId`, `TargetNodeType`, `TargetEntityId`) |

### IDs: do not confuse them

- `DiagramScopeItem` with `ScopeType=ProviderEnvironment` carries **`EnvironmentDefinition.Id`**. It is the "environment" filter of the global view.
- `DiagramNode` with `NodeType=ProviderEnvironment` carries **`ProviderEnvironment.Id`**.
- `DiagramNode` `Provider`/`Server`/`ServerApplication` carries the ID of the entity with the same name.
- `TopologyEnvironmentDto.Id` is the `ProviderEnvironment.Id`; `EnvironmentId` is `EnvironmentDefinition.Id`.

These IDs are verified by tests and must not change: the legacy import (Phase 7) preserves them.

## Topology

`GET /api/topology?providerId=&environmentId=&projectId=` returns provider → environments → servers → applications, plus the proxy connections with their routes.

- `environmentId` filters on `EnvironmentDefinition.Id`.
- `projectId` filters servers with at least one deploy of an app in the project and adds the servers linked by proxy, so the project view does not lose proxies and WAFs.
- Empty providers and environments stay in the global view; with a project filter only containers with servers remain.

`TopologyService` is used both by the endpoint and by the diagram graph.

## Diagrams

- `GET /api/diagrams`, `/{id}`, `/default`; CRUD on `/api/diagrams`.
- `GET /api/diagrams/{id}/graph` returns the diagram, the topology filtered by the scopes, and the nodes and edges **in scope**. Nodes and edges outside the scope stay stored and come back when the scope includes them.
- `PUT /api/diagrams/{id}/nodes` updates/creates positions; ignores keys outside the scope.
- `PUT /api/diagrams/{id}/edges` replaces the edges in scope; deduplicates by logical key, validates handles ≤ 50 characters.
- `IsDefault` is unique: setting it clears the others.
- `GET /api/diagrams/default` returns the default global view; 404 if it does not exist.

## Permissions (D7 = B)

| Operation | Role |
|---|---|
| Topology, diagram, proxy reads | authenticated |
| Global or default diagram, with `Provider` or `Project` scope | `SystemAdmin` |
| Diagram with only `ProviderEnvironment` scopes | `ServerAdmin` on **all** the `ProviderEnvironment` entries of the environments in scope |
| Scope change | union of old and new scopes |
| Node/edge save | same permission as the diagram |
| Deleting a `Provider`/`ProviderEnvironment` node | `SystemAdmin` |
| Deleting a `Server`/`ServerApplication` node | `ServerAdmin` on the server's environment |
| Proxy connection CRUD | `ServerAdmin` on the source and target environments |
| Proxy route CRUD | `ServerAdmin` on the environments of the connection and of the target (application or connection) |

`SystemAdmin` does not replace `ServerAdmin` for servers and environment diagrams.

## Topology deletes

`GET /api/topology/nodes/{nodeType}/{id}/delete-preview` reports the impact: environments, servers, applications, connections, routes, routes that lose their target, role assignments.

`DELETE /api/topology/nodes/{nodeType}/{id}` deletes the subtree in a transaction. External proxy routes that pointed to the subtree are left without a target; deploys linked to removed routes lose `ProxyRouteId`. The catalog (applications, versions, global environments) is not touched.

## Frontend

- `lib/buildGraph.ts` is pure and tested: it builds React Flow nodes from the topology, respects saved positions, routes each route to the target application or target server.
- Canvas `/diagrams/{id}` and `/diagrams/default` with React Flow 12, loaded in a separate chunk.
- Saves positions and anchors/bends; "Save as…" clones the scopes into a new diagram.
- Node panel with impact preview and delete when the role allows it.
- Curve drawing with bends is not editable from the UI: saved values are preserved.

## Tests

- Integration: topology with filters, graph, node/edge round-trip, single default, environment diagram permissions, server delete with environment role, proxy CRUD with dual environment.
- Vitest: `buildGraph` (hierarchy, edges to application/server, saved positions, 500 nodes).
- Playwright: diagram creation, canvas opening, layout save, reload, deletion.

## Known limits

- Legacy diagram import: deferred to Phase 7; a sanitized dump is needed (the full catalog is kept outside the repository).
- Creating nodes from the canvas is not implemented: the inventory pages are used.
- Bends and handles are saved but not modified by the UI.
