# Release

Local procedure to tag a `v0.MINOR.PATCH` version. No automatic push.

## Preconditions

- Clean working tree and `main` branch in the four repos (`InfraOrgITApi`, `InfraOrgITWeb`, `InfraOrgITDocker`, `AllInfraOrgIT`).
- Green gates: `make ci` (build `-warnaserror`, unit/integration, Biome, tsc, Vitest, frontend build, `jq versions.lock`, generated OpenAPI without drift).
- Stack running for `make e2e` (or `E2E_BASE_URL`); `SKIP_E2E=1` only for local tests.
- OpenAPI regenerated and committed (`make openapi`, no diff).
- Pre-deploy backup executed (`make backup`) and restore tested.
- Phase 7: the rehearsal on a real legacy dump remains a known blocker; the synthetic release does not cover the real cutover.

## Command

```bash
cd AllInfraOrgIT
make release VERSION=0.8.0
```

`scripts/release.sh`:

1. rejects versions not `0.x.y`, branch other than `main`, dirty working tree and already existing tags;
2. runs `make ci` and `make e2e` (`SKIP_GATES=1`/`SKIP_E2E=1` only for testing);
3. writes `versions.lock` with `generatedAt` and the current SHAs of the three application repos;
4. commits `:bookmark: release v0.8.0` in the meta repo;
5. creates the annotated tag `v0.8.0` in the three repos and in the meta repo;
6. prints the push commands, to be run by hand.

## Push and deploy

Local tags are not a public release. After verification:

```bash
git -C InfraOrgITApi push origin main --follow-tags
git -C InfraOrgITWeb push origin main --follow-tags
git -C InfraOrgITDocker push origin main --follow-tags
git -C AllInfraOrgIT push origin main --follow-tags
```

The deploy starts from `versions.lock`: checkout of the SHAs, image build with `API_TAG=0.8.0`, `make full`, `migrate` job, smoke test (login, inventory, diagram, health/ready).

## Published images

The `v*` tags start `.github/workflows/docker.yml` of `InfraOrgITApi` and `InfraOrgITWeb` and publish to GHCR:

- `ghcr.io/senseikiritof/infraorgit-api:0.8.0` (`0.8`, `sha-<commit>`, `latest`)
- `ghcr.io/senseikiritof/infraorgit-web:0.8.0` (same tags)

Before deploying, check `gh run list --workflow docker.yml` in both repos and the image pull. On a host without a local build, use `API_TAG=0.8.0` with the Compose `image:` instead of `build:`.

## Rollback

- Restore the pre-deploy backup (`CONFIRM_RESTORE=yes make restore BACKUP_DIR=...`).
- Checkout of the previous tag's `versions.lock` and new deploy.
- Keycloak: SSO sessions may expire; users remain.

## Status 2026-10-27

`make release` implemented and guards verified (invalid version → exit 2, dirty working tree → exit 1). Release not executed: the repos have uncommitted changes and the real Phase 7 is still open.
