"""winget backend (Windows Package Manager)."""
from __future__ import annotations

import json
import os
import re
import tempfile

from ..core import proc
from ..core.system import which
from .base import PackageManager, Source

# winget exit codes that mean "nothing to do" rather than failure.
WINGET_OK = {
    0,
    -1978335189, 0x8A15002B,   # APPINSTALLER_CLI_ERROR_UPDATE_NOT_APPLICABLE
    -1978335212, 0x8A150014,   # NO_APPLICATIONS_FOUND on upgrade of up-to-date pkg
    -1978335135, 0x8A150061,   # PACKAGE_ALREADY_INSTALLED
    -1978334963, 0x8A15010D,   # INSTALL_ALREADY_INSTALLED
    3010,                      # success, reboot required
}

COMMON = ["--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"]


class Winget(PackageManager):
    name = "winget"
    label = "winget"
    binary = "winget"

    def path(self) -> str | None:
        found = which("winget")
        if found:
            return found
        local = os.environ.get("LOCALAPPDATA", "")
        cand = os.path.join(local, "Microsoft", "WindowsApps", "winget.exe")
        return cand if os.path.exists(cand) else None

    def version(self) -> str:
        p = self.path()
        return proc.run([p, "--version"], timeout=20).out.strip().lstrip("v") if p else ""

    def installed(self) -> set[str]:
        p = self.path()
        if not p:
            return set()
        # `winget export` yields exact PackageIdentifiers — far more reliable
        # than scraping the column layout of `winget list`.
        fd, tmp = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            proc.run([p, "export", "-o", tmp, "--include-versions", "--accept-source-agreements",
                      "--disable-interactivity"], timeout=180)
            with open(tmp, encoding="utf-8-sig") as fh:
                data = json.load(fh)
            ids = {pkg["PackageIdentifier"].lower()
                   for src in data.get("Sources", []) for pkg in src.get("Packages", [])}
            if ids:
                return ids
        except Exception:
            pass
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        return self._installed_from_list(p)

    @staticmethod
    def _installed_from_list(p: str) -> set[str]:
        out = proc.run([p, "list", "--accept-source-agreements", "--disable-interactivity"], timeout=180).out
        ids: set[str] = set()
        for line in out.splitlines():
            for tok in line.split():
                if re.fullmatch(r"[A-Za-z0-9][\w\-+]*\.[\w.\-+]+", tok) and not re.fullmatch(r"[\d.]+", tok):
                    ids.add(tok.lower())
        return ids

    def install_cmd(self, sources: list[Source]) -> list[str]:
        (src,) = sources
        return [self.path() or "winget", "install", "--id", src.id, "--exact", "--silent", *COMMON]

    def download_cmd(self, src: Source, dest: str) -> list[str]:
        return [self.path() or "winget", "download", "--id", src.id, "--exact", "-d", dest, *COMMON]

    def upgrade_cmd(self, sources: list[Source]) -> list[str]:
        (src,) = sources
        return [self.path() or "winget", "upgrade", "--id", src.id, "--exact", "--silent", *COMMON]

    def uninstall_cmd(self, sources: list[Source]) -> list[str]:
        (src,) = sources
        return [self.path() or "winget", "uninstall", "--id", src.id, "--exact", "--silent",
                "--accept-source-agreements", "--disable-interactivity"]

    def ok(self, code: int, output: str) -> bool:
        if code in WINGET_OK or (code & 0xFFFFFFFF) in WINGET_OK:
            return True
        low = output.lower()
        return "already installed" in low or "found an existing package already installed" in low
