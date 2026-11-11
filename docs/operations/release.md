# Release

Local procedure to tag a `v0.MINOR.PATCH` version. No automatic push.

## Preconditions

- Clean working tree and `main` branch in the five repos (`InfraOrgITApi`,
  `InfraOrgITWeb`, `InfraOrgITDocker`, `InfraOrgITDesktop`, `AllInfraOrgIT`),
  with `dev` already merged into `main` and the branch pushed. The desktop tag
  is created only from `main`.
- Green gates: `make ci` (build `-warnaserror`, unit/integration, Biome, tsc,
  Vitest, frontend build, `jq versions.lock`, generated OpenAPI without drift)
  and `make desktop-ci` (`dotnet build` with `-warnaserror` and `dotnet test`
  on `InfraOrgITDesktop.slnx`).
- Stack running for `make e2e` (or `E2E_BASE_URL`); `SKIP_E2E=1` only for local tests.
- OpenAPI regenerated and committed (`make openapi`, no diff).
- Version tags only from `main`: merging with `[Major]`, `[Minor]` or `[Patch]`
  in the title creates the tag automatically on API/Web; `make release` skips
  existing tags and completes the others. `v*` is protected from update and
  deletion, and the docker workflow checks that the tagged commit is on `main`.
  The desktop `publish` workflow does not create tags and does not check the
  branch: a desktop tag pushed from another branch would still publish.
- Pre-deploy backup executed (`make backup`) and restore tested.
- Phase 7: the rehearsal on a real legacy dump remains a known blocker; the synthetic release does not cover the real cutover.

## Command

```bash
cd AllInfraOrgIT
make release VERSION=0.8.0
```

`scripts/release.sh`:

1. rejects versions not `0.x.y`, branch other than `main`, dirty working tree and already existing tags;
2. runs `make ci`, `make desktop-ci` and `make e2e` (`SKIP_GATES=1`/`SKIP_E2E=1` only for testing);
3. writes `versions.lock` with `generatedAt` and the current SHAs of the four application repos (`InfraOrgITApi`, `InfraOrgITWeb`, `InfraOrgITDocker`, `InfraOrgITDesktop`);
4. commits `:bookmark: release v0.8.0` in the meta repo;
5. creates the annotated tag `v0.8.0` in the four repos and in the meta repo;
6. prints the push commands, to be run by hand.

`versions.lock` is generated: do not edit it by hand. `repos` is an object of
commit SHAs keyed by repo name, so the desktop entry is additive. The committed
file keeps its three entries until the next `make release`, which adds
`InfraOrgITDesktop`. Consumers only validate the JSON (`jq empty`) and read the
SHAs they need; they must ignore unknown keys.

## Push and deploy

Local tags are not a public release. After verification:

```bash
git -C InfraOrgITApi push origin main --follow-tags
git -C InfraOrgITWeb push origin main --follow-tags
git -C InfraOrgITDocker push origin main --follow-tags
git -C InfraOrgITDesktop push origin main --follow-tags
git -C AllInfraOrgIT push origin main --follow-tags
```

Pushing the tag starts the API/Web image builds and the desktop publish
workflow. Wait for both before announcing the version; the desktop update check
reads the latest stable GitHub release.

The server deploy starts from `versions.lock`: checkout of the API/Web/Docker
SHAs, image build with `API_TAG=0.8.0`, `make full`, `migrate` job, smoke test
(login, inventory, diagram, health/ready). The desktop SHA pins the source but
is not deployed on the server.

## Published images

`.github/workflows/docker.yml` publishes branch images (`main`, `dev`,
`sha-<commit>`) on every push, so `deploy/compose.yaml` can run without a
release. The `v*` tags publish the versioned images to GHCR:

- `ghcr.io/senseikiritof/infraorgit-api:0.8.0` (`0.8`, `sha-<commit>`, `latest`)
- `ghcr.io/senseikiritof/infraorgit-web:0.8.0` (same tags)

Before deploying, check `gh run list --workflow docker.yml` in both repos and the image pull. On a host without a local build, use `API_TAG=0.8.0` and `WEB_TAG=0.8.0` with the Compose `image:` instead of `build:`.

## Desktop release

The desktop repo is tagged with the same `v0.MINOR.PATCH`, from `main`. The
`v*` tag push triggers `.github/workflows/publish.yml`, which:

- builds all four RIDs: `InfraOrgIT-Desktop-<version>-osx-arm64`,
  `-osx-x64`, `-win-x64`, `-linux-x64`;
- signs and notarizes macOS and signs Windows only when the repository secrets
  exist; otherwise it logs a warning and publishes the unsigned archive;
- uploads the archives and their `.sha256` files as workflow artifacts and to
  the GitHub Release named after the tag (created or updated, never a new tag).

Signing secrets (optional, documented in `../InfraOrgITDesktop/README.md`):
`MACOS_CERTIFICATE`, `MACOS_CERTIFICATE_PASSWORD`, `APPLE_ID`,
`APPLE_TEAM_ID`, `APPLE_APP_PASSWORD` for macOS;
`WINDOWS_CERTIFICATE`, `WINDOWS_CERTIFICATE_PASSWORD` for Windows. Never commit
certificates or passwords.

Manual `workflow_dispatch` runs only upload workflow artifacts. Re-running the
workflow for the same tag updates the existing GitHub Release. Without the
secrets the desktop signatures are still manual: `CODESIGN_IDENTITY`,
`notarytool` and `stapler` as described in the desktop README.

## Rollback

- Restore the pre-deploy backup (`CONFIRM_RESTORE=yes make restore BACKUP_DIR=...`).
- Checkout of the previous tag's `versions.lock` and new deploy.
- Keycloak: SSO sessions may expire; users remain.
- Desktop: the update check only offers the latest stable release; to roll
  back, publish a new tag rather than re-tagging an existing one.

## Status 2026-11-11

`make release` integrated with `InfraOrgITDesktop`: desktop gate
(`make desktop-ci`), SHAs in `versions.lock`, tag and push instructions, and the
desktop GitHub Release are part of the runbook. Guards verified (invalid
version → exit 2, dirty working tree → exit 1). Release not executed: the real
Phase 7 is still open.
