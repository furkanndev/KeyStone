"""Host detection: OS family, distribution, architecture, privileges, desktop.

Everything platform-specific in KeyStone branches on ``SystemInfo.os``
("windows" | "macos" | "linux"), never on ``sys.platform`` directly, so tests
can simulate any host by constructing a ``SystemInfo`` by hand.
"""
from __future__ import annotations

import ctypes
import os
import platform
import shutil
import socket
import sys
from dataclasses import asdict, dataclass, field
from functools import lru_cache

WINDOWS, MACOS, LINUX = "windows", "macos", "linux"


@dataclass
class SystemInfo:
    os: str                       # windows | macos | linux
    os_name: str                  # "Windows 11 Pro", "macOS 15.1", "Ubuntu 24.04 LTS"
    os_version: str
    arch: str                     # x64 | arm64 | x86
    distro_id: str = ""           # ubuntu, fedora, arch ... (linux only)
    distro_like: list[str] = field(default_factory=list)
    desktop: str = ""             # gnome, kde, ... (linux) / aqua / explorer
    hostname: str = ""
    username: str = ""
    is_admin: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def family(self) -> str:
        """Coarse family used for file-layout compatibility (unix vs windows)."""
        return "windows" if self.os == WINDOWS else "unix"


def _arch() -> str:
    m = platform.machine().lower()
    if m in ("amd64", "x86_64"):
        return "x64"
    if m in ("arm64", "aarch64"):
        return "arm64"
    if m in ("i386", "i686", "x86"):
        return "x86"
    return m or "unknown"


def _read_os_release() -> dict[str, str]:
    data: dict[str, str] = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        data[k] = v.strip().strip('"')
            break
        except OSError:
            continue
    return data


def _is_admin(os_family: str) -> bool:
    try:
        if os_family == WINDOWS:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        return os.geteuid() == 0
    except Exception:
        return False


def _windows_name() -> tuple[str, str]:
    ver = platform.version()          # 10.0.26100
    release = platform.release()      # "10" or "11" (Python >= 3.12 reports 11)
    try:
        build = int(ver.split(".")[2])
    except (IndexError, ValueError):
        build = 0
    if build >= 22000:
        release = "11"
    edition = ""
    display = ""
    try:
        import winreg  # type: ignore
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            edition = winreg.QueryValueEx(k, "EditionID")[0]
            display = winreg.QueryValueEx(k, "DisplayVersion")[0]
    except Exception:
        pass
    name = f"Windows {release}"
    if edition:
        name += f" {edition.replace('Professional', 'Pro').replace('Core', 'Home')}"
    if display:
        name += f" {display}"
    return name, ver


def _macos_name() -> tuple[str, str]:
    ver = platform.mac_ver()[0] or platform.release()
    names = {"26": "Tahoe", "15": "Sequoia", "14": "Sonoma", "13": "Ventura", "12": "Monterey"}
    major = ver.split(".")[0]
    nice = names.get(major)
    return (f"macOS {ver}" + (f" {nice}" if nice else "")), ver


def _linux_desktop() -> str:
    raw = (os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "").lower()
    for de in ("gnome", "kde", "xfce", "cinnamon", "mate", "lxqt", "budgie", "pantheon", "cosmic", "hyprland", "sway"):
        if de in raw:
            return de
    return raw.split(":")[0] if raw else ""


@lru_cache(maxsize=1)
def detect() -> SystemInfo:
    host = socket.gethostname()
    user = os.environ.get("USER") or os.environ.get("USERNAME") or ""
    if sys.platform.startswith("win"):
        name, ver = _windows_name()
        return SystemInfo(WINDOWS, name, ver, _arch(), desktop="explorer",
                          hostname=host, username=user, is_admin=_is_admin(WINDOWS))
    if sys.platform == "darwin":
        name, ver = _macos_name()
        return SystemInfo(MACOS, name, ver, _arch(), desktop="aqua",
                          hostname=host, username=user, is_admin=_is_admin(MACOS))
    rel = _read_os_release()
    return SystemInfo(
        LINUX,
        rel.get("PRETTY_NAME") or f"Linux {platform.release()}",
        rel.get("VERSION_ID", platform.release()),
        _arch(),
        distro_id=rel.get("ID", "linux"),
        distro_like=rel.get("ID_LIKE", "").split(),
        desktop=_linux_desktop(),
        hostname=host,
        username=user,
        is_admin=_is_admin(LINUX),
    )


def which(name: str) -> str | None:
    """shutil.which plus well-known locations that GUI apps miss from PATH."""
    found = shutil.which(name)
    if found:
        return found
    extra = []
    if sys.platform == "darwin":
        extra = ["/opt/homebrew/bin", "/usr/local/bin"]
    elif sys.platform.startswith("win"):
        local = os.environ.get("LOCALAPPDATA", "")
        extra = [os.path.join(local, "Microsoft", "WindowsApps")]
    else:
        extra = ["/usr/local/bin", "/usr/bin", "/bin", "/var/lib/flatpak/exports/bin", "/snap/bin"]
    for d in extra:
        cand = os.path.join(d, name + (".exe" if sys.platform.startswith("win") and not name.endswith(".exe") else ""))
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None
