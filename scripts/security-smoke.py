#!/usr/bin/env python3
"""Penetration-lite security smoke test for a running InfraOrgIT instance.

It checks the public MCP/tunnel surface with real tokens and reports one
PASS/FAIL/SKIP line per control. It never prints a token and never calls a
mutating action: the action checks use a non-existent test id, so a token that
is wrongly authorized would pass the grant checks without running any probe.

Checks:
  - protected endpoints without auth return 401;
  - OAuth protected-resource metadata is public and complete, and the /mcp
    401 challenge points to it;
  - mcp:read can list tools but not run an action tool;
  - an operate token without McpGrant/environment right is denied the action;
  - /api/tunnels/targets returns 200 plus allowlisted fields for a tunnel
    token, and 403 for a read-only token;
  - /api/audit-events denies a non-admin token;
  - optional rate-limit burst returns 429;
  - security headers are present;
  - CORS does not allow an arbitrary origin.

Environment variables (CLI flags override them):
  SECURITY_SMOKE_BASE_URL   base URL, default https://localhost:8443
  MCP_TOKEN                 personal token with mcp:read (preferred over --token)
  MCP_OPERATE_TOKEN         token with mcp:operate and tunnels:operate
  MCP_OUTSIDER_TOKEN        optional low-privilege token for the audit check
  SECURITY_SMOKE_RATE_REQUESTS  burst size for the rate-limit check, 0 = off
  SECURITY_SMOKE_INSECURE_TLS   1/true/yes to skip TLS verification
  SECURITY_SMOKE_TIMEOUT        per-request timeout in seconds, default 15

Examples:
  MCP_TOKEN=itk_... MCP_OPERATE_TOKEN=itk_... make security-smoke
  python3 scripts/security-smoke.py --self-test

The script only reads. Run it against production only in an approved window:
it writes LastUsedAt, consumes the token rate budget and creates audit rows.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import ssl
import sys
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, TextIO, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

DEFAULT_BASE_URL = "https://localhost:8443"
USER_AGENT = "infraorgit-security-smoke/1.0"
PROTOCOL_VERSION = "2025-11-25"
MAX_BODY = 1024 * 1024
WELL_KNOWN = "/.well-known/oauth-protected-resource"
REQUIRED_SCOPES = ("mcp:read", "mcp:operate")
ACTION_TOOL = "run_reachability_tests"

TARGET_FIELDS = {
    "serverId",
    "serverName",
    "environmentLabel",
    "sshHost",
    "sshPort",
    "username",
    "jump",
    "jumps",
    "targets",
    "services",
}
JUMP_FIELDS = {"host", "port", "username"}
ENDPOINT_FIELDS = {
    "serverApplicationId",
    "applicationId",
    "application",
    "version",
    "targetHost",
    "targetPort",
    "suggestedLocalPort",
}
SERVICE_FIELDS = {
    "id",
    "serverId",
    "name",
    "mode",
    "targetHost",
    "targetPort",
    "localPort",
    "remotePort",
    "kind",
    "openPath",
    "autoStart",
    "enabled",
}
SENSITIVE_FRAGMENTS = (
    "password",
    "secret",
    "privatekey",
    "private_key",
    "credential",
    "apikey",
    "api_key",
    "token",
)

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


class SmokeError(RuntimeError):
    """A request that could not be completed."""


@dataclass
class Response:
    status: int
    headers: Dict[str, str]
    body: bytes

    def json(self) -> Optional[Any]:
        text = self.body.decode("utf-8", "replace").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None


@dataclass
class McpReply:
    status: int
    payload: Optional[dict]
    error: Optional[str]
    text: str


@dataclass
class Summary:
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def ok(self) -> bool:
        return self.failed == 0


@dataclass
class Config:
    base_url: str
    token: str
    operate_token: Optional[str] = None
    outsider_token: Optional[str] = None
    timeout: float = 15.0
    insecure_tls: bool = False
    rate_limit_requests: int = 0
    expected_issuer: Optional[str] = None
    server_id: Optional[int] = None
    action_test_id: int = -1


class _NoRedirect(HTTPRedirectHandler):
    """Surface a 3xx instead of following it (a login redirect is a finding)."""

    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


class HttpClient:
    def __init__(self, base_url: str, insecure_tls: bool, timeout: float) -> None:
        endpoint = base_url.rstrip("/")
        if endpoint.endswith("/mcp"):
            endpoint = endpoint[: -len("/mcp")]
        self.base_url = endpoint
        self.timeout = timeout
        handlers: List[Any] = [_NoRedirect()]
        if insecure_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            handlers.append(HTTPSHandler(context=context))
        self.opener = build_opener(*handlers)

    def request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        payload: Optional[dict] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        body = None
        request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        request_headers.update(headers or {})

        request = Request(
            self.base_url + path,
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                status = response.status
                response_headers = dict(response.headers.items())
                content = response.read(MAX_BODY)
        except HTTPError as error:
            status = error.code
            response_headers = dict(error.headers.items()) if error.headers else {}
            content = error.read(MAX_BODY)
        except (URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", error)
            hint = " (try --insecure-tls for a self-signed certificate)" if isinstance(
                reason, ssl.SSLError
            ) else ""
            raise SmokeError(f"{type(error).__name__}: {reason}{hint}") from error

        return Response(
            status,
            {key.lower(): value for key, value in response_headers.items()},
            content,
        )


def _parse_sse(text: str, request_id: int) -> Optional[dict]:
    candidates: List[Any] = []
    for event in re.split(r"\r?\n\r?\n", text):
        data_lines = []
        for line in event.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            continue
        data = "\n".join(data_lines).strip()
        if not data or data == "[DONE]":
            continue
        try:
            candidates.append(json.loads(data))
        except json.JSONDecodeError:
            continue
    if not candidates:
        return None
    for item in reversed(candidates):
        if (
            isinstance(item, dict)
            and item.get("id") == request_id
            and ("result" in item or "error" in item)
        ):
            return item
    for item in reversed(candidates):
        if isinstance(item, dict) and ("result" in item or "error" in item):
            return item
    return candidates[-1] if isinstance(candidates[-1], dict) else None


class McpSession:
    """Stateless JSON-RPC calls with one protocol/session handshake."""

    def __init__(self, client: HttpClient, token: str) -> None:
        self.client = client
        self.token = token
        self.next_id = 0
        self.protocol_version: Optional[str] = None
        self.session_id: Optional[str] = None

    def post(
        self,
        method: str,
        params: Optional[dict] = None,
        initialize: bool = False,
    ) -> McpReply:
        self.next_id += 1
        request_id = self.next_id
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        headers = {"Accept": "application/json, text/event-stream"}
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        if self.session_id and not initialize:
            headers["Mcp-Session-Id"] = self.session_id

        try:
            response = self.client.request(
                "POST", "/mcp", token=self.token, payload=payload, headers=headers
            )
        except SmokeError as error:
            return McpReply(0, None, str(error), "")

        text = response.body.decode("utf-8", "replace").strip()
        if not 200 <= response.status < 300:
            return McpReply(response.status, None, f"HTTP {response.status}", text)

        parsed: Optional[dict]
        looks_like_sse = "text/event-stream" in response.headers.get(
            "content-type", ""
        ).lower() or text.startswith(("event:", "data:", "id:"))
        if looks_like_sse:
            parsed = _parse_sse(text, request_id)
        else:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                parsed = parsed[-1] if parsed else None
        if not isinstance(parsed, dict):
            return McpReply(response.status, None, "response is not JSON-RPC", text)

        if initialize:
            session_id = response.headers.get("mcp-session-id")
            if session_id:
                self.session_id = session_id
            result = parsed.get("result")
            if isinstance(result, dict) and isinstance(
                result.get("protocolVersion"), str
            ):
                self.protocol_version = result["protocolVersion"]
        return McpReply(response.status, parsed, None, text)

    def initialize(self) -> McpReply:
        return self.post(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "infraorgit-security-smoke", "version": "1.0"},
            },
            initialize=True,
        )

    def list_tools(self) -> McpReply:
        return self.post("tools/list", {})

    def call_tool(self, name: str, arguments: dict) -> McpReply:
        return self.post("tools/call", {"name": name, "arguments": arguments})


def _result(payload: Optional[dict]) -> Optional[dict]:
    if not isinstance(payload, dict):
        return None
    result = payload.get("result")
    return result if isinstance(result, dict) else None


def _content_text(payload: Optional[dict]) -> str:
    result = _result(payload)
    if not result:
        return ""
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    parts = [
        item.get("text", "")
        for item in content
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    ]
    return " ".join(parts).strip()


def _denial(payload: Optional[dict]) -> Tuple[bool, str]:
    """True when the call failed without executing the action."""
    if not isinstance(payload, dict):
        return False, "no JSON-RPC response"
    if isinstance(payload.get("error"), dict):
        message = str(payload["error"].get("message", "JSON-RPC error"))
        return True, f"JSON-RPC error: {message}"
    result = _result(payload)
    if result and result.get("isError") is True:
        return True, _content_text(payload) or "tool reported isError=true"
    return False, "tool reported success"


def _sensitive_field(value: Any, path: str = "") -> Optional[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            lowered = key.lower()
            if any(fragment in lowered for fragment in SENSITIVE_FRAGMENTS):
                return child_path
            found = _sensitive_field(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _sensitive_field(child, f"{path}[{index}]")
            if found:
                return found
    return None


def _unexpected_keys(value: Any, allowed: set, path: str) -> Optional[str]:
    if not isinstance(value, dict):
        return f"{path} is not an object"
    extra = sorted(set(value) - allowed)
    if extra:
        return f"{path} has unexpected fields: {', '.join(extra)}"
    return None


def validate_targets(document: Any) -> Optional[str]:
    """Return a problem description when the target payload is not allowlisted."""
    if not isinstance(document, dict):
        return "response is not an object"
    problem = _unexpected_keys(document, {"items"}, "response")
    if problem:
        return problem
    items = document.get("items")
    if not isinstance(items, list):
        return "items is not a list"

    for index, item in enumerate(items):
        path = f"items[{index}]"
        problem = _unexpected_keys(item, TARGET_FIELDS, path)
        if problem:
            return problem

        jump = item.get("jump")
        if jump is not None:
            problem = _unexpected_keys(jump, JUMP_FIELDS, f"{path}.jump")
            if problem:
                return problem
        for jump_index, child in enumerate(item.get("jumps") or []):
            problem = _unexpected_keys(
                child, JUMP_FIELDS, f"{path}.jumps[{jump_index}]"
            )
            if problem:
                return problem
        for target_index, child in enumerate(item.get("targets") or []):
            problem = _unexpected_keys(
                child, ENDPOINT_FIELDS, f"{path}.targets[{target_index}]"
            )
            if problem:
                return problem
        for service_index, child in enumerate(item.get("services") or []):
            problem = _unexpected_keys(
                child, SERVICE_FIELDS, f"{path}.services[{service_index}]"
            )
            if problem:
                return problem

    sensitive = _sensitive_field(document)
    return f"sensitive field in payload: {sensitive}" if sensitive else None


class Runner:
    def __init__(
        self,
        config: Config,
        secrets: List[str],
        out: TextIO = sys.stdout,
    ) -> None:
        self.config = config
        self.secrets = [secret for secret in secrets if secret]
        self.out = out
        self.client = HttpClient(config.base_url, config.insecure_tls, config.timeout)
        self.summary = Summary()
        self.mcp_401: Optional[Response] = None
        self.metadata: Optional[Response] = None
        self.server_id: Optional[int] = None
        self.read_session = McpSession(self.client, config.token)
        self.operate_session = (
            McpSession(self.client, config.operate_token)
            if config.operate_token
            else None
        )

    def redact(self, text: Any, limit: int = 240) -> str:
        value = str(text)
        for secret in self.secrets:
            value = value.replace(secret, "[redacted]")
        value = " ".join(value.split())
        return value[:limit] + ("..." if len(value) > limit else "")

    def record(self, name: str, status: str, detail: str = "") -> None:
        if status == PASS:
            self.summary.passed += 1
        elif status == FAIL:
            self.summary.failed += 1
        else:
            self.summary.skipped += 1
        suffix = f": {self.redact(detail)}" if detail else ""
        print(f"{status:<4} {name}{suffix}", file=self.out)

    def check(self, name: str, function: Any) -> None:
        try:
            status, detail = function()
        except SmokeError as error:
            status, detail = FAIL, f"request error: {error}"
        except Exception as error:  # noqa: BLE001 - one broken check must not stop the rest
            status, detail = FAIL, f"unexpected error: {type(error).__name__}: {error}"
        self.record(name, status, detail)

    # -- checks -------------------------------------------------------------

    def _expect_401(self, path: str, method: str = "GET") -> Tuple[str, str]:
        response = self.client.request(method, path)
        return (
            (PASS, f"{response.status}")
            if response.status == 401
            else (FAIL, f"expected 401, got {response.status}")
        )

    def _check_unauth_mcp(self) -> Tuple[str, str]:
        response = self.client.request(
            "POST",
            "/mcp",
            payload={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "security-smoke", "version": "1.0"},
                },
            },
            headers={
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": PROTOCOL_VERSION,
            },
        )
        self.mcp_401 = response
        if response.status == 401:
            return PASS, "401"
        return FAIL, f"expected 401, got {response.status}"

    def _check_metadata_public(self) -> Tuple[str, str]:
        self.metadata = self.client.request("GET", WELL_KNOWN)
        if self.metadata.status != 200:
            return FAIL, f"expected 200, got {self.metadata.status}"
        if self.metadata.json() is None:
            return FAIL, "response is not JSON"
        return PASS, "200, public JSON"

    def _check_metadata_content(self) -> Tuple[str, str]:
        if self.metadata is None or self.metadata.status != 200:
            return FAIL, "metadata unavailable"
        document = self.metadata.json()
        if not isinstance(document, dict):
            return FAIL, "metadata is not an object"

        resource = document.get("resource")
        if not isinstance(resource, str) or not _absolute_url(resource):
            return FAIL, "resource is missing or not an absolute URL"
        if not urlparse(resource).path.rstrip("/").endswith("/mcp"):
            return FAIL, f"resource does not point at /mcp: {resource}"

        servers = document.get("authorization_servers")
        if (
            not isinstance(servers, list)
            or not servers
            or not all(isinstance(item, str) and _absolute_url(item) for item in servers)
        ):
            return FAIL, "authorization_servers is missing or not absolute URLs"

        if self.config.expected_issuer:
            expected = self.config.expected_issuer.rstrip("/")
            if expected not in [item.rstrip("/") for item in servers]:
                return FAIL, f"authorization server does not include {expected}"

        scopes = document.get("scopes_supported")
        if not isinstance(scopes, list) or not all(
            isinstance(scope, str) for scope in scopes
        ):
            return FAIL, "scopes_supported is missing or not a string list"
        missing = [scope for scope in REQUIRED_SCOPES if scope not in scopes]
        if missing:
            return FAIL, f"scopes_supported is missing {', '.join(missing)}"
        return PASS, f"resource={resource} scopes={','.join(scopes)}"

    def _check_www_authenticate(self) -> Tuple[str, str]:
        if self.mcp_401 is None:
            return FAIL, "no unauthenticated /mcp response captured"
        header = self.mcp_401.headers.get("www-authenticate", "")
        if not header:
            return FAIL, "missing WWW-Authenticate on the /mcp 401"
        if not header.lower().startswith("bearer"):
            return FAIL, f"challenge is not Bearer: {header}"

        match = re.search(r'resource_metadata\s*=\s*"([^"]+)"', header)
        if not match:
            return (
                FAIL,
                "Bearer challenge lacks resource_metadata (RFC 9728): "
                'add resource_metadata=".../.well-known/oauth-protected-resource"',
            )
        metadata_url = match.group(1)
        if not _absolute_url(metadata_url):
            return FAIL, f"resource_metadata is not absolute: {metadata_url}"
        if urlparse(metadata_url).path.rstrip("/") != WELL_KNOWN:
            return FAIL, f"resource_metadata does not point at {WELL_KNOWN}"
        response = self.client.request("GET", WELL_KNOWN)
        if response.status != 200:
            return FAIL, f"resource_metadata is not reachable: HTTP {response.status}"
        return PASS, "Bearer resource_metadata points at the public metadata"

    def _handshake(self, session: McpSession) -> Optional[str]:
        reply = session.initialize()
        if reply.status != 200 or not reply.payload:
            return f"initialize failed: {reply.error or f'HTTP {reply.status}'}"
        return None

    def _check_read_tools(self) -> Tuple[str, str]:
        error = self._handshake(self.read_session)
        if error:
            return FAIL, error
        reply = self.read_session.list_tools()
        if reply.status != 200:
            return FAIL, f"tools/list returned HTTP {reply.status}"
        result = _result(reply.payload)
        tools = result.get("tools") if result else None
        if not isinstance(tools, list) or not tools:
            return FAIL, "tools/list returned no tools"
        return PASS, f"{len(tools)} tools"

    def _check_read_action_denied(self) -> Tuple[str, str]:
        server_id = self.server_id or self.config.server_id or 1
        reply = self.read_session.call_tool(
            ACTION_TOOL,
            {
                "serverId": server_id,
                "confirm": True,
                "testIds": [self.config.action_test_id],
            },
        )
        if reply.status != 200:
            return FAIL, f"action call returned HTTP {reply.status}"
        denied, detail = _denial(reply.payload)
        return (PASS, f"denied: {detail}") if denied else (FAIL, detail)

    def _discover_server_id(self, session: McpSession) -> Optional[int]:
        if self.config.server_id:
            return self.config.server_id
        reply = session.call_tool("list_servers", {"limit": 1})
        if reply.status != 200:
            return None
        text = _content_text(reply.payload)
        try:
            document = json.loads(text)
            items = document.get("items") if isinstance(document, dict) else None
            if items and isinstance(items[0], dict) and isinstance(items[0].get("id"), int):
                return items[0]["id"]
        except (json.JSONDecodeError, AttributeError, IndexError):
            return None
        return None

    def _check_operate_action_denied(self) -> Tuple[str, str]:
        if self.operate_session is None:
            return SKIP, "no --operate-token provided"
        error = self._handshake(self.operate_session)
        if error:
            return FAIL, f"operate token {error}"
        if self.server_id is None:
            self.server_id = self._discover_server_id(self.operate_session)
        if self.server_id is None:
            return SKIP, "no server id available (use --server-id)"
        reply = self.operate_session.call_tool(
            ACTION_TOOL,
            {
                "serverId": self.server_id,
                "confirm": True,
                "testIds": [self.config.action_test_id],
            },
        )
        if reply.status != 200:
            return FAIL, f"action call returned HTTP {reply.status}"
        denied, detail = _denial(reply.payload)
        if denied:
            if "non trovato" in detail.lower() or "not found" in detail.lower():
                return FAIL, f"serverId={self.server_id} does not exist: {detail}"
            return PASS, f"denied: {detail}"
        return (
            FAIL,
            "operate token without grant/operator right executed the action "
            f"(serverId={self.server_id})",
        )

    def _check_tunnels_tunnel_token(self) -> Tuple[str, str]:
        if self.config.operate_token is None:
            return SKIP, "no --operate-token provided"
        response = self.client.request(
            "GET", "/api/tunnels/targets", token=self.config.operate_token
        )
        if response.status == 403:
            return FAIL, "operate token has no tunnels:operate scope or no operator right"
        if response.status != 200:
            return FAIL, f"expected 200, got {response.status}"
        document = response.json()
        problem = validate_targets(document)
        if problem:
            return FAIL, problem
        count = len(document.get("items") or []) if isinstance(document, dict) else 0
        return PASS, f"200, allowlisted fields, {count} targets"

    def _check_tunnels_read_token(self) -> Tuple[str, str]:
        response = self.client.request(
            "GET", "/api/tunnels/targets", token=self.config.token
        )
        if response.status == 403:
            return PASS, "403"
        return FAIL, f"expected 403, got {response.status}"

    def _check_audit_non_admin(self) -> Tuple[str, str]:
        token = self.config.outsider_token or self.config.token
        persona = "outsider" if self.config.outsider_token else "read"
        response = self.client.request("GET", "/api/audit-events", token=token)
        if response.status == 403:
            return PASS, f"403 ({persona} token)"
        if response.status == 401:
            return (
                PASS,
                f"401 ({persona} token): route accepts browser sessions, "
                "so a bearer token is rejected before the admin check",
            )
        return FAIL, f"expected 403, got {response.status}"

    def _check_security_headers(self) -> Tuple[str, str]:
        response = self.client.request("GET", "/health/live")
        used = "/health/live"
        if response.status != 200:
            response = self.client.request("GET", "/")
            used = "/"
        if response.status != 200:
            return FAIL, f"/health/live and / returned {response.status}"

        missing = []
        if response.headers.get("x-content-type-options", "").lower() != "nosniff":
            missing.append("X-Content-Type-Options: nosniff")
        if not response.headers.get("referrer-policy"):
            missing.append("Referrer-Policy")
        if missing:
            return FAIL, f"{used} is missing {', '.join(missing)}"
        return PASS, f"{used}: nosniff and {response.headers['referrer-policy']}"

    def _check_cors(self) -> Tuple[str, str]:
        origin = "https://security-smoke.invalid"
        response = self.client.request(
            "OPTIONS",
            "/api/servers",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        allowed = response.headers.get("access-control-allow-origin")
        if allowed is None:
            return PASS, f"no CORS headers (HTTP {response.status})"
        if allowed in ("*", origin):
            return FAIL, f"arbitrary origin allowed: {allowed}"
        return PASS, f"fixed origin: {allowed}"

    def _check_rate_limit(self) -> Tuple[str, str]:
        total = self.config.rate_limit_requests
        if total <= 0:
            return SKIP, (
                "disabled (set --rate-limit-requests or "
                "SECURITY_SMOKE_RATE_REQUESTS)"
            )
        for index in range(1, total + 1):
            reply = self.read_session.list_tools()
            if reply.status == 429:
                return PASS, f"429 after {index} requests"
            if reply.status != 200:
                return FAIL, f"HTTP {reply.status} after {index} requests"
        return FAIL, f"no 429 in {total} requests (limit 120/min per token)"

    def run(self) -> Summary:
        print(f"security smoke: {self.client.base_url}", file=self.out)
        print(
            "  read=mcp:read operate="
            + ("provided" if self.config.operate_token else "absent")
            + " outsider="
            + ("provided" if self.config.outsider_token else "absent")
            + f" timeout={self.config.timeout:g}s",
            file=self.out,
        )

        self.check("unauthenticated POST /mcp -> 401", self._check_unauth_mcp)
        self.check(
            "unauthenticated GET /api/servers -> 401",
            lambda: self._expect_401("/api/servers"),
        )
        self.check(
            "unauthenticated GET /api/tunnels/targets -> 401",
            lambda: self._expect_401("/api/tunnels/targets"),
        )
        self.check(
            "unauthenticated GET /api/audit-events -> 401",
            lambda: self._expect_401("/api/audit-events"),
        )
        self.check("oauth protected-resource is public", self._check_metadata_public)
        self.check(
            "oauth metadata advertises resource, server and scopes",
            self._check_metadata_content,
        )
        self.check(
            "mcp 401 challenge points to metadata", self._check_www_authenticate
        )
        self.check("read token can call tools/list", self._check_read_tools)
        self.check(
            "read token cannot call an action tool", self._check_read_action_denied
        )
        self.check(
            "operate token without grant is denied the action",
            self._check_operate_action_denied,
        )
        self.check(
            "tunnels targets with tunnel token", self._check_tunnels_tunnel_token
        )
        self.check(
            "tunnels targets with read-only token -> 403",
            self._check_tunnels_read_token,
        )
        self.check(
            "audit-events with non-admin token -> denied", self._check_audit_non_admin
        )
        self.check("security headers present", self._check_security_headers)
        self.check(
            "CORS does not allow an arbitrary origin", self._check_cors
        )
        self.check("mcp rate limit burst -> 429", self._check_rate_limit)

        print(
            f"result: {'PASS' if self.summary.ok else 'FAIL'} "
            f"({self.summary.passed} passed, {self.summary.failed} failed, "
            f"{self.summary.skipped} skipped)",
            file=self.out,
        )
        return self.summary


def _absolute_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _run_capture(config: Config) -> Tuple[Summary, str]:
    buffer = io.StringIO()
    secrets = [config.token, config.operate_token, config.outsider_token]
    summary = Runner(config, [secret for secret in secrets if secret], out=buffer).run()
    return summary, buffer.getvalue()


# -- self-test stub ---------------------------------------------------------


class _StubState:
    read_token = "itk_self_test_read_token"
    operate_token = "itk_self_test_operate_token"
    metadata_scopes: List[str] = ["mcp:read", "mcp:operate"]
    www_authenticate: Optional[str] = None
    headers_enabled = True
    tunnels_extra = False
    cors_origin: Optional[str] = None
    rate_limit_after = 0
    rate_requests = 0
    lock = threading.Lock()

    def reset(self) -> None:
        self.metadata_scopes = ["mcp:read", "mcp:operate"]
        self.www_authenticate = None
        self.headers_enabled = True
        self.tunnels_extra = False
        self.cors_origin = None
        self.rate_limit_after = 0
        self.rate_requests = 0


class _StubServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    state: _StubState


class _StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: _StubServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send(
        self,
        status: int,
        payload: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if payload is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        if self.server.state.headers_enabled:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _base(self) -> str:
        return f"http://{self.headers.get('Host', '127.0.0.1')}"

    def _token(self) -> Optional[str]:
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            return header[len("Bearer ") :].strip()
        return None

    def _jsonrpc(self, request_id: Any, result: Any = None, error: Any = None) -> None:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
        if error is not None:
            payload["error"] = error
        else:
            payload["result"] = result
        self._send(200, payload)

    def do_OPTIONS(self) -> None:
        headers = {"Allow": "GET, POST"}
        if self.server.state.cors_origin:
            headers["Access-Control-Allow-Origin"] = self.server.state.cors_origin
            headers["Access-Control-Allow-Methods"] = "GET, POST"
        self._send(204, headers=headers)

    def do_GET(self) -> None:
        state = self.server.state
        path = urlparse(self.path).path
        token = self._token()

        if path in (WELL_KNOWN, "/mcp/.well-known/oauth-protected-resource"):
            self._send(
                200,
                {
                    "resource": self._base() + "/mcp",
                    "authorization_servers": [self._base() + "/realms/infraorgit"],
                    "scopes_supported": state.metadata_scopes,
                    "bearer_methods_supported": ["header"],
                },
            )
            return
        if path == "/api/servers":
            self._send(401, {"error": "unauthorized"})
            return
        if path == "/api/audit-events":
            if token is None:
                self._send(401, {"error": "unauthorized"})
            else:
                self._send(403, {"error": "forbidden"})
            return
        if path == "/api/tunnels/targets":
            if token is None:
                self._send(401, {"error": "unauthorized"})
                return
            if token == state.read_token:
                self._send(403, {"error": "forbidden"})
                return
            item = {
                "serverId": 1,
                "serverName": "stub",
                "environmentLabel": "stub / test",
                "sshHost": "127.0.0.1",
                "sshPort": 22,
                "username": "stub",
                "jump": None,
                "jumps": [],
                "targets": [
                    {
                        "serverApplicationId": 1,
                        "applicationId": 1,
                        "application": "app",
                        "version": "1.0.0",
                        "targetHost": "127.0.0.1",
                        "targetPort": 8080,
                        "suggestedLocalPort": 8080,
                    }
                ],
                "services": [],
            }
            if state.tunnels_extra:
                item["credentials"] = {"password": "must-not-leak"}
            self._send(200, {"items": [item]})
            return
        if path in ("/health/live", "/"):
            self._send(200, {"status": "ok"})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        state = self.server.state
        path = urlparse(self.path).path
        if path != "/mcp":
            self._send(404, {"error": "not found"})
            return

        with state.lock:
            state.rate_requests += 1
            limited = 0 < state.rate_limit_after < state.rate_requests
        if limited:
            self._send(429, {"error": "rate limited"}, headers={"Retry-After": "60"})
            return

        if self.headers.get("Authorization") not in (
            None,
            f"Bearer {state.read_token}",
            f"Bearer {state.operate_token}",
        ):
            self._send(401, {"error": "unauthorized"})
            return
        token = self._token()
        if token is None:
            challenge = state.www_authenticate
            if challenge is None:
                challenge = (
                    'Bearer resource_metadata="'
                    + self._base()
                    + WELL_KNOWN
                    + '"'
                )
            self._send(401, {}, headers={"WWW-Authenticate": challenge})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid json"})
            return

        request_id = request.get("id")
        method = request.get("method")
        if method == "initialize":
            self._send(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {},
                        "serverInfo": {"name": "stub", "version": "1"},
                    },
                },
                headers={"Mcp-Session-Id": "stub-session"},
            )
            return
        if method == "tools/list":
            self._jsonrpc(
                request_id,
                {
                    "tools": [
                        {
                            "name": "list_servers",
                            "description": "stub",
                            "inputSchema": {"type": "object"},
                        },
                        {
                            "name": ACTION_TOOL,
                            "description": "stub",
                            "inputSchema": {"type": "object"},
                        },
                    ]
                },
            )
            return
        if method == "tools/call":
            call = (request.get("params") or {})
            name = call.get("name")
            if name == "list_servers":
                self._jsonrpc(
                    request_id,
                    {
                        "content": [
                            {"type": "text", "text": json.dumps({"items": [{"id": 1}]})}
                        ],
                        "isError": False,
                    },
                )
                return
            if name == ACTION_TOOL:
                message = (
                    "Serve lo scope mcp:operate."
                    if token == state.read_token
                    else "Nessun grant MCP per reachability.run su questo ambiente."
                )
                self._jsonrpc(
                    request_id,
                    {
                        "content": [{"type": "text", "text": message}],
                        "isError": True,
                    },
                )
                return
        self._jsonrpc(
            request_id,
            error={"code": -32601, "message": "method not found"},
        )


def _start_stub() -> Tuple[_StubServer, threading.Thread, str]:
    state = _StubState()
    server = _StubServer(("127.0.0.1", 0), _StubHandler)
    server.state = state
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_address[1]}"


def _self_test() -> int:
    checks = 0
    server, thread, base_url = _start_stub()
    state = server.state
    captured = ""

    def config(rate_requests: int = 0) -> Config:
        return Config(
            base_url=base_url,
            token=state.read_token,
            operate_token=state.operate_token,
            timeout=5.0,
            rate_limit_requests=rate_requests,
        )

    try:
        summary, captured = _run_capture(config())
        assert summary.ok and summary.failed == 0, captured
        assert summary.skipped == 1, captured  # only the disabled rate-limit check
        assert state.read_token not in captured, "read token leaked in output"
        assert state.operate_token not in captured, "operate token leaked in output"
        checks += 1

        state.metadata_scopes = ["mcp:read"]
        state.www_authenticate = "Bearer"
        state.headers_enabled = False
        state.tunnels_extra = True
        state.cors_origin = "*"
        summary, captured = _run_capture(config(rate_requests=3))
        assert not summary.ok, captured
        assert summary.failed >= 5, captured
        assert "resource_metadata" in captured, captured
        assert "unexpected fields" in captured, captured
        assert "arbitrary origin" in captured, captured
        assert "no 429" in captured, captured
        state.reset()
        checks += 1

        state.reset()
        # The run sends seven MCP requests before the final burst; leave
        # headroom so only the burst itself is throttled.
        state.rate_limit_after = 10
        summary, captured = _run_capture(config(rate_requests=5))
        assert summary.ok, captured
        assert "429 after" in captured, captured
        state.reset()
        checks += 1

        summary, captured = _run_capture(
            Config(base_url=base_url, token=state.read_token, timeout=5.0)
        )
        assert summary.ok, captured
        assert "SKIP" in captured and "operate-token" in captured, captured
        checks += 1

        redacted = Runner(config(), [state.read_token], out=io.StringIO()).redact(
            f"Bearer {state.read_token}"
        )
        assert state.read_token not in redacted and "[redacted]" in redacted
        checks += 1
    except AssertionError as error:
        print(f"self-test failed: {error}", file=sys.stderr)
        if captured:
            print(captured, file=sys.stderr)
        return 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print(f"self-test: ok ({checks} checks, stub {base_url})")
    return 0


# -- CLI --------------------------------------------------------------------


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, fallback: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return fallback
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{name} must be an integer") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Penetration-lite security smoke test for a running InfraOrgIT "
            "instance. Tokens are read from the environment by default."
        ),
        epilog=(
            "Examples:\n"
            "  MCP_TOKEN=itk_... MCP_OPERATE_TOKEN=itk_... make security-smoke\n"
            "  MCP_TOKEN=itk_... python3 scripts/security-smoke.py "
            "--base-url https://localhost:8443 --insecure-tls\n"
            "  python3 scripts/security-smoke.py --self-test\n\n"
            "The script is read-only: action checks use a non-existent test id. "
            "It consumes the /mcp rate budget; the burst check runs last."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SECURITY_SMOKE_BASE_URL")
        or os.environ.get("MCP_BASE_URL")
        or DEFAULT_BASE_URL,
        help=(
            "instance base URL without /mcp "
            f"(env SECURITY_SMOKE_BASE_URL, default {DEFAULT_BASE_URL})"
        ),
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("MCP_TOKEN"),
        help="personal token with mcp:read (env MCP_TOKEN; prefer the env over the flag)",
    )
    parser.add_argument(
        "--operate-token",
        default=os.environ.get("MCP_OPERATE_TOKEN"),
        help=(
            "optional token with mcp:operate and tunnels:operate "
            "(env MCP_OPERATE_TOKEN)"
        ),
    )
    parser.add_argument(
        "--outsider-token",
        default=os.environ.get("MCP_OUTSIDER_TOKEN"),
        help="optional low-privilege token for the audit check (env MCP_OUTSIDER_TOKEN)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("SECURITY_SMOKE_TIMEOUT", "15")),
        help="per-request timeout in seconds, default 15",
    )
    parser.add_argument(
        "--insecure-tls",
        action="store_true",
        default=_env_flag("SECURITY_SMOKE_INSECURE_TLS")
        or _env_flag("MCP_INSECURE_TLS"),
        help=(
            "skip TLS verification for a self-signed local stack "
            "(env SECURITY_SMOKE_INSECURE_TLS=1)"
        ),
    )
    parser.add_argument(
        "--rate-limit-requests",
        type=int,
        default=_env_int("SECURITY_SMOKE_RATE_REQUESTS", 0),
        help=(
            "burst size for the 429 check, default 0 (off); use at least 121 "
            "to exceed the 120/min budget after a fresh window"
        ),
    )
    parser.add_argument(
        "--expected-issuer",
        default=os.environ.get("SECURITY_SMOKE_EXPECTED_ISSUER"),
        help="optional authorization server that must appear in the metadata",
    )
    parser.add_argument(
        "--server-id",
        type=int,
        help="optional server id for the action denial checks (default: first listed)",
    )
    parser.add_argument(
        "--action-test-id",
        type=int,
        default=-1,
        help=(
            "test id sent to the action tool; default -1 so a wrongly authorized "
            "call runs no probe"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the local stub server and internal checks, no live instance needed",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    try:
        parser = build_parser()
    except (ValueError, argparse.ArgumentTypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not args.token:
        parser.error("missing token: set MCP_TOKEN or pass --token")
    if not _absolute_url(args.base_url):
        parser.error("--base-url must be an absolute http(s) URL")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.rate_limit_requests < 0:
        parser.error("--rate-limit-requests must be 0 or greater")
    if args.server_id is not None and args.server_id < 1:
        parser.error("--server-id must be a positive integer")

    config = Config(
        base_url=args.base_url,
        token=args.token,
        operate_token=args.operate_token,
        outsider_token=args.outsider_token,
        timeout=args.timeout,
        insecure_tls=args.insecure_tls,
        rate_limit_requests=args.rate_limit_requests,
        expected_issuer=args.expected_issuer,
        server_id=args.server_id,
        action_test_id=args.action_test_id,
    )
    secrets = [config.token, config.operate_token, config.outsider_token]
    summary = Runner(config, [secret for secret in secrets if secret]).run()
    return 0 if summary.ok else 1


if __name__ == "__main__":
    sys.exit(main())
