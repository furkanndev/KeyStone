"""Windows start-up entries: an Autoruns-style view with safe actions.

What it covers
* ``Run`` / ``RunOnce`` (HKCU, HKLM, HKLM\\WOW6432Node), the Startup folders and
  scheduled tasks that fire at logon or boot            -> switch on/off, delete
* Auto-start Windows services                           -> start type Automatic / Manual / Disabled
* Logon points: Winlogon, AppInit_DLLs, Image File Execution Options debuggers,
  Active Setup                                          -> read-only
* For every entry: publisher and signature, "open location", VirusTotal, and a
  saved snapshot to compare against (what is new, changed or gone).

Not covered: drivers, codecs, shell extensions, Boot Execute, LSA / Winsock /
print providers, WMI, Office and Internet Explorer add-ins, Store-app tasks.

On/off for Run / folders uses Task Manager's own switch
(``Explorer\\StartupApproved``), so nothing is lost when an entry is turned off.

Security: the interface only ever sends an opaque entry id, resolved against a
fresh scan of that entry's kind. Read-only entries and protected services are
refused here, because the API is reachable over HTTP as well as through the
native window.
"""
from __future__ import annotations

import hashlib
import json
import ntpath
import os
import re
import shutil
import struct
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..core import proc
from ..core.system import WINDOWS, SystemInfo
from ..tweaks.engine import ps
from .payload import Payload, exists as program_exists, expand, is_abs, program_of, real_path, resolve_payload
from .registry import NeedsAdmin, StartupRegistry, WinStartupRegistry
from .signatures import Inspector
from .vt import VirusTotal

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUNONCE = r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
RUN32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
RUNONCE32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce"
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
SERVICES = r"SYSTEM\CurrentControlSet\Services"
LAYERS = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
REGEDIT_STATE = r"Software\Microsoft\Windows\CurrentVersion\Applets\Regedit"
NT = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
WINLOGON = NT + r"\Winlogon"
APPINIT = (NT + r"\Windows", r"SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Windows")
IFEO = (NT + r"\Image File Execution Options", r"SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Image File Execution Options")
ACTIVE_SETUP = (r"SOFTWARE\Microsoft\Active Setup\Installed Components",
                r"SOFTWARE\WOW6432Node\Microsoft\Active Setup\Installed Components")

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
WIN32_SERVICE_TYPES = {16, 32, 272, 288}   # own / shared process (and their interactive variants)
START_LABELS = {2: "auto", 3: "manual", 4: "disabled"}
SC_MODES = {"auto": "auto", "delayed": "delayed-auto", "manual": "demand", "disabled": "disabled"}

# Services whose start type must never be changed from here: the system will not boot or sign in without them.
CRITICAL_SERVICES = {
    "rpcss", "rpceptmapper", "dcomlaunch", "lsm", "samss", "eventlog", "winmgmt", "plugplay", "power", "profsvc",
    "usermanager", "gpsvc", "brokerinfrastructure", "systemeventsbroker", "timebrokersvc", "coremessagingregistrar",
    "staterepository", "cryptsvc", "keyiso", "lanmanworkstation", "lanmanserver", "dhcp", "dnscache", "nsi", "bfe",
    "mpssvc", "windefend", "wdnissvc", "sense", "trustedinstaller", "schedule", "wudfsvc", "netlogon", "lsass",
    "audioendpointbuilder", "audiosrv", "themes", "sens", "msiserver", "appinfo", "camsvc", "tokenbroker",
    "cdpsvc", "wlidsvc", "securityhealthservice", "wscsvc", "sysmain", "fontcache", "gamingservices",
}


def disabled_flag(now: float | None = None) -> bytes:
    """Value Task Manager writes when an entry is turned off: 03 00 00 00 + FILETIME."""
    ticks = int(((now if now is not None else time.time()) + _FILETIME_EPOCH) * 10_000_000)
    return b"\x03\x00\x00\x00" + struct.pack("<Q", ticks)


def is_disabled(data: bytes | None) -> bool:
    """A missing value means enabled; an odd first byte means disabled."""
    return bool(data) and (data[0] & 1) == 1


def _prefix(kind: str) -> str:
    return {"registry": "reg", "folder": "fld", "task": "tsk", "service": "svc", "logon": "log"}[kind]


KIND_BY_PREFIX = {"reg": "registry", "fld": "folder", "tsk": "task", "svc": "service", "log": "logon"}


def _make_id(kind: str, *parts: str) -> str:
    h = hashlib.sha1("\x1f".join(parts).lower().encode("utf-8")).hexdigest()[:16]
    return f"{_prefix(kind)}-{h}"


@dataclass
class Entry:
    id: str
    kind: str                # registry | folder | task | service | logon
    name: str
    command: str
    location: str            # human readable source
    scope: str               # user | machine
    enabled: bool
    can_toggle: bool
    exists: bool | None      # does the program exist (None: unknown)
    needs_admin: bool = False     # changing this item needs administrator rights
    runs_elevated: bool = False   # the program itself starts with administrator rights
    readonly: bool = False        # shown for information only
    suspicious: bool = False      # a logon point that was changed from its default
    note: str = ""
    start: str = ""               # services: auto | manual | disabled
    delayed: bool = False
    protected: str = ""           # services: "" | critical | dependency
    description: str = ""
    # private resolution data, never sent to the interface
    hive: str = ""
    key: str = ""
    approved: str = ""
    path: str = ""           # folder entries: file path / task entries: task path
    service: str = ""
    regpath: str = ""        # HKLM\... key a "show in regedit" action opens
    target: str = ""         # the file that really runs ("" when unknown: then never judged by signature)

    def public(self) -> dict:
        return {"id": self.id, "kind": self.kind, "name": self.name, "command": self.command,
                "location": self.location, "scope": self.scope, "enabled": self.enabled,
                "can_toggle": self.can_toggle, "exists": self.exists, "needs_admin": self.needs_admin,
                "runs_elevated": self.runs_elevated, "readonly": self.readonly, "suspicious": self.suspicious,
                "note": self.note, "start": self.start, "delayed": self.delayed, "protected": self.protected,
                "description": self.description, "can_registry": bool(self.regpath),
                "can_file": bool(self.target or self.kind == "folder")}


TASK_LIST = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$rows = @(Get-ScheduledTask | Where-Object {
    $_.Triggers | Where-Object { $_.CimClass.CimClassName -in 'MSFT_TaskLogonTrigger', 'MSFT_TaskBootTrigger' }
  } | ForEach-Object {
    [pscustomobject]@{
      name = $_.TaskName; path = $_.TaskPath; enabled = ($_.State -ne 'Disabled')
      user = [string]$_.Principal.UserId; highest = ($_.Principal.RunLevel -eq 'Highest')
      clsid = (($_.Actions | ForEach-Object { [string]$_.ClassId } | Where-Object { $_ }) -join ',')
      command = (($_.Actions | ForEach-Object { (([string]$_.Execute) + ' ' + ([string]$_.Arguments)).Trim() } | Where-Object { $_ }) -join ' && ')
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


def _same_user(principal: str) -> bool:
    """Is a task principal the signed-in user (rather than SYSTEM, a group or another account)?"""
    me = (os.environ.get("USERNAME") or "").lower()
    return bool(me) and principal.replace("/", "\\").split("\\")[-1].lower() == me


def _load_indirect(text: str) -> str:
    """Resolve ``@%SystemRoot%\\system32\\x.dll,-123`` style display names."""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        hr = ctypes.windll.shlwapi.SHLoadIndirectString(text, buf, 512, None)  # type: ignore[attr-defined]
        return buf.value if hr == 0 else ""
    except Exception:
        return ""


def _default_spawn(argv: list[str]) -> None:
    subprocess.Popen(argv)


def _default_shell_open(target: str) -> None:
    os.startfile(target)  # type: ignore[attr-defined]


class StartupManager:
    def __init__(self, info: SystemInfo, reg: StartupRegistry | None = None,
                 run: Callable[..., proc.Result] | None = None, folders: list[tuple[str, str, str]] | None = None,
                 data_dir: Path | None = None, cache_file: Path | None = None,
                 opener: Callable[..., Any] | None = None, indirect: Callable[[str], str] | None = None,
                 spawn: Callable[[list[str]], None] | None = None,
                 shell_open: Callable[[str], None] | None = None) -> None:
        self.info = info
        self.reg = reg or WinStartupRegistry()
        self._run = run
        self._folders = folders
        self._data_dir = Path(data_dir) if data_dir else None
        self._indirect = indirect or _load_indirect
        self._spawn = spawn or _default_spawn
        self._shell_open = shell_open or _default_shell_open
        self.sigs = Inspector(run=self.run, cache_file=cache_file)
        self.vt = VirusTotal(opener=opener)
        self._seen: dict[str, Entry] = {}        # entries of the latest scans: the only ids served
        self._icons: dict[str, str] = {}         # file path -> PNG data URI ("" = no icon)
        self._changed: dict[str, dict] = self._read_json("startup_services.json", {})

    # -- helpers --------------------------------------------------------------
    @property
    def supported(self) -> bool:
        return self.info.os == WINDOWS

    def run(self, *a, **kw) -> proc.Result:
        return (self._run or proc.run)(*a, **kw)

    def _read_json(self, name: str, default: Any) -> Any:
        if not self._data_dir:
            return default
        try:
            return json.loads((self._data_dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    def _write_json(self, name: str, data: Any) -> None:
        if not self._data_dir:
            return
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            tmp = self._data_dir / (name + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self._data_dir / name)
        except OSError:
            pass

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

    @staticmethod
    def _exists(p: Payload, command: str) -> bool | None:
        return os.path.exists(p.path) if p.resolved and p.generic else program_exists(command)

    # -- scan -----------------------------------------------------------------
    def scan(self, include_tasks: bool = True) -> list[Entry]:
        if not self.supported:
            return []
        entries = self._scan_registry() + self._scan_folders()
        if include_tasks:
            entries += self._scan_tasks()
        entries += self._scan_services() + self._scan_logon()
        self._seen = {e.id: e for e in entries}
        return entries

    def _scan_kind(self, kind: str) -> list[Entry]:
        entries = {"registry": self._scan_registry, "folder": self._scan_folders, "task": self._scan_tasks,
                   "service": self._scan_services, "logon": self._scan_logon}[kind]()
        for e in entries:
            self._seen[e.id] = e
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
        elevated = self._elevated_programs()
        out: list[Entry] = []
        for hive, key, label, sub in REG_SOURCES:
            for name, data in self.reg.values(hive, key):
                pl = resolve_payload(data)
                out.append(Entry(
                    id=_make_id("registry", hive, key, name), kind="registry", name=name, command=data,
                    location=label, scope="user" if hive == "HKCU" else "machine",
                    enabled=not self._approved_off(hive, sub, name), can_toggle=bool(sub),
                    exists=self._exists(pl, data), needs_admin=hive == "HKLM",
                    runs_elevated=bool({pl.path.lower(), pl.host.lower()} & elevated),
                    hive=hive, key=key, approved=sub, regpath=f"{hive}\\{key}",
                    target=real_path(pl.path) if pl.inspectable else ""))
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
                    exists=True, needs_admin=scope == "machine", hive=hive, approved="StartupFolder",
                    path=it.path, target=it.path))
        return out

    def _clsid_server(self, clsid: str) -> str:
        """The DLL / EXE behind a COM class used as a scheduled-task action."""
        for sub in ("InprocServer32", "LocalServer32"):
            v = self.reg.get_value("HKLM", rf"SOFTWARE\Classes\CLSID\{clsid}\{sub}", "")
            if isinstance(v, str) and v.strip():
                return real_path(resolve_payload(v).path or program_of(v))
        return ""

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
            command = str(row.get("command") or "")
            clsid = str(row.get("clsid") or "").split(",")[0].strip()
            if command:
                pl = resolve_payload(command)
                target, exists_ = (real_path(pl.path) if pl.inspectable else ""), self._exists(pl, command)
            elif clsid:
                command = f"COM {clsid}"
                target = self._clsid_server(clsid)
                exists_ = os.path.exists(target) if target else None
            else:
                target, exists_ = "", None
            out.append(Entry(
                id=_make_id("task", tpath, row["name"]), kind="task", name=str(row["name"]),
                command=command, location=f"Task Scheduler {tpath}", scope="machine",
                enabled=bool(row.get("enabled")), can_toggle=True, exists=exists_,
                needs_admin=bool(row.get("highest")) or not _same_user(str(row.get("user") or "")),
                runs_elevated=bool(row.get("highest")), path=tpath, target=target))
        out.sort(key=lambda e: e.name.lower())
        return out

    def _scan_services(self) -> list[Entry]:
        base = SERVICES
        listed: list[tuple[str, str, int, str]] = []
        dependents: dict[str, set[str]] = {}
        for n in self.reg.subkeys("HKLM", base):
            k = f"{base}\\{n}"
            if self.reg.get_value("HKLM", k, "Type") not in WIN32_SERVICE_TYPES:
                continue
            start = self.reg.get_value("HKLM", k, "Start")
            if not isinstance(start, int):
                continue
            if start == 2:
                deps = self.reg.get_value("HKLM", k, "DependOnService")
                for d in deps if isinstance(deps, list) else []:
                    dependents.setdefault(str(d).lstrip("+").lower(), set()).add(n.lower())
            if start in (2, 4) or n in self._changed:
                image = self.reg.get_value("HKLM", k, "ImagePath")
                if isinstance(image, str) and image.strip():
                    listed.append((n, k, start, image))
        out: list[Entry] = []
        for n, k, start, image in listed:
            lname = n.lower()
            delayed = start == 2 and self.reg.get_value("HKLM", k, "DelayedAutostart") == 1
            display = self.reg.get_value("HKLM", k, "DisplayName")
            display = display if isinstance(display, str) else ""
            if display.startswith("@"):
                display = self._indirect(display) or ""
            desc = self.reg.get_value("HKLM", k, "Description")
            desc = desc if isinstance(desc, str) else ""
            if desc.startswith("@"):
                desc = self._indirect(desc) or ""
            prog = program_of(image)
            note, target = "", ""
            if ntpath.basename(prog).lower() == "svchost.exe":
                dll = self.reg.get_value("HKLM", f"{k}\\Parameters", "ServiceDll")
                if isinstance(dll, str) and dll.strip():
                    target = real_path(expand(dll))
                    note = f"ServiceDll: {expand(dll)}"
            else:
                pl = resolve_payload(image)
                target = real_path(pl.path) if pl.inspectable else ""
            reason = ""
            if lname in CRITICAL_SERVICES:
                reason = "critical"
            elif start == 2 and dependents.get(lname, set()) - {lname}:
                reason = "dependency"
            check = target or prog
            out.append(Entry(
                id=_make_id("service", n), kind="service", name=display or n, command=image,
                location=f"Services · {n}", scope="machine", enabled=start == 2, can_toggle=True,
                exists=os.path.exists(check) if check and is_abs(check) else None,
                needs_admin=True, note=note, start=START_LABELS.get(start, "manual"), delayed=delayed,
                protected=reason, description=desc, service=n,
                regpath=f"HKLM\\{k}", target=target))
        out.sort(key=lambda e: e.name.lower())
        return out

    # -- logon points (read-only) --------------------------------------------
    def _scan_logon(self) -> list[Entry]:
        out: list[Entry] = []

        def add(name: str, command: str, location: str, regpath: str, suspicious: bool, note: str = "") -> None:
            pl = resolve_payload(command)
            out.append(Entry(
                id=_make_id("logon", regpath, name), kind="logon", name=name, command=command, location=location,
                scope="machine", enabled=True, can_toggle=False, exists=self._exists(pl, command), readonly=True,
                suspicious=suspicious, note=note, regpath=regpath, target=real_path(pl.path) if pl.inspectable else ""))

        shell = self.reg.get_value("HKLM", WINLOGON, "Shell")
        if isinstance(shell, str) and shell.strip():
            add("Winlogon · Shell", shell, "Winlogon", f"HKLM\\{WINLOGON}", shell.strip().lower() != "explorer.exe")
        ui = self.reg.get_value("HKLM", WINLOGON, "Userinit")
        if isinstance(ui, str) and ui.strip():
            parts = [p.strip() for p in ui.split(",") if p.strip()]
            ok = len(parts) == 1 and parts[0].lower().replace("/", "\\").endswith("system32\\userinit.exe")
            add("Winlogon · Userinit", ui.rstrip(", ") if ok else ui, "Winlogon", f"HKLM\\{WINLOGON}", not ok)
        for extra in ("Taskman", "AppSetup"):
            v = self.reg.get_value("HKLM", WINLOGON, extra)
            if isinstance(v, str) and v.strip():
                add(f"Winlogon · {extra}", v, "Winlogon", f"HKLM\\{WINLOGON}", True)
        for key in APPINIT:
            v = self.reg.get_value("HKLM", key, "AppInit_DLLs")
            if isinstance(v, str) and v.strip():
                load = self.reg.get_value("HKLM", key, "LoadAppInit_DLLs")
                add("AppInit_DLLs", v, "AppInit_DLLs", f"HKLM\\{key}", True,
                    "LoadAppInit_DLLs = %s" % (load if load is not None else "?"))
        for key in IFEO:
            for exe in sorted(self.reg.subkeys("HKLM", key), key=str.lower):
                dbg = self.reg.get_value("HKLM", f"{key}\\{exe}", "Debugger")
                if isinstance(dbg, str) and dbg.strip():
                    add(f"{exe} · Debugger", dbg, "Image File Execution Options", f"HKLM\\{key}\\{exe}", True)
        for key in ACTIVE_SETUP:
            for cid in sorted(self.reg.subkeys("HKLM", key), key=str.lower):
                stub = self.reg.get_value("HKLM", f"{key}\\{cid}", "StubPath")
                if isinstance(stub, str) and stub.strip():
                    label = self.reg.get_value("HKLM", f"{key}\\{cid}", "")
                    add(f"Active Setup · {label if isinstance(label, str) and label else cid}", stub,
                        "Active Setup", f"HKLM\\{key}\\{cid}", False)
        return out

    # -- inspection (signatures), icons ---------------------------------------
    def inspect(self, ids: list[str]) -> dict[str, dict]:
        """Publisher / signature for entries of the latest scan. Entries that cannot be judged are left out."""
        if not self.supported:
            return {}
        es = [self._seen[i] for i in ids if i in self._seen and self._seen[i].target]
        info = self.sigs.inspect([e.target for e in es])
        out: dict[str, dict] = {}
        for e in es:
            r = info.get(e.target)
            if r:
                out[e.id] = {"signature": r["signature"], "publisher": r["publisher"], "microsoft": r["microsoft"]}
        return out

    def _payload_file(self, e: Entry) -> str:
        """The file this entry really runs, if it is known and exists."""
        path = e.target
        if path.lower().endswith(".lnk"):
            path = (self.sigs.inspect([path]).get(path) or {}).get("target") or ""
        return path if path and os.path.isfile(path) else ""

    def _icon_source(self, e: Entry) -> str:
        if e.kind == "folder":
            return e.path
        if e.target and os.path.isfile(e.target):
            return e.target
        prog = program_of(e.command)
        if prog and os.path.isfile(prog):
            return prog
        return shutil.which(prog) or "" if prog else ""

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

    # -- snapshots --------------------------------------------------------------
    @staticmethod
    def _item(e: Entry) -> dict:
        return {"kind": e.kind, "name": e.name, "location": e.location, "command": e.command,
                "enabled": e.enabled, "start": e.start}

    def _snapshots(self) -> list[dict]:
        data = self._read_json("startup_snapshots.json", {})
        snaps = data.get("snapshots") if isinstance(data, dict) else None
        return [s for s in snaps if isinstance(s, dict) and isinstance(s.get("items"), dict)] if isinstance(snaps, list) else []

    def save_snapshot(self, label: str = "") -> dict:
        if not self.supported:
            return {"ok": False, "error": "Windows only"}
        entries = self.scan()
        snap = {"id": f"s{int(time.time())}", "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": str(label)[:80],
                "items": {e.id: self._item(e) for e in entries}}
        if not self._data_dir:
            return {"ok": False, "error": "no_storage"}
        self._write_json("startup_snapshots.json", {"snapshots": (self._snapshots() + [snap])[-5:]})
        return {"ok": True, "time": snap["time"], "count": len(entries)}

    def diff(self, entries: list[Entry]) -> dict:
        """Compare the current entries with the newest snapshot. No snapshot: nothing is flagged."""
        snaps = self._snapshots()
        if not snaps:
            return {"has": False, "time": "", "count": 0, "added": [], "changed": [], "removed": []}
        snap = snaps[-1]
        old = snap["items"]
        cur = {e.id: e for e in entries}
        added = [i for i in cur if i not in old]
        changed = [i for i, e in cur.items() if i in old and
                   (old[i].get("command") != e.command or old[i].get("enabled") != e.enabled or old[i].get("start") != e.start)]
        removed = [{"id": i, **{k: v.get(k, "") for k in ("kind", "name", "location", "command")}}
                   for i, v in old.items() if i not in cur]
        return {"has": True, "time": snap.get("time", ""), "count": len(old), "added": added, "changed": changed,
                "removed": removed}

    def list_public(self) -> dict:
        entries = self.scan()
        return {"supported": True, "entries": [e.public() for e in entries], "snapshot": self.diff(entries)}

    # -- reveal ---------------------------------------------------------------
    def reveal(self, eid: str, what: str) -> dict:
        e = self._find(eid)
        if not e:
            return {"ok": False, "error": "not_found"}
        if what == "registry":
            if not e.regpath:
                return {"ok": False, "error": "no_registry"}
            full = e.regpath.replace("HKLM\\", "HKEY_LOCAL_MACHINE\\", 1).replace("HKCU\\", "HKEY_CURRENT_USER\\", 1)
            try:
                self.reg.set_string("HKCU", REGEDIT_STATE, "LastKey", "Computer\\" + full)
                self._shell_open("regedit.exe")
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
            return {"ok": True}
        path = e.path if e.kind == "folder" else self._payload_file(e)
        if not path or not os.path.exists(path):
            return {"ok": False, "error": "no_file"}
        try:
            self._spawn(["explorer.exe", "/select,", os.path.normpath(path)])     # same form open_path ships
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    # -- VirusTotal -----------------------------------------------------------
    def _vt_file(self, eid: str) -> tuple[str, dict | None]:
        e = self._find(eid)
        if not e:
            return "", {"ok": False, "error": "not_found"}
        path = self._payload_file(e)
        if not path:
            return "", {"ok": False, "error": "no_file"}
        return path, None

    def vt_url(self, eid: str) -> dict:
        """Hash the file locally and return the VirusTotal page for it. Nothing is sent."""
        path, err = self._vt_file(eid)
        if err:
            return err
        try:
            sha = self.vt.hash_file(path)
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "sha256": sha, "url": self.vt.link(sha)}

    def vt_lookup(self, eid: str, enabled: bool, api_key: str) -> dict:
        if not enabled:
            return {"ok": False, "error": "disabled"}
        if not api_key:
            return {"ok": False, "error": "no_key"}
        path, err = self._vt_file(eid)
        if err:
            return err
        try:
            sha = self.vt.hash_file(path)
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return self.vt.lookup(sha, api_key)

    # -- actions --------------------------------------------------------------
    def _find(self, eid: str) -> Entry | None:
        """Resolve an id by scanning only the kind its prefix names (never the whole machine)."""
        kind = KIND_BY_PREFIX.get(str(eid).split("-", 1)[0])
        if not kind or not self.supported:
            return None
        return next((e for e in self._scan_kind(kind) if e.id == eid), None)

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
        if e.readonly or e.kind in ("logon", "service"):
            return {"ok": False, "error": "readonly"}
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

    def set_start(self, eid: str, mode: str) -> dict:
        """Change a service's start type: auto, manual or disabled."""
        if not self.supported:
            return {"ok": False, "error": "Windows only"}
        if mode not in ("auto", "manual", "disabled"):
            return {"ok": False, "error": "bad_mode"}
        e = self._find(eid)
        if not e:
            return {"ok": False, "error": "not_found"}
        if e.kind != "service":
            return {"ok": False, "error": "readonly"}
        if e.start == mode:
            return {"ok": True, "unchanged": True}
        if e.protected and mode != "auto":
            return {"ok": False, "error": "protected", "reason": e.protected}
        saved = self._changed.get(e.service) or {}
        sc_mode = SC_MODES[mode]
        if mode == "auto":
            sc_mode = "delayed-auto" if (e.delayed or saved.get("delayed")) else "auto"
        r = self.run(["sc.exe", "config", e.service, "start=", sc_mode], timeout=30)
        if not r.ok:
            if r.code == 5:           # access denied: needs admin, or the service guards itself
                return {"ok": False, "error": "protected" if self.info.is_admin else "admin",
                        **({"reason": "system"} if self.info.is_admin else {})}
            if r.code == 1060:
                return {"ok": False, "error": "not_found"}
            return {"ok": False, "error": (r.out.strip()[:200] or f"exit {r.code}")}
        if mode == "auto":
            self._changed.pop(e.service, None)
        else:
            self._changed.setdefault(e.service, {"start": 2, "delayed": e.delayed})
        self._write_json("startup_services.json", self._changed)
        return {"ok": True}

    def delete(self, eid: str) -> dict:
        if not self.supported:
            return {"ok": False, "error": "Windows only"}
        e = self._find(eid)
        if not e:
            return {"ok": False, "error": "not_found"}
        if e.readonly or e.kind in ("logon", "service"):
            return {"ok": False, "error": "readonly"}
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
