# Deploy from published images

Starts the full stack from GHCR images: no API/Web source checkout and no
local build. Only this repository is needed; the database schema comes from
the API image's `migrate` job, and `init/base-data.sql` adds the base data
(environments, roles, menus, translations and the bootstrap admin user).

## Requirements

- Docker Engine or Docker Desktop with Compose v2.
- A published image tag: `main`/`dev`/`sha-<commit>` from a branch push, or
  `X.Y.Z`/`latest` from a `v*` tag (see the `docker` workflows in
  `InfraOrgITApi` and `InfraOrgITWeb`). Prefer a version or `sha-<commit>`
  tag; `API_DIGEST`/`WEB_DIGEST` can pin the exact manifest.
- The images must be readable: GHCR packages are private by default; either
  make them public or `docker login ghcr.io` with a token that can read them.

## First run

```bash
cd AllInfraOrgIT
cp deploy/.env.example deploy/.env
chmod 600 deploy/.env
```

The example contains placeholders only. Generate every password and secret
with `openssl rand -base64 32` (the SSH credential key must decode to exactly
32 bytes, so the same command applies). One portable way to fill the file on
first run:

```bash
for key in \
  MYSQL_PASSWORD MYSQL_ROOT_PASSWORD \
  KEYCLOAK_DB_PASSWORD KEYCLOAK_DB_ROOT_PASSWORD \
  KEYCLOAK_ADMIN_PASSWORD INFRAORGIT_ADMIN_PASSWORD \
  Oidc__ClientSecret MCP_CLIENT_SECRET ServerAccess__CredentialKey; do
  value="$(openssl rand -base64 32)"
  awk -v key="$key" -v value="$value" '
    BEGIN { FS = "=" }
    $1 == key { print key "=" value; next }
    { print }
  ' deploy/.env > deploy/.env.tmp
  mv deploy/.env.tmp deploy/.env
done
chmod 600 deploy/.env
```

Then set `API_TAG` and `WEB_TAG` to a published version or `sha-<commit>`
(`CHANGE_ME_*` is rejected by the preflight). Optionally set
`API_DIGEST`/`WEB_DIGEST` to `sha256:...` to pin the manifest:

```bash
deploy/scripts/check-env.sh deploy/.env
make up-images
# or: docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --wait
```

`check-env.sh` refuses missing values, `CHANGE_ME` placeholders, the known
`dev-*` secrets and the old all-`a` credential key. `make up-images` runs it
before Compose, so the stack cannot start with the shipped defaults.

Open `https://localhost:8443` (self-signed certificate) and
`http://localhost:18081/admin` for the Keycloak console.

## Network exposure

The web port is published on loopback by default: `WEB_BIND=127.0.0.1`
produces `127.0.0.1:8443 -> 443/tcp`. MySQL (`127.0.0.1:13336`), the Keycloak
database (`127.0.0.1:13337`) and the Keycloak admin port (`127.0.0.1:18081`)
stay on loopback.

For an intentional network exposure set `WEB_BIND` to the required interface,
for example:

```dotenv
WEB_BIND=0.0.0.0
```

Then update these consistently and update the Keycloak client redirect URIs:
`SITE_ADDRESS`, `SITE_URL`, `KEYCLOAK_HOSTNAME_ADMIN`, `OIDC_ISSUER`,
`OIDC_REDIRECT_URI` and `FRONTEND_BASE_URL`. Terminate TLS with a valid
certificate in front of the stack (or configure Caddy for a real hostname),
and restrict the port with a firewall. `check-env.sh` prints a warning when
`WEB_BIND` is not loopback; the exposure is accepted only because it is
explicit.

## Administrator bootstrap

The shipped Keycloak realm still creates the username `admin`, because the
application database row in `init/base-data.sql` is also keyed to that name.
The username is not a secret; the password must be unique. It comes from
`INFRAORGIT_ADMIN_PASSWORD`, and the imported user has
`temporary: true`: Keycloak forces a password change at the first login.
Never use the old `dev-admin` password or any other value from the local
development stack.

The master-realm Keycloak administrator is controlled by `KEYCLOAK_ADMIN`
(default `admin`) and `KEYCLOAK_ADMIN_PASSWORD`. These values are only used on
the first start, when the master realm is created. `check-env.sh` warns while
the username remains `admin`; rename it or create a separate administrator
after bootstrap if your policy requires it.

`base-data.sql` maps the application user `admin` to `SystemAdmin`. If you
rename or replace that user in Keycloak, update or remove the corresponding
row and role mapping in the application database as well.

## Secrets and rotation

| Secret | Used by | Rotation |
|---|---|---|
| `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` | API/`migrate`, MySQL | Change the MySQL user password, update `.env`, recreate the affected services. |
| `KEYCLOAK_DB_PASSWORD`, `KEYCLOAK_DB_ROOT_PASSWORD` | Keycloak, `mysql-keycloak` | Change the MySQL user password, update `.env`, recreate Keycloak. |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak master realm | First start only; afterwards change it in the Keycloak console. |
| `INFRAORGIT_ADMIN_PASSWORD` | Bootstrap `admin` user | First login only (temporary password). Afterwards rotate in the Keycloak console; update `.env` only if the realm may be imported again. |
| `Oidc__ClientSecret` | API BFF client `infraorgit` | Keycloak console -> Clients -> `infraorgit` -> Credentials -> Regenerate, update `.env`, restart `api`. |
| `MCP_CLIENT_SECRET` | `infraorgit-mcp` service account | Keycloak console -> Clients -> `infraorgit-mcp` -> Credentials, update `.env`, update every MCP client. |
| `ServerAccess__CredentialKey` | AES-GCM encryption of SSH credentials | Add a new key version and rewrap the stored credentials with the API's `RewrapCredentials` tool; do not overwrite the current key in place. This stack exposes the current key only. |

The realm file is a template: changing `deploy/keycloak/realm-infraorgit.json`
does not update an existing realm on restart. `--import-realm` imports only
when the realm is absent. Apply changes in the Keycloak console, or stop the
stack and remove the Keycloak database bind mount
(`deploy/data/mysql-keycloak`) to force a fresh import. Removing that directory
destroys Keycloak users, clients and sessions; the application database in
`deploy/data/mysql` is separate.

## MCP and the desktop client

The deploy realm defines `infraorgit-mcp` with `mcp:read` as its only default
scope. `mcp:operate` and `tunnels:operate` are optional scopes: a token is
read-only unless the client explicitly requests them. To enforce an approval
step, remove the optional scopes from the client in Keycloak until an
integration needs actions, then re-add them.

`infraorgit-mcp-desktop` is a public client with PKCE and the device grant;
its default scope is also `mcp:read`, with the two operate scopes optional.
The secret in the realm template is a placeholder rendered at container start
from `OIDC_CLIENT_SECRET`/`MCP_CLIENT_SECRET`; no working secret is committed.

## Container hardening

`web` runs with `read_only: true`, `cap_drop: [ALL]` and
`no-new-privileges:true`, with `/tmp` on tmpfs. `keycloak` runs with
`cap_drop: [ALL]`, `no-new-privileges:true` and tmpfs for `/tmp` and
`/opt/keycloak/data`, but keeps a writable root filesystem: the upstream image
re-augments Quarkus into `/opt/keycloak/lib/quarkus` at startup, so a
read-only root would prevent it from starting. Keycloak runs as uid 1000 and
keeps its state in MySQL; the import file is rendered into tmpfs on each start.

Two deliberate compromises:

- `web` still runs as root. The published Caddy image has no unprivileged
  user, and its `/data` and `/config` volumes are root-owned. Capabilities are
  dropped instead. `NET_BIND_SERVICE` is added back because the Caddy binary
  carries that file capability and `no-new-privileges` would otherwise refuse
  to execute it.
- With a read-only root filesystem Caddy logs a non-fatal warning that it
  cannot install its local CA into the container trust store. The browser
  already treats the `localhost` certificate as self-signed.

MySQL 8.4 and Keycloak are pinned by digest. API/Web images remain tag-based
because digests are release-specific; use a version or `sha-<commit>` tag, or
set `API_DIGEST`/`WEB_DIGEST`, and `check-env.sh` warns about `main`, `dev` and
`latest` without a digest.

## Update / stop

```bash
docker compose --env-file deploy/.env -f deploy/compose.yaml pull
docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --wait
docker compose --env-file deploy/.env -f deploy/compose.yaml down
```

`down -v` removes the named volumes (Caddy certificates/config and API data
protection keys). Application and Keycloak databases are bind mounts under
`deploy/data/` and survive `down` and `down -v`; remove them explicitly only
when you intend to reset that database.

## Notes

- `deploy/keycloak/realm-infraorgit.json` is deploy-specific and templated
  (`__OIDC_CLIENT_SECRET__`, `__MCP_CLIENT_SECRET__`, `__ADMIN_PASSWORD__`).
  `deploy/init/base-data.sql` is still a copy of the Docker repository's base
  data; update both when the source of truth changes.
- For a real host set `SITE_ADDRESS`, `SITE_URL`, `KEYCLOAK_HOSTNAME_ADMIN`,
  `OIDC_ISSUER`, `OIDC_REDIRECT_URI` and `FRONTEND_BASE_URL` consistently, and
  update the Keycloak client redirect URIs.
