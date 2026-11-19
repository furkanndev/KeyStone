"""Work out which file a start-up command line really runs.

Signature checks, "hide Microsoft", icons and VirusTotal hashes must look at the
*payload*, not at a generic host: ``rundll32.exe C:\\Vendor\\x.dll,Run`` is x.dll,
``wscript.exe "C:\\a\\start.vbs"`` is start.vbs. When the payload cannot be found the
entry is reported as unresolved and is never treated as Microsoft's.
"""
from __future__ import annotations

import ntpath
import os
import re
from dataclasses import dataclass

# A quoted program, else everything up to the FIRST token that ends in a program extension (paths may contain
# spaces: C:\Program Files\x\a.exe /arg), else the first word. The lazy ".*?" is what makes it the first one.
_EXE_RE = re.compile(
    r'^\s*(?:"([^"]+)"|(\S.*?\.(?:exe|bat|cmd|com|lnk|vbs|ps1|msc|cpl))(?=\s|$)|(\S+))', re.I)
_TOKEN_RE = re.compile(r'"([^"]*)"|(\S+)')

# Programs that only host someone else's code.
GENERIC_HOSTS = {"rundll32.exe", "regsvr32.exe", "wscript.exe", "cscript.exe", "cmd.exe", "powershell.exe",
                 "pwsh.exe", "mshta.exe", "msiexec.exe", "svchost.exe", "conhost.exe", "wmic.exe"}
_SCRIPT_EXT = (".vbs", ".vbe", ".js", ".jse", ".wsf", ".ps1", ".bat", ".cmd", ".exe", ".dll", ".lnk", ".msi", ".hta")


def expand(text: str) -> str:
    """Expand %VARS% and the NT-style prefixes service ImagePaths use."""
    t = (text or "").strip()
    if t.lower().startswith("\\systemroot\\"):
        t = "%SystemRoot%" + t[11:]
    if t.startswith("\\??\\"):
        t = t[4:]
    return os.path.expandvars(t.replace('""', '"'))


def program_of(command: str) -> str:
    """Best guess at the program a start-up command line launches."""
    m = _EXE_RE.match(expand(command))
    return (m.group(1) or m.group(2) or m.group(3) or "") if m else ""


def _args_of(command: str) -> list[str]:
    cmd = expand(command)
    m = _EXE_RE.match(cmd)
    rest = cmd[m.end():] if m else ""
    return [a or b for a, b in _TOKEN_RE.findall(rest)]


def _system32(name: str) -> str:
    return os.path.join(os.environ.get("SystemRoot") or os.environ.get("windir") or "C:\\Windows", "System32", name)


def _with_dir(p: str) -> str:
    p = p.strip().strip('"')
    return p if ("\\" in p or "/" in p) else _system32(p)


@dataclass(frozen=True)
class Payload:
    host: str          # the program on the command line
    path: str          # the file that actually runs ("" when it cannot be found)
    generic: bool      # the host only runs other code
    resolved: bool     # path is known

    @property
    def inspectable(self) -> bool:
        """Safe to judge by signature: either a normal program or a generic host whose payload was found."""
        return bool(self.path) and (self.resolved or not self.generic)


def _first(tokens: list[str], skip_prefixes: tuple[str, ...] = ("/", "-")) -> str:
    return next((t for t in tokens if t and not t.startswith(skip_prefixes)), "")


def resolve_payload(command: str) -> Payload:
    host = program_of(command)
    base = ntpath.basename(host).lower()
    if base not in GENERIC_HOSTS:
        return Payload(host, host, False, bool(host))
    args = _args_of(command)
    path = ""
    if base == "rundll32.exe":
        first = _first(args)
        path = _with_dir(first.split(",")[0]) if first else ""
    elif base == "regsvr32.exe":
        first = _first(args)
        path = _with_dir(first) if first else ""
    elif base in ("wscript.exe", "cscript.exe"):
        first = _first(args)
        path = first if first and ("\\" in first or "/" in first) else ""
    elif base == "mshta.exe":
        first = _first(args)
        path = first if first and "\\" in first and not first.lower().startswith(("http", "javascript", "vbscript")) else ""
    elif base == "cmd.exe":
        low = [a.lower() for a in args]
        for flag in ("/c", "/k", "/r"):
            if flag in low:
                tail = args[low.index(flag) + 1:]
                path = next((t for t in tail if ("\\" in t or "/" in t) and t.lower().endswith(_SCRIPT_EXT)), "")
                break
    elif base in ("powershell.exe", "pwsh.exe"):
        low = [a.lower() for a in args]
        for i, a in enumerate(low):
            if a in ("-file", "-f") and i + 1 < len(args):
                path = args[i + 1]
                break
        if not path:
            path = next((t for t in args if t.lower().endswith(".ps1") and ("\\" in t or "/" in t)), "")
    # svchost.exe, msiexec.exe, conhost.exe, wmic.exe: nothing to resolve from the command line.
    return Payload(host, path, True, bool(path))


def real_path(path: str) -> str:
    """An absolute file path for ``path``, or "" when it is not one (flags, bare words, unknown names)."""
    import shutil
    p = (path or "").strip().strip('"')
    if not p:
        return ""
    if os.path.isabs(p):
        return p
    if "\\" not in p and "/" not in p:
        return shutil.which(p) or ""
    return ""


def exists(command_or_path: str) -> bool | None:
    """Does the program on a command line exist? None when it is a bare name resolved through PATH."""
    prog = program_of(command_or_path)
    if not prog or not (os.path.isabs(prog) or "\\" in prog or "/" in prog):
        return None
    return os.path.exists(prog)
