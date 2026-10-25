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

## Target v1 — D7 = B (deciso 2026-10-25)

Tightening per ambiente. Le letture restano aperte a ogni autenticato; cambiano le scritture.

Regole generali:

- **Anagrafiche globali** → `SystemAdmin`.
- **Risorse legate a uno o più ambienti** → `ServerAdmin` su **tutti** gli ambienti coinvolti. `SystemAdmin` da solo non basta: la separazione dei ruoli per ambiente resta.
- Se un'operazione tocca entità in ambienti diversi (proxy source→target, deploy con route, move di un server), servono i ruoli su tutti gli ambienti coinvolti.
- **Eccezione credenziali**: assegnazione SSH, reset host key e cambio indirizzo/ambiente di un server con credenziale restano `SystemAdmin`, come nell'originale; non richiedono `ServerAdmin`.
- La UI nasconde le azioni non consentite; l'API resta la fonte di verità (403, non 404, per risorse esistenti).
- **Menu filtrato** da `MenuRole` e **CSRF esplicito** su tutte le mutazioni, oltre a `Origin` e `SameSite`.

### Matrice target

| Operazione | Ruolo richiesto |
|---|---|
| CRUD Providers, EnvironmentDefinitions, ProviderEnvironments | `SystemAdmin` |
| CRUD Applications, ApplicationVersions, ApplicationVersionApis, ApplicationApiQueryParams, Projects | `SystemAdmin` |
| CRUD Users, Groups, Roles, Menus, ProviderEnvironmentGroupRoles | `SystemAdmin` |
| CRUD ServerCredentials; assegnazione SSH; reset host key | `SystemAdmin` |
| CRUD CommandTemplates; config ApplicationActions | `SystemAdmin` |
| ReachabilityTests globali (CRUD e run) | `SystemAdmin` |
| Lettura CommandExecutions (audit) | `SystemAdmin` |
| Creazione/modifica/delete Server | `ServerAdmin` sull'ambiente del server |
| Move Server tra ambienti | `ServerAdmin` su source e target; `SystemAdmin` se il server ha una credenziale |
| Cambio IP/hostname di un server con credenziale | `SystemAdmin` |
| CRUD ServerApplications | `ServerAdmin` sull'ambiente del server; se la route target è in un altro ambiente, `ServerAdmin` anche lì |
| CRUD ProxyConnections | `ServerAdmin` sugli ambienti di source e target |
| CRUD ProxyRoutes | `ServerAdmin` sugli ambienti della connessione e del target (ServerApplication o ProxyConnection) |
| CRUD Diagrammi e salvataggio nodi/edge, diagramma default o globale | `SystemAdmin` |
| CRUD Diagrammi con soli scope `ProviderEnvironment` | `ServerAdmin` su tutti gli ambienti in scope |
| Cambio scope di un diagramma | unione vecchi/nuovi scope; se compare `Provider`, `Project` o default → `SystemAdmin` |
| Delete nodo Topology `Provider` o `ProviderEnvironment` | `SystemAdmin` |
| Delete nodo Topology `Server` o `ServerApplication` | `ServerAdmin` su tutti gli ambienti toccati dalla cascata |
| Console SSH | `ServerAdmin` sull'ambiente del server |
| Run ApplicationActions e reachability per server/ambiente | `ServerOperator` sull'ambiente |
| CRUD ReachabilityTests per server | `ServerAdmin` sull'ambiente del server |
| Tutte le letture | autenticato |
| `/auth/login`, `/auth/callback` | anonimo |

`SystemAdmin` non implica `ServerAdmin`/`ServerOperator`: per un server o una console serve comunque il ruolo d'ambiente. Un `ServerAdmin` è anche operatore sul proprio ambiente.

## Test da scrivere in Fase 2–6

- `SystemAdmin` senza ruoli ambiente: CRUD provider ok; creazione server 403; console 403; run 403.
- `ServerAdmin` su ambiente A: CRUD server A ok; CRUD provider 403; server B 403; proxy A→B 403 se non è admin anche su B; diagramma con scope A ok; diagramma con scope B 403; diagramma Provider 403.
- `ServerOperator` su A: run A ok; console A 403; CRUD server A 403; CRUD reachability A 403.
- Utente autenticato senza ruoli: letture ok; ogni scrittura 403.
- Menu: ogni ruolo vede solo le voci assegnate.
- CSRF: mutazione senza token → 403; `Origin` estranea → 403.
