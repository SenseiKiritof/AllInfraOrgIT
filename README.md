# AllInfraOrgIT

Workspace di InfraOrgIT: repo meta con decisioni architetturali, configurazione condivisa, orchestrazione e lock di release.

## Repo del workspace

| Repo | Contenuto |
|---|---|
| `AllInfraOrgIT` | questo repo: docs, ADR, `Makefile`, `scripts/`, `versions.lock` |
| `InfraOrgITApi` | backend .NET 10: API, migration EF, importer legacy |
| `InfraOrgITWeb` | frontend React + Vite |
| `InfraOrgITDocker` | Docker Compose, Caddy, Keycloak |
| `InfraOrgIt`, `legacy copy`, `legacy Docker copy`, `infra-org-it-fe` | copie del progetto legacy, solo riferimento |

Le quattro directory del workspace stanno sullo stesso livello:

```
workspace/
  AllInfraOrgIT/
  InfraOrgITApi/
  InfraOrgITWeb/
  InfraOrgITDocker/
```

## Stato

Fase 8 completata sul perimetro tecnico — 2026-10-27; release non eseguita. Backend, frontend, admin/RBAC, gestione remota e importer legacy (sorgente MySQL o fixture JSON) sono operativi; il dump legacy fittizio gira in Docker. Profilo `full` con API, migrazioni, Keycloak production e Caddy; `make ci` e 5 E2E verdi. Restano il rehearsal su dati rappresentativi e l'esecuzione di `make release`.

## Contenuto

| Percorso | Scopo |
|---|---|
| `docs/` | ERD, data dictionary, permessi, UX, mapping legacy, OpenAPI |
| `docs/adr/` | ADR 001–008 e template |
| `docs/backlog.md` | lavori aperti e loro verifica |
| `.opencode/` | regole, skill e plugin OpenCode del workspace |
| `scripts/` | `dev.sh` e `env.sh` per lo sviluppo locale |
| `tools/graphify/` | configurazione del workspace graphify |
| `Makefile` | orchestrazione di infra, API, web, test e migrazioni |
| `versions.lock` | commit SHA e immagini dei repo applicativi per release riproducibili |

## Avvio rapido

Prerequisiti: Docker con Compose v2, .NET SDK 10, Node 24, Yarn 1, `make`.

```bash
git clone https://github.com/SenseiKiritof/AllInfraOrgIT.git
git clone https://github.com/SenseiKiritof/InfraOrgITApi.git
git clone https://github.com/SenseiKiritof/InfraOrgITWeb.git
git clone https://github.com/SenseiKiritof/InfraOrgITDocker.git
cp InfraOrgITDocker/.env.example InfraOrgITDocker/.env
make dev
```

`make dev` crea `.env` se manca, avvia MySQL/Keycloak, applica le migration EF e lancia API e Vite. Le credenziali di sviluppo sono in `InfraOrgITDocker/.env`.

## Comandi

```bash
make dev      # infra + migration + API :5298 + Vite :3000; crea .env se manca
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

## Release e pubblicazione

`make release VERSION=0.8.0` esegue i gate, aggiorna `versions.lock` e crea i tag locali `v0.8.0`; il push resta manuale (`git push` e `git push --tags` per ogni repo). Procedura in `docs/operations/release.md`.

I tag `v*` avviano `.github/workflows/docker.yml` di `InfraOrgITApi` e `InfraOrgITWeb`: build dell'immagine, tag con la versione dell'applicazione e push su GHCR.

```bash
docker pull ghcr.io/senseikiritof/infraorgit-api:0.8.0
docker pull ghcr.io/senseikiritof/infraorgit-web:0.8.0
docker run --rm -p 8080:80 ghcr.io/senseikiritof/infraorgit-web:0.8.0
```

Tag pubblicati: `X.Y.Z`, `X.Y`, `sha-<commit>`, `latest`. Il numero di versione è baked nell'immagine (`org.opencontainers.image.version`, `APP_VERSION` dell'API, `VITE_APP_VERSION` della web).

`versions.lock` fissa i commit di backend, frontend e docker. Una release è il checkout di quei commit; il rollback è il lock precedente.

## Regole

Vedi `AGENTS.md`. Nessun segreto, nessun dato reale, nessun artefatto del legacy.
