# Remote management and audit

Phase 5, 2026-10-26. Functional reference: the legacy system, read-only. The permission rules are in `docs/security/permissions.md` (D7 = B).

## SSH credentials

- `ServerCredentials` stores a password or private key **encrypted with AES-GCM**; the client only receives `hasSecret`, never ciphertext or plaintext.
- Layout: `v2:` + `base64(nonce|tag|ciphertext)`, 12-byte nonce, 16-byte tag, written by **SSecureUtils 1.1.1**; the AES key is the SHA-256 of the configured string. A 32-byte base64 key per version in `ServerAccess:CredentialKeys:<n>`; `ServerAccess:CurrentKeyVersion` selects the encryption key. The row keeps `KeyVersion`, so a rotation decrypts the old rows.
- Values written before the switch carry no `v2:` prefix and are **not readable** by the new code: run `tools/RewrapCredentials` once per database before deploying (`--apply`, dry-run by default, idempotent).
- In development `scripts/env.sh` generates a key and stores it in `InfraOrgITDocker/.env` (ignored). In production the key comes from a secret manager.
- A private key is validated with SSH.NET before saving; a password is not.
- On update an empty secret leaves the stored one unchanged; changing `AuthType` requires the secret.
- A credential assigned to a server cannot be deleted (409). SSH assignment and host key reset are `SystemAdmin`.

## SSH

`SshConnector` uses SSH.NET:

- 10 s connection; command with configurable timeout (`ServerAccess:CommandTimeoutMinutes`, 1–60, default 10);
- maximum output 1 MB (`MaxOutputBytes`), the audit keeps the last 64 KB (`MaxAuditOutputBytes`);
- **host key TOFU**: on first connection the SHA256 fingerprint is saved on the server; if it changes, the connection is rejected with 409 `host_key_mismatch` and the audit records the attempt. Reset is `SystemAdmin` only;
- errors do not contain secrets.
- **jump host**: `Servers.JumpServerId` points to another server used as an SSH proxy. `SshConnector` opens the jump session, forwards a local port to the target `host:port`, then connects with the target credential; the tunnel and the jump session are disposed with the target session. Chains are allowed and protected against cycles (422 `jump_cycle`), the API rejects self-reference and cycles on write, and a server used as a jump host cannot be deleted (409).

## File transfer

- `Servers.FileTransferProtocol` (`Sftp` or `Ftp`), `FileTransferPort` and an optional `FileTransferCredentialId`: the file credential is separate from the SSH one and falls back to it when empty. Configuration is `SystemAdmin` (`PUT /api/servers/{id}/file-transfer`).
- **SFTP** uses SSH.NET on the same jump-host chain as the console, with the file credential and port; the host key is checked like the SSH connection.
- **FTP** uses FluentFTP directly with a password credential (a private key is rejected with 422); there is no jump-host tunnel for FTP.
- Browser API (`ServerAdmin` on the environment, 60 requests/min per user): `GET /api/servers/{id}/files?path=`, `GET .../files/download`, `POST .../files/upload` (multipart, max 200 MB), `POST .../files/directory`, `POST .../files/rename`, `DELETE .../files`. Paths are normalized POSIX paths; `..` cannot escape the root.
- The UI exposes the browser from the console dock and from the server detail header; the file credential can be chosen independently from the SSH one.

## Templating and actions

- `{{Name}}` placeholders; built-ins: `ServerName`, `Hostname`, `IpAddress`, `ApplicationName`, `BasePath`, `Version`, `ExposedPort`.
- Built-ins take precedence over custom values and are checked both at save time and at execution time.
- Values are wrapped in single quotes with `'` escaped; shell metacharacters (`$`, backtick, `\`, `"`, CR/LF) are rejected in the values of the placeholders used, custom ones included.
- An action has a template **or** a custom script (`SystemAdmin` only), with JSON `ParameterValues`.
- Action configuration: `SystemAdmin`; button list and run: `ServerOperator` on the deploy's environment.
- The run reserves the audit row with `Idempotency-Key` **before** executing: a duplicate submission receives 409 and does not execute. If the command or the connection fails, the audit is still completed with the error.
- The audit stores the unrendered template and replaces custom values with `***` in the output.

## Reachability

- Global tests: `SystemAdmin` CRUD, run on every server. Per-server tests: `ServerAdmin` CRUD, read and run `ServerOperator`.
- Hostname validated (`[A-Za-z0-9.:-]`), port 1–65535; the command uses `timeout 5 bash -c '</dev/tcp/host/port>'` on the server, with a 10 s SSH timeout.
- Each server produces a `Reachability` audit row with the aggregated outcome.

## Executions and console

- `GET /api/command-executions` (`SystemAdmin`): paginated, filterable by server, kind and text; script and output are redacted.
- WebSocket console `/api/socket/servers/{id}/console`: session cookie, **Origin** required and allowed, `ServerAdmin` role on the environment, maximum duration 30 min. The audit records opening/closing and any error, never the keystrokes.
- The console dock at the bottom also has **+** to open a console by choosing a server (only environments where the user is `ServerAdmin`) and **File** to open the SFTP/FTP browser for the same servers.

## Frontend

- `/credentials`: credential CRUD, write-only secret, "set" indicator.
- `/commands`: template CRUD and placeholder count.
- `/reachability`: global tests.
- `/executions`: log with expandable output.
- Server detail: SSH credential/port, host key reset, file access (SFTP/FTP protocol, port, optional separate credential), reachability test with run, deploy actions, console and file browser.
- Application detail: action configuration (template or custom script, JSON parameters, confirmation).

## Configuration

```text
ServerAccess__CurrentKeyVersion=1
ServerAccess__CredentialKeys__1=<32-byte base64>
ServerAccess__CommandTimeoutMinutes=10
ServerAccess__MaxOutputBytes=1048576
ServerAccess__MaxAuditOutputBytes=65536
ServerAccess__ConsoleMaxMinutes=30
```

The keys are mandatory at startup: without `CredentialKeys` the API does not start.

## Tests

- 34 unit: encryption (round-trip, tamper, missing version), renderer (quotes, missing placeholders, metacharacters), remote path normalization, error handler.
- 53 integration: encrypted credentials never returned, SSH assignment, host key, actions with redacted audit and idempotency, reachability, console with a foreign Origin, file-transfer RBAC and API, **real SSH/SFTP against a disposable OpenSSH container** with TOFU and mismatch, **real FTP against a disposable vsftpd container** (list, upload, download, create/rename/delete).
- 5 Playwright E2E, including credentials, commands, reachability, log.

## Known limits

- The console shows the terminal without full ANSI emulation (sequences stripped) and only has the duration limit, not a separate idle timeout.
- Key rotation is done from configuration, not from the UI.
- Reachability runs servers sequentially; a very large environment needs a queue.
- Importing legacy credentials with the old key remains in Phase 7; without a key, `NeedsReauth` is used.
