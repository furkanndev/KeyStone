"""Browser mode: serves the same UI over http://127.0.0.1 with JSON calls and
Server-Sent Events. Used when no native webview is available (headless Linux,
remote sessions) and for development.

Security: binds to loopback only, rejects foreign Host headers (DNS
rebinding) and requires a random per-run token on every API call.
"""
from __future__ import annotations

import json
import mimetypes
import queue
import secrets
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .api import PUBLIC, Api
from .core.paths import resource

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")


def make_server(api: Api, port: int = 0, token: str | None = None) -> tuple[ThreadingHTTPServer, str]:
    token = token or secrets.token_urlsafe(24)
    ui_root = resource("ui").resolve()
    clients: set[queue.Queue] = set()
    lock = threading.Lock()

    def fanout(ev: dict) -> None:
        with lock:
            for q in list(clients):
                q.put(ev)

    api.subscribe(fanout)

    class Handler(BaseHTTPRequestHandler):
        server_version = "KeyStone"
        protocol_version = "HTTP/1.1"

        def log_message(self, *a) -> None:  # quiet
            pass

        # -- guards ---------------------------------------------------------
        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("127.0.0.1", "localhost", "[::1]")

        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"),
                       "application/json; charset=utf-8")

        # -- routes ---------------------------------------------------------
        def do_GET(self) -> None:
            if not self._host_ok():
                return self._send(403, b"forbidden", "text/plain")
            url = urlparse(self.path)
            if url.path == "/events":
                if parse_qs(url.query).get("token", [""])[0] != token:
                    return self._send(401, b"unauthorized", "text/plain")
                return self._events()
            rel = url.path.lstrip("/") or "index.html"
            target = (ui_root / rel).resolve()
            if ui_root not in target.parents or not target.is_file():
                return self._send(404, b"not found", "text/plain")
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self._send(200, target.read_bytes(), ctype,
                       {"Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                                                   "font-src 'self'; connect-src 'self'; frame-ancestors 'none'"})

        def do_POST(self) -> None:
            if not self._host_ok():
                return self._send(403, b"forbidden", "text/plain")
            if self.headers.get("X-KeyStone-Token") != token:
                return self._json(401, {"error": "unauthorized"})
            url = urlparse(self.path)
            name = url.path.removeprefix("/api/")
            if name not in PUBLIC:
                return self._json(404, {"error": f"unknown method {name}"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(n) or b"{}") if n else {}
                result = getattr(api, name)(*payload.get("args", []))
                self._json(200, {"result": result})
            except Exception as exc:
                self._json(500, {"error": str(exc)})

        def _events(self) -> None:
            q: queue.Queue = queue.Queue()
            with lock:
                clients.add(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                self.wfile.write(b": hi\n\n")
                self.wfile.flush()
                while True:
                    try:
                        ev = q.get(timeout=15)
                        data = json.dumps(ev, ensure_ascii=False, default=str)
                        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with lock:
                    clients.discard(q)

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    return httpd, token


def serve(api: Api, port: int = 0, open_browser: bool = True) -> None:
    import webbrowser
    httpd, token = make_server(api, port)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/#token={token}"
    print(f"KeyStone is running at {url}\nPress Ctrl+C to stop.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
