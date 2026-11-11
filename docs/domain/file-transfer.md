# SFTP/FTP file transfer

The file browser lets a `ServerAdmin` browse, download, upload, rename and delete files on a managed server without leaving InfraOrgIT. The connection is opened server-side; credentials never reach the browser.

## Model

| Column | Type | Notes |
|---|---|---|
| `Servers.FileTransferProtocol` | `varchar(10)` nullable | `Sftp`, `Ftp` or `Ftps`; `NULL` disables the browser |
| `Servers.FileTransferPort` | `int` nullable | `22` for SFTP and `21` for FTP when empty; any 1–65535 value otherwise |
| `Servers.FileTransferCredentialId` | `int` nullable | FK to `ServerCredentials`, `RESTRICT`; falls back to `Servers.CredentialId` |

- The file credential is **independent** from the SSH one: one server can use an SSH key for the console and a dedicated password for SFTP/FTP.
- A credential used by either `CredentialId` or `FileTransferCredentialId` cannot be deleted (409).
- Configuration is written by `PUT /api/servers/{id}/file-transfer`; sending `protocol: null` clears protocol, port and credential.
- Protocol and port are validated server-side; the UI preselects 22/21 when the protocol changes.

## Protocols

### SFTP

- SSH.NET `SftpClient`, same 10 s connection timeout as the console.
- Uses `FileTransferPort` and the file credential (password or private key).
- Follows `Servers.JumpServerId` exactly like the SSH console: the jump session forwards a local port to the target, then SFTP connects through it; chains and cycle detection are shared with `SshConnector`.
- Host key TOFU is enforced with the same `HostKeyFingerprint`; a changed key returns 409 `host_key_mismatch`.
- The tunnel, SFTP client and jump session are disposed together.

### FTP and FTPS

> **Transport warning (PT-16).** Plain FTP is cleartext: username, password,
> commands and file content cross the network unencrypted. The deploy stack
> sets `FileTransfer__AllowPlainFtp=false`, so the API refuses to save or open
> a server with `protocol: "Ftp"` (422 `plain_ftp_disabled`); SFTP and FTPS stay
> available. The flag defaults to `true` only in development. See
> [`../security/transport.md`](../security/transport.md).

- FluentFTP `AsyncFtpClient`, direct connection to the server address; **FTP is not tunnelled through a jump host**.
- Requires a credential with `AuthType = Password`; a private key returns 422 `ftp_requires_password`.
- Passive mode is used by default. The FTP server must advertise a passive address and port range reachable from the API container; a server behind NAT needs its passive settings fixed (for example `pasv_address` and `pasv_min_port`/`pasv_max_port`).
- `Ftps` uses explicit TLS (`AUTH TLS`): data connections are encrypted too, and the server certificate is validated against the host trust store (invalid or self-signed certificates fail).

## Browser API

Base path: `/api/servers/{id}`. Authorization is `ServerAdmin` on the server's environment for every call; `SystemAdmin` alone is not enough.

| Method | Path | Body / query | Result |
|---|---|---|---|
| `PUT` | `/file-transfer` | `{ protocol, port, credentialId }` | 204; `SystemAdmin` only |
| `GET` | `/files` | `?path=/dir` | `{ path, items: [{ name, path, isDirectory, size, modifiedUtc }] }` |
| `GET` | `/files/download` | `?path=/dir/file` | attachment stream |
| `POST` | `/files/upload` | multipart `file`, `?path=/dir` | `{ path }`; max 200 MB |
| `POST` | `/files/directory` | `{ path }` | `{ path }` |
| `POST` | `/files/rename` | `{ path, newName, isDirectory }` | `{ path }` |
| `DELETE` | `/files` | `?path=/dir/file&isDirectory=false` | 204 |

- Rate limit: 60 requests per minute per user (`files` policy).
- CSRF token and allowed `Origin` are required on mutations, like every other write.
- Upload size is raised per request with `IHttpMaxRequestBodySizeFeature`; Caddy does not impose a lower body limit.
- `path` is always normalized to an absolute POSIX path; `.` and `..` are collapsed and cannot escape `/`. Upload file names are reduced to their base name.
- Deleting `/` is rejected.
- The frontend uses one file per upload; multiple selection and drag-and-drop are not implemented.

## UI

- **Footer dock**: the `File` button opens the browser; the `+` button next to `Console` opens the console server picker. Both list only servers where the user is `ServerAdmin`.
- **Server detail**: header actions **File** and **Console SSH**; the *File access (SFTP/FTP)* section lets a `SystemAdmin` choose protocol, port and optional credential.
- Browser: server picker, protocol badge, breadcrumb, up, refresh, filter, new folder, upload, download, rename, delete. Load errors and action errors are shown separately.
- The browser is a modal above the console dock; console sessions keep running while it is open.

## Errors

| Code | Status | Meaning |
|---|---|---|
| `file_transfer_not_configured` | 422 | protocol is empty |
| `file_transfer_protocol` | 422 | protocol is not `Sftp`/`Ftp` |
| `ftp_requires_password` | 422 | FTP with a private-key credential |
| `credential_missing` | 422 | no file or SSH credential on the server |
| `jump_cycle`, `jump_missing`, `jump_unsupported` | 422 | jump chain invalid |
| `host_key_mismatch` | 409 | SFTP host key differs from the saved fingerprint |
| `ssh_unreachable`, `ftp_unreachable` | 502 | connection failed |
| `file_transfer_failed` | 502 | operation failed on the remote filesystem |

## Tests

- `RemotePathTests`: normalization, root clamp, combine and name.
- `InventoryApiTests.File_transfer_configuration_and_listing_respect_roles`: configuration is `SystemAdmin`; listing is `ServerAdmin`; invalid protocol is 422; DTO exposes protocol and port.
- `RealSshTests.Real_sftp_lists_downloads_uploads_and_deletes`: real OpenSSH container, SFTP list/download/upload/delete.
- `RealFtpTests.Real_ftp_lists_downloads_uploads_and_deletes`: real vsftpd container, FTP list/download/upload/create/rename/delete.
- Frontend: `ConsoleProvider.test.tsx` (footer picker) and `FileBrowserModal.test.tsx` (server + protocol + listing + download URL).

## Limits and next steps

- No FTPS, SFTP resume, permissions/chmod, recursive delete or bulk upload.
- File operations are not written to `CommandExecutions`; the audit currently covers console and commands only.
- FTP through a jump host is not supported.
- A very large directory is returned in one response; there is no server-side pagination or virtualised table.
- Upload progress and cancellation are not shown.
