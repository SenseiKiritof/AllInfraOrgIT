# Deploy from published images

Starts the full stack from GHCR images: no API/Web source checkout and no
local build. Only this repository is needed; the database schema comes from
the API image's `migrate` job, and `init/base-data.sql` adds the base data
(environments, roles, menus, translations, dev admin).

## Requirements

- Docker Engine or Docker Desktop with Compose v2.
- A published image tag: `main`/`dev`/`sha-<commit>` from a branch push, or
  `X.Y.Z`/`latest` from a `v*` tag (see the `docker` workflows in
  `InfraOrgITApi` and `InfraOrgITWeb`).
- The images must be readable: GHCR packages are private by default; either
  make them public or `docker login ghcr.io` with a token that can read them.

## Start

```bash
cd AllInfraOrgIT
cp deploy/.env.example deploy/.env   # secrets and tags
make up-images
# or: docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --wait
```

Open `https://localhost:8443` (self-signed certificate) and
`http://localhost:18081/admin` for the Keycloak console.

## Update / stop

```bash
docker compose --env-file deploy/.env -f deploy/compose.yaml pull
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --wait
docker compose --env-file deploy/.env -f deploy/compose.yaml down
```

`down -v` also deletes the volumes (login sessions and Caddy certificates).
Application data lives in `deploy/data/` and survives `down`.

## Notes

- `deploy/keycloak/realm-infraorgit.json` and `deploy/init/base-data.sql` are
  copies of the files in `InfraOrgITDocker`; update both when the source of
  truth changes.
- For a real host set `SITE_ADDRESS`, `SITE_URL`, `KEYCLOAK_HOSTNAME_ADMIN`,
  `OIDC_ISSUER`, `OIDC_REDIRECT_URI` and `FRONTEND_BASE_URL` consistently, and
  update the Keycloak client redirect URIs.
