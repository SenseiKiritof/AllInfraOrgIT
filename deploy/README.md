# Deploy from published images

Starts the full stack from GHCR images: no API/Web source checkout and no
local build. Only this repository is needed; the database schema comes from
the API image's `migrate` job, and `init/base-data.sql` adds the base data
(environments, roles, menus, translations and the bootstrap admin user).

## Requirements

- Docker Engine or Docker Desktop with Compose v2.
- A published image tag: `main`/`dev`/`sha-<commit>` from a branch push, or
  `X.Y.Z`/`latest` from a `v*` tag (see the `docker` workflows in
  `InfraOrgITApi` and `InfraOrgITWeb`). Use an immutable `X.Y.Z` or
  `sha-<commit>` tag. `main`, `dev` and `latest` are refused by the preflight
  unless `API_DIGEST`/`WEB_DIGEST` pins the exact manifest.
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
(`CHANGE_ME_*` is rejected by the preflight). To pin the exact manifest, copy
the digest printed by the registry and set it in `.env`; `main`/`dev`/`latest`
without a digest are refused:

```bash
docker buildx imagetools inspect ghcr.io/senseikiritof/infraorgit-api:0.4.0 \
  --format '{{json .Manifest}}' | jq -r .digest
# API_DIGEST=sha256:<64 hex> in deploy/.env
```

The tag and the digest must describe the same manifest: the image reference
becomes `<repository>:<tag>@sha256:<digest>`. After a registry update, re-pin
the digest rather than leaving a moving branch tag.

```bash
deploy/scripts/check-env.sh deploy/.env
make up-images
# or: docker compose --env-file deploy/.env -f deploy/compose.yaml up -d --wait
```

`check-env.sh` refuses missing values, `CHANGE_ME` placeholders, the known
`dev-*` secrets, the old all-`a` credential key, a bootstrap administrator
password weaker than the realm password policy (see below), a non-boolean
`FileTransfer__AllowPlainFtp` and a mutable `main`/`dev`/`latest` tag without a
digest; it warns when `WEB_BIND` leaves loopback or plain FTP is re-enabled.
`make up-images` runs it before Compose, so the stack cannot start with the
shipped defaults.

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

- **Plain FTP is off; use SFTP or FTPS.** `compose.yaml` sets
  `FileTransfer__AllowPlainFtp=false` (overridable in `.env`), so the API
  refuses to save or open a server configured with the `Ftp` protocol (422
  `plain_ftp_disabled`). SFTP and FTPS (explicit TLS) remain available; FTPS
  validates the server certificate against the host trust store and refuses
  invalid or self-signed certificates. Plain FTP sends the username, password,
  commands and file content unencrypted. Treat it only as a legacy exception:
  set the flag to `true` deliberately, keep the target on a trusted network,
  record the exception per server and never use it with an administrator
  credential. `check-env.sh` warns when the flag is not `false` and rejects a
  value that is not a boolean.
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
`INFRAORGIT_ADMIN_PASSWORD`, and the imported user has `temporary: true` plus
the `UPDATE_PASSWORD` and `CONFIGURE_TOTP` required actions. TOTP is enforced
for every realm user by the browser flow (see below), so the first login must
enroll an authenticator before reaching the application; the `admin` account
also has to change the seeded password. Never use the old `dev-admin` password
or any other value from the local development stack.

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

The deploy realm requires TOTP for **every** username/password login, not only
for the bootstrap administrator. The realm binds `browserFlow` to
`browser-mfa`: the `Cookie` step (ALTERNATIVE), then a `browser-mfa-forms`
subflow with `Username Password Form` and `OTP Form` both REQUIRED. A user
without an OTP credential is sent to the `Configure OTP` enrollment page right
after the password and cannot reach the application before enrolling; later
logins ask for the six-digit code. The realm also marks `CONFIGURE_TOTP` as a
default required action, so users created later in the console or through the
API get enrollment at their first login. The OTP policy is TOTP, 6 digits,
30-second period, one look-ahead window and no code reuse, and cancelling the
required-action page aborts the login.

The imported `admin` additionally carries `UPDATE_PASSWORD`. Required actions
do not weaken the flow: even after the password change the browser flow still
requires OTP, and the temporary password is the only seeded credential.

Validated against a disposable Keycloak 26.8.1 import: the `admin` password is
followed by TOTP enrollment and login completes only after a valid code; a
second user created after the import is sent to enrollment; a user whose
`CONFIGURE_TOTP` required action was removed is still forced into enrollment by
the browser flow; a later login for the same user asks for TOTP and the
password alone never reaches the application.

What a realm import cannot do, and remains manual:

1. `--import-realm` does not update an existing realm. On a stack created
   before this change, either remove the Keycloak database
   (`deploy/data/mysql-keycloak`; this destroys Keycloak users, clients and
   sessions) for a fresh import, or reproduce the flow in the console:
   Authentication -> Flows -> duplicate `browser` as `browser-mfa`, replace the
   conditional 2FA subflow with a REQUIRED `OTP Form`, bind it as the realm
   browser flow, then set `CONFIGURE_TOTP` as a default action. Existing
   accounts are covered as soon as the flow is bound (the flow forces
   enrollment); the default action only covers users created afterwards.
   Verify on a disposable user.
2. The master realm (`KEYCLOAK_ADMIN`, `http://localhost:18081/admin`) has its
   own flow and is not part of the realm import. Enable OTP there in the console
   if the emergency account must be MFA-protected.
3. A brokered identity provider bypasses the local browser flow. If one is
   added, enforce MFA at the provider (or add a pass-through step before the
   redirector) and test it like the local login.
4. Direct access grants stay disabled on every realm client. Enabling one would
   bypass the browser flow (and TOTP) until the user has enrolled an OTP
   credential; do not enable it for human clients.
5. The local `InfraOrgITDocker` realm intentionally keeps development
   credentials without forced TOTP; it is not a production profile.

Break-glass and recovery:

1. The master-realm administrator (`KEYCLOAK_ADMIN`, loopback
   `http://localhost:18081/admin`) can remove the OTP credential or reset a
   required action for a locked-out application administrator. Secure that
   account separately and keep its password offline; it is the emergency path.
2. Create a second application administrator before relying on MFA, so one
   lost phone does not block administration. Enroll recovery codes (Keycloak
   `Configure recovery authentication codes`) on it and store them offline.
3. Lost authenticator: sign in with a recovery code, then re-enroll TOTP from
   the account console, or use the master realm to clear the OTP credential.

MFA is realm-wide, so there is no `mfa-required` group to keep aligned with
application roles: keep the realm's enabled user list tight instead.
`SystemAdmin` is an application role in the InfraOrgIT database, not a Keycloak
role; disabling or deleting the Keycloak account is the only way to block
login. The application has no step-up authentication of its own, so the
Keycloak flow is the only second factor in front of console, action and
credential operations. The local `InfraOrgITDocker` realm keeps its development
credentials and does not force TOTP.

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

`web` runs as the unprivileged uid/gid `10001`, with `read_only: true`,
`cap_drop: [ALL]`, `no-new-privileges:true`, `/tmp` on tmpfs and the two
Caddy volumes mounted read-write. `NET_BIND_SERVICE` is the only capability
added: uid 10001 cannot bind `:443` without it, and `no-new-privileges`
prevents Caddy from using the file capability on its own binary. The upstream
image has no `caddy` user and `/data`/`/config` are root-owned, but
`/data/caddy` and `/config/caddy` are mode `1777` in the image (and in a fresh
named volume copied from it), so the arbitrary uid can write certificates and
autosave state while the root filesystem stays read-only.

Upgrading a deployment created before this change: the existing certificates
and autosave file are root-owned, and Caddy as uid 10001 cannot read them.
Chown both volumes once, then recreate `web`:

```bash
docker run --rm --user 0 --cap-drop ALL --cap-add CHOWN \
  -v infraorgit-deploy_caddy-data:/data \
  -v infraorgit-deploy_caddy-config:/config \
  --entrypoint chown <web-image> -R 10001:10001 /data /config
```

`keycloak` runs as the image's uid 1000, read-only, with `cap_drop: [ALL]`,
`no-new-privileges:true`, tmpfs for `/tmp` and `/opt/keycloak/data`, and a
named volume at `/opt/keycloak/lib/quarkus`. The unoptimized upstream image
re-augments Quarkus there at startup; a plain read-only root fails with
`NoSuchFileException: /opt/keycloak/lib/quarkus/quarkus-application.dat`, and
an empty tmpfs at that path fails the same way because it hides the file
shipped in the image. The named volume starts as a copy of the image directory
and remains writable for the augmentation. The entrypoint renders the realm
into the `/opt/keycloak/data` tmpfs on every start; Keycloak state stays in
MySQL. After a Keycloak image upgrade, remove
`infraorgit-deploy_keycloak-quarkus` if the cached augmentation prevents
startup (it holds only build output, no realm data).

With a read-only root filesystem Caddy logs a non-fatal warning that it cannot
install its local CA into the container trust store. The browser already treats
the `localhost` certificate as self-signed.

MySQL 8.4 and Keycloak are pinned by digest. API/Web images must have an
explicit `API_TAG`/`WEB_TAG`; `main`, `dev` and `latest` are refused by
`check-env.sh` unless `API_DIGEST`/`WEB_DIGEST` is a full `sha256:<64 hex>`
manifest digest. Image signing and provenance/SBOM attestations are still open
and tracked separately from this deploy hardening.

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

`down -v` removes the named volumes (Caddy certificates/config, API data
protection keys and the Keycloak Quarkus build cache). Application and
Keycloak databases are bind mounts under
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
