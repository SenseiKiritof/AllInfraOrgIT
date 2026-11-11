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
`dev-*` secrets, the old all-`a` credential key and a bootstrap administrator
password weaker than the realm password policy (see below). `make up-images`
runs it before Compose, so the stack cannot start with the shipped defaults.

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

## Transport security

The stack protects only its own TLS endpoints. Every target and client
connection is the operator's responsibility:

- **FTP is cleartext.** The file-transfer connector supports SFTP over SSH and
  plain FTP. Plain FTP sends the username, password, commands and file content
  unencrypted, and an on-path attacker can read or alter them. Use SFTP for
  every target. FTPS is not implemented in the connector, so it cannot be
  selected as a mitigation today; if a legacy target only offers FTP, reach it
  through an SSH tunnel or a dedicated management network and record a
  time-boxed exception. Never expose FTP to the internet and never use it with
  an administrator credential.
- **Local HTTP stays on loopback.** `http://localhost:18081/admin` (Keycloak)
  and the `http://localhost:3000` redirect in the realm are cleartext and must
  remain bound to `127.0.0.1`. Do not point `KEYCLOAK_HOSTNAME_ADMIN`,
  `SITE_URL` or an OIDC redirect at plain HTTP on a real interface: the
  authorization code, session cookie and bearer tokens would travel in clear.
  For remote administration keep the loopback bind and forward the port over
  SSH (`ssh -L 18081:127.0.0.1:18081 <host>`), or put the stack behind a
  TLS-terminating reverse proxy with a valid certificate.
- **Tokens are passwords.** Personal API tokens, MCP bearer tokens and client
  secrets must only cross HTTPS; never put them in a query string (they end up
  in access logs, saved call history and backups), prefer the `Authorization`
  header, and do not paste them into tickets, chat or shell history. Keep
  `deploy/.env` at mode `600` and out of unencrypted backups. Do not set
  `INFRAORGIT_INSECURE_TLS=1` outside an isolated lab: the desktop client sends
  its bearer and refresh token to the configured instance, so an `http://`
  non-loopback instance URL exposes them. On a shared host the macOS Keychain
  helper can briefly expose a token in the process argument list (PT-16); use a
  dedicated machine for desktop sessions.

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

## Password policy and MFA

The deploy realm sets a password policy: at least 12 characters with an
uppercase letter, a lowercase letter, a digit and a special character, and the
password must not equal the username or the email:

```text
length(12) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1) and notUsername(undefined) and notEmail(undefined)
```

Keycloak validates it whenever a password is set or changed, including the
forced first-login change for `admin`. The preflight mirrors the policy for
`INFRAORGIT_ADMIN_PASSWORD`: import-time validation of the seeded credential
is not a reliable control (it depends on the Keycloak version and can fail the
whole realm import), so `check-env.sh` rejects a bootstrap password that is too
short or misses a character class before the container starts.

Limitations: a password policy does not apply retroactively until the next
password change, and `--import-realm` does not update an existing realm. On a
stack deployed before this change, set the same policy in the Keycloak console
(Realm settings -> Authentication -> Password policy) and rotate the
administrator password. The master realm (`KEYCLOAK_ADMIN`) has its own policy
and OTP settings; configure them in the console after the first start.

MFA is deliberately **not** forced by the realm import. Enabling OTP on the
only imported administrator before anyone has enrolled an authenticator would
lock the deployment out. Require it as a post-bootstrap step:

1. In the Keycloak admin console open Authentication -> Required actions and
   enable **Configure OTP**, so users can enroll a TOTP authenticator.
2. For every administrator and every account that can use stored SSH
   credentials, the console or actions, open Users -> <user> -> Required
   actions, add **Configure OTP** and save. The next login forces enrollment.
3. To require OTP for a group rather than one user at a time, create a Keycloak
   group or role (for example `mfa-required`), assign the administrators to it,
   and bind a copy of the `browser` flow with a `Condition - user role`
   subflow around `OTP Form`. Export the realm (or the custom flow) afterwards
   so a rebuilt stack can reproduce it.
4. Keep a break-glass path: a second administrator, the master-realm
   administrator on the loopback port, and recovery codes stored offline. Test
   the flow with a normal account before binding it realm-wide.

`SystemAdmin` is an application role in the InfraOrgIT database, not a Keycloak
role, so keeping the `mfa-required` group aligned with application
administrators is an operational task: review it whenever roles change. The
application has no step-up authentication of its own, so the Keycloak flow is
the only second factor in front of console, action and credential operations.

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

## Resource limits

Every long-running service sets `mem_limit`, `cpus` and `pids_limit`, each
overridable from `.env` (PT-17):

| Service | `mem_limit` | `cpus` | `pids_limit` | Overrides |
|---|---|---|---|---|
| `mysql` | 1g | 1.0 | 512 | `MYSQL_MEM_LIMIT`, `MYSQL_CPUS`, `MYSQL_PIDS_LIMIT` |
| `mysql-keycloak` | 768m | 1.0 | 512 | `KEYCLOAK_DB_MEM_LIMIT`, `KEYCLOAK_DB_CPUS`, `KEYCLOAK_DB_PIDS_LIMIT` |
| `keycloak` | 2g | 2.0 | 1024 | `KEYCLOAK_MEM_LIMIT`, `KEYCLOAK_CPUS`, `KEYCLOAK_PIDS_LIMIT` |
| `api` | 768m | 1.0 | 512 | `API_MEM_LIMIT`, `API_CPUS`, `API_PIDS_LIMIT` |
| `web` | 256m | 0.5 | 256 | `WEB_MEM_LIMIT`, `WEB_CPUS`, `WEB_PIDS_LIMIT` |

The defaults assume a single host for a small team: up to ~50 servers and ~20
concurrent users, MySQL keeping its default 128 MiB InnoDB buffer pool,
Keycloak 26 keeping its upstream 2 GB recommendation for a small production
deployment (it allocates up to 70% of the limit as JVM heap plus ~300 MiB
non-heap, and the unoptimized image augments Quarkus at startup), and Caddy
serving only as a reverse proxy. `mem_limit` is a hard cgroup cap, so an
undersized value OOM-kills the container (MySQL during an import, Keycloak
during the realm import) rather than degrading gracefully; `pids_limit` counts
threads, not just processes, so MySQL and the JVM need headroom. Raise the
values in `.env` before importing a large inventory, running a backup on the
same host, or serving more users. The one-shot `migrate` and `base-data` jobs
stay unlimited so the first start cannot fail on an undersized cap. After a
restart check `docker stats` and
`docker inspect --format '{{.State.OOMKilled}}' <container>`; these are Compose
(non-Swarm) limits, not Swarm reservations. The defaults add up to ~4.75 GiB
for the five services, so plan an 8 GiB host to leave room for Docker, the OS
and backups.

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
