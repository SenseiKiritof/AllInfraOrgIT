# Matrice permessi

Verificata sul backend legacy il 2026-10-25 (`MinimalApis/*`, `ServerAccessService`, `SystemAdminWriteFilter`, `Services/*`).

## Ruoli

| Ruolo | Scope | Dove vive |
|---|---|---|
| `SystemAdmin` | sistema | `Users.Roles` |
| `ServerAdmin` | `ProviderEnvironment` | `ProviderEnvironmentGroupRoles` via gruppo utente |
| `ServerOperator` | `ProviderEnvironment` | `ProviderEnvironmentGroupRoles` via gruppo utente |

`SystemAdmin` **non** implica `ServerAdmin`/`ServerOperator`. Un `ServerAdmin` è anche operatore sul proprio ambiente (`OperatorEnvironmentIds` include gli admin).

## Autenticazione

- Tutte le route `/api/*` richiedono un token, tranne `Auth/Login`, `Auth/Token`, `Auth/RefreshToken`, `Auth/Logout`.
- Il token arriva da cookie HttpOnly; la console WebSocket accetta anche `access_token` in query string (solo `/api/socket`).
- La console controlla `Origin` contro `FeConn.Host`.
- Non esiste un token CSRF esplicito: le mutazioni si affidano a `SameSite=Strict` e al content-type JSON.

## Matrice effettiva (legacy)

| Area / route | Lettura | Scrittura | Note verificate |
|---|---|---|---|
| Providers, Enviroments, ProviderEnvironments | autenticati | **autenticati** | nessun filtro; `Enviroments` è il typo legacy |
| Servers | autenticati | **autenticati** | `PUT /Servers/{id}` richiede SystemAdmin solo se il server ha una credenziale e cambia IP/hostname/ambiente; `MoveServer` idem |
| ServerApplications, ProxyConnections, ProxyRoutes, Projects | autenticati | **autenticati** | nessun filtro |
| Applications, ApplicationVersions, ApplicationVersionApis, ApplicationApiQueryParams | autenticati | **autenticati** | nessun filtro |
| Diagrams | autenticati | **autenticati** | nessun filtro; `IsDefault` unico gestito dal servizio |
| Topology (`GET`, delete nodo, delete preview) | autenticati | **autenticati** | la delete cancella il sottoalbero: superficie distruttiva aperta |
| Users, Groups, Roles, Menus, ProviderEnvironmentGroupRoles | autenticati | `SystemAdmin` | `SystemAdminWriteFilter` su POST/PUT/DELETE |
| ServerCredentials (incluse `/Servers/{id}/Ssh`, `/HostKey`) | `SystemAdmin` | `SystemAdmin` | letture e scritture protette |
| CommandTemplates | `SystemAdmin` | `SystemAdmin` | letture e scritture protette |
| ApplicationActions config (`GET/POST` per applicazione, `PUT/DELETE`) | `SystemAdmin` | `SystemAdmin` | gli operatori non vedono script/parametri |
| ApplicationActions deploy (`GET` bottoni, `POST .../Run`) | `ServerOperator` | `ServerOperator` | `ServerAdmin` incluso |
| ReachabilityTests globali (`/ReachabilityTests`) | `SystemAdmin` | `SystemAdmin` | la run è solo per server o ambiente |
| ReachabilityTests per server | `ServerOperator` | `ServerAdmin` | `GET` e run = Operator; CRUD = Admin |
| Reachability run per ambiente | — | `ServerOperator` | `POST /ProviderEnvironments/{id}/ReachabilityTests/Run` |
| CommandExecutions (audit) | `SystemAdmin` | — | filtro e paginazione lato server |
| ServerAccess (`/ServerAccess/Me`) | autenticati | — | restituisce ambienti admin/operator |
| Console SSH (`/socket/Servers/{id}/Console`) | `ServerAdmin` | — | Origin obbligatoria; nessun `SystemAdmin` implicito |
| Auth/CurrentUser | autenticati | — | |

## Gap verificati

1. **Scritture inventario aperte a ogni autenticato.** Un utente senza ruoli può creare/modificare/eliminare provider, ambienti, server, applicazioni, progetti, proxy e diagrammi. Può anche cancellare un sottoalbero dalla topologia (`DELETE /Topology/Nodes/...`). È il gap più ampio.
2. **Menu non filtrato dal ruolo.** `MenusService.GetMenus` restituisce tutte le voci e non carica `Menu.Roles`; la tabella `MenuRole` non ha effetto sul menu. La UI mostra le pagine admin a tutti (le scritture poi falliscono).
3. **Nessuna delete ambiente.** `EnviromentsApi` espone GET/POST/PUT, non DELETE; il nuovo CRUD dovrà decidere se aggiungerla con anteprima impatti.
4. **CSRF implicito.** Non c'è un token CSRF; `SameSite=Strict` protegge, ma la difesa non è esplicita e non è testata.
5. **Audit incompleto sulle scritture inventario.** Non c'è audit per create/update/delete di inventario e diagrammi; solo le esecuzioni remote sono registrate.

## Target v1 (proposta, D7 aperta)

Mantenere la matrice attuale come baseline documentata, con due correzioni non negoziabili:

- **Menu filtrato**: `GET /api/menus` restituisce solo le voci visibili ai ruoli dell'utente; `MenuRole` diventa effettivo; test per ogni ruolo.
- **CSRF esplicito** su tutte le mutazioni, oltre a `Origin` e `SameSite`.

Per il resto, D7 resta aperta. Le opzioni:

- **A — Preservare** (default del piano): scritture inventario a tutti gli autenticati, documentate e coperte da test. Rapido, ma lascia il gap 1.
- **B — Tightening**: scritture inventario richiedono `SystemAdmin` per le anagrafiche globali (provider, ambienti, catalogo) e `ServerAdmin` sull'ambiente per server, deploy, proxy e diagrammi che lo contengono. Più sicuro, ma cambia il flusso e richiede una matrice di test più ampia.

La UI deve comunque nascondere le azioni non consentite; l'API resta la fonte di verità (403, non 404, per risorse esistenti).

## Test da scrivere in Fase 2–6

- `SystemAdmin` senza ruoli ambiente: console e run devono fallire.
- `ServerAdmin` su ambiente A: console A ok, ambiente B 403, run A ok, CRUD credenziali 403.
- `ServerOperator` su A: run A ok, console A 403, CRUD reachability A 403.
- Utente autenticato senza ruoli: letture ok; scritture secondo D7.
- Menu: ogni ruolo vede solo le voci assegnate.
- CSRF: mutazione senza token → 403; `Origin` estranea → 403.
