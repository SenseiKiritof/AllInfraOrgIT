# Transport and local exposure (PT-16)

Warnings for paths that can move credentials or data outside TLS, and for local
token exposure. These are configuration/transport risks, not authorization
bypasses. The evidence from the internal test is in
[`pentest-2026-11.md`](pentest-2026-11.md) (PT-16).

## File transfer: FTP is cleartext

- `Servers.FileTransferProtocol = Ftp` uses plain FTP: username, password,
  commands and file content are not encrypted. Anyone on the network path can
  read or alter them.
- Prefer `Sftp` (SSH, port 22 by default). It reuses the SSH host-key pinning
  and jump-host path.
- FTPS is **not implemented**. An FTP-only target is a legacy exception:
  restrict it to a trusted network or VPN, record why per server, and never use
  it over the internet. Removing FTP is the safest end state.
- See [`../domain/file-transfer.md`](../domain/file-transfer.md).

## Browser and API: HTTPS outside loopback

- A deployed stack terminates TLS at Caddy. `make dev` uses
  `http://localhost:3000` (Vite) and `http://localhost:5298` (API) for local
  development only.
- Do not publish the dev server or the API on a non-loopback interface. The
  production session cookie is `Secure`, but credentials typed into a
  cleartext dev page still cross the network.
- `WEB_BIND=0.0.0.0` in `deploy/.env` is an explicit exposure decision: put a
  valid certificate in front and restrict the port with a firewall.

## Desktop: instance URL and TLS verification

- Use `https://` for every instance that is not loopback. The desktop sends
  `Authorization: Bearer` and inventory data to the instance; over `http://`
  both are readable on the network.
- `INFRAORGIT_INSECURE_TLS=1` disables certificate validation for every
  instance in the process. Treat it as a development-only switch; never set it
  in a packaged install or on a shared host.
- The desktop binds tunnels to `127.0.0.1`; do not change that to a public
  interface.

## Token handling on the local host

- Prefer the OS secret store: the desktop uses macOS Keychain, Windows
  Credential Manager or `secret-tool`.
- **macOS limitation:** the current Keychain write passes the refresh token to
  `security` with `-w <token>`, so the value is visible in the process argument
  list (`ps`) to other local processes while the command runs. The window is
  short and local, but on a host with untrusted local users treat the token as
  exposed and revoke the device session after use. Passing the value on stdin or
  using the native Security framework is the fix.
- Do not paste tokens into shell history or command lines. Use `read -rs` into
  an environment variable or the client's secret store, and never pass a token
  with `--token` on a shared host.

## Checklist

- [ ] Every file-transfer server uses SFTP; each FTP exception is documented.
- [ ] Non-loopback instance URLs are HTTPS and the certificate validates.
- [ ] `INFRAORGIT_INSECURE_TLS` is unset outside local development.
- [ ] Dev servers and the API are not reachable from untrusted networks.
- [ ] Tokens come from a secret store or environment, not argv or shell history.
