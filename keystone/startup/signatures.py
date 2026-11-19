"""Digital-signature checks for the files start-up entries run.

One batched PowerShell pass per chunk of paths (handed over through the
environment, never spliced into the script), cached by path, mtime and size.
An entry counts as Microsoft's only when the signature is *valid* and the
certificate's organisation is Microsoft Corporation, never by ``CompanyName``.
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Callable

from ..core import proc
from ..tweaks.engine import ps

CHUNK = 40

INSPECT_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$out = @{}
$paths = @(ConvertFrom-Json $env:KS_PATHS | ForEach-Object { $_ })
foreach ($p in $paths) {
  $t = [string]$p
  $r = @{ target = $t; status = 'Missing'; publisher = ''; subject = '' }
  if ($t -and (Test-Path -LiteralPath $t -PathType Leaf)) {
    $s = Get-AuthenticodeSignature -LiteralPath $t
    $r.status = [string]$s.Status
    if ($s.SignerCertificate) {
      $r.publisher = [string]$s.SignerCertificate.GetNameInfo('SimpleName', $false)
      $r.subject = [string]$s.SignerCertificate.Subject
    }
  }
  $out[[string]$p] = $r
}
ConvertTo-Json -InputObject $out -Compress -Depth 4
"""

LNK_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$shell = New-Object -ComObject WScript.Shell
$out = @{}
$paths = @(ConvertFrom-Json $env:KS_PATHS | ForEach-Object { $_ })
foreach ($p in $paths) { $out[[string]$p] = [string]$shell.CreateShortcut([string]$p).TargetPath }
ConvertTo-Json -InputObject $out -Compress
"""

_MS_ORG = re.compile(r'(?:^|,\s*)O="?Microsoft Corporation"?(?:,|$)', re.I)


def classify(raw: dict) -> dict:
    """Turn the raw PowerShell record into the small shape the interface uses."""
    status = str(raw.get("status") or "")
    if status == "Valid":
        sig = "valid"
    elif status in ("NotSigned", "NotSupportedFileFormat"):
        sig = "unsigned"
    elif status == "Missing":
        sig = "missing"
    else:
        sig = "invalid"
    microsoft = sig == "valid" and bool(_MS_ORG.search(str(raw.get("subject") or "")))
    return {"signature": sig, "publisher": str(raw.get("publisher") or ""), "microsoft": microsoft,
            "target": str(raw.get("target") or "")}


def _stamp(path: str) -> str:
    try:
        st = os.stat(path)
    except OSError:
        return ""
    return f"{path.lower()}|{st.st_mtime_ns}|{st.st_size}"


class Inspector:
    def __init__(self, run: Callable[..., proc.Result] | None = None, cache_file: Path | None = None) -> None:
        self._run = run
        self._file = cache_file
        self._lock = threading.Lock()
        self._cache: dict[str, dict] = {}
        if cache_file:
            try:
                data = json.loads(Path(cache_file).read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._cache = {k: v for k, v in data.items() if isinstance(v, dict)}
            except (OSError, ValueError):
                pass

    def run(self, *a, **kw) -> proc.Result:
        return (self._run or proc.run)(*a, **kw)

    def _save(self) -> None:
        if not self._file:
            return
        try:
            Path(self._file).parent.mkdir(parents=True, exist_ok=True)
            tmp = Path(self._file).with_suffix(".tmp")
            tmp.write_text(json.dumps(self._cache), encoding="utf-8")
            os.replace(tmp, self._file)
        except OSError:
            pass

    def _resolve_lnks(self, lnks: list[str]) -> dict[str, str]:
        """Shortcut -> the file it points to, cached by the shortcut's own mtime and size."""
        out: dict[str, str] = {}
        todo: list[str] = []
        for p in lnks:
            hit = self._cache.get("lnk|" + _stamp(p)) if _stamp(p) else None
            if hit:
                out[p] = str(hit.get("target") or "")
            else:
                todo.append(p)
        if todo:
            r = self.run(ps(LNK_SCRIPT), timeout=60, env={"KS_PATHS": json.dumps(todo)})
            try:
                raw = json.loads(r.out.strip().lstrip("\ufeff") or "{}") if r.ok else {}
            except ValueError:
                raw = {}
            for p in todo:
                if isinstance(raw, dict) and isinstance(raw.get(p), str):
                    out[p] = raw[p]
                    if _stamp(p):
                        self._cache["lnk|" + _stamp(p)] = {"target": raw[p]}
            self._save()
        return out

    def inspect(self, paths: list[str]) -> dict[str, dict]:
        """``{path: {signature, publisher, microsoft, target}}`` for every path that could be inspected.

        Shortcuts are resolved to the file they run first; that file is what gets judged.
        A path missing from the result means "unknown"; callers must keep such entries visible.
        """
        wanted = list(dict.fromkeys(x for x in paths if x))
        lnk_targets = self._resolve_lnks([p for p in wanted if p.lower().endswith(".lnk")])
        real = {p: (lnk_targets.get(p, "") if p.lower().endswith(".lnk") else p) for p in wanted}
        judged = self._judge([t for t in dict.fromkeys(real.values()) if t])
        return {p: {**judged[t], "target": t} for p, t in real.items() if t in judged}

    def _judge(self, paths: list[str]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        todo: list[str] = []
        for p in paths:
            stamp = _stamp(p)
            hit = self._cache.get(stamp) if stamp else None
            if hit:
                out[p] = hit
            else:
                todo.append(p)
        changed = False
        for i in range(0, len(todo), CHUNK):
            chunk = todo[i:i + CHUNK]
            r = self.run(ps(INSPECT_SCRIPT), timeout=180, env={"KS_PATHS": json.dumps(chunk)})
            try:
                raw = json.loads(r.out.strip().lstrip("\ufeff") or "{}") if r.ok else {}
            except ValueError:
                raw = {}
            if not isinstance(raw, dict):
                continue
            for p in chunk:
                rec = raw.get(p)
                if not isinstance(rec, dict):
                    continue
                info = classify(rec)
                out[p] = info
                stamp = _stamp(p)
                if stamp and info["signature"] != "missing" and not p.lower().endswith(".lnk"):
                    with self._lock:
                        self._cache[stamp] = info
                    changed = True
        if changed:
            self._save()
        return out
