"""Windows start-up entries: list, enable, disable and delete.

A small Autoruns-style view. It covers the places most programs use to start
with Windows:

* ``Run`` / ``RunOnce`` in HKCU, HKLM and HKLM\\WOW6432Node,
* the per-user and the all-users Startup folders,
* scheduled tasks that fire at logon or boot (Microsoft's own tasks hidden).

Not covered: services, drivers, shell extensions, Winlogon, packaged (Store)
app start-up tasks and the other Autoruns categories.

Enabling and disabling uses the same switch as Task Manager's *Startup apps*
tab (``Explorer\\StartupApproved``): the entry itself is left untouched, so a
disabled program can be turned back on without losing anything. ``RunOnce``
keys have no such switch, so those entries can only be listed and deleted.

Security: the interface only ever sends an opaque entry id. It is resolved
against a fresh scan on this machine, so no path or registry name coming from
the client is ever used.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .core import proc
from .core.system import WINDOWS, SystemInfo
from .tweaks.engine import ps

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUNONCE = r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
RUN32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
RUNONCE32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce"
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"

# (hive, key, label, StartupApproved sub-key or "" when the entry cannot be switched)
REG_SOURCES: list[tuple[str, str, str, str]] = [
    ("HKCU", RUN, "HKCU\\Run", "Run"),
    ("HKCU", RUNONCE, "HKCU\\RunOnce", ""),
    ("HKLM", RUN, "HKLM\\Run", "Run"),
    ("HKLM", RUNONCE, "HKLM\\RunOnce", ""),
    ("HKLM", RUN32, "HKLM\\Run (32-bit)", "Run32"),
    ("HKLM", RUNONCE32, "HKLM\\RunOnce (32-bit)", ""),
]

ENABLED_FLAG = b"\x02\x00\x00\x00" + b"\x00" * 8
_FILETIME_EPOCH = 11644473600          # seconds between 1601-01-01 and 1970-01-01


def disabled_flag(now: float | None = None) -> bytes:
    """Value Task Manager writes when an entry is turned off: 03 00 00 00 + FILETIME."""
    ticks = int(((now if now is not None else time.time()) + _FILETIME_EPOCH) * 10_000_000)
    return b"\x03\x00\x00\x00" + struct.pack("<Q", ticks)


def is_disabled(data: bytes | None) -> bool:
    """A missing value means enabled; an odd first byte means disabled."""
    return bool(data) and (data[0] & 1) == 1


class NeedsAdmin(Exception):
    pass


# ----------------------------------------------------------------------------- registry

class StartupRegistry(Protocol):
    def values(self, hive: str, key: str) -> list[tuple[str, str]]: ...
    def get_binary(self, hive: str, key: str, name: str) -> bytes | None: ...
    def set_binary(self, hive: str, key: str, name: str, data: bytes) -> None: ...
    def delete_value(self, hive: str, key: str, name: str) -> None: ...


class WinStartupRegistry:
    """Real registry. Always the 64-bit view; 32-bit entries use the explicit WOW6432Node path."""

    def _w(self):
        import winreg  # type: ignore
        return winreg

    def _root(self, hive: str):
        w = self._w()
        return {"HKCU": w.HKEY_CURRENT_USER, "HKLM": w.HKEY_LOCAL_MACHINE}[hive]

    def _open(self, hive: str, key: str, access: int):
        w = self._w()
        return w.OpenKey(self._root(hive), key, 0, access | w.KEY_WOW64_64KEY)

    def values(self, hive, key):
        w = self._w()
        out: list[tuple[str, str]] = []
        try:
            with self._open(hive, key, w.KEY_READ) as k:
                i = 0
                while True:
                    try:
                        name, data, kind = w.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    if kind in (w.REG_SZ, w.REG_EXPAND_SZ):
                        out.append((name, str(data)))
        except OSError:
            pass
        return out

    def get_binary(self, hive, key, name):
        w = self._w()
        try:
            with self._open(hive, key, w.KEY_READ) as k:
                data, kind = w.QueryValueEx(k, name)
                return bytes(data) if kind == w.REG_BINARY else None
        except OSError:
            return None

    def set_binary(self, hive, key, name, data):
        w = self._w()
        try:
            with w.CreateKeyEx(self._root(hive), key, 0, w.KEY_SET_VALUE | w.KEY_WOW64_64KEY) as k:
                w.SetValueEx(k, name, 0, w.REG_BINARY, data)
        except PermissionError as exc:
            raise NeedsAdmin(str(exc)) from exc

    def delete_value(self, hive, key, name):
        w = self._w()
        try:
            with self._open(hive, key, w.KEY_SET_VALUE) as k:
                w.DeleteValue(k, name)
        except FileNotFoundError:
            pass
        except PermissionError as exc:
            raise NeedsAdmin(str(exc)) from exc


# ----------------------------------------------------------------------------- entries

@dataclass
class Entry:
    id: str
    kind: str                # registry | folder | task
    name: str
    command: str
    location: str            # human readable source
    scope: str               # user | machine
    enabled: bool
    can_toggle: bool
    exists: bool | None      # does the program on the command line exist (None: unknown)
    needs_admin: bool = False     # changing this item needs administrator rights
    runs_elevated: bool = False   # the program itself starts with administrator rights
    # private resolution data, never sent to the interface
    hive: str = ""
    key: str = ""
    approved: str = ""       # StartupApproved sub-key
    path: str = ""           # folder entries: file path / task entries: task path

    def public(self) -> dict:
        return {"id": self.id, "kind": self.kind, "name": self.name, "command": self.command,
                "location": self.location, "scope": self.scope, "enabled": self.enabled,
                "can_toggle": self.can_toggle, "exists": self.exists,
                "needs_admin": self.needs_admin, "runs_elevated": self.runs_elevated}


def _make_id(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).lower().encode("utf-8")).hexdigest()[:16]


_EXE_RE = re.compile(r'^\s*(?:"([^"]+)"|(\S+(?:\s+\S+)*?\.(?:exe|bat|cmd|com|lnk|vbs|ps1|msc|cpl))(?=\s|$)|(\S+))', re.I)


def program_of(command: str) -> str:
    """Best guess at the file a start-up command line launches."""
    m = _EXE_RE.match(os.path.expandvars((command or "").replace('""', '"')))
    return (m.group(1) or m.group(2) or m.group(3) or "") if m else ""


def _exists(command: str) -> bool | None:
    prog = program_of(command)
    if not prog or not (os.path.isabs(prog) or "\\" in prog or "/" in prog):
        return None            # bare names (cmd, powershell, ...) are resolved via PATH
    return os.path.exists(prog)


TASK_LIST = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rows = @(Get-ScheduledTask | Where-Object {
    $_.TaskPath -notlike '\Microsoft\*' -and
    ($_.Triggers | Where-Object { $_.CimClass.CimClassName -in 'MSFT_TaskLogonTrigger', 'MSFT_TaskBootTrigger' })
  } | ForEach-Object {
    [pscustomobject]@{
      name = $_.TaskName; path = $_.TaskPath; enabled = ($_.State -ne 'Disabled')
      user = [string]$_.Principal.UserId; highest = ($_.Principal.RunLevel -eq 'Highest')
      command = (($_.Actions | ForEach-Object { (([string]$_.Execute) + ' ' + ([string]$_.Arguments)).Trim() }) -join ' && ')
    }
  })
ConvertTo-Json -InputObject $rows -Compress -Depth 3
"""

# The task is identified through the environment, never spliced into the script text.
TASK_ACTION = r"""
$ErrorActionPreference = 'Stop'
$n = $env:KS_TASK_NAME; $p = $env:KS_TASK_PATH
switch ($env:KS_TASK_ACTION) {
  'enable'  { Enable-ScheduledTask -TaskName $n -TaskPath $p | Out-Null }
  'disable' { Disable-ScheduledTask -TaskName $n -TaskPath $p | Out-Null }
  'delete'  { Unregister-ScheduledTask -TaskName $n -TaskPath $p -Confirm:$false }
}
"""


# Icons are read for a list of paths handed over through the environment, never spliced into the script.
ICON_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Drawing
$res = @{}
$paths = @(ConvertFrom-Json $env:KS_ICON_PATHS | ForEach-Object { $_ })
foreach ($p in $paths) {
  try {
    $ic = [System.Drawing.Icon]::ExtractAssociatedIcon($p)
    $ms = New-Object System.IO.MemoryStream
    $ic.ToBitmap().Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    $res[[string]$p] = [Convert]::ToBase64String($ms.ToArray())
  } catch {}
}
ConvertTo-Json -InputObject $res -Compress
"""

# Compatibility layers that make Windows start a program elevated ("Run this program as an administrator").
LAYERS = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"


def _same_user(principal: str) -> bool:
    """Is a task principal the signed-in user (rather than SYSTEM, a group or another account)?"""
    me = (os.environ.get("USERNAME") or "").lower()
    return bool(me) and principal.replace("/", "\\").split("\\")[-1].lower() == me


class StartupManager:
    def __init__(self, info: SystemInfo, reg: StartupRegistry | None = None,
                 run: Callable[..., proc.Result] | None = None, folders: list[tuple[str, str, str]] | None = None) -> None:
        self.info = info
        self.reg = reg or WinStartupRegistry()
        self._run = run
        self._folders = folders
        self._seen: dict[str, Entry] = {}        # entries of the latest scan: the only ids icons are served for
        self._icons: dict[str, str] = {}         # program path -> PNG data URI ("" = no icon)

    # -- helpers --------------------------------------------------------------
    @property
    def supported(self) -> bool:
        return self.info.os == WINDOWS

    def run(self, *a, **kw) -> proc.Result:
        return (self._run or proc.run)(*a, **kw)

    def folders(self) -> list[tuple[str, str, str]]:
        """(directory, scope, StartupApproved hive) for each Startup folder."""
        if self._folders is not None:
            return self._folders
        rel = Path("Microsoft/Windows/Start Menu/Programs/Startup")
        out = []
        if os.environ.get("APPDATA"):
            out.append((str(Path(os.environ["APPDATA"]) / rel), "user", "HKCU"))
        if os.environ.get("PROGRAMDATA"):
            out.append((str(Path(os.environ["PROGRAMDATA"]) / rel), "machine", "HKLM"))
        return out

    def _approved_off(self, hive: str, sub: str, name: str) -> bool:
        if not sub:
            return False
        return is_disabled(self.reg.get_binary(hive, f"{APPROVED}\\{sub}", name))

    # -- scan -----------------------------------------------------------------
    def scan(self, include_tasks: bool = True) -> list[Entry]:
        if not self.supported:
            return []
        entries = self._scan_registry() + self._scan_folders()
        if include_tasks:
            entries += self._scan_tasks()
        elevated = self._elevated_programs()
        for e in entries:
            if e.kind != "task" and program_of(e.command).lower() in elevated:
                e.runs_elevated = True
        self._seen = {e.id: e for e in entries}
        return entries

    def _elevated_programs(self) -> set[str]:
        """Programs flagged "Run as administrator" in the compatibility layers."""
        out: set[str] = set()
        for hive in ("HKCU", "HKLM"):
            for name, data in self.reg.values(hive, LAYERS):
                if "RUNASADMIN" in data.upper():
                    out.add(os.path.expandvars(name).lower())
        return out

    def _scan_registry(self) -> list[Entry]:
        out: list[Entry] = []
        for hive, key, label, sub in REG_SOURCES:
            for name, data in self.reg.values(hive, key):
                out.append(Entry(
                    id=_make_id("reg", hive, key, name), kind="registry", name=name, command=data,
                    location=label, scope="user" if hive == "HKCU" else "machine",
                    enabled=not self._approved_off(hive, sub, name), can_toggle=bool(sub),
                    exists=_exists(data), needs_admin=hive == "HKLM", hive=hive, key=key, approved=sub))
        return out

    def _scan_folders(self) -> list[Entry]:
        out: list[Entry] = []
        for directory, scope, hive in self.folders():
            try:
                items = sorted(os.scandir(directory), key=lambda e: e.name.lower())
            except OSError:
                continue
            for it in items:
                if not it.is_file() or it.name.lower() == "desktop.ini":
                    continue
                out.append(Entry(
                    id=_make_id("folder", directory, it.name), kind="folder", name=it.name, command=it.path,
                    location=directory, scope=scope,
                    enabled=not self._approved_off(hive, "StartupFolder", it.name), can_toggle=True,
                    exists=True, needs_admin=scope == "machine", hive=hive, approved="StartupFolder", path=it.path))
        return out

    def _scan_tasks(self) -> list[Entry]:
        r = self.run(ps(TASK_LIST), timeout=60)
        if not r.ok or not r.out.strip():
            return []
        try:
            rows: Any = json.loads(r.out.strip().lstrip("\ufeff"))
        except ValueError:
            return []
        if isinstance(rows, dict):
            rows = [rows]
        out: list[Entry] = []
        for row in rows or []:
            if not isinstance(row, dict) or not row.get("name"):
                continue
            tpath = row.get("path") or "\\"
            out.append(Entry(
                id=_make_id("task", tpath, row["name"]), kind="task", name=str(row["name"]),
                command=str(row.get("command") or ""), location=f"Task Scheduler {tpath}", scope="machine",
                enabled=bool(row.get("enabled")), can_toggle=True, exists=_exists(str(row.get("command") or "")),
                needs_admin=bool(row.get("highest")) or not _same_user(str(row.get("user") or "")),
                runs_elevated=bool(row.get("highest")), path=tpath))
        out.sort(key=lambda e: e.name.lower())
        return out

    # -- icons ----------------------------------------------------------------
    def _icon_source(self, e: Entry) -> str:
        if e.kind == "folder":
            return e.path
        prog = program_of(e.command)
        if not prog:
            return ""
        if os.path.isfile(prog):
            return prog
        found = shutil.which(prog)
        return found or ""

    def icons(self, ids: list[str]) -> dict[str, str]:
        """PNG data URIs for entries of the latest scan. Unknown ids are ignored."""
        if not self.supported:
            return {}
        wanted = {i: self._icon_source(self._seen[i]) for i in ids if i in self._seen}
        missing = sorted({p for p in wanted.values() if p and p not in self._icons})
        if missing:
            r = self.run(ps(ICON_SCRIPT), timeout=60, env={"KS_ICON_PATHS": json.dumps(missing)})
            try:
                got = json.loads(r.out.strip().lstrip("\ufeff") or "{}") if r.ok else {}
            except ValueError:
                got = {}
            for p in missing:
                b64 = got.get(p) if isinstance(got, dict) else None
                self._icons[p] = f"data:image/png;base64,{b64}" if b64 else ""
        return {i: self._icons[p] for i, p in wanted.items() if p and self._icons.get(p)}

    # -- actions --------------------------------------------------------------
    def _find(self, eid: str) -> Entry | None:
        return next((e for e in self.scan() if e.id == eid), None)

    def _task_action(self, e: Entry, action: str) -> None:
        r = self.run(ps(TASK_ACTION), timeout=60, env={
            "KS_TASK_NAME": e.name, "KS_TASK_PATH": e.path, "KS_TASK_ACTION": action})
        if not r.ok:
            if re.search(r"denied|0x80070005|privilege|elevat", r.out, re.I):
                raise NeedsAdmin(r.out.strip()[:300])
            raise RuntimeError(r.out.strip()[:300] or f"exit {r.code}")

    def set_enabled(self, eid: str, on: bool) -> dict:
        if not self.supported:
            return {"ok": False, "error": "Windows only"}
        e = self._find(eid)
        if not e:
            return {"ok": False, "error": "not_found"}
        if not e.can_toggle:
            return {"ok": False, "error": "cannot_toggle"}
        try:
            if e.kind == "task":
                self._task_action(e, "enable" if on else "disable")
            else:
                self.reg.set_binary(e.hive, f"{APPROVED}\\{e.approved}", e.name,
                                    ENABLED_FLAG if on else disabled_flag())
        except NeedsAdmin:
            return {"ok": False, "error": "admin"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    def delete(self, eid: str) -> dict:
        if not self.supported:
            return {"ok": False, "error": "Windows only"}
        e = self._find(eid)
        if not e:
            return {"ok": False, "error": "not_found"}
        try:
            if e.kind == "task":
                self._task_action(e, "delete")
            elif e.kind == "folder":
                os.remove(e.path)
                self.reg.delete_value(e.hive, f"{APPROVED}\\{e.approved}", e.name)
            else:
                self.reg.delete_value(e.hive, e.key, e.name)
                if e.approved:
                    self.reg.delete_value(e.hive, f"{APPROVED}\\{e.approved}", e.name)
        except (NeedsAdmin, PermissionError):
            return {"ok": False, "error": "admin"}
        except FileNotFoundError:
            pass
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}
