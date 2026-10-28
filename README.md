# AllInfraOrgIT

InfraOrgIT workspace: meta repository with architecture decisions, shared configuration, orchestration and release lock.

## Workspace repositories

| Repository | Content |
|---|---|
| `AllInfraOrgIT` | this repo: docs, ADRs, `Makefile`, `scripts/`, `versions.lock` |
| `InfraOrgITApi` | .NET 10 backend: API, EF migrations, legacy importer |
| `InfraOrgITWeb` | React + Vite frontend |
| `InfraOrgITDocker` | Docker Compose, Caddy, Keycloak |

The four directories live side by side:

```
workspace/
  AllInfraOrgIT/
  InfraOrgITApi/
  InfraOrgITWeb/
  InfraOrgITDocker/
```

## Status

Phase 8 completed on the technical perimeter — 2026-10-27; no release executed yet. Backend, frontend, admin/RBAC, remote management and the legacy importer (MySQL source or JSON fixtures) are working; the fake legacy dump runs in Docker. `full` profile with API, migrations, Keycloak production mode and Caddy; `make ci` and 5 E2E tests green. Still open: rehearsal on a representative dataset and running `make release`.

## Contents

| Path | Purpose |
|---|---|
| `docs/` | ERD, data dictionary, permissions, UX, legacy mapping, OpenAPI |
| `docs/adr/` | ADRs 001–008 and template |
| `docs/backlog.md` | open work and its verification |
| `scripts/` | `dev.sh` and `env.sh` for local development |
| `tools/graphify/` | graphify workspace configuration |
| `Makefile` | orchestration for infra, API, web, tests and migrations |
| `versions.lock` | commit SHAs and images of the application repos for reproducible releases |

## Quick start

Prerequisites: Docker with Compose v2, .NET SDK 10, Node 24, Yarn 1, `make`.

```bash
git clone https://github.com/SenseiKiritof/AllInfraOrgIT.git
git clone https://github.com/SenseiKiritof/InfraOrgITApi.git
git clone https://github.com/SenseiKiritof/InfraOrgITWeb.git
git clone https://github.com/SenseiKiritof/InfraOrgITDocker.git
cp InfraOrgITDocker/.env.example InfraOrgITDocker/.env
make dev
```

`make dev` creates `.env` when missing, starts MySQL/Keycloak, applies EF migrations and starts API and Vite. Development credentials live in `InfraOrgITDocker/.env`.

## Commands

```bash
make dev      # infra + migrations + API :5298 + Vite :3000; creates .env when missing
make full     # single compose: API + web images, migration job, Keycloak production
make test     # xunit + Testcontainers MySQL + Vitest
make ci       # same gates as the workflows, locally
make openapi  # regenerate openapi/InfraOrgIt.Api.json from the backend
make backup   # MySQL application + Keycloak dump into backups/<UTC>
make restore  # only with CONFIRM_RESTORE=yes BACKUP_DIR=...; overwrites the DBs
make load-test # targeted load on lists, topology and saves
make legacy-dry-run  # importer dry-run on JSON fixtures
make legacy-rehearsal # importer dry-run against the fake legacy MySQL (legacy profile)
make migrate  # dotnet-ef from the local manifest
make e2e      # Playwright; requires make dev running
make e2e-full # Playwright against the full profile (Caddy/HTTPS)
make config   # validate the Compose file
make reset    # removes volumes: needed after Keycloak realm/client changes
make down
```

`make e2e` uses `http://localhost:3000`; `make e2e-full` uses `https://localhost` and requires the `full` profile.

## Release and publishing

`make release VERSION=0.8.0` runs the gates, updates `versions.lock` and creates local `v0.8.0` tags; pushing stays manual (`git push` and `git push --tags` in each repo). Procedure in `docs/operations/release.md`.

`v*` tags trigger `.github/workflows/docker.yml` in `InfraOrgITApi` and `InfraOrgITWeb`: image build, application version tag and push to GHCR.

```bash
docker pull ghcr.io/senseikiritof/infraorgit-api:0.8.0
docker pull ghcr.io/senseikiritof/infraorgit-web:0.8.0
docker run --rm -p 8080:80 ghcr.io/senseikiritof/infraorgit-web:0.8.0
```

Published tags: `X.Y.Z`, `X.Y`, `sha-<commit>`, `latest`. The version number is baked into the image (`org.opencontainers.image.version`, `APP_VERSION` for the API, `VITE_APP_VERSION` for the web app).

`versions.lock` pins backend, frontend and docker commits. A release is the checkout of those commits; rollback is the previous lock.

## Rules

See `AGENTS.md`. No secrets, no production data, no legacy artifacts.
