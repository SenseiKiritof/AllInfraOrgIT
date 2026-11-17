# ADR-014 — MCP agent consent and permissions

- Status: accepted
- Date: 2026-11-15
- Amends: ADR-010 (action tools enabled per user/group through `McpGrants`)

## Context

ADR-010 and the PT-18 hardening created one `McpApproval` per action call.
Every `run_reachability_tests` or `run_application_action` stopped on a Pending
row and waited for the owner to approve it from `/approvals`. The model could
not complete a routine task without a human decision per call, even after the
same user had already granted the agent the permission and held the
environment role.

The desired behaviour is consent at the agent level: approve the client once,
with individual permissions, then let it work until the owner changes or
revokes those permissions. The client may request a new permission; the owner
still decides.

## Decision

- An **MCP agent** is one client of one user: an API token (`token:{id}`) or an
  OAuth client (`oauth:{client_id}` / `azp`). The first action call creates it
  as `Pending`.
- The owner approves the agent from the cookie-authenticated web UI with
  individual permissions: `reachability.run`, `actions.run`, each scoped to one
  environment definition or to every environment. `SystemAdmin` can see and
  edit every agent; an MCP bearer token can never decide.
- After approval, action tools run without a per-call approval. They still
  require `mcp:operate`, an approved agent with a matching permission (or a
  legacy user/group `McpGrant`), the environment `ServerOperator`/`ServerAdmin`
  right and `confirm=true`. RBAC, rate limits and audit remain mandatory.
- Permissions are editable and reversible from `/approvals` (owner) and from
  the admin pages. Revoking or denying the agent blocks all its actions.
- The agent can call `request_mcp_permission` to create a Pending permission
  request; the owner approves or denies it in the same UI. Approving adds the
  permission, denying changes nothing. `get_mcp_agent` returns status,
  permissions and pending requests.
- The per-call `McpApprovals` table, endpoints and tool are removed. Audit
  events keep the decision history.

## Alternatives considered

- **Keep per-call approval and add a "remember" option**: rejected, it keeps
  the per-call row and an expiry window that does not match an agent session.
- **Approve the token scope only**: rejected, `mcp:operate` is coarse and does
  not distinguish reachability from application actions.
- **Approve at the Keycloak client level globally**: rejected, one user's
  consent must not enable the client for every user.
- **No agent approval, only `McpGrants`**: rejected, the user asked for an
  explicit first-use consent per client.

## Consequences

- A persistent permission lets an approved agent act without a fresh human
  check until the owner revokes it. Environment RBAC, `confirm=true`, rate
  limits and audit remain the compensating controls; destructive actions still
  need an operator role.
- New tables `McpAgents`, `McpAgentPermissions` and `McpPermissionRequests`;
  the `McpApprovals` table is dropped by the migration.
- The `/approvals` page becomes the agent and permission-request page; the
  legacy `/mcp-grants` page remains for user/group grants.
- Denying or revoking an agent revokes the personal API token that created it;
  the client must create a new token and be approved again. OAuth clients are
  revoked in Keycloak.
- API clients see `agent_approval_required` and `permission_required` instead
  of `approval_required`.
