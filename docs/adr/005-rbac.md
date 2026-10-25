# ADR-005 — RBAC per ambiente

- Stato: proposta
- Data: 2026-10-25
- Decisione: D7 (aperta)

## Contesto

L'originale ha tre ruoli applicativi: `SystemAdmin`, `ServerAdmin` e `ServerOperator` per `ProviderEnvironment`. `SystemAdmin` non implica i ruoli per ambiente. Oggi la scrittura dell'inventario è aperta a qualsiasi utente autenticato; la matrice non è documentata né coperta da test.

## Decisione proposta

Mantenere la matrice attuale, documentarla e coprirla da test. Un eventuale tightening è una decisione separata.

| Capacità | SystemAdmin | ServerAdmin (env) | ServerOperator (env) | Altri autenticati |
|---|---|---|---|---|
| Lettura inventario e menu | sì | sì | sì | sì |
| Scrittura inventario (provider, environment, server, app, progetti, proxy, diagrammi) | sì | sì | sì | **sì, oggi** (gap verificato) |
| Gestione (scrittura) di Users/Groups/Roles/Menus e assegnazioni | sì | no | no | no |
| Credenziali, template, azioni CRUD, test globali, audit | sì | no | no | no |
| Console SSH e test server | solo se anche ServerAdmin | sì | no | no |
| Eseguire azioni e reachability | solo se anche Operator | sì | sì | no |
| Cambio indirizzo/ambiente di un server con credenziale, reset host key | sì | no | no | no |

Il menu laterale non è filtrato: `MenusService.GetMenus` restituisce tutte le voci e non usa `MenuRole`. La UI mostra le pagine admin a tutti, anche se le scritture falliscono. Va corretto in v1 indipendentemente da D7.

## Alternative considerate

- **Tightening subito**: scrittura inventario solo a SystemAdmin/ServerAdmin/ServerOperator. Cambia il flusso attuale; richiede una decisione esplicita e migrazione dei permessi.
- **SystemAdmin come superuser anche per ambiente**: scartata, rompe la separazione attuale.

## Conseguenze

- Policy API testate per ogni riga della matrice; 403 vs 404 coerenti.
- Menu e azioni frontend filtrati sugli stessi ruoli.
- La decisione D7 resta aperta: se cambia, cambiano API, UI e test.

## Verifica Fase 1

`SystemAdminWriteFilter` copre solo Users, Groups, Roles, Menus e ProviderEnvironmentGroupRoles. Le scritture di inventario, catalogo, proxy, progetti, diagrammi e topologia non hanno filtro: qualsiasi autenticato può anche cancellare un sottoalbero con `DELETE /Topology/Nodes/...`. La matrice completa è in `docs/security/permissions.md`. D7 deve scegliere tra preservare questo comportamento (A) o richiedere i ruoli per ambiente (B).
