#!/usr/bin/env python3
"""Load test for the InfraOrgIT MCP Streamable HTTP endpoint.

The script speaks JSON-RPC 2.0 over POST /mcp, accepts both JSON and
text/event-stream responses and reports latency percentiles plus throughput.
It is read-only by default: initialize, tools/list and, only when --tool is
given, tools/call. Use a personal token with mcp:read.

Environment variables (CLI flags override them):
  MCP_BASE_URL       base URL, default http://localhost:5298
  MCP_TOKEN          personal token with mcp:read (preferred over --token)
  MCP_REQUESTS       measured requests, default 30
  MCP_CONCURRENCY    worker threads, default 5
  MCP_TOOL           optional read tool to call, e.g. list_servers
  MCP_ARGUMENTS      JSON object for tools/call, default {}
  MCP_TIMEOUT        per-request timeout in seconds, default 30
  MCP_INSECURE_TLS   1/true/yes to skip TLS verification (self-signed local)

Examples:
  MCP_TOKEN=itk_... python3 scripts/loadtest-mcp.py
  MCP_TOKEN=itk_... python3 scripts/loadtest-mcp.py --requests 60 --concurrency 6
  MCP_TOKEN=itk_... python3 scripts/loadtest-mcp.py \\
      --tool list_servers --arguments '{"limit":10}' --requests 60
  MCP_TOKEN=itk_... MCP_INSECURE_TLS=1 make loadtest-mcp
  python3 scripts/loadtest-mcp.py --self-test

The rate limit on /mcp is 120 requests/minute per token (or username), so a
single run above that includes expected 429 responses and exits non-zero.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import ssl
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, TextIO, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPSHandler, Request, build_opener

DEFAULT_BASE_URL = "http://localhost:5298"
PROTOCOL_VERSION = "2025-11-25"
MAX_BODY = 4 * 1024 * 1024
USER_AGENT = "infraorgit-loadtest-mcp/1.0"
ACTION_TOOLS = {"run_reachability_tests", "run_application_action"}


@dataclass
class Outcome:
    """One JSON-RPC attempt, already classified."""

    category: str
    message: str = ""
    status: int = 0
    duration_ms: float = 0.0

    def describe(self) -> str:
        label = self.message or self.category
        if self.status and str(self.status) not in label:
            label = f"HTTP {self.status} {label}"
        return f"{self.category}: {label}"


CATEGORY_FIELDS = {
    "ok": "ok",
    "http": "http_errors",
    "auth": "auth_errors",
    "rate_limited": "rate_limited",
    "jsonrpc": "jsonrpc_errors",
    "tool": "tool_errors",
    "protocol": "protocol_errors",
    "network": "network_errors",
}


@dataclass
class Result:
    expected: int
    ok: int = 0
    http_errors: int = 0
    auth_errors: int = 0
    rate_limited: int = 0
    jsonrpc_errors: int = 0
    tool_errors: int = 0
    protocol_errors: int = 0
    network_errors: int = 0
    attempted: int = 0
    warmup_ok: int = 0
    warmup_failures: int = 0
    latencies: List[float] = field(default_factory=list)
    messages: Dict[str, int] = field(default_factory=dict)
    warmup_messages: Dict[str, int] = field(default_factory=dict)
    first_start: Optional[float] = None
    last_end: Optional[float] = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def passed(self) -> bool:
        return (
            self.warmup_failures == 0
            and self.attempted == self.expected
            and self.expected > 0
            and self.ok == self.attempted
        )

    def add_warmup_ok(self) -> None:
        with self.lock:
            self.warmup_ok += 1

    def add_warmup_failure(self, outcome: Outcome) -> None:
        with self.lock:
            self.warmup_failures += 1
            key = outcome.describe()
            self.warmup_messages[key] = self.warmup_messages.get(key, 0) + 1

    def add_measured(self, outcome: Outcome, started: float, ended: float) -> None:
        with self.lock:
            self.attempted += 1
            setattr(
                self,
                CATEGORY_FIELDS.get(outcome.category, "protocol_errors"),
                getattr(self, CATEGORY_FIELDS.get(outcome.category, "protocol_errors"))
                + 1,
            )
            self.latencies.append(outcome.duration_ms)
            if outcome.category != "ok":
                key = outcome.describe()
                self.messages[key] = self.messages.get(key, 0) + 1
            if self.first_start is None or started < self.first_start:
                self.first_start = started
            if self.last_end is None or ended > self.last_end:
                self.last_end = ended


def percentile(values: List[float], wanted: float) -> float:
    """Nearest-rank percentile; zero when there is no sample."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = math.ceil(wanted / 100.0 * len(ordered)) - 1
    return ordered[max(0, min(rank, len(ordered) - 1))]


def redact(text: str, token: str) -> str:
    return text.replace(token, "[redacted]") if token else text


def _parse_sse(text: str, request_id: int) -> Tuple[Optional[dict], Optional[str]]:
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
        return None, "no JSON data in SSE stream"

    for item in reversed(candidates):
        if (
            isinstance(item, dict)
            and item.get("id") == request_id
            and ("result" in item or "error" in item)
        ):
            return item, None
    for item in reversed(candidates):
        if isinstance(item, dict) and ("result" in item or "error" in item):
            return item, None
    return candidates[-1], None


def parse_payload(
    content_type: str, body: bytes, request_id: int
) -> Tuple[Optional[dict], Optional[str]]:
    text = body.decode("utf-8", "replace").strip()
    if not text:
        return None, "empty response body"

    looks_like_sse = "text/event-stream" in content_type.lower() or text.startswith(
        ("event:", "data:", "id:")
    )
    if looks_like_sse:
        payload, error = _parse_sse(text, request_id)
    else:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, f"invalid JSON: {exc}"

    if isinstance(payload, list):
        payload = payload[-1] if payload else None
    if not isinstance(payload, dict):
        return None, "response is not a JSON-RPC object"
    return payload, None


class McpClient:
    def __init__(
        self,
        endpoint: str,
        token: str,
        timeout: float,
        insecure_tls: bool,
    ) -> None:
        self.endpoint = endpoint
        self.token = token
        self.timeout = timeout
        self.protocol_version: Optional[str] = None
        self.session_id: Optional[str] = None
        self.next_id = 0
        handlers = []
        if insecure_tls:
            handlers.append(HTTPSHandler(context=ssl._create_unverified_context()))
        self.opener = build_opener(*handlers)

    def _request_id(self) -> int:
        self.next_id += 1
        return self.next_id

    def _post(self, method: str, params: Optional[dict] = None) -> Outcome:
        request_id = self._request_id()
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": USER_AGENT,
        }
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                retry_after = response.headers.get("Retry-After", "")
                session_id = response.headers.get("Mcp-Session-Id")
                body = response.read(MAX_BODY)
        except HTTPError as error:
            status = error.code
            content_type = error.headers.get("Content-Type", "") if error.headers else ""
            retry_after = error.headers.get("Retry-After", "") if error.headers else ""
            session_id = None
            body = error.read(MAX_BODY)
        except (URLError, TimeoutError, OSError) as error:
            return Outcome(
                "network",
                redact(f"{type(error).__name__}: {error}", self.token),
            )

        if status == 429:
            detail = f"rate limited (Retry-After: {retry_after})" if retry_after else "rate limited"
            return Outcome("rate_limited", detail, status)
        if status in (401, 403):
            return Outcome("auth", "authentication or scope rejected", status)
        if not 200 <= status < 300:
            return Outcome("http", "unexpected status", status)

        if session_id:
            self.session_id = session_id

        response_object, parse_error = parse_payload(content_type, body, request_id)
        if parse_error or response_object is None:
            return Outcome(
                "protocol",
                redact(parse_error or "empty response", self.token),
                status,
            )

        error = response_object.get("error")
        if isinstance(error, dict):
            message = str(error.get("message", "JSON-RPC error"))
            return Outcome(
                "jsonrpc",
                redact(f"JSON-RPC {error.get('code')}: {message}", self.token),
                status,
            )

        if response_object.get("id") != request_id:
            return Outcome(
                "protocol",
                f"response id {response_object.get('id')!r} does not match {request_id}",
                status,
            )

        result = response_object.get("result")
        if result is None:
            return Outcome("protocol", "response has no result", status)
        if isinstance(result, dict) and result.get("isError"):
            return Outcome("tool", "tool returned isError=true", status)

        if method == "initialize" and isinstance(result, dict):
            version = result.get("protocolVersion")
            if isinstance(version, str) and version:
                self.protocol_version = version
        return Outcome("ok", "", status)

    def initialize(self) -> Outcome:
        return self._post(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "infraorgit-loadtest-mcp", "version": "1.0"},
            },
        )

    def list_tools(self) -> Outcome:
        return self._post("tools/list", {})

    def call_tool(self, name: str, arguments: dict) -> Outcome:
        return self._post("tools/call", {"name": name, "arguments": arguments})


@dataclass
class Config:
    base_url: str
    token: str
    requests: int
    concurrency: int
    tool: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    insecure_tls: bool = False


def _endpoint(base_url: str) -> str:
    endpoint = base_url.rstrip("/")
    return endpoint if endpoint.endswith("/mcp") else endpoint + "/mcp"


def _split(total: int, workers: int) -> List[int]:
    base, extra = divmod(total, workers)
    return [base + (1 if index < extra else 0) for index in range(workers)]


def _worker(config: Config, count: int, result: Result) -> None:
    client = McpClient(
        _endpoint(config.base_url),
        config.token,
        config.timeout,
        config.insecure_tls,
    )
    try:
        outcome = client.initialize()
        if outcome.category != "ok":
            result.add_warmup_failure(outcome)
            return
        result.add_warmup_ok()

        if config.tool:
            outcome = client.list_tools()
            if outcome.category != "ok":
                result.add_warmup_failure(outcome)
                return
            result.add_warmup_ok()

        for _ in range(count):
            started = time.perf_counter()
            if config.tool:
                outcome = client.call_tool(config.tool, config.arguments)
            else:
                outcome = client.list_tools()
            ended = time.perf_counter()
            outcome.duration_ms = (ended - started) * 1000.0
            result.add_measured(outcome, started, ended)
    except Exception as error:  # noqa: BLE001 - a worker crash must fail the run
        result.add_warmup_failure(
            Outcome("network", redact(f"worker error: {error}", config.token))
        )


def run_load(config: Config, out: TextIO = sys.stdout) -> Result:
    endpoint = _endpoint(config.base_url)
    workers = min(config.concurrency, config.requests)
    counts = _split(config.requests, workers)
    result = Result(expected=config.requests)

    arguments = json.dumps(config.arguments, separators=(",", ":"))
    print(f"MCP load test: POST {endpoint}", file=out)
    print(
        f"  requests={config.requests} concurrency={config.concurrency} "
        f"workers={workers} tool={config.tool or '-'} arguments={arguments} "
        f"timeout={config.timeout:g}s",
        file=out,
    )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_worker, config, count, result)
            for count in counts
        ]
        for future in futures:
            future.result()

    print(
        f"warm-up: {workers} workers, {result.warmup_ok} ok, "
        f"{result.warmup_failures} failed",
        file=out,
    )
    print(
        f"total={result.attempted}/{result.expected} ok={result.ok} "
        f"http={result.http_errors} auth={result.auth_errors} "
        f"rate_limited={result.rate_limited} jsonrpc={result.jsonrpc_errors} "
        f"tool={result.tool_errors} protocol={result.protocol_errors} "
        f"network={result.network_errors}",
        file=out,
    )

    if result.latencies:
        print(
            "latency: "
            f"p50={percentile(result.latencies, 50):.1f}ms "
            f"p95={percentile(result.latencies, 95):.1f}ms "
            f"p99={percentile(result.latencies, 99):.1f}ms "
            f"max={max(result.latencies):.1f}ms",
            file=out,
        )
    if result.first_start is not None and result.last_end is not None:
        window = max(result.last_end - result.first_start, 1e-9)
        print(
            f"throughput: {result.attempted / window:.1f} req/s "
            f"over {window:.3f}s measured window",
            file=out,
        )

    for label, messages in (
        ("warm-up error", result.warmup_messages),
        ("error", result.messages),
    ):
        for message, count in sorted(
            messages.items(), key=lambda item: (-item[1], item[0])
        )[:8]:
            print(f"  {count}x {label}: {redact(message, config.token)}", file=out)

    print(f"result: {'PASS' if result.passed else 'FAIL'}", file=out)
    return result


def _opener_tls_from_env() -> bool:
    return os.environ.get("MCP_INSECURE_TLS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


class _StubServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    token = "itk_self_test_token_do_not_print"
    rate_limit_tool_calls = 0
    rate_limit_lock = threading.Lock()


class _StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: _StubServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send(
        self,
        status: int,
        payload: Any,
        content_type: str = "application/json",
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, status: int, payload: Any) -> None:
        body = b"event: message\ndata: " + json.dumps(payload).encode("utf-8") + b"\n\n"
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/mcp":
            self._send(404, {"error": "not found"})
            return
        if self.headers.get("Authorization") != f"Bearer {self.server.token}":
            self._send(401, {"error": "unauthorized"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid json"})
            return

        method = payload.get("method")
        request_id = payload.get("id")
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
        if (
            self.headers.get("Mcp-Session-Id") != "stub-session"
            or self.headers.get("MCP-Protocol-Version") != PROTOCOL_VERSION
        ):
            self._send(400, {"error": "missing session or protocol header"})
            return
        if method == "tools/list":
            self._send_sse(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "list_servers",
                                "description": "stub",
                                "inputSchema": {"type": "object"},
                            },
                            {
                                "name": "boom",
                                "description": "stub error",
                                "inputSchema": {"type": "object"},
                            },
                        ]
                    },
                },
            )
            return
        if method == "tools/call":
            with self.server.rate_limit_lock:
                limited = self.server.rate_limit_tool_calls > 0
                if limited:
                    self.server.rate_limit_tool_calls -= 1
            if limited:
                self._send(429, {"error": "rate limited"}, headers={"Retry-After": "1"})
                return
            name = (payload.get("params") or {}).get("name")
            if name == "boom":
                self._send(
                    200,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32000, "message": "stub tool failed"},
                    },
                )
                return
            self._send(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": "[]"}],
                        "isError": False,
                    },
                },
            )
            return

        self._send(
            200,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "method not found"},
            },
        )


def _run_capture(config: Config) -> Tuple[Result, str]:
    buffer = io.StringIO()
    result = run_load(config, out=buffer)
    return result, buffer.getvalue()


def _self_test() -> int:
    checks = 0
    server = _StubServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    captured = ""

    try:
        assert percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.0
        assert percentile([1.0, 2.0, 3.0, 4.0], 95) == 4.0
        assert percentile([], 95) == 0.0
        checks += 1

        parsed, error = _parse_sse(
            'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n',
            1,
        )
        assert error is None and parsed and parsed["result"]["ok"] is True
        checks += 1

        parsed, error = parse_payload(
            "application/json",
            b'{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}',
            2,
        )
        assert error is None and parsed and parsed["id"] == 2
        checks += 1

        result, captured = _run_capture(
            Config(base_url=base_url, token=_StubServer.token, requests=4, concurrency=2)
        )
        assert result.passed, captured
        assert result.ok == 4 and result.attempted == 4
        assert _StubServer.token not in captured
        checks += 1

        result, captured = _run_capture(
            Config(
                base_url=base_url,
                token=_StubServer.token,
                requests=4,
                concurrency=2,
                tool="list_servers",
            )
        )
        assert result.passed, captured
        assert result.ok == 4
        checks += 1

        result, captured = _run_capture(
            Config(
                base_url=base_url,
                token=_StubServer.token,
                requests=4,
                concurrency=2,
                tool="boom",
            )
        )
        assert not result.passed and result.jsonrpc_errors == 4, captured
        assert "stub tool failed" in captured
        checks += 1

        server.rate_limit_tool_calls = 1
        result, captured = _run_capture(
            Config(
                base_url=base_url,
                token=_StubServer.token,
                requests=4,
                concurrency=2,
                tool="list_servers",
            )
        )
        server.rate_limit_tool_calls = 0
        assert not result.passed and result.rate_limited == 1, captured
        assert "429" in captured and "rate limited" in captured
        checks += 1

        result, captured = _run_capture(
            Config(
                base_url=base_url,
                token="itk_wrong_token",
                requests=4,
                concurrency=2,
            )
        )
        assert not result.passed and result.warmup_failures == 2, captured
        assert "401" in captured
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


def _arguments(value: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise argparse.ArgumentTypeError(f"invalid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("expected a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Load test the MCP Streamable HTTP endpoint (read-only by default). "
            "The token is read from MCP_TOKEN unless --token is given."
        ),
        epilog=(
            "Examples:\n"
            "  MCP_TOKEN=itk_... python3 scripts/loadtest-mcp.py\n"
            "  MCP_TOKEN=itk_... python3 scripts/loadtest-mcp.py --requests 60 --concurrency 6\n"
            "  MCP_TOKEN=itk_... python3 scripts/loadtest-mcp.py --tool list_servers --arguments '{\"limit\":10}'\n"
            "  MCP_TOKEN=itk_... MCP_INSECURE_TLS=1 make loadtest-mcp\n"
            "  python3 scripts/loadtest-mcp.py --self-test\n\n"
            "The /mcp rate limit is 120 requests/minute per token: a run above that "
            "includes expected 429 responses and exits non-zero."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("MCP_BASE_URL", DEFAULT_BASE_URL),
        help=f"base URL without or with /mcp (env MCP_BASE_URL, default {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("MCP_TOKEN"),
        help="personal token with mcp:read (env MCP_TOKEN; prefer the env over the flag)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=int(os.environ.get("MCP_REQUESTS", "30")),
        help="measured requests, default 30 (env MCP_REQUESTS)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.environ.get("MCP_CONCURRENCY", "5")),
        help="worker threads, default 5 (env MCP_CONCURRENCY)",
    )
    parser.add_argument(
        "--tool",
        default=os.environ.get("MCP_TOOL") or None,
        help="optional read tool to call; default measures tools/list (env MCP_TOOL)",
    )
    parser.add_argument(
        "--arguments",
        type=_arguments,
        default=os.environ.get("MCP_ARGUMENTS", "{}"),
        help="JSON object for tools/call, default {} (env MCP_ARGUMENTS)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("MCP_TIMEOUT", "30")),
        help="per-request timeout in seconds, default 30 (env MCP_TIMEOUT)",
    )
    parser.add_argument(
        "--insecure-tls",
        action="store_true",
        default=_opener_tls_from_env(),
        help="skip TLS verification for self-signed local stacks (env MCP_INSECURE_TLS=1)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the local stub server and internal checks, no live instance needed",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not 1 <= args.requests <= 1_000_000:
        parser.error("--requests must be between 1 and 1000000")
    if not 1 <= args.concurrency <= 256:
        parser.error("--concurrency must be between 1 and 256")
    if args.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if args.tool in ACTION_TOOLS:
        parser.error(
            "--tool is for read tools only; "
            f"{args.tool} is an action tool and is not load-tested"
        )
    if not args.token:
        parser.error("missing token: set MCP_TOKEN or pass --token")
    parsed_url = urlparse(args.base_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        parser.error("--base-url must be an absolute http(s) URL")

    config = Config(
        base_url=args.base_url,
        token=args.token,
        requests=args.requests,
        concurrency=args.concurrency,
        tool=args.tool,
        arguments=args.arguments,
        timeout=args.timeout,
        insecure_tls=args.insecure_tls,
    )
    return 0 if run_load(config).passed else 1


if __name__ == "__main__":
    sys.exit(main())
