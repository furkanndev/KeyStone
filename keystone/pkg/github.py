"""Windows downloads from a project's latest GitHub release."""
from __future__ import annotations

import json
import re
import urllib.request

API = "https://api.github.com/repos/{repo}/releases/latest"
SKIP = re.compile(r"sha\d*|checksum|\.sig$|\.asc$|\.blockmap$|symbols|debug|source|\bsrc\b"
                  r"|linux|ubuntu|mac|darwin|osx|freebsd|netbsd|openbsd|plan9|solaris|aix|\.appimage$|\.deb$|\.rpm$", re.I)
ARM = re.compile(r"arm64|aarch64", re.I)
X86 = re.compile(r"\b(x86|386|i[36]86|win32|32-?bit)\b", re.I)
SUFFIX_RANK = {".msi": 2, ".exe": 2, ".zip": 1}


def pick_asset(assets: list[dict], arch: str = "x86_64", pattern: str = "") -> dict | None:
    """The best Windows asset for ``arch``; ``pattern`` overrides the name heuristics."""
    if pattern:
        return next((a for a in assets if re.search(pattern, a["name"], re.I)), None)
    want_arm = bool(ARM.search(arch))

    def score(a: dict) -> int:
        name = a["name"]
        rank = next((r for s, r in SUFFIX_RANK.items() if name.lower().endswith(s)), 0)
        if name.lower().endswith(".zip") and "win" not in name.lower():
            return 0
        if not rank or SKIP.search(name) or X86.search(name) or bool(ARM.search(name)) != want_arm:
            return 0
        return rank * 2 + bool(re.search(r"setup|install", name, re.I))

    best = max(assets, key=score, default=None)
    return best if best and score(best) else None


def latest_asset(repo: str, arch: str = "x86_64", pattern: str = "") -> dict | None:
    req = urllib.request.Request(API.format(repo=repo), headers={
        "User-Agent": "KeyStone", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return pick_asset(json.load(r).get("assets", []), arch, pattern)
