# InfraOrgIT

InfraOrgIT maps an organization's IT infrastructure and lets authorized people operate it from the browser: which providers and environments exist, which servers live in them, which application versions run where, how traffic reaches them through proxies, and who may act on each environment.

![Diagram of the production environment with servers, deployed applications and proxy routes](docs/screenshots/diagram.png)

## Features

- **Inventory**: providers (datacenters, clouds), environments (PRE, INT, PROD…) and their combinations; servers with IP, hostname, SSH port and jump host.
- **Application catalog**: applications with versions, APIs and query parameters, also imported from OpenAPI 3.x or Swagger 2.0; projects group applications. A deployment binds an application version to a server and port. An API can be called server-side on a chosen environment, with that environment's hostname and API keys, and the call can be saved to a personal history.
- **Topology and diagrams**: proxy connections between servers with their routes, drawn as an interactive diagram (provider → environment → server → deployed application) filtered by provider, environment or project, with saved layouts.
- **Remote management**: web SSH console with several sessions docked at the bottom of the page and reconnection; SSH credentials encrypted with AES-GCM and host key pinned on first connection; command templates with `{{Name}}` placeholders and application actions (restart, logs, health check); network reachability tests, all or a selection, run from the server itself. Every run is recorded in an audit log.
- **Access control**: Keycloak login through a backend-for-frontend, no token in the browser; users, groups and roles. `SystemAdmin` manages master data, `ServerAdmin` and `ServerOperator` are granted to groups per environment, and the side menu shows only the allowed entries.
- **Interface**: Italian and English, light and dark theme.
- **Legacy import**: one-shot importer from the previous system's MySQL database or from JSON fixtures.

## See it in action

Recordings and screenshots come from a local instance with fictitious data (the "Acme" company); `pre-app-01` is a real SSH server in that instance.

**SSH console**

![SSH session on pre-app-01: hostname, uptime, disk usage, application log and health endpoint](docs/screenshots/console.gif)

**Network tests and application actions**

![Reachability tests run from pre-app-01 with OK and KO results, then the Health check and Recent logs actions of orders-api](docs/screenshots/tests-actions.gif)

**Diagram**

![Zoom, pan and fit on the production diagram](docs/screenshots/diagram.gif)

| Servers | Application |
|---|---|
| ![Server list with environment, IP, SSH port and jump host](docs/screenshots/servers.png) | ![Application with versions, APIs and deployments](docs/screenshots/application.png) |
| **Server** | **Execution log** |
| ![Server detail with SSH credential and reachability tests](docs/screenshots/server.png) | ![Audit log of console sessions, actions and reachability tests](docs/screenshots/executions.png) |

## Architecture

```
browser ──► Caddy ─┬─ /             SPA: React 19, Vite, React Flow, xterm.js
                   ├─ /api, /auth   API: .NET 10, EF Core ──► MySQL 8.4
                   │                     └─ SSH (SSH.NET) ──► managed servers
                   └─ /realms       Keycloak 26 ──► MySQL 8.4
```

- One origin for SPA, API and Keycloak: the session is an HttpOnly cookie, every mutation is checked for CSRF and `Origin`.
- The backend owns the schema (EF Core migrations), RBAC and the OpenAPI contract the frontend is typed from.
- Health checks and optional OpenTelemetry export (OTLP).

## Workspace repositories

This repository is the workspace meta repository: architecture decisions, shared configuration, orchestration and release lock.

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

## Quick start

Prerequisites: Docker with Compose v2, .NET SDK 10, Node 24, Yarn 1, `make`.

```bash
git clone https://github.com/SenseiKiritof/AllInfraOrgIT.git
git clone https://github.com/SenseiKiritof/InfraOrgITApi.git
git clone https://github.com/SenseiKiritof/InfraOrgITWeb.git
git clone https://github.com/SenseiKiritof/InfraOrgITDocker.git
cp InfraOrgITDocker/.env.example InfraOrgITDocker/.env
cd AllInfraOrgIT
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

## Status

Phase 8 completed on the technical perimeter — 2026-10-27; no release executed yet. Backend, frontend, admin/RBAC, remote management and the legacy importer (MySQL source or JSON fixtures) are working; the application database is initialized with schema, base data and the installation data from `InfraOrgITDocker/init/mysql`. `full` profile with API, migrations, Keycloak production mode and Caddy; `make ci` and 5 E2E tests green. Still open: rehearsal on a representative dataset and running `make release`.

## Contents

| Path | Purpose |
|---|---|
| `docs/` | ERD, data dictionary, permissions, UX, legacy mapping, OpenAPI |
| `docs/adr/` | ADRs 001–009 and template |
| `docs/backlog.md` | open work and its verification |
| `docs/screenshots/` | screenshots and recordings used in this README |
| `scripts/` | `dev.sh` and `env.sh` for local development |
| `tools/graphify/` | graphify workspace configuration |
| `Makefile` | orchestration for infra, API, web, tests and migrations |
| `versions.lock` | commit SHAs and images of the application repos for reproducible releases |

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
