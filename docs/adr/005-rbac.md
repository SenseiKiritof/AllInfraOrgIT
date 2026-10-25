# ADR-005 — RBAC per ambiente

- Stato: accettata
- Data: 2026-10-25
- Decisione: D7 = B (tightening per ambiente)

## Contesto

L'originale ha tre ruoli applicativi: `SystemAdmin`, `ServerAdmin` e `ServerOperator` per `ProviderEnvironment`. `SystemAdmin` non implica i ruoli per ambiente. Le scritture di inventario sono aperte a qualsiasi utente autenticato; la matrice non è documentata né coperta da test. La verifica di Fase 1 è in `docs/security/permissions.md`.

## Decisione

Applicare il tightening B:

- **Anagrafiche globali** → `SystemAdmin`: Providers, EnvironmentDefinitions, ProviderEnvironments, Applications, ApplicationVersions, ApplicationVersionApis, ApplicationApiQueryParams, Projects, CommandTemplates, ServerCredentials, Users, Groups, Roles, Menus, assegnazioni, test globali, audit.
- **Risorse legate a un ambiente** → `ServerAdmin` su **tutti** gli ambienti coinvolti: Server, ServerApplication, ProxyConnection, ProxyRoute, diagrammi con soli scope `ProviderEnvironment`, delete di nodi Server/ServerApplication.
- Se l'operazione tocca più ambienti (proxy A→B, deploy con route, move di un server), servono i ruoli su tutti.
- **Diagrammi** default/globali o con scope `Provider`/`Project` → `SystemAdmin`; con soli scope `ProviderEnvironment` → `ServerAdmin` su tutti gli scope.
- **Topology delete**: Provider/ProviderEnvironment → `SystemAdmin`; Server/ServerApplication → `ServerAdmin` su tutti gli ambienti della cascata.
- **Eccezione credenziali**: assegnazione SSH, reset host key e cambio indirizzo/ambiente di un server con credenziale restano `SystemAdmin`, come nell'originale; non richiedono `ServerAdmin`.
- `SystemAdmin` **non** implica `ServerAdmin`/`ServerOperator`: per server, console e run serve il ruolo d'ambiente.
- Letture invariate: aperte a ogni autenticato.
- Menu filtrato da `MenuRole`; CSRF token su tutte le mutazioni.

| Capacità | SystemAdmin | ServerAdmin (env) | ServerOperator (env) | Altri autenticati |
|---|---|---|---|---|
| Lettura inventario e menu | sì | sì | sì | sì |
| Scrittura anagrafiche globali (provider, ambienti, provider×ambiente, catalogo, progetti, template, credenziali, utenti/gruppi/ruoli/menu) | sì | no | no | no |
| Scrittura Server, ServerApplication, ProxyConnection, ProxyRoute | solo se anche ServerAdmin sugli ambienti coinvolti | sì, su tutti gli ambienti coinvolti | no | no |
| Diagrammi default/globali o con scope Provider/Project | sì | no | no | no |
| Diagrammi con soli scope ProviderEnvironment | solo se anche ServerAdmin su tutti gli scope | sì, su tutti gli scope | no | no |
| Delete nodo Topology Provider/ProviderEnvironment | sì | no | no | no |
| Delete nodo Topology Server/ServerApplication | solo se anche ServerAdmin sugli ambienti della cascata | sì, sugli ambienti della cascata | no | no |
| Console SSH | solo se anche ServerAdmin | sì | no | no |
| Eseguire azioni e reachability | solo se anche Operator | sì | sì | no |
| ReachabilityTests globali | sì | no | no | no |
| ReachabilityTests per server (CRUD) | solo se anche ServerAdmin | sì | no | no |
| Cambio indirizzo/ambiente di un server con credenziale, reset host key | sì | no | no | no |
| Audit esecuzioni | sì | no | no | no |

## Alternative considerate

- **A — Preservare le scritture aperte**: scartata. Un utente senza ruoli poteva cancellare un sottoalbero con `DELETE /Topology/Nodes/...` e modificare qualsiasi entità.
- **SystemAdmin come superuser anche per ambiente**: scartata, rompe la separazione attuale e rende invisibile il confine tra amministrazione globale e operatività sui server.

## Conseguenze

- Serve un helper di policy `RequireAdminOnAll(environmentIds)`; le operazioni multi-ambiente calcolano l'unione degli ambienti toccati e rifiutano con 403 se ne manca uno.
- La matrice va testata per ruolo e per ambiente, inclusi i casi multi-ambiente e la delete con cascata.
- La UI deve nascondere azioni e menu non consentiti; l'API resta la fonte di verità.
- Nessuna migrazione dati: i ruoli esistenti restano validi; cambia solo l'autorizzazione.

## Verifica Fase 1

`SystemAdminWriteFilter` copreva solo Users, Groups, Roles, Menus e ProviderEnvironmentGroupRoles. Inventario, catalogo, proxy, progetti, diagrammi e topologia non avevano filtro. `MenusService.GetMenus` restituiva tutte le voci e non usava `MenuRole`. La matrice legacy completa è in `docs/security/permissions.md`; D7 = B è la risposta.
