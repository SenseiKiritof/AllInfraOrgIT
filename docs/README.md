# Documentazione InfraOrgIT

Indice dei documenti di Fase 1.

| Documento | Contenuto |
|---|---|
| `domain/erd.md` | modello entità-relazione, aggregati e invarianti |
| `domain/data-dictionary.md` | tabelle, colonne, tipi, vincoli e mapping enum |
| `domain/inventory-parity.md` | checklist di parità Fase 3, scostamenti e dry-run |
| `domain/topology-diagrams.md` | topologia, proxy, diagrammi, scope, permessi e test Fase 4 |
| `domain/remote-management.md` | credenziali cifrate, SSH/host key, templating, azioni, reachability, audit Fase 5 |
| `domain/admin-rbac.md` | utenti, gruppi, ruoli, menu, assegnazioni e protezioni Fase 6 |
| `migration/phase7-plan.md` | piano importer, ordine, validazione e cutover Fase 7 |
| `operations/release-audit.md` | audit hardening/release Fase 8, Must/Should/Nice |
| `security/permissions.md` | matrice permessi verificata sul legacy e target v1 |
| `ux/pages.md` | mappa pagine, flussi e differenze rispetto all'originale |
| `migration/legacy-mapping.md` | mapping schema legacy → nuovo, ID, credenziali, diagrammi |
| `api/route-inventory.md` | inventario completo delle route legacy e nuova route |
| `api/openapi.yaml` | draft OpenAPI 3.0.3 del contratto v1 |
| `operations/first-push.md` | creazione repo, primo push, protezione `main`, segreti CI |
| `adr/` | ADR 001–008 |

L'OpenAPI copre 148 operazioni: le 20 route legacy `/Paginated` sono fuse nelle liste con `page`/`pageSize` e il refresh token non è esposto (avviene lato server). Le 168 operazioni HTTP legacy + il WebSocket sono tutte mappate in `api/route-inventory.md`.

## Stato

Fase 6 — admin e RBAC — 2026-10-26. Documenti allineati al codice legacy `../InfraOrgIT` e al piano `../../PLAN.md`. D1–D10 chiuse; D7 = B (tightening per ambiente). Fase 2 ha implementato auth BFF, identity e shell; Fase 3 inventario/catalogo, Fase 4 topologia/diagrammi, Fase 5 gestione remota, Fase 6 admin/RBAC. Checklist in `domain/inventory-parity.md`, `topology-diagrams.md`, `remote-management.md`, `admin-rbac.md`. Fase 7 e 8 hanno piano e audit dedicati.

Nessun codice applicativo è stato copiato: i documenti descrivono il dominio e le scelte, non il codice sorgente.
