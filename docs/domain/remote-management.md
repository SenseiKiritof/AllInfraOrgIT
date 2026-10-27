# Remote management and audit

Phase 5, 2026-10-26. Functional reference: the legacy system, read-only. The permission rules are in `docs/security/permissions.md` (D7 = B).

## SSH credentials

- `ServerCredentials` stores a password or private key **encrypted with AES-GCM**; the client only receives `hasSecret`, never ciphertext or plaintext.
- Layout: `base64(nonce|tag|ciphertext)`, 12-byte nonce, 16-byte tag. A 32-byte key per version in `ServerAccess:CredentialKeys:<n>`; `ServerAccess:CurrentKeyVersion` selects the encryption key. The row keeps `KeyVersion`, so a rotation decrypts the old rows.
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

## Frontend

- `/credentials`: credential CRUD, write-only secret, "set" indicator.
- `/commands`: template CRUD and placeholder count.
- `/reachability`: global tests.
- `/executions`: log with expandable output.
- Server detail: SSH credential/port, host key reset, reachability test with run, deploy actions, console.
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

- 11 unit: encryption (round-trip, tamper, missing version), renderer (quotes, missing placeholders, metacharacters), error handler.
- 22 integration: encrypted credentials never returned, SSH assignment, host key, actions with redacted audit and idempotency, reachability, console with a foreign Origin, **real SSH against a disposable OpenSSH container** with TOFU and mismatch.
- 4 Playwright E2E, including credentials, commands, reachability, log.

## Known limits

- The console shows the terminal without full ANSI emulation (sequences stripped) and only has the duration limit, not a separate idle timeout.
- Key rotation is done from configuration, not from the UI.
- Reachability runs servers sequentially; a very large environment needs a queue.
- Importing legacy credentials with the old key remains in Phase 7; without a key, `NeedsReauth` is used.
