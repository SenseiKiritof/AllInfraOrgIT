# AllInfraOrgIT

Repo meta di InfraOrgIT: decisioni architetturali, configurazione del workspace e lock di release.

## Stato

Fase 8 completata sul perimetro tecnico — 2026-10-27; release non eseguita. Backend, frontend, admin/RBAC, gestione remota e importer legacy (sorgente MySQL o fixture JSON) sono operativi; il dump legacy fittizio gira in Docker. Profilo `full` con API, migrazioni, Keycloak production e Caddy; `make ci` e 5 E2E verdi. Restano il rehearsal su dati rappresentativi e l'esecuzione di `make release`.

## Contenuto

| Percorso | Scopo |
|---|---|
| `docs/` | ERD, data dictionary, permessi, UX, mapping legacy, OpenAPI |
| `docs/adr/` | ADR 001–008 e template |
| `scripts/` | `dev.sh` e `env.sh` per lo sviluppo locale |
| `tools/graphify/` | configurazione del workspace graphify |
| `Makefile` | orchestrazione di infra, API, web, test e migrazioni |
| `versions.lock` | commit SHA dei repo applicativi per release riproducibili |

I documenti di workspace `AGENTS.md` e `PLAN.md` stanno nella radice, un livello sopra questo repo.

## Comandi

Prerequisiti: Docker con Compose v2, .NET SDK 10, Node 24, Yarn 1, `make`.

```bash
make dev      # infra + API :5298 + Vite :3000; crea .env se manca
make full     # build frontend + API container, job migrazioni, Keycloak production e Caddy
make test     # xunit + Testcontainers MySQL + Vitest
make ci       # stessi gate dei workflow, in locale
make openapi  # rigenera openapi/InfraOrgIt.Api.json dal backend
make backup   # dump MySQL applicativo + Keycloak in backups/<UTC>
make restore  # solo con CONFIRM_RESTORE=yes BACKUP_DIR=...; sovrascrive i DB
make load-test # carico mirato su liste, topologia e save
make legacy-dry-run  # dry-run importer su fixture JSON
make legacy-rehearsal # dry-run importer contro il MySQL legacy fittizio (profilo legacy)
make migrate  # dotnet-ef dal manifest locale
make e2e      # Playwright; richiede make dev attivo
make e2e-full # Playwright contro il profilo full (Caddy/HTTPS)
make config   # valida il Compose
make reset    # rimuove i volumi: serve dopo modifiche a realm/client Keycloak
make down
```

`make e2e` usa `http://localhost:3000`; `make e2e-full` usa `https://localhost` e richiede il profilo `full` attivo.

`make release VERSION=0.8.0` esegue i gate, aggiorna `versions.lock` e crea i tag locali; il push resta manuale. Procedura in `docs/operations/release.md`.

## Release

`versions.lock` fissa i commit di backend, frontend e docker. Una release è il checkout di quei commit; il rollback è il lock precedente.

## Regole

Vedi `AGENTS.md` e `../AGENTS.md`. Nessun segreto, nessun dato reale, nessun artefatto del legacy.
