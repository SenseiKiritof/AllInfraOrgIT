# AllInfraOrgIT — agent guide

`AGENTS.md` is a symlink to this file: edit `CLAUDE.md` only.

Meta repository of the InfraOrgIT workspace. Command reference in `README.md`,
open work in `docs/backlog.md`, decisions in `docs/adr/`.

## Workspace

- Four sibling git repositories: this one plus `../InfraOrgITApi` (.NET 10
  API, EF migrations, legacy importer), `../InfraOrgITWeb` (React 19 + Vite)
  and `../InfraOrgITDocker` (Compose, Caddy, Keycloak).
- The `Makefile` and `scripts/` assume exactly that side-by-side layout. Run
  `make` from this directory; do not rename or move the four folders.
- When prose and scripts disagree, trust `Makefile`, `scripts/` and the CI
  workflows.
- Work often spans repositories: commit separately in each one. Read the
  repo-local `CLAUDE.md` before editing a sibling.
- Backend owns the schema, the generated OpenAPI contract and RBAC; the SPA
  calls only same-origin `/api` and `/auth` (Keycloak BFF, no token in
  JavaScript). Docker owns Compose and Keycloak; the Caddyfile is in the web
  repo.
- Toolchain: .NET SDK 10, Node 24, Yarn 1.22.22, Docker Compose v2.
- UI copy is Italian; code identifiers and commit messages are English
  (Conventional Commits).

## Branching

- `dev` is the integration branch; `main` is the release branch and receives
  only merges from `dev`.
- Start every change from `dev` on `feature/{scope}` or `fix/{scope}`, with a
  short kebab-case scope (`feature/server-details`, `fix/e2e-cleanup`). When a
  change touches several repositories, use the same branch name in each.
- Push the branch and open a pull request into `dev`; merge only when the
  required checks are green (`build-test`/`image` for the API,
  `lint-test-build`/`image` for the web, `config` for Docker, `check` for this
  repo). Then open `dev` -> `main`.
- The `Main` ruleset blocks direct pushes, force-push and deletion on `main`
  and `dev`, and requires the checks; the repo admin bypass exists only for
  emergencies. Never commit directly to `main`.
- Release from `main` after the merge; `versions.lock` and the local tags are
  built there. `v*` tags are created only from `main`: on API/Web a merge
  whose title contains `[Major]`, `[Minor]` or `[Patch]` creates the next tag
  automatically and starts the image build; `make release` completes the
  missing repos and skips tags that already exist. The `Version tags` ruleset
  makes them immutable, and the docker workflow refuses a version tag whose
  commit is not on `main`.

## Commands and gates

- `make dev`: MySQL/Keycloak containers, EF migrations, API on `:5298`, Vite
  on `:3000`. It creates `InfraOrgITDocker/.env` and the dev credential key
  when missing.
- `make test`: .NET solution (unit + Testcontainers MySQL integration, Docker
  required) plus Vitest.
- `make ci`: run this before claiming done. It checks Compose config, builds
  the API with `-warnaserror`, runs tests and the credential rewrap self-check,
  then Biome, `tsc --noEmit`, Vitest, the web build, `jq versions.lock`, the
  OpenAPI regeneration/drift check and the Redocly lint.
- `.github/workflows/ci.yml` here only validates `versions.lock` and rejects a
  tracked `.env`; it does not run the build or tests. `make ci` is the real
  gate.
- Single tests: `dotnet test ../InfraOrgITApi/InfraOrgIt.slnx --filter
  FullyQualifiedName~Name`; `yarn --cwd ../InfraOrgITWeb vitest run
  src/path/file.test.ts`.
- `make openapi` regenerates `InfraOrgITApi/openapi/InfraOrgIt.Api.json`.
  The file is generated: never edit it by hand. Commit it in `InfraOrgITApi`
  with endpoint/DTO changes; `make ci` regenerates it and fails on drift.
- Migrations: `make migrate` applies them with the pinned `dotnet-ef`
  (`.config/dotnet-tools.json`). To add one, run `source scripts/env.sh &&
  dotnet tool restore && dotnet tool run dotnet-ef migrations add <Name>
  --project ../InfraOrgITApi/src/InfraOrgIt.Api --startup-project
  ../InfraOrgITApi/src/InfraOrgIt.Api` from this directory; never hand-edit
  migrations or the model snapshot.
- `make e2e` needs `make dev` running and Playwright browsers installed
  (`yarn --cwd ../InfraOrgITWeb playwright install chromium`). `make e2e-full`
  needs `make full`, uses `https://localhost:8443`, and inserts the dev
  `admin` user before running.
- `make up-images` starts the stack from the published images with
  `deploy/compose.yaml` (no API/Web source or local build); see
  `deploy/README.md`.
- `make reset` deletes Compose volumes and `InfraOrgITDocker/data`; it is
  required after Keycloak realm/client changes and destroys local data.
  `make dev` runs Keycloak with `KC_MODE=dev`; `make full` uses `prod`.
- `make restore` overwrites both databases: it needs stopped API/web/Keycloak
  and `CONFIRM_RESTORE=yes BACKUP_DIR=<dir>`.

## Gotchas

- Running `dotnet run` or `dotnet ef` directly skips `scripts/env.sh`. Use the
  make targets or `source scripts/env.sh` first for DB/OIDC/credential vars.
- The `full` stack serves the web image built at image-build time; the Vite
  dev server is used by `make dev`/`make web`. Rebuild the web service after
  frontend changes before testing through Caddy.
- Init SQL runs only on an empty MySQL volume; changes to
  `InfraOrgITDocker/init/mysql/*.sql` need `make reset`. `1-*.sql` mirrors
  the EF schema (re-export it after a migration), `2-*.sql` is base data;
  a local `3-CustomData.sql` is git-ignored. Never force-add dumps, `data/`
  or SQL exports.
- RBAC D7 = B: `SystemAdmin` does not imply `ServerAdmin`. Server, deployment,
  console and run actions require `ServerAdmin` on the environment, so a
  missing button can be correct. See `docs/security/permissions.md`.
- Secrets belong only in `InfraOrgITDocker/.env` (ignored) or a secret manager.
  Versioned files use fake values; no production dumps or personal absolute
  paths.
- `versions.lock` is generated by `make release` (all four repos clean on
  `main`, gates + e2e, local tags; push manual). Do not edit it by hand.
- Local-only and ignored: `.opencode/`, `tools/graphify/workspace.json`,
  `graphify-out/`, `backups/`, `InfraOrgITWeb/dist/`, `InfraOrgITDocker/.env`.
- ADR rule: never edit an accepted ADR; add a new one and mark the old one
  `Status: superseded by ADR-NNN`.
- `docs/api/openapi.yaml` is the Phase 1 draft; the executable contract is
  `InfraOrgITApi/openapi/InfraOrgIt.Api.json`.

## Pointers

- `docs/security/permissions.md`: role matrix and target v1 rules.
- `docs/operations/release.md`: release, rollback, tags.
- `tools/graphify/README.md`: workspace graph configuration.
