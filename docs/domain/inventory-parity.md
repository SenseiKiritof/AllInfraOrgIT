# Inventory — parity checklist (Phase 3)

Verification of 2026-10-25 based on `docs/domain/data-dictionary.md`, `docs/security/permissions.md` and `docs/ux/pages.md`. The reference is the legacy system, read-only.

## Implemented endpoints

| Area | Route | Read | Write | Test |
|---|---|---|---|---|
| Provider | `GET/POST /api/providers`, `GET/PUT/DELETE /api/providers/{id}` | authenticated | `SystemAdmin` | integration, dry-run, E2E |
| Environments | `GET/POST /api/environments`, `GET/PUT /api/environments/{id}` | authenticated | `SystemAdmin` | integration, E2E |
| Provider × environment | `GET/POST /api/provider-environments`, `GET/PUT/DELETE /api/provider-environments/{id}` | authenticated | `SystemAdmin` | integration, E2E |
| Roles per environment | `GET/POST /api/provider-environments/{id}/group-roles` (paginated list), `DELETE …/{groupRoleId}` | authenticated | `SystemAdmin` | integration |
| Server | `GET/POST /api/servers`, `GET/PUT/DELETE /api/servers/{id}` | authenticated | ServerAdmin on the environments involved | integration, E2E |
| Move server | `PUT /api/servers/{id}/provider-environment/{providerEnvironmentId}` | — | ServerAdmin on source and target; SystemAdmin if the server has a credential | integration |
| Server application | `GET/POST /api/servers/{id}/applications`, CRUD `/api/server-applications` | authenticated | ServerAdmin on the server's environment (both if the server changes) | integration, E2E |
| Applications | `GET/POST /api/applications`, `GET/PUT/DELETE /api/applications/{id}` | authenticated | `SystemAdmin` | integration, E2E |
| Versions | CRUD `/api/application-versions`, `GET/POST /api/applications/{id}/versions` (paginated list) | authenticated | `SystemAdmin` | integration, E2E |
| Application API | CRUD `/api/application-version-apis`, `GET/POST /api/application-versions/{id}/apis` (paginated list) | authenticated | `SystemAdmin` | integration, E2E |
| Query param | CRUD `/api/application-api-query-params`, `GET/POST /api/application-version-apis/{id}/query-params` (paginated list) | authenticated | `SystemAdmin` | integration |
| Projects | CRUD `/api/projects` | authenticated | `SystemAdmin` | integration, E2E |
| Application ↔ project link | `GET/POST/DELETE /api/projects/{id}/applications`, `GET/POST/DELETE /api/applications/{id}/projects` | authenticated | `SystemAdmin` | integration, E2E |
| Server access | `GET /api/server-access/me` | authenticated | — | integration |

Paginated lists `{items,total,page,pageSize}` with `page`, `pageSize` (max 200), `q`, `sort` where it makes sense. RFC 7807 errors with a stable `code`; 422 for validation, 404 for a missing resource, 403 for a missing role, 409 for constraints.

## Frontend pages

`/providers`, `/providers/{id}`, `/environments`, `/environments/{id}`, `/servers`, `/servers/{id}`, `/applications`, `/applications/{id}`, `/projects`, `/projects/{id}`.

- Tables with search and CRUD; actions hidden without permission (the API remains the source of truth).
- Server detail: master data, deployed applications with deploy/removal.
- Application detail: versions, APIs per version, query params per API, linked projects.
- Environment detail: master data and provider link.
- Provider/project detail: master data and links.

## Deliberate deviations from the legacy

1. **Deletes without destructive cascade.** The legacy deleted the subtree from the topology; here parents with children return 409 with the count. The `ApplicationProject` joins are the only ones with `ON DELETE CASCADE`. Rationale: avoid accidental deletion of servers or catalog entries; the impact preview arrives with topology (Phase 4).
2. **No environment delete.** Parity with the legacy; the target only considers it with an impact preview.
3. **Credentials and proxy not linked yet.** `Servers.CredentialId` and `ServerApplications.ProxyRouteId` exist as columns without FK: the entities arrive in Phase 5 and Phase 4. `credentialName` is always `null`.
4. **`ProxyRouteId` accepted from Phase 4** and validated: a non-existent id returns 404; the FK is active and deleting the route clears the link on the deploy.
5. **Role assignment per environment without UI.** The nested `group-roles` API exists and is used by tests and the dev environment; the admin page arrives in Phase 6.
6. **No delete-preview endpoint.** The 409 reports the dependency count; the structured preview is in Phase 4.
7. **Sorting limited** to exposed fields (`id`, `name`, `version`, `provider`, `environment`, `url`, `server`, `application`). The legacy sorted client-side.
8. **`SystemAdmin` is not enough for servers.** Consistent with D7 = B: `ServerAdmin` is required on the environment, except for credential exceptions that require `SystemAdmin`.
9. **Changing the provider/environment pair blocked with linked data.** If the pair has servers or role assignments, PUT returns 409: otherwise it would move servers and permissions without the `ServerAdmin` checks.

## Data differences

- `EnvironmentDefinition` replaces `Environments`; `ProviderEnvironment` is the pair. Route `/api/environments`, no `Enviroments` alias.
- `RequestType` and `QueryParamType` enums as strings, with a check constraint on the DB.
- `Version` as concurrency token; concurrent updates → 409 `concurrent_update`.
- UTC `CreatedAt`/`UpdatedAt` on every entity with a PK.

## Import dry-run (legacy-shaped fixture)

`Legacy_dry_run_maps_reference_and_catalog_fixture` loads `tests/InfraOrgIt.IntegrationTests/Legacy/Fixtures/legacy-reference-catalog.json`: a sanitized fixture with the **shape of the legacy tables** (explicit IDs, integer enums) for reference and catalog. The fixture is validated (uniqueness, FK, ports, lengths), mapped to the new entities and inserted into the test DB. The test verifies:

- IDs preserved (9101, 9001, 9401, 9501, 9601);
- legacy enums mapped (0 → `GET`, 4 → `DELETE`, 2 → `Bool`);
- consistent API reads for provider, provider/environment pairs, versions, APIs with query params and project links;
- provider delete blocked with 409.

`Legacy_fixture_rejects_orphan_foreign_keys` verifies that an orphan provider/environment pair is rejected before insertion.

The dry-run **with representative legacy data remains in Phase 7**: it requires a sanitized dump and the .NET importer. The committed reference seed contains only base master data; the full catalog is kept outside the repository.

## Phase 3 test coverage

- `InventoryApiTests` (13 integration tests, MySQL Testcontainers): write RBAC, provider CRUD, full catalog with version/API/query param updates, server with environment role, deploy and blocked delete, rejected proxy route, invalid filter, blocked pair change, project link, dry-run.
- `EntitySection.test.tsx`: table, creation, actions hidden without permission.
- `inventory.test.ts`: `saveEntity` creates on the collection and updates on the item (`/api/providers/{id}`).
- Playwright: provider created and updated → environment linked → application with version and APIs created and updated → project linked.

## Out of scope for Phase 3

SSH credentials and host key (Phase 5), proxy and topology (Phase 4), diagrams (Phase 4), application actions and reachability (Phase 5), users/groups/roles/menu management (Phase 6), real legacy import (Phase 7).
