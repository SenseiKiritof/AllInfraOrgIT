# AllInfraOrgIT

Repo meta di InfraOrgIT: decisioni architetturali, configurazione del workspace e lock di release.

## Stato

Fase 2 (fondamenta e auth) — 2026-10-25. Backend identity + BFF Keycloak, frontend shell, Compose e CI sono operativi. L'inventario parte in Fase 3.

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
make test     # xunit + Testcontainers MySQL + Vitest
make migrate  # dotnet-ef dal manifest locale
make e2e      # Playwright; richiede make dev attivo
make config   # valida il Compose
make reset    # rimuove i volumi: serve dopo modifiche a realm/client Keycloak
make down
```

`make e2e` usa `http://localhost:3000`; per un ambiente diverso impostare `E2E_BASE_URL`.

`make release` resta TODO fino alla Fase 8.

## Release

`versions.lock` fissa i commit di backend, frontend e docker. Una release è il checkout di quei commit; il rollback è il lock precedente.

## Regole

Vedi `AGENTS.md` e `../AGENTS.md`. Nessun segreto, nessun dato reale, nessun artefatto del legacy.
