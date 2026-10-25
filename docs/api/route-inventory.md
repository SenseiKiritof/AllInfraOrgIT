# Inventario route legacy → target

Generato dal codice legacy `InfraOrgIt/MinimalApis` il 2026-10-25. 168 operazioni HTTP + 1 WebSocket.

`/Paginated` è fuso nella lista con `page`/`pageSize`; le route target sono la proposta v1, non implementate.

| Gruppo | Metodo | Route legacy | Route target | Permesso legacy |
|---|---|---|---|---|
|---|---|---|---|---|
| ApplicationActions | Delete | `/ApplicationActions/{id}` | `/api/application-actions/{id}` | SystemAdmin |
| ApplicationActions | Put | `/ApplicationActions/{id}` | `/api/application-actions/{id}` | SystemAdmin |
| ApplicationApiQueryParams | Get | `/ApplicationApiQueryParams` | `/api/application-api-query-params` | autenticato |
| ApplicationApiQueryParams | Post | `/ApplicationApiQueryParams` | `/api/application-api-query-params` | autenticato |
| ApplicationApiQueryParams | Get | `/ApplicationApiQueryParams/Paginated` | `/api/application-api-query-params` | autenticato |
| ApplicationApiQueryParams | Delete | `/ApplicationApiQueryParams/{id}` | `/api/application-api-query-params/{id}` | autenticato |
| ApplicationApiQueryParams | Get | `/ApplicationApiQueryParams/{id}` | `/api/application-api-query-params/{id}` | autenticato |
| ApplicationApiQueryParams | Put | `/ApplicationApiQueryParams/{id}` | `/api/application-api-query-params/{id}` | autenticato |
| ApplicationVersionApis | Get | `/ApplicationVersionApis` | `/api/application-version-apis` | autenticato |
| ApplicationVersionApis | Post | `/ApplicationVersionApis` | `/api/application-version-apis` | autenticato |
| ApplicationVersionApis | Get | `/ApplicationVersionApis/Paginated` | `/api/application-version-apis` | autenticato |
| ApplicationVersionApis | Delete | `/ApplicationVersionApis/{id}` | `/api/application-version-apis/{id}` | autenticato |
| ApplicationVersionApis | Get | `/ApplicationVersionApis/{id}` | `/api/application-version-apis/{id}` | autenticato |
| ApplicationVersionApis | Put | `/ApplicationVersionApis/{id}` | `/api/application-version-apis/{id}` | autenticato |
| ApplicationVersionApis | Get | `/ApplicationVersionApis/{id}/QueryParams` | `/api/application-version-apis/{id}/query-params` | autenticato |
| ApplicationVersionApis | Post | `/ApplicationVersionApis/{id}/QueryParams` | `/api/application-version-apis/{id}/query-params` | autenticato |
| ApplicationVersions | Get | `/ApplicationVersions` | `/api/application-versions` | autenticato |
| ApplicationVersions | Post | `/ApplicationVersions` | `/api/application-versions` | autenticato |
| ApplicationVersions | Get | `/ApplicationVersions/Paginated` | `/api/application-versions` | autenticato |
| ApplicationVersions | Delete | `/ApplicationVersions/{id}` | `/api/application-versions/{id}` | autenticato |
| ApplicationVersions | Get | `/ApplicationVersions/{id}` | `/api/application-versions/{id}` | autenticato |
| ApplicationVersions | Put | `/ApplicationVersions/{id}` | `/api/application-versions/{id}` | autenticato |
| ApplicationVersions | Get | `/ApplicationVersions/{id}/Apis` | `/api/application-versions/{id}/apis` | autenticato |
| ApplicationVersions | Post | `/ApplicationVersions/{id}/Apis` | `/api/application-versions/{id}/apis` | autenticato |
| Applications | Get | `/Applications` | `/api/applications` | autenticato |
| Applications | Post | `/Applications` | `/api/applications` | autenticato |
| Applications | Get | `/Applications/Paginated` | `/api/applications` | autenticato |
| Applications | Delete | `/Applications/{id}` | `/api/applications/{id}` | autenticato |
| Applications | Get | `/Applications/{id}` | `/api/applications/{id}` | autenticato |
| Applications | Put | `/Applications/{id}` | `/api/applications/{id}` | autenticato |
| Applications | Get | `/Applications/{id}/Actions` | `/api/applications/{id}/actions` | SystemAdmin |
| Applications | Post | `/Applications/{id}/Actions` | `/api/applications/{id}/actions` | SystemAdmin |
| Applications | Get | `/Applications/{id}/Projects` | `/api/applications/{id}/projects` | autenticato |
| Applications | Post | `/Applications/{id}/Projects` | `/api/applications/{id}/projects` | autenticato |
| Applications | Delete | `/Applications/{id}/Projects/{projectId}` | `/api/applications/{id}/projects/{projectId}` | autenticato |
| Applications | Get | `/Applications/{id}/Versions` | `/api/applications/{id}/versions` | autenticato |
| Applications | Post | `/Applications/{id}/Versions` | `/api/applications/{id}/versions` | autenticato |
| Auth | Get | `/Auth/CurrentUser` | `/api/session` | autenticato |
| Auth | Post | `/Auth/Login` | `/auth/login` | anonimo |
| Auth | Post | `/Auth/Logout` | `/auth/logout` | anonimo |
| Auth | Post | `/Auth/RefreshToken` | `— (refresh lato server)` | anonimo |
| Auth | Post | `/Auth/Token` | `/auth/callback` | anonimo |
| CommandExecutions | Get | `/CommandExecutions/Paginated` | `/api/command-executions` | SystemAdmin |
| CommandTemplates | Get | `/CommandTemplates` | `/api/command-templates` | SystemAdmin |
| CommandTemplates | Post | `/CommandTemplates` | `/api/command-templates` | SystemAdmin |
| CommandTemplates | Get | `/CommandTemplates/Paginated` | `/api/command-templates` | SystemAdmin |
| CommandTemplates | Delete | `/CommandTemplates/{id}` | `/api/command-templates/{id}` | SystemAdmin |
| CommandTemplates | Get | `/CommandTemplates/{id}` | `/api/command-templates/{id}` | SystemAdmin |
| CommandTemplates | Put | `/CommandTemplates/{id}` | `/api/command-templates/{id}` | SystemAdmin |
| Diagrams | Get | `/Diagrams` | `/api/diagrams` | autenticato |
| Diagrams | Post | `/Diagrams` | `/api/diagrams` | autenticato |
| Diagrams | Get | `/Diagrams/Paginated` | `/api/diagrams` | autenticato |
| Diagrams | Delete | `/Diagrams/{id}` | `/api/diagrams/{id}` | autenticato |
| Diagrams | Get | `/Diagrams/{id}` | `/api/diagrams/{id}` | autenticato |
| Diagrams | Put | `/Diagrams/{id}` | `/api/diagrams/{id}` | autenticato |
| Diagrams | Put | `/Diagrams/{id}/Edges` | `/api/diagrams/{id}/edges` | autenticato |
| Diagrams | Get | `/Diagrams/{id}/Graph` | `/api/diagrams/{id}/graph` | autenticato |
| Diagrams | Put | `/Diagrams/{id}/Nodes` | `/api/diagrams/{id}/nodes` | autenticato |
| Enviroments | Get | `/Enviroments` | `/api/environments` | autenticato |
| Enviroments | Post | `/Enviroments` | `/api/environments` | autenticato |
| Enviroments | Get | `/Enviroments/Paginated` | `/api/environments` | autenticato |
| Enviroments | Get | `/Enviroments/{id}` | `/api/environments/{id}` | autenticato |
| Enviroments | Put | `/Enviroments/{id}` | `/api/environments/{id}` | autenticato |
| Groups | Get | `/Groups` | `/api/groups` | autenticato |
| Groups | Post | `/Groups` | `/api/groups` | SystemAdmin |
| Groups | Get | `/Groups/Paginated` | `/api/groups` | autenticato |
| Groups | Delete | `/Groups/{id}` | `/api/groups/{id}` | SystemAdmin |
| Groups | Get | `/Groups/{id}` | `/api/groups/{id}` | autenticato |
| Groups | Put | `/Groups/{id}` | `/api/groups/{id}` | SystemAdmin |
| Menus | Get | `/Menus` | `/api/menus` | autenticato |
| Menus | Post | `/Menus` | `/api/menus` | SystemAdmin |
| Menus | Get | `/Menus/Paginated` | `/api/menus` | autenticato |
| Menus | Delete | `/Menus/{id}` | `/api/menus/{id}` | SystemAdmin |
| Menus | Get | `/Menus/{id}` | `/api/menus/{id}` | autenticato |
| Menus | Put | `/Menus/{id}` | `/api/menus/{id}` | SystemAdmin |
| Projects | Get | `/Projects` | `/api/projects` | autenticato |
| Projects | Post | `/Projects` | `/api/projects` | autenticato |
| Projects | Get | `/Projects/Paginated` | `/api/projects` | autenticato |
| Projects | Delete | `/Projects/{id}` | `/api/projects/{id}` | autenticato |
| Projects | Get | `/Projects/{id}` | `/api/projects/{id}` | autenticato |
| Projects | Put | `/Projects/{id}` | `/api/projects/{id}` | autenticato |
| Projects | Get | `/Projects/{id}/Applications` | `/api/projects/{id}/applications` | autenticato |
| Projects | Post | `/Projects/{id}/Applications` | `/api/projects/{id}/applications` | autenticato |
| Projects | Delete | `/Projects/{id}/Applications/{applicationId}` | `/api/projects/{id}/applications/{applicationId}` | autenticato |
| ProviderEnvironmentGroupRoles | Get | `/ProviderEnvironmentGroupRoles` | `/api/provider-environment-group-roles` | autenticato |
| ProviderEnvironmentGroupRoles | Post | `/ProviderEnvironmentGroupRoles` | `/api/provider-environment-group-roles` | SystemAdmin |
| ProviderEnvironmentGroupRoles | Get | `/ProviderEnvironmentGroupRoles/Paginated` | `/api/provider-environment-group-roles` | autenticato |
| ProviderEnvironmentGroupRoles | Delete | `/ProviderEnvironmentGroupRoles/{id}` | `/api/provider-environment-group-roles/{id}` | SystemAdmin |
| ProviderEnvironmentGroupRoles | Get | `/ProviderEnvironmentGroupRoles/{id}` | `/api/provider-environment-group-roles/{id}` | autenticato |
| ProviderEnvironmentGroupRoles | Put | `/ProviderEnvironmentGroupRoles/{id}` | `/api/provider-environment-group-roles/{id}` | SystemAdmin |
| ProviderEnvironments | Get | `/ProviderEnvironments` | `/api/provider-environments` | autenticato |
| ProviderEnvironments | Post | `/ProviderEnvironments` | `/api/provider-environments` | autenticato |
| ProviderEnvironments | Get | `/ProviderEnvironments/Paginated` | `/api/provider-environments` | autenticato |
| ProviderEnvironments | Delete | `/ProviderEnvironments/{id}` | `/api/provider-environments/{id}` | autenticato |
| ProviderEnvironments | Get | `/ProviderEnvironments/{id}` | `/api/provider-environments/{id}` | autenticato |
| ProviderEnvironments | Put | `/ProviderEnvironments/{id}` | `/api/provider-environments/{id}` | autenticato |
| ProviderEnvironments | Post | `/ProviderEnvironments/{id}/ReachabilityTests/Run` | `/api/provider-environments/{id}/reachability-tests/run` | ServerOperator |
| ProviderEnvironments | Get | `/ProviderEnvironments/{providerEnvironmentId}/GroupRoles` | `/api/provider-environments/{providerEnvironmentId}/group-roles` | autenticato |
| ProviderEnvironments | Post | `/ProviderEnvironments/{providerEnvironmentId}/GroupRoles` | `/api/provider-environments/{providerEnvironmentId}/group-roles` | SystemAdmin |
| ProviderEnvironments | Delete | `/ProviderEnvironments/{providerEnvironmentId}/GroupRoles/{groupRoleId}` | `/api/provider-environments/{providerEnvironmentId}/group-roles/{groupRoleId}` | SystemAdmin |
| Providers | Get | `/Providers` | `/api/providers` | autenticato |
| Providers | Post | `/Providers` | `/api/providers` | autenticato |
| Providers | Get | `/Providers/Paginated` | `/api/providers` | autenticato |
| Providers | Delete | `/Providers/{id}` | `/api/providers/{id}` | autenticato |
| Providers | Get | `/Providers/{id}` | `/api/providers/{id}` | autenticato |
| Providers | Put | `/Providers/{id}` | `/api/providers/{id}` | autenticato |
| ProxyConnections | Get | `/ProxyConnections` | `/api/proxy-connections` | autenticato |
| ProxyConnections | Post | `/ProxyConnections` | `/api/proxy-connections` | autenticato |
| ProxyConnections | Get | `/ProxyConnections/Paginated` | `/api/proxy-connections` | autenticato |
| ProxyConnections | Delete | `/ProxyConnections/{id}` | `/api/proxy-connections/{id}` | autenticato |
| ProxyConnections | Get | `/ProxyConnections/{id}` | `/api/proxy-connections/{id}` | autenticato |
| ProxyConnections | Put | `/ProxyConnections/{id}` | `/api/proxy-connections/{id}` | autenticato |
| ProxyConnections | Get | `/ProxyConnections/{id}/Routes` | `/api/proxy-connections/{id}/routes` | autenticato |
| ProxyConnections | Post | `/ProxyConnections/{id}/Routes` | `/api/proxy-connections/{id}/routes` | autenticato |
| ProxyRoutes | Get | `/ProxyRoutes` | `/api/proxy-routes` | autenticato |
| ProxyRoutes | Post | `/ProxyRoutes` | `/api/proxy-routes` | autenticato |
| ProxyRoutes | Get | `/ProxyRoutes/Paginated` | `/api/proxy-routes` | autenticato |
| ProxyRoutes | Delete | `/ProxyRoutes/{id}` | `/api/proxy-routes/{id}` | autenticato |
| ProxyRoutes | Get | `/ProxyRoutes/{id}` | `/api/proxy-routes/{id}` | autenticato |
| ProxyRoutes | Put | `/ProxyRoutes/{id}` | `/api/proxy-routes/{id}` | autenticato |
| ReachabilityTests | Get | `/ReachabilityTests` | `/api/reachability-tests` | SystemAdmin |
| ReachabilityTests | Post | `/ReachabilityTests` | `/api/reachability-tests` | SystemAdmin |
| ReachabilityTests | Delete | `/ReachabilityTests/{id}` | `/api/reachability-tests/{id}` | SystemAdmin |
| ReachabilityTests | Put | `/ReachabilityTests/{id}` | `/api/reachability-tests/{id}` | SystemAdmin |
| Roles | Get | `/Roles` | `/api/roles` | autenticato |
| Roles | Post | `/Roles` | `/api/roles` | SystemAdmin |
| Roles | Get | `/Roles/Paginated` | `/api/roles` | autenticato |
| Roles | Delete | `/Roles/{id}` | `/api/roles/{id}` | SystemAdmin |
| Roles | Get | `/Roles/{id}` | `/api/roles/{id}` | autenticato |
| Roles | Put | `/Roles/{id}` | `/api/roles/{id}` | SystemAdmin |
| ServerAccess | Get | `/ServerAccess/Me` | `/api/server-access/me` | autenticato |
| ServerApplications | Get | `/ServerApplications` | `/api/server-applications` | autenticato |
| ServerApplications | Post | `/ServerApplications` | `/api/server-applications` | autenticato |
| ServerApplications | Get | `/ServerApplications/Paginated` | `/api/server-applications` | autenticato |
| ServerApplications | Delete | `/ServerApplications/{id}` | `/api/server-applications/{id}` | autenticato |
| ServerApplications | Get | `/ServerApplications/{id}` | `/api/server-applications/{id}` | autenticato |
| ServerApplications | Put | `/ServerApplications/{id}` | `/api/server-applications/{id}` | autenticato |
| ServerApplications | Get | `/ServerApplications/{id}/Actions` | `/api/server-applications/{id}/actions` | ServerOperator |
| ServerApplications | Post | `/ServerApplications/{id}/Actions/{actionId}/Run` | `/api/server-applications/{id}/actions/{actionId}/run` | ServerOperator |
| ServerCredentials | Get | `/ServerCredentials` | `/api/server-credentials` | SystemAdmin |
| ServerCredentials | Post | `/ServerCredentials` | `/api/server-credentials` | SystemAdmin |
| ServerCredentials | Get | `/ServerCredentials/Paginated` | `/api/server-credentials` | SystemAdmin |
| ServerCredentials | Delete | `/ServerCredentials/{id}` | `/api/server-credentials/{id}` | SystemAdmin |
| ServerCredentials | Get | `/ServerCredentials/{id}` | `/api/server-credentials/{id}` | SystemAdmin |
| ServerCredentials | Put | `/ServerCredentials/{id}` | `/api/server-credentials/{id}` | SystemAdmin |
| Servers | Get | `/Servers` | `/api/servers` | autenticato |
| Servers | Post | `/Servers` | `/api/servers` | autenticato |
| Servers | Get | `/Servers/Paginated` | `/api/servers` | autenticato |
| Servers | Delete | `/Servers/{id}` | `/api/servers/{id}` | autenticato |
| Servers | Get | `/Servers/{id}` | `/api/servers/{id}` | autenticato |
| Servers | Put | `/Servers/{id}` | `/api/servers/{id}` | autenticato; SystemAdmin se cambio indirizzo/ambiente con credenziale |
| Servers | Get | `/Servers/{id}/Applications` | `/api/servers/{id}/applications` | autenticato |
| Servers | Post | `/Servers/{id}/Applications` | `/api/servers/{id}/applications` | autenticato |
| Servers | Delete | `/Servers/{id}/HostKey` | `/api/servers/{id}/host-key` | SystemAdmin |
| Servers | Put | `/Servers/{id}/ProviderEnvironment/{providerEnvironmentId}` | `/api/servers/{id}/provider-environment/{providerEnvironmentId}` | autenticato; SystemAdmin se cambio indirizzo/ambiente con credenziale |
| Servers | Get | `/Servers/{id}/ReachabilityTests` | `/api/servers/{id}/reachability-tests` | ServerOperator |
| Servers | Post | `/Servers/{id}/ReachabilityTests` | `/api/servers/{id}/reachability-tests` | ServerAdmin |
| Servers | Post | `/Servers/{id}/ReachabilityTests/Run` | `/api/servers/{id}/reachability-tests/run` | ServerOperator |
| Servers | Put | `/Servers/{id}/Ssh` | `/api/servers/{id}/ssh` | SystemAdmin |
| Topology | Get | `/Topology` | `/api/topology` | autenticato |
| Topology | Delete | `/Topology/Nodes/{nodeType}/{id}` | `/api/topology/nodes/{nodeType}/{id}` | autenticato (gap: delete sottoalbero) |
| Topology | Get | `/Topology/Nodes/{nodeType}/{id}/DeletePreview` | `/api/topology/nodes/{nodeType}/{id}/delete-preview` | autenticato |
| Users | Get | `/Users` | `/api/users` | autenticato |
| Users | Post | `/Users` | `/api/users` | SystemAdmin |
| Users | Get | `/Users/Paginated` | `/api/users` | autenticato |
| Users | Delete | `/Users/{id}` | `/api/users/{id}` | SystemAdmin |
| Users | Get | `/Users/{id}` | `/api/users/{id}` | autenticato |
| Users | Put | `/Users/{id}` | `/api/users/{id}` | SystemAdmin |
| socket | ANY | `/socket/Servers/{id}/Console` | `/api/socket/servers/{id}/console` | ServerAdmin |

## Eccezioni e note

- La colonna `Permesso legacy` descrive il comportamento dell'originale; il target D7 = B è in `docs/security/permissions.md`.
- `Enviroments` legacy → `environments` target; nessun alias in v1 (D10).
- `GET /X` e `GET /X/Paginated` convergono in `GET /api/x?page=&pageSize=`; risposta `{items,total,page,pageSize}`.
- `Auth/*` diventa BFF: `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout`, `GET /api/session`; i metodi target di login/callback sono GET. Gli endpoint token non sono esposti alla SPA.
- `socket/Servers/{id}/Console` → `GET /api/socket/servers/{id}/console` (upgrade WebSocket).
- `Topology/Nodes/{nodeType}/{id}` usa `nodeType` come stringa; il body della delete preview è `DeletePreview`.
- `ServerAccess/Me` → `GET /api/server-access/me`; `CommandExecutions/Paginated` → `GET /api/command-executions?page=`.
- Le route `ApplicationActions` top-level non hanno `POST`: la creazione è annidata in `Applications/{id}/Actions`.
- `Environments` legacy non ha `DELETE`; la v1 può aggiungerla con anteprima impatti (decisione in Fase 3).
