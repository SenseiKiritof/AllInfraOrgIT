# ADR-013 — Connection policy and server-relayed tunnels

- Status: accepted
- Date: 2026-11-13
- Related: ADR-010 (MCP server and tunnel app), ADR-012 (Electron desktop shell)

## Context

ADR-010 rejected API-host tunnels because the API would become a general TCP
proxy. The desktop opens `ssh` locally with the user's agent, so every tunnel
requires client-to-SSH reachability and an agent on the client.

The installation now needs a per-deployment choice:

- connections only through the server;
- connections opened directly by the client;
- automatic selection based on the desktop and client-to-target reachability.

The setting must work when several API nodes run behind a load balancer. A
file or per-node setting would make the cluster inconsistent.

## Decision

Store a singleton `ConnectionPolicies` row in MySQL with three modes. The
default is `Auto`; a missing row or an empty write also resolves to `Auto`:

| Mode | Tunnel transport |
|---|---|
| `Server` | The API node opens the SSH forward and relays raw bytes to the desktop over a WebSocket. |
| `Client` | The desktop opens `ssh` with the local agent, as before. |
| `Auto` | The desktop tests the first SSH hop; direct when reachable, server relay otherwise. |

- `GET /api/connection-policy` is available to every authenticated client;
  `PUT` requires `SystemAdmin` and writes an `AdminChange` audit row.
- The admin page `/settings` exposes the three modes and states that the value
  is shared by every API node.
- Server relay is deliberately narrow: only a `TunnelService` with
  `Mode = Local` or a deployment (`serverApplicationId`) with a fixed target
  port. The client sends ids, never a host or port. `Dynamic` and `Remote`
  stay client-only; relaying them would turn the API into an open proxy and
  widen the stored-credential privilege boundary.
- The relay endpoint requires `tunnels:operate` (or the BFF session), the
  `ServerOperator` role on the server's environment, an allowed Origin and the
  `tunnel-relay` rate limit. It opens a loopback `ForwardedPortLocal` on the
  API node and pipes it to the WebSocket.
- The desktop binds the local listener on `127.0.0.1`, opens one relay
  WebSocket per local TCP connection and caps concurrent relay connections per
  tunnel.
- `TunnelSessions.Transport` records `Client` or `Server`, so the central
  `/tunnels` page shows which side opened the connection.

### Cluster behaviour

- The policy row is read from the shared database on every decision, so all
  nodes see the same mode without a restart.
- A relay connection is owned by the node that accepted the WebSocket and is
  not shared with other nodes. Each local TCP connection opens its own relay,
  so the load balancer does not need sticky sessions, only WebSocket upgrade
  support.
- The existing in-memory audit hash-chain lock remains a single-process
  assumption. A strict multi-writer chain needs a database lock or a
  single-writer queue; this ADR does not change that.

## Consequences

- `Server` mode makes the API use the stored server credential for outbound
  SSH. Users who are operators but have no personal SSH access can reach the
  allowlisted `Local` targets. This is the intended trade-off, bounded by the
  fixed target and the `Local`-only rule.
- `Client` mode keeps the current agent-based security model but requires the
  client to reach the SSH target. If it cannot, `Auto` falls back to `Server`;
  `Client` fails with an explicit error.
- Console, files and application actions follow the same mode. `Client` and
  reachable `Auto` desktop sessions use `ssh2`/SFTP with the user's agent. The
  API returns the target metadata and host-key fingerprint, creates the
  `CommandExecution` for console/actions, and the desktop posts the result or
  output back; direct file operations write the `FileTransfer` audit kind.
  `Server` keeps the existing server-side endpoints.
- Direct uploads are capped at 8 MB because they cross the message bridge as
  base64. Larger files use the server path in `Auto`/`Server`; `Client` rejects
  them. Chunked/streamed uploads are a follow-up.
- Direct console/action output is client-reported, like tunnel events: the API
  validates ownership and records the `CommandExecution`, but cannot verify the
  bytes the desktop displays. The desktop redacts custom action values before
  posting. The security boundary is the user's SSH agent, not the API.
- The relay adds one WebSocket per local TCP connection. This is simple and
  stateless across the cluster, at the cost of an SSH setup per connection;
  multiplexing is a possible later optimisation.
