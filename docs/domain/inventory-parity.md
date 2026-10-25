# Inventario — checklist di parità (Fase 3)

Verifica del 2026-10-25 sulla base di `docs/domain/data-dictionary.md`, `docs/security/permissions.md` e `docs/ux/pages.md`. Il riferimento è `../InfraOrgIT` in sola lettura.

## Endpoint implementati

| Area | Route | Lettura | Scrittura | Test |
|---|---|---|---|---|
| Provider | `GET/POST /api/providers`, `GET/PUT/DELETE /api/providers/{id}` | autenticati | `SystemAdmin` | integrazione, dry-run, E2E |
| Ambienti | `GET/POST /api/environments`, `GET/PUT /api/environments/{id}` | autenticati | `SystemAdmin` | integrazione, E2E |
| Provider × ambiente | `GET/POST /api/provider-environments`, `GET/PUT/DELETE /api/provider-environments/{id}` | autenticati | `SystemAdmin` | integrazione, E2E |
| Ruoli per ambiente | `GET/POST /api/provider-environments/{id}/group-roles`, `DELETE …/{groupRoleId}` | autenticati | `SystemAdmin` | integrazione |
| Server | `GET/POST /api/servers`, `GET/PUT/DELETE /api/servers/{id}` | autenticati | `ServerAdmin` sugli ambienti coinvolti | integrazione, E2E |
| Move server | `PUT /api/servers/{id}/provider-environment/{providerEnvironmentId}` | — | `ServerAdmin` su source e target; `SystemAdmin` se il server ha una credenziale | integrazione |
| Server application | `GET/POST /api/servers/{id}/applications`, CRUD `/api/server-applications` | autenticati | `ServerAdmin` sull'ambiente del server (entrambi se cambia server) | integrazione, E2E |
| Applicazioni | `GET/POST /api/applications`, `GET/PUT/DELETE /api/applications/{id}` | autenticati | `SystemAdmin` | integrazione, E2E |
| Versioni | CRUD `/api/application-versions`, `GET/POST /api/applications/{id}/versions` | autenticati | `SystemAdmin` | integrazione, E2E |
| API applicazione | CRUD `/api/application-version-apis`, `GET/POST /api/application-versions/{id}/apis` | autenticati | `SystemAdmin` | integrazione, E2E |
| Query param | CRUD `/api/application-api-query-params`, `GET/POST /api/application-version-apis/{id}/query-params` | autenticati | `SystemAdmin` | integrazione |
| Progetti | CRUD `/api/projects` | autenticati | `SystemAdmin` | integrazione, E2E |
| Link applicazione ↔ progetto | `GET/POST/DELETE /api/projects/{id}/applications`, `GET/POST/DELETE /api/applications/{id}/projects` | autenticati | `SystemAdmin` | integrazione, E2E |
| Server access | `GET /api/server-access/me` | autenticati | — | integrazione |

Liste paginate `{items,total,page,pageSize}` con `page`, `pageSize` (max 200), `q`, `sort` dove ha senso. Errori RFC 7807 con `code` stabile; 422 per validazione, 404 per risorsa assente, 403 per ruolo mancante, 409 per vincoli.

## Pagine frontend

`/providers`, `/providers/{id}`, `/environments`, `/environments/{id}`, `/servers`, `/servers/{id}`, `/applications`, `/applications/{id}`, `/projects`, `/projects/{id}`.

- Tabelle con ricerca e CRUD; azioni nascoste senza permesso (API resta la fonte di verità).
- Dettaglio server: anagrafica, applicazioni deployate con deploy/rimozione.
- Dettaglio applicazione: versioni, API per versione, query param per API, progetti collegati.
- Dettaglio ambiente: anagrafica e collegamento provider.
- Dettaglio provider/progetto: anagrafica e collegamenti.

## Scostamenti consapevoli dal legacy

1. **Delete senza cascata distruttiva.** Il legacy cancellava il sottoalbero dalla topologia; qui i padri con figli rispondono 409 con il conteggio. Le join `ApplicationProject` sono le uniche con `ON DELETE CASCADE`. Motivazione: evitare cancellazioni involontarie di server o catalogo; l'anteprima impatti arriva con la topologia (Fase 4).
2. **Nessuna delete ambiente.** Parità con il legacy; il target la valuta solo con anteprima impatti.
3. **Credenziali e proxy non ancora collegati.** `Servers.CredentialId` e `ServerApplications.ProxyRouteId` esistono come colonne senza FK: le entità arrivano in Fase 5 e Fase 4. `credentialName` è sempre `null`.
4. **`ProxyRouteId` rifiutato con 422** finché `ProxyRoutes` non esiste (Fase 4): un id pendente bloccherebbe la FK in migrazione.
5. **Assegnazione ruoli per ambiente senza UI.** L'API nested `group-roles` esiste ed è usata dai test e dall'ambiente di sviluppo; la pagina admin arriva in Fase 6.
6. **Nessun endpoint di delete preview.** Il 409 riporta il conteggio delle dipendenze; la preview strutturata è nella Fase 4.
7. **Ordinamento limitato** ai campi esposti (`id`, `name`, `version`, `provider`, `environment`, `url`, `server`, `application`). Il legacy ordinava lato client.
8. **`SystemAdmin` non basta per i server.** Coerente con D7 = B: serve `ServerAdmin` sull'ambiente, salvo le eccezioni credenziali che richiedono `SystemAdmin`.
9. **Cambio coppia provider/ambiente bloccato con dati collegati.** Se la coppia ha server o assegnazioni di ruolo, PUT risponde 409: altrimenti sposterebbe server e permessi senza i controlli di `ServerAdmin`.
10. **Liste annidate non paginate** (versioni, API, query param, group roles). Limite noto: paginare oltre ~100 righe; il catalogo attuale resta sotto.

## Differenze dati

- `EnvironmentDefinition` sostituisce `Environments`; `ProviderEnvironment` è la coppia. Route `/api/environments`, nessun alias `Enviroments`.
- Enum `RequestType` e `QueryParamType` come stringhe, con check constraint sul DB.
- `Version` come token di concorrenza; update concorrenti → 409 `concurrent_update`.
- `CreatedAt`/`UpdatedAt` UTC su ogni entità con PK.

## Dry-run di import (fixture sintetica)

`Inventory_dry_run_loads_reference_and_catalog_fixture` carica nel nuovo schema, tramite EF, un set rappresentativo: provider, ambiente, provider × ambiente, 2 server, applicazione, versione, API con query param, progetto e link applicazione-progetto. Poi verifica via API i conteggi e il blocco della delete del provider (409).

Il dry-run **con dati legacy reali resta in Fase 7**: richiede un dump sanificato, e `the legacy export` è vietato perché contiene dati locali reali. La fixture sintetica valida schema, relazioni e contratti senza usare dati cliente.

## Copertura test Fase 3

- `InventoryApiTests` (12 test di integrazione, MySQL Testcontainers): RBAC scritture, CRUD provider, catalogo completo con update di versione/API/query param, server con ruolo d'ambiente, deploy e delete bloccata, proxy route rifiutata, filtro non valido, cambio coppia bloccato, link progetto, dry-run.
- `EntitySection.test.tsx`: tabella, creazione, azioni nascoste senza permesso.
- `inventory.test.ts`: `saveEntity` crea sulla collezione e aggiorna sull'elemento (`/api/providers/{id}`).
- Playwright: provider creato e modificato → ambiente collegato → applicazione con versione e API create e modificate → progetto collegato.

## Fuori perimetro Fase 3

Credenziali SSH e host key (Fase 5), proxy e topologia (Fase 4), diagrammi (Fase 4), azioni applicazione e reachability (Fase 5), gestione utenti/gruppi/ruoli/menu (Fase 6), import legacy reale (Fase 7).
