#!/usr/bin/env python3
"""Load test mirato: liste, topologia e una mutazione create/delete.

Uso (dopo `make full` con un utente SystemAdmin):
  BASE_URL=https://localhost:8443 LOADTEST_USER=admin LOADTEST_PASSWORD=dev-admin \
  REQUESTS=30 CONCURRENCY=5 INSECURE_TLS=1 scripts/loadtest.py
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import re
import ssl
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from html import unescape
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener


BASE = os.environ.get("BASE_URL", "https://localhost:8443").rstrip("/")
USER = os.environ.get("LOADTEST_USER", "admin")
PASSWORD = os.environ.get("LOADTEST_PASSWORD", "dev-admin")
REQUESTS = int(os.environ.get("REQUESTS", "30"))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "5"))
MAX_AVG_MS = float(os.environ.get("MAX_AVG_MS", "1000"))


@dataclass
class Stats:
    ok: int = 0
    errors: list[str] = field(default_factory=list)
    durations: list[float] = field(default_factory=list)

    def add(self, duration: float) -> None:
        self.ok += 1
        self.durations.append(duration)

    def fail(self, message: str) -> None:
        self.errors.append(message)

    def report(self, label: str) -> bool:
        if not self.durations:
            print(f"{label}: nessuna risposta")
            return False
        ordered = sorted(self.durations)
        avg = statistics.fmean(ordered)
        p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
        print(
            f"{label}: ok={self.ok} errori={len(self.errors)} "
            f"avg={avg:.0f}ms p95={p95:.0f}ms max={ordered[-1]:.0f}ms"
        )
        for error in self.errors[:5]:
            print(f"  errore: {error}")
        return not self.errors and avg <= MAX_AVG_MS


def opener():
    jar = http.cookiejar.CookieJar()
    context = ssl._create_unverified_context() if os.environ.get("INSECURE_TLS") == "1" else None
    handlers = [HTTPCookieProcessor(jar)]
    if context is not None:
        handlers.append(HTTPSHandler(context=context))
    return build_opener(*handlers), jar


def open_retry(client, request, attempts: int = 20, delay: float = 3.0):
    for attempt in range(attempts):
        try:
            return client.open(request)
        except Exception as error:  # noqa: BLE001 - Keycloak può rispondere 503 durante il bootstrap
            code = getattr(error, "code", 0)
            if code not in (502, 503) or attempt == attempts - 1:
                raise
            time.sleep(delay)
    raise RuntimeError("unreachable")


def login(client) -> tuple[str, str]:
    with open_retry(client, Request(BASE + "/auth/login")) as response:
        page = response.read().decode("utf-8", "replace")

    action = re.search(r'action="([^"]+)"', page)
    if action is None:
        raise RuntimeError("form di login Keycloak non trovato")
    action = unescape(action.group(1))

    data = urlencode(
        {"username": USER, "password": PASSWORD, "credentialId": ""}
    ).encode()
    with open_retry(client, Request(action, data=data)) as response:
        response.read()

    with client.open(BASE + "/api/session") as response:
        session = json.loads(response.read())
    return session["csrfToken"], session["user"]["username"]


def request_json(client, path: str, csrf: str | None = None, body: dict | None = None) -> tuple[int, dict | None]:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
        method = "POST"
    if csrf is not None:
        headers["X-CSRF-Token"] = csrf
        headers["Origin"] = BASE
    request = Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with client.open(request) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except Exception as error:  # noqa: BLE001 - report HTTP errors, keep the run going
        return 0, {"error": str(error)}


def timed(func, *args):
    start = time.perf_counter()
    result = func(*args)
    return result, (time.perf_counter() - start) * 1000


def main() -> int:
    if os.environ.get("INSECURE_TLS") != "1":
        print("Avviso: INSECURE_TLS non impostato; certificati self-signed falliranno.", file=sys.stderr)

    client, _ = opener()
    csrf, username = login(client)
    print(f"Login {username} su {BASE}; {REQUESTS} richieste, concorrenza {CONCURRENCY}")

    def get(path: str) -> tuple[int, dict | None]:
        return request_json(client, path)

    for path in ("/api/menus", "/api/providers", "/api/topology"):
        stats = Stats()

        def one(path=path, stats=stats):
            result, duration = timed(get, path)
            status, _ = result
            stats.add(duration) if 200 <= status < 300 else stats.fail(f"{path} -> {status}")

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            list(pool.map(lambda _: one(), range(REQUESTS)))
        if not stats.report(path):
            return 1

    saves = Stats()
    deletes = Stats()
    for index in range(max(5, REQUESTS // 5)):
        name = f"Load {uuid.uuid4().hex[:8]}-{index}"
        (status, created), duration = timed(
            request_json, client, "/api/providers", csrf, {"name": name})
        saves.add(duration) if 200 <= status < 300 else saves.fail(f"POST -> {status}")
        if not 200 <= status < 300 or not created:
            continue
        provider_id = created.get("id")
        delete_start = time.perf_counter()
        try:
            request = Request(
                BASE + f"/api/providers/{provider_id}",
                method="DELETE",
                headers={"X-CSRF-Token": csrf, "Origin": BASE},
            )
            with client.open(request) as response:
                del_status = response.status
        except Exception as error:  # noqa: BLE001
            del_status = 0
            deletes.fail(str(error))
        del_duration = (time.perf_counter() - delete_start) * 1000
        deletes.add(del_duration) if 200 <= del_status < 300 else deletes.fail(f"DELETE -> {del_status}")

    ok = saves.report("POST /api/providers") & deletes.report("DELETE /api/providers")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
