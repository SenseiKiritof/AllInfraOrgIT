# Legacy → target route inventory

Generated from the legacy code `InfraOrgIt/MinimalApis` on 2026-10-25. 168 HTTP operations + 1 WebSocket.

`/Paginated` is merged into the list with `page`/`pageSize`; the target routes are the v1 proposal, not implemented.

| Group | Method | Legacy route | Target route | Legacy permission |
|---|---|---|---|---|
|---|---|---|---|---|
| ApplicationActions | Delete | `/ApplicationActions/{id}` | `/api/application-actions/{id}` | SystemAdmin |
| ApplicationActions | Put | `/ApplicationActions/{id}` | `/api/application-actions/{id}` | SystemAdmin |
| ApplicationApiQueryParams | Get | `/ApplicationApiQueryParams` | `/api/application-api-query-params` | authenticated |
| ApplicationApiQueryParams | Post | `/ApplicationApiQueryParams` | `/api/application-api-query-params` | authenticated |
| ApplicationApiQueryParams | Get | `/ApplicationApiQueryParams/Paginated` | `/api/application-api-query-params` | authenticated |
| ApplicationApiQueryParams | Delete | `/ApplicationApiQueryParams/{id}` | `/api/application-api-query-params/{id}` | authenticated |
| ApplicationApiQueryParams | Get | `/ApplicationApiQueryParams/{id}` | `/api/application-api-query-params/{id}` | authenticated |
| ApplicationApiQueryParams | Put | `/ApplicationApiQueryParams/{id}` | `/api/application-api-query-params/{id}` | authenticated |
| ApplicationVersionApis | Get | `/ApplicationVersionApis` | `/api/application-version-apis` | authenticated |
| ApplicationVersionApis | Post | `/ApplicationVersionApis` | `/api/application-version-apis` | authenticated |
| ApplicationVersionApis | Get | `/ApplicationVersionApis/Paginated` | `/api/application-version-apis` | authenticated |
| ApplicationVersionApis | Delete | `/ApplicationVersionApis/{id}` | `/api/application-version-apis/{id}` | authenticated |
| ApplicationVersionApis | Get | `/ApplicationVersionApis/{id}` | `/api/application-version-apis/{id}` | authenticated |
| ApplicationVersionApis | Put | `/ApplicationVersionApis/{id}` | `/api/application-version-apis/{id}` | authenticated |
| ApplicationVersionApis | Get | `/ApplicationVersionApis/{id}/QueryParams` | `/api/application-version-apis/{id}/query-params` | authenticated |
| ApplicationVersionApis | Post | `/ApplicationVersionApis/{id}/QueryParams` | `/api/application-version-apis/{id}/query-params` | authenticated |
| ApplicationVersions | Get | `/ApplicationVersions` | `/api/application-versions` | authenticated |
| ApplicationVersions | Post | `/ApplicationVersions` | `/api/application-versions` | authenticated |
| ApplicationVersions | Get | `/ApplicationVersions/Paginated` | `/api/application-versions` | authenticated |
| ApplicationVersions | Delete | `/ApplicationVersions/{id}` | `/api/application-versions/{id}` | authenticated |
| ApplicationVersions | Get | `/ApplicationVersions/{id}` | `/api/application-versions/{id}` | authenticated |
| ApplicationVersions | Put | `/ApplicationVersions/{id}` | `/api/application-versions/{id}` | authenticated |
| ApplicationVersions | Get | `/ApplicationVersions/{id}/Apis` | `/api/application-versions/{id}/apis` | authenticated |
| ApplicationVersions | Post | `/ApplicationVersions/{id}/Apis` | `/api/application-versions/{id}/apis` | authenticated |
| Applications | Get | `/Applications` | `/api/applications` | authenticated |
| Applications | Post | `/Applications` | `/api/applications` | authenticated |
| Applications | Get | `/Applications/Paginated` | `/api/applications` | authenticated |
| Applications | Delete | `/Applications/{id}` | `/api/applications/{id}` | authenticated |
| Applications | Get | `/Applications/{id}` | `/api/applications/{id}` | authenticated |
| Applications | Put | `/Applications/{id}` | `/api/applications/{id}` | authenticated |
| Applications | Get | `/Applications/{id}/Actions` | `/api/applications/{id}/actions` | SystemAdmin |
| Applications | Post | `/Applications/{id}/Actions` | `/api/applications/{id}/actions` | SystemAdmin |
| Applications | Get | `/Applications/{id}/Projects` | `/api/applications/{id}/projects` | authenticated |
| Applications | Post | `/Applications/{id}/Projects` | `/api/applications/{id}/projects` | authenticated |
| Applications | Delete | `/Applications/{id}/Projects/{projectId}` | `/api/applications/{id}/projects/{projectId}` | authenticated |
| Applications | Get | `/Applications/{id}/Versions` | `/api/applications/{id}/versions` | authenticated |
| Applications | Post | `/Applications/{id}/Versions` | `/api/applications/{id}/versions` | authenticated |
| Auth | Get | `/Auth/CurrentUser` | `/api/session` | authenticated |
| Auth | Post | `/Auth/Login` | `/auth/login` | anonymous |
| Auth | Post | `/Auth/Logout` | `/auth/logout` | anonymous |
| Auth | Post | `/Auth/RefreshToken` | `— (server-side refresh)` | anonymous |
| Auth | Post | `/Auth/Token` | `/auth/callback` | anonymous |
| CommandExecutions | Get | `/CommandExecutions/Paginated` | `/api/command-executions` | SystemAdmin |
| CommandTemplates | Get | `/CommandTemplates` | `/api/command-templates` | SystemAdmin |
| CommandTemplates | Post | `/CommandTemplates` | `/api/command-templates` | SystemAdmin |
| CommandTemplates | Get | `/CommandTemplates/Paginated` | `/api/command-templates` | SystemAdmin |
| CommandTemplates | Delete | `/CommandTemplates/{id}` | `/api/command-templates/{id}` | SystemAdmin |
| CommandTemplates | Get | `/CommandTemplates/{id}` | `/api/command-templates/{id}` | SystemAdmin |
| CommandTemplates | Put | `/CommandTemplates/{id}` | `/api/command-templates/{id}` | SystemAdmin |
| Diagrams | Get | `/Diagrams` | `/api/diagrams` | authenticated |
| Diagrams | Post | `/Diagrams` | `/api/diagrams` | authenticated |
| Diagrams | Get | `/Diagrams/Paginated` | `/api/diagrams` | authenticated |
| Diagrams | Delete | `/Diagrams/{id}` | `/api/diagrams/{id}` | authenticated |
| Diagrams | Get | `/Diagrams/{id}` | `/api/diagrams/{id}` | authenticated |
| Diagrams | Put | `/Diagrams/{id}` | `/api/diagrams/{id}` | authenticated |
| Diagrams | Put | `/Diagrams/{id}/Edges` | `/api/diagrams/{id}/edges` | authenticated |
| Diagrams | Get | `/Diagrams/{id}/Graph` | `/api/diagrams/{id}/graph` | authenticated |
| Diagrams | Put | `/Diagrams/{id}/Nodes` | `/api/diagrams/{id}/nodes` | authenticated |
| Enviroments | Get | `/Enviroments` | `/api/environments` | authenticated |
| Enviroments | Post | `/Enviroments` | `/api/environments` | authenticated |
| Enviroments | Get | `/Enviroments/Paginated` | `/api/environments` | authenticated |
| Enviroments | Get | `/Enviroments/{id}` | `/api/environments/{id}` | authenticated |
| Enviroments | Put | `/Enviroments/{id}` | `/api/environments/{id}` | authenticated |
| Groups | Get | `/Groups` | `/api/groups` | authenticated |
| Groups | Post | `/Groups` | `/api/groups` | SystemAdmin |
| Groups | Get | `/Groups/Paginated` | `/api/groups` | authenticated |
| Groups | Delete | `/Groups/{id}` | `/api/groups/{id}` | SystemAdmin |
| Groups | Get | `/Groups/{id}` | `/api/groups/{id}` | authenticated |
| Groups | Put | `/Groups/{id}` | `/api/groups/{id}` | SystemAdmin |
| Menus | Get | `/Menus` | `/api/menus` | authenticated |
| Menus | Post | `/Menus` | `/api/menus` | SystemAdmin |
| Menus | Get | `/Menus/Paginated` | `/api/menus` | authenticated |
| Menus | Delete | `/Menus/{id}` | `/api/menus/{id}` | SystemAdmin |
| Menus | Get | `/Menus/{id}` | `/api/menus/{id}` | authenticated |
| Menus | Put | `/Menus/{id}` | `/api/menus/{id}` | SystemAdmin |
| Projects | Get | `/Projects` | `/api/projects` | authenticated |
| Projects | Post | `/Projects` | `/api/projects` | authenticated |
| Projects | Get | `/Projects/Paginated` | `/api/projects` | authenticated |
| Projects | Delete | `/Projects/{id}` | `/api/projects/{id}` | authenticated |
| Projects | Get | `/Projects/{id}` | `/api/projects/{id}` | authenticated |
| Projects | Put | `/Projects/{id}` | `/api/projects/{id}` | authenticated |
| Projects | Get | `/Projects/{id}/Applications` | `/api/projects/{id}/applications` | authenticated |
| Projects | Post | `/Projects/{id}/Applications` | `/api/projects/{id}/applications` | authenticated |
| Projects | Delete | `/Projects/{id}/Applications/{applicationId}` | `/api/projects/{id}/applications/{applicationId}` | authenticated |
| ProviderEnvironmentGroupRoles | Get | `/ProviderEnvironmentGroupRoles` | `/api/provider-environment-group-roles` | authenticated |
| ProviderEnvironmentGroupRoles | Post | `/ProviderEnvironmentGroupRoles` | `/api/provider-environment-group-roles` | SystemAdmin |
| ProviderEnvironmentGroupRoles | Get | `/ProviderEnvironmentGroupRoles/Paginated` | `/api/provider-environment-group-roles` | authenticated |
| ProviderEnvironmentGroupRoles | Delete | `/ProviderEnvironmentGroupRoles/{id}` | `/api/provider-environment-group-roles/{id}` | SystemAdmin |
| ProviderEnvironmentGroupRoles | Get | `/ProviderEnvironmentGroupRoles/{id}` | `/api/provider-environment-group-roles/{id}` | authenticated |
| ProviderEnvironmentGroupRoles | Put | `/ProviderEnvironmentGroupRoles/{id}` | `/api/provider-environment-group-roles/{id}` | SystemAdmin |
| ProviderEnvironments | Get | `/ProviderEnvironments` | `/api/provider-environments` | authenticated |
| ProviderEnvironments | Post | `/ProviderEnvironments` | `/api/provider-environments` | authenticated |
| ProviderEnvironments | Get | `/ProviderEnvironments/Paginated` | `/api/provider-environments` | authenticated |
| ProviderEnvironments | Delete | `/ProviderEnvironments/{id}` | `/api/provider-environments/{id}` | authenticated |
| ProviderEnvironments | Get | `/ProviderEnvironments/{id}` | `/api/provider-environments/{id}` | authenticated |
| ProviderEnvironments | Put | `/ProviderEnvironments/{id}` | `/api/provider-environments/{id}` | authenticated |
| ProviderEnvironments | Post | `/ProviderEnvironments/{id}/ReachabilityTests/Run` | `/api/provider-environments/{id}/reachability-tests/run` | ServerOperator |
| ProviderEnvironments | Get | `/ProviderEnvironments/{providerEnvironmentId}/GroupRoles` | `/api/provider-environments/{providerEnvironmentId}/group-roles` | authenticated |
| ProviderEnvironments | Post | `/ProviderEnvironments/{providerEnvironmentId}/GroupRoles` | `/api/provider-environments/{providerEnvironmentId}/group-roles` | SystemAdmin |
| ProviderEnvironments | Delete | `/ProviderEnvironments/{providerEnvironmentId}/GroupRoles/{groupRoleId}` | `/api/provider-environments/{providerEnvironmentId}/group-roles/{groupRoleId}` | SystemAdmin |
| Providers | Get | `/Providers` | `/api/providers` | authenticated |
| Providers | Post | `/Providers` | `/api/providers` | authenticated |
| Providers | Get | `/Providers/Paginated` | `/api/providers` | authenticated |
| Providers | Delete | `/Providers/{id}` | `/api/providers/{id}` | authenticated |
| Providers | Get | `/Providers/{id}` | `/api/providers/{id}` | authenticated |
| Providers | Put | `/Providers/{id}` | `/api/providers/{id}` | authenticated |
| ProxyConnections | Get | `/ProxyConnections` | `/api/proxy-connections` | authenticated |
| ProxyConnections | Post | `/ProxyConnections` | `/api/proxy-connections` | authenticated |
| ProxyConnections | Get | `/ProxyConnections/Paginated` | `/api/proxy-connections` | authenticated |
| ProxyConnections | Delete | `/ProxyConnections/{id}` | `/api/proxy-connections/{id}` | authenticated |
| ProxyConnections | Get | `/ProxyConnections/{id}` | `/api/proxy-connections/{id}` | authenticated |
| ProxyConnections | Put | `/ProxyConnections/{id}` | `/api/proxy-connections/{id}` | authenticated |
| ProxyConnections | Get | `/ProxyConnections/{id}/Routes` | `/api/proxy-connections/{id}/routes` | authenticated |
| ProxyConnections | Post | `/ProxyConnections/{id}/Routes` | `/api/proxy-connections/{id}/routes` | authenticated |
| ProxyRoutes | Get | `/ProxyRoutes` | `/api/proxy-routes` | authenticated |
| ProxyRoutes | Post | `/ProxyRoutes` | `/api/proxy-routes` | authenticated |
| ProxyRoutes | Get | `/ProxyRoutes/Paginated` | `/api/proxy-routes` | authenticated |
| ProxyRoutes | Delete | `/ProxyRoutes/{id}` | `/api/proxy-routes/{id}` | authenticated |
| ProxyRoutes | Get | `/ProxyRoutes/{id}` | `/api/proxy-routes/{id}` | authenticated |
| ProxyRoutes | Put | `/ProxyRoutes/{id}` | `/api/proxy-routes/{id}` | authenticated |
| ReachabilityTests | Get | `/ReachabilityTests` | `/api/reachability-tests` | SystemAdmin |
| ReachabilityTests | Post | `/ReachabilityTests` | `/api/reachability-tests` | SystemAdmin |
| ReachabilityTests | Delete | `/ReachabilityTests/{id}` | `/api/reachability-tests/{id}` | SystemAdmin |
| ReachabilityTests | Put | `/ReachabilityTests/{id}` | `/api/reachability-tests/{id}` | SystemAdmin |
| Roles | Get | `/Roles` | `/api/roles` | authenticated |
| Roles | Post | `/Roles` | `/api/roles` | SystemAdmin |
| Roles | Get | `/Roles/Paginated` | `/api/roles` | authenticated |
| Roles | Delete | `/Roles/{id}` | `/api/roles/{id}` | SystemAdmin |
| Roles | Get | `/Roles/{id}` | `/api/roles/{id}` | authenticated |
| Roles | Put | `/Roles/{id}` | `/api/roles/{id}` | SystemAdmin |
| ServerAccess | Get | `/ServerAccess/Me` | `/api/server-access/me` | authenticated |
| ServerApplications | Get | `/ServerApplications` | `/api/server-applications` | authenticated |
| ServerApplications | Post | `/ServerApplications` | `/api/server-applications` | authenticated |
| ServerApplications | Get | `/ServerApplications/Paginated` | `/api/server-applications` | authenticated |
| ServerApplications | Delete | `/ServerApplications/{id}` | `/api/server-applications/{id}` | authenticated |
| ServerApplications | Get | `/ServerApplications/{id}` | `/api/server-applications/{id}` | authenticated |
| ServerApplications | Put | `/ServerApplications/{id}` | `/api/server-applications/{id}` | authenticated |
| ServerApplications | Get | `/ServerApplications/{id}/Actions` | `/api/server-applications/{id}/actions` | ServerOperator |
| ServerApplications | Post | `/ServerApplications/{id}/Actions/{actionId}/Run` | `/api/server-applications/{id}/actions/{actionId}/run` | ServerOperator |
| ServerCredentials | Get | `/ServerCredentials` | `/api/server-credentials` | SystemAdmin |
| ServerCredentials | Post | `/ServerCredentials` | `/api/server-credentials` | SystemAdmin |
| ServerCredentials | Get | `/ServerCredentials/Paginated` | `/api/server-credentials` | SystemAdmin |
| ServerCredentials | Delete | `/ServerCredentials/{id}` | `/api/server-credentials/{id}` | SystemAdmin |
| ServerCredentials | Get | `/ServerCredentials/{id}` | `/api/server-credentials/{id}` | SystemAdmin |
| ServerCredentials | Put | `/ServerCredentials/{id}` | `/api/server-credentials/{id}` | SystemAdmin |
| Servers | Get | `/Servers` | `/api/servers` | authenticated |
| Servers | Post | `/Servers` | `/api/servers` | authenticated |
| Servers | Get | `/Servers/Paginated` | `/api/servers` | authenticated |
| Servers | Delete | `/Servers/{id}` | `/api/servers/{id}` | authenticated |
| Servers | Get | `/Servers/{id}` | `/api/servers/{id}` | authenticated |
| Servers | Put | `/Servers/{id}` | `/api/servers/{id}` | authenticated; SystemAdmin if changing address/environment with a credential |
| Servers | Get | `/Servers/{id}/Applications` | `/api/servers/{id}/applications` | authenticated |
| Servers | Post | `/Servers/{id}/Applications` | `/api/servers/{id}/applications` | authenticated |
| Servers | Delete | `/Servers/{id}/HostKey` | `/api/servers/{id}/host-key` | SystemAdmin |
| Servers | Put | `/Servers/{id}/ProviderEnvironment/{providerEnvironmentId}` | `/api/servers/{id}/provider-environment/{providerEnvironmentId}` | authenticated; SystemAdmin if changing address/environment with a credential |
| Servers | Get | `/Servers/{id}/ReachabilityTests` | `/api/servers/{id}/reachability-tests` | ServerOperator |
| Servers | Post | `/Servers/{id}/ReachabilityTests` | `/api/servers/{id}/reachability-tests` | ServerAdmin |
| Servers | Post | `/Servers/{id}/ReachabilityTests/Run` | `/api/servers/{id}/reachability-tests/run` | ServerOperator |
| Servers | Put | `/Servers/{id}/Ssh` | `/api/servers/{id}/ssh` | SystemAdmin |
| Topology | Get | `/Topology` | `/api/topology` | authenticated |
| Topology | Delete | `/Topology/Nodes/{nodeType}/{id}` | `/api/topology/nodes/{nodeType}/{id}` | authenticated (gap: subtree delete) |
| Topology | Get | `/Topology/Nodes/{nodeType}/{id}/DeletePreview` | `/api/topology/nodes/{nodeType}/{id}/delete-preview` | authenticated |
| Users | Get | `/Users` | `/api/users` | authenticated |
| Users | Post | `/Users` | `/api/users` | SystemAdmin |
| Users | Get | `/Users/Paginated` | `/api/users` | authenticated |
| Users | Delete | `/Users/{id}` | `/api/users/{id}` | SystemAdmin |
| Users | Get | `/Users/{id}` | `/api/users/{id}` | authenticated |
| Users | Put | `/Users/{id}` | `/api/users/{id}` | SystemAdmin |
| socket | ANY | `/socket/Servers/{id}/Console` | `/api/socket/servers/{id}/console` | ServerAdmin |

## Exceptions and notes

- The `Legacy permission` column describes the behaviour of the original; target D7 = B is in `docs/security/permissions.md`.
- Legacy `Enviroments` → target `environments`; no alias in v1 (D10).
- `GET /X` and `GET /X/Paginated` converge into `GET /api/x?page=&pageSize=`; response `{items,total,page,pageSize}`.
- `Auth/*` becomes a BFF: `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout`, `GET /api/session`; the target methods for login/callback are GET. The token endpoints are not exposed to the SPA.
- `socket/Servers/{id}/Console` → `GET /api/socket/servers/{id}/console` (WebSocket upgrade).
- `Topology/Nodes/{nodeType}/{id}` uses `nodeType` as a string; the delete preview body is `DeletePreview`.
- `ServerAccess/Me` → `GET /api/server-access/me`; `CommandExecutions/Paginated` → `GET /api/command-executions?page=`.
- Top-level `ApplicationActions` routes have no `POST`: creation is nested under `Applications/{id}/Actions`.
- Legacy `Environments` has no `DELETE`; v1 may add it with impact preview (decision in Phase 3).
