# InfraOrgIT — development

Technical guide for the workspace. The user-facing overview and feature tour
are in [`../README.md`](../README.md).

## Workspace

The five repositories live side by side:

```
workspace/
  AllInfraOrgIT/      # meta repo: docs, ADRs, Makefile, scripts, deploy
  InfraOrgITApi/      # .NET 10 API, EF migrations, MCP, legacy importer
  InfraOrgITWeb/      # React 19 + Vite SPA
  InfraOrgITDocker/   # local Compose stack, Caddy, Keycloak
  InfraOrgITDesktop/  # Electron shell + legacy .NET Photino app (optional)
```

`make` runs from `AllInfraOrgIT`. The desktop repository is optional for
`make dev` and `make ci`; `make release` and `make desktop-ci` need it.

Toolchain: .NET SDK 10, Node 24, Yarn 1.22.22, Docker Compose v2.

## Local stack

```bash
cp InfraOrgITDocker/.env.example InfraOrgITDocker/.env
cd AllInfraOrgIT
make dev
```

`make dev` creates the dev credential key and `.env` when missing, starts
MySQL and Keycloak, applies the EF migrations, and starts the API on `:5298`
and Vite on `:3000`.

`make full` builds and starts the single Compose stack with the API, web image,
migration job, Keycloak in production mode and Caddy on
`https://localhost:8443`. The Vite server is used by `make dev`/`make web`;
rebuild the web service after frontend changes before testing through Caddy.

`make reset` deletes the Compose volumes and `InfraOrgITDocker/data`; it is
required after Keycloak realm/client changes and destroys local data.
`make restore` overwrites both databases and needs stopped API/web/Keycloak,
`CONFIRM_RESTORE=yes` and `BACKUP_DIR=<dir>`.

## Commands and gates

```bash
make dev       # infrastructure, migrations, API :5298, Vite :3000
make full      # single Compose stack, including web and Caddy
make test      # xunit + Testcontainers MySQL + Vitest
make ci        # the real local gate: builds, tests, OpenAPI drift, lint
make desktop-ci # dotnet build/test for InfraOrgITDesktop.slnx
make e2e       # Playwright against make dev
make e2e-full  # Playwright against the full stack on https://localhost:8443
make openapi   # regenerate openapi/InfraOrgIt.Api.json
make migrate   # dotnet-ef with the pinned local tool
make backup    # MySQL application + Keycloak dump under backups/<UTC>
make load-test # targeted load on lists, topology and saves
make loadtest-mcp # MCP /mcp load with MCP_TOKEN
make security-smoke # negative security checks with MCP tokens
make legacy-dry-run # importer dry-run on JSON fixtures
make config    # validate the Compose file
make down
```

The API workflow requires `build-test` and `image`; the web workflow requires
`lint-test-build` and `image`; Docker requires `config`; the meta repo requires
`check`; the desktop requires `build-test` plus the platform smoke jobs. Run
`make ci` before claiming a change is done.

Single tests:

```bash
dotnet test ../InfraOrgITApi/InfraOrgIt.slnx --filter FullyQualifiedName~Name
yarn --cwd ../InfraOrgITWeb vitest run src/path/file.test.ts
```

## Branching and pull requests

`dev` is the integration branch; `main` is the release branch and receives
only merges from `dev`.

```bash
git switch dev
git switch -c feature/<scope>   # or fix/<scope>
# implement, commit, run make ci
git push -u origin feature/<scope>
gh pr create --base dev
```

Use the same branch name in every repository touched by the change. Merge only
when the required checks are green, then open `dev` → `main`. `main` and `dev`
are protected: no direct pushes, force-push or deletion.

## Release

Merging into `main` with `[Major]`, `[Minor]` or `[Patch]` in the pull request
title makes the API/Web `tag` workflow create the next `vX.Y.Z` tag and start
the image build. `make release VERSION=x.y.z` completes the missing repos
(including the desktop), updates `versions.lock` and skips tags that already
exist; pushing stays manual.

Version tags are created only from `main`; the `Version tags` ruleset makes
them immutable, and the docker workflows reject a tag whose commit is not on
`main`. The desktop `v*` tag starts `publish.yml`, which publishes the signed
(when the secrets exist) archives and creates or updates the GitHub Release.
The full procedure and rollback are in
[`operations/release.md`](operations/release.md).

## Packages and releases

- **API/Web images**: `.github/workflows/docker.yml` builds on every PR
  (build only), publishes `main`, `dev` and `sha-<commit>` on branch pushes, and
  `X.Y.Z`, `X.Y`, `sha-<commit>` and `latest` on `v*` tags. Branch and tag
  images are multi-arch. On non-PR runs the workflow uploads an SPDX SBOM,
  attests the build provenance and signs the image digest with keyless cosign.
- The `v0.2.0` images predate the signing/SBOM/provenance steps; the next
  version tag publishes signed versioned images.
- **Desktop release**: `InfraOrgITDesktop/.github/workflows/publish.yml` runs
  on a `v*` tag from `main` and creates or updates the GitHub Release with the
  four platform archives, per-archive SHA-256 files and the signed checksum
  manifest. A manual dispatch only uploads workflow artifacts. macOS
  signing/notarization and Windows signing are enabled only when the repository
  secrets exist; the manifest is signed with `UPDATE_SIGNING_KEY`.
- `AllInfraOrgIT` and `InfraOrgITDocker` do not publish packages or releases;
  the deploy stack consumes the API/Web images from GHCR.

## Generated contracts and schema

- `make openapi` regenerates `InfraOrgITApi/openapi/InfraOrgIt.Api.json`; the
  file is generated and `make ci` fails on drift.
- EF migrations are created with the pinned `dotnet-ef` from
  `.config/dotnet-tools.json`. New migrations must be mirrored in
  `InfraOrgITDocker/init/mysql/1-InfrastructureApps.sql` (schema and
  `__EFMigrationsHistory`) and verified with a throwaway MySQL import.
- `versions.lock` is generated by `make release`; do not edit it by hand.

## Documentation

- [`README.md`](README.md) — documentation index.
- [`security/permissions.md`](security/permissions.md) — role matrix and D7.
- [`security/pentest-2026-11.md`](security/pentest-2026-11.md) — pentest,
  OWASP mappings and remediation status.
- [`operations/release.md`](operations/release.md) — release and rollback.
- [`backlog.md`](backlog.md) — open work and verification.
- [`adr/`](adr/) — architecture decisions.
