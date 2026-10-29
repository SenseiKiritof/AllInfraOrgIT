# AllInfraOrgIT

InfraOrgIT workspace: meta repository with architecture decisions, shared configuration, orchestration and release lock.

## What it does

InfraOrgIT maps an organization's IT infrastructure and lets authorized people operate it from one web app: which providers and environments exist, which servers live in them, which application versions run where, how traffic reaches them through proxies, and who may act on each environment.

- **Inventory**: providers (datacenters, clouds), environments (PRE, INT, PROD…) and their combinations; servers with IP, hostname, SSH port and jump host.
- **Application catalog**: applications with versions, APIs and query parameters, also imported from OpenAPI 3.x or Swagger 2.0; projects group applications. A deployment binds an application version to a server and port. An API can be called server-side on a chosen environment, with that environment's hostname and API keys, and the call can be saved to a personal history.
- **Topology and diagrams**: proxy connections between servers with their routes, drawn as an interactive diagram (provider → environment → server → deployed application) filtered by provider, environment or project, with saved layouts.
- **Remote management**: SSH credentials encrypted with AES-GCM, host key pinned on first connection, web SSH console, command templates with `{{Name}}` placeholders, application actions (restart, logs, health check) and network reachability tests; every run is recorded in an audit log.
- **Access control**: Keycloak login through a backend-for-frontend, no token in the browser; users, groups and roles. `SystemAdmin` manages master data, `ServerAdmin` and `ServerOperator` are granted to groups per environment, and the side menu shows only the allowed entries.
- **Legacy import**: one-shot importer from the previous system's MySQL database or from JSON fixtures.

Screenshots from a local instance with fictitious data:

| Topology diagram | Servers |
|---|---|
| ![Diagram of the production environment with servers, deployed applications and proxy routes](docs/screenshots/diagram.png) | ![Server list with environment, IP, SSH port and jump host](docs/screenshots/servers.png) |
| **Application** | **Server** |
| ![Application with versions, APIs and deployments](docs/screenshots/application.png) | ![Server detail with SSH console, credential and reachability tests](docs/screenshots/server.png) |
| **Execution log** | |
| ![Audit log of remote actions and reachability tests](docs/screenshots/executions.png) | |

## Workspace repositories

| Repository | Content |
|---|---|
| [`AllInfraOrgIT`](https://github.com/SenseiKiritof/AllInfraOrgIT) | this repo: docs, ADRs, `Makefile`, `scripts/`, `versions.lock` |
| [`InfraOrgITApi`](https://github.com/SenseiKiritof/InfraOrgITApi) | .NET 10 backend: API, EF migrations, legacy importer |
| [`InfraOrgITWeb`](https://github.com/SenseiKiritof/InfraOrgITWeb) | React + Vite frontend |
| [`InfraOrgITDocker`](https://github.com/SenseiKiritof/InfraOrgITDocker) | Docker Compose, Caddy, Keycloak |

The four directories live side by side:

```
workspace/
  AllInfraOrgIT/
  InfraOrgITApi/
  InfraOrgITWeb/
  InfraOrgITDocker/
```

## Status

Phase 8 completed on the technical perimeter — 2026-10-27; no release executed yet. Backend, frontend, admin/RBAC, remote management and the legacy importer (MySQL source or JSON fixtures) are working; the application database is initialized with schema, base data and the installation data from `InfraOrgITDocker/init/mysql`. `full` profile with API, migrations, Keycloak production mode and Caddy; `make ci` and 5 E2E tests green. Still open: rehearsal on a representative dataset and running `make release`.

## Contents

| Path | Purpose |
|---|---|
| `docs/` | ERD, data dictionary, permissions, UX, legacy mapping, OpenAPI |
| `docs/adr/` | ADRs 001–009 and template |
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
