"""VirusTotal hash lookups for start-up entries.

Privacy: only the SHA-256 of a file is ever sent, and only when the user has
switched lookups on and supplied their own API key. Files are never uploaded.
The "open in VirusTotal" link needs neither: the hash is computed locally and
the browser opens it when the user clicks.

API (v3): ``GET https://www.virustotal.com/api/v3/files/{sha256}`` with an
``x-apikey`` header. Errors use ``{"error": {"code": ...}}``: 401 means a wrong
key, 404 an unknown file, 429 a quota or rate limit. The public API allows 4
requests per minute and 500 per day, so calls are spaced out here.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable

API = "https://www.virustotal.com/api/v3/files/"
GUI = "https://www.virustotal.com/gui/file/"
MIN_GAP = 16.0           # seconds between network calls (4 per minute on the public API)
TIMEOUT = 15


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class VirusTotal:
    def __init__(self, opener: Callable[..., Any] | None = None, clock: Callable[[], float] | None = None) -> None:
        self._open = opener or urllib.request.urlopen
        self._now = clock or time.monotonic
        self._lock = threading.Lock()
        self._last_call = -1e9
        self._hashes: dict[str, str] = {}          # path|mtime|size -> sha256
        self._results: dict[str, dict] = {}        # sha256 -> result

    def hash_file(self, path: str) -> str:
        st = os.stat(path)
        stamp = f"{path.lower()}|{st.st_mtime_ns}|{st.st_size}"
        if stamp not in self._hashes:
            self._hashes[stamp] = sha256_of(path)
        return self._hashes[stamp]

    @staticmethod
    def link(sha256: str) -> str:
        return GUI + sha256

    def lookup(self, sha256: str, api_key: str) -> dict:
        """Look a hash up. Never raises; returns ``{"ok": bool, ...}``."""
        link = self.link(sha256)
        if sha256 in self._results:
            return self._results[sha256]
        with self._lock:
            wait = MIN_GAP - (self._now() - self._last_call)
            if wait > 0:
                return {"ok": False, "error": "rate_limit", "retry_after": int(wait) + 1, "sha256": sha256, "link": link}
            self._last_call = self._now()
        req = urllib.request.Request(API + sha256, headers={"x-apikey": api_key, "Accept": "application/json",
                                                            "User-Agent": "KeyStone"})
        try:
            with self._open(req, timeout=TIMEOUT) as resp:
                body = json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            code = exc.code
            if code == 404:
                return {"ok": False, "error": "not_found", "sha256": sha256, "link": link}
            if code in (401, 403):
                return {"ok": False, "error": "bad_key", "sha256": sha256, "link": link}
            if code == 429:
                return {"ok": False, "error": "rate_limit", "retry_after": 60, "sha256": sha256, "link": link}
            return {"ok": False, "error": "http_%d" % code, "sha256": sha256, "link": link}
        except (urllib.error.URLError, OSError, ValueError):
            return {"ok": False, "error": "network", "sha256": sha256, "link": link}
        attrs = ((body.get("data") or {}).get("attributes") or {}) if isinstance(body, dict) else {}
        stats = attrs.get("last_analysis_stats") or {}

        def n(k: str) -> int:
            v = stats.get(k)
            return v if isinstance(v, int) else 0

        res = {"ok": True, "sha256": sha256, "link": link, "malicious": n("malicious"), "suspicious": n("suspicious"),
               "harmless": n("harmless"), "undetected": n("undetected")}
        res["total"] = res["malicious"] + res["suspicious"] + res["harmless"] + res["undetected"]
        if res["total"] == 0:
            # No verdicts (missing stats, or nothing analysed yet): never show that as a clean result.
            return {"ok": False, "error": "no_data", "sha256": sha256, "link": link}
        self._results[sha256] = res
        return res
