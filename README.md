# AllInfraOrgIT

Repo meta di InfraOrgIT: decisioni architetturali, configurazione del workspace e lock di release.

## Stato

Fase 0 (workspace e regole) — 2026-10-25. Nessun codice applicativo: backend e frontend partono in Fase 2.

## Contenuto

| Percorso | Scopo |
|---|---|
| `docs/adr/` | ADR 001–006 e template |
| `tools/graphify/` | configurazione del workspace graphify |
| `Makefile` | comandi di orchestrazione |
| `versions.lock` | commit SHA dei repo applicativi per release riproducibili |

I documenti di workspace `AGENTS.md` e `PLAN.md` stanno nella radice, un livello sopra questo repo.

## Comandi

Prerequisiti: Docker con Compose v2, `make`.

```bash
cp ../infraorgit-docker/.env.example ../infraorgit-docker/.env  # una volta
make infra   # MySQL, MySQL Keycloak, Keycloak
make down
make config  # valida il Compose con .env.example
```

`make test`, `migrate`, `seed`, `e2e`, `release` falliscono con TODO fino alla Fase 2.

## Release

`versions.lock` fissa i commit di backend, frontend e docker. Una release è il checkout di quei commit; il rollback è il lock precedente.

## Regole

Vedi `AGENTS.md` e `../AGENTS.md`. Nessun segreto, nessun dato reale, nessun artefatto del legacy.
