# Admin e RBAC completo

Fase 6, 2026-10-26. Riferimento: `docs/security/permissions.md` (D7 = B) e ADR-005.

## Endpoint

| Area | Route | Lettura | Scrittura |
|---|---|---|---|
| Utenti | `GET/POST /api/users`, `GET/PUT/DELETE /api/users/{id}` | autenticati | `SystemAdmin` |
| Gruppi | `GET/POST /api/groups`, `GET/PUT/DELETE /api/groups/{id}` | autenticati | `SystemAdmin` |
| Ruoli | `GET/POST /api/roles`, `GET/PUT/DELETE /api/roles/{id}` (filtro `scopeEnum`) | autenticati | `SystemAdmin` |
| Menu | `GET /api/menus` (albero filtrato), `GET /api/menus/all`, `GET/PUT/DELETE /api/menus/{id}`, `POST /api/menus` | autenticati (`/all` SystemAdmin) | `SystemAdmin` |
| Assegnazioni ambiente | `GET/POST /api/provider-environment-group-roles`, `GET/PUT/DELETE /{id}`, nested `…/provider-environments/{id}/group-roles` | autenticati | `SystemAdmin` |

Liste paginate `{items,total,page,pageSize}`; `q`, `sort`, filtri dove indicato. Errori 403/404/409/422 coerenti.

## Regole

- Utenti: `username` unico, gruppi e ruoli risolti e validati; `PUT` sostituisce integralmente le assegnazioni.
- **Protezioni nuove** (scostamenti dal legacy, motivati):
  - non puoi eliminare il tuo utente (409);
  - deve restare almeno un `SystemAdmin` (409);
  - i ruoli `SystemAdmin`, `ServerAdmin`, `ServerOperator` non si eliminano e non cambiano nome o scope (409): il nome è usato dal RBAC;
  - un ruolo assegnato a utenti, menu o ambienti non si elimina (409);
  - un gruppo usato in assegnazioni ambiente non si elimina (409);
  - un menu con figli non si elimina (409).
- Menu: `parentId` validato (esistenza, self-parent, cicli); `roleIds` sincronizzati in create e update (il legacy non li aggiornava); nessun ruolo = visibile a tutti gli autenticati.
- Menu filtrato: ruoli di sistema dalla sessione **più** `ServerAdmin`/`ServerOperator` calcolati dagli ambienti del gruppo. Un menu assegnato a un ruolo d'ambiente è visibile a chi ha quel ruolo.
- Assegnazioni: solo ruoli con `ScopeEnum=Environment`; terna (`ProviderEnvironmentId`,`GroupId`,`RoleId`) unica → 409.
- `SystemAdmin` non concede server/console/run: i ruoli d'ambiente restano separati (`EnvironmentAccessService`).

## Frontend

- `/users`: CRUD con gruppi e ruoli a checkbox.
- `/groups`: CRUD gruppo e conteggio utenti.
- `/roles`: CRUD con scope e conteggi; i ruoli di sistema mostrano l'errore dell'API.
- `/menu`: albero piatto con padre, ordine, visibilità/attivo, ruoli.
- Dettaglio ambiente: sezione "Ruoli per ambiente" con gruppo + ruolo, create/delete.

## Test

- Test di integrazione `Admin_identity_and_menu_crud_with_guards`: letture aperte/scritture 403, CRUD gruppo/ruolo/utente, protezione ruoli di sistema, menu padre/figlio, assegnazione ambiente, menu visibile a `ServerOperator` via gruppo, self-delete 409, cleanup.
- `PageRequestTests`: `q` e `sort` letti dalle chiavi corrette (bug corretto in Fase 6).
- E2E `admin.spec.ts`: crea gruppo, ruolo, utente con assegnazioni, menu; elimina.
- Gate: 12 unit, 23 integrazione, 5 E2E, Vitest/Biome/tsc/build verdi.

## Limiti noti

- I ruoli di sistema nella sessione sono uno snapshot del login/refresh: una revoca di `SystemAdmin` ha effetto al refresh della sessione. I ruoli d'ambiente sono letti a ogni richiesta.
- Eliminare un utente non invalida subito le sue sessioni (lo store non ha remove-by-username): la sessione resta valida fino a scadenza/refresh. Da chiudere in Fase 8.
- Import utenti e `sub` Keycloak: Fase 7.
- Audit delle mutazioni admin non ancora registrato (Fase 8).
