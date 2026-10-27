# Admin and complete RBAC

Phase 6, 2026-10-26. Reference: `docs/security/permissions.md` (D7 = B) and ADR-005.

## Endpoints

| Area | Route | Read | Write |
|---|---|---|---|
| Users | `GET/POST /api/users`, `GET/PUT/DELETE /api/users/{id}` | authenticated | `SystemAdmin` |
| Groups | `GET/POST /api/groups`, `GET/PUT/DELETE /api/groups/{id}` | authenticated | `SystemAdmin` |
| Roles | `GET/POST /api/roles`, `GET/PUT/DELETE /api/roles/{id}` (filter `scopeEnum`) | authenticated | `SystemAdmin` |
| Menu | `GET /api/menus` (filtered tree), `GET /api/menus/all`, `GET/PUT/DELETE /api/menus/{id}`, `POST /api/menus` | authenticated (`/all` SystemAdmin) | `SystemAdmin` |
| Environment assignments | `GET/POST /api/provider-environment-group-roles`, `GET/PUT/DELETE /{id}`, nested `…/provider-environments/{id}/group-roles` | authenticated | `SystemAdmin` |

Paginated lists `{items,total,page,pageSize}`; `q`, `sort`, filters where indicated. Consistent 403/404/409/422 errors.

## Rules

- Users: unique `username`, groups and roles resolved and validated; `PUT` fully replaces assignments.
- **New protections** (justified deviations from the legacy):
  - you cannot delete your own user (409);
  - at least one `SystemAdmin` must remain (409);
  - the `SystemAdmin`, `ServerAdmin`, `ServerOperator` roles cannot be deleted and cannot change name or scope (409): the name is used by RBAC;
  - a role assigned to users, menus or environments cannot be deleted (409);
  - a group used in environment assignments cannot be deleted (409);
  - a menu with children cannot be deleted (409).
- Menu: `parentId` validated (existence, self-parent, cycles); `roleIds` synchronized on create and update (the legacy did not update them); no role = visible to all authenticated users.
- Filtered menu: system roles from the session **plus** `ServerAdmin`/`ServerOperator` computed from the group's environments. A menu assigned to an environment role is visible to anyone holding that role.
- Assignments: only roles with `ScopeEnum=Environment`; unique triple (`ProviderEnvironmentId`,`GroupId`,`RoleId`) → 409.
- `SystemAdmin` does not grant server/console/run: environment roles stay separate (`EnvironmentAccessService`).

## Frontend

- `/users`: CRUD with groups and roles as checkboxes.
- `/groups`: group CRUD and user count.
- `/roles`: CRUD with scope and counts; system roles show the API error.
- `/menu`: flat tree with parent, order, visibility/active, roles.
- Environment detail: "Roles per environment" section with group + role, create/delete.

## Tests

- Integration test `Admin_identity_and_menu_crud_with_guards`: reads open/writes 403, group/role/user CRUD, system role protection, parent/child menu, environment assignment, menu visible to `ServerOperator` via group, self-delete 409, cleanup.
- `PageRequestTests`: `q` and `sort` read from the correct keys (bug fixed in Phase 6).
- E2E `admin.spec.ts`: creates group, role, user with assignments, menu; deletes them.
- Gate: 12 unit, 23 integration, 5 E2E, Vitest/Biome/tsc/build green.

## Known limits

- System roles in the session are a snapshot from login/refresh: revoking `SystemAdmin` takes effect at session refresh. Environment roles are read on every request.
- Deleting a user does not immediately invalidate their sessions (the store has no remove-by-username): the session stays valid until expiry/refresh. To be closed in Phase 8.
- User import and Keycloak `sub`: Phase 7.
- Admin mutation audit not recorded yet (Phase 8).
