"""Which managers exist on this host, and which source a catalog entry uses."""
from __future__ import annotations

from functools import lru_cache

from ..core.system import LINUX, MACOS, WINDOWS, SystemInfo
from .base import PackageManager, Source
from .linux import Apt, Dnf, Flatpak, Pacman, Snap, Zypper
from .macos import Brew
from .windows import Winget

ALL: dict[str, type[PackageManager]] = {
    "winget": Winget, "brew": Brew, "apt": Apt, "dnf": Dnf, "pacman": Pacman,
    "zypper": Zypper, "flatpak": Flatpak, "snap": Snap,
}

# distro id / ID_LIKE  ->  native manager
NATIVE = {
    "debian": "apt", "ubuntu": "apt", "linuxmint": "apt", "pop": "apt", "elementary": "apt",
    "zorin": "apt", "kali": "apt", "raspbian": "apt", "neon": "apt",
    "fedora": "dnf", "rhel": "dnf", "centos": "dnf", "rocky": "dnf", "almalinux": "dnf", "nobara": "dnf",
    "arch": "pacman", "manjaro": "pacman", "endeavouros": "pacman", "cachyos": "pacman", "garuda": "pacman",
    "opensuse": "zypper", "opensuse-tumbleweed": "zypper", "opensuse-leap": "zypper", "suse": "zypper",
}


def native_linux_pm(info: SystemInfo) -> str | None:
    for d in [info.distro_id, *info.distro_like]:
        if d in NATIVE:
            return NATIVE[d]
    return None


def candidate_names(info: SystemInfo) -> list[str]:
    if info.os == WINDOWS:
        return ["winget"]
    if info.os == MACOS:
        return ["brew"]
    names = []
    native = native_linux_pm(info)
    if native:
        names.append(native)
    names += ["flatpak", "snap"]
    return names


@lru_cache(maxsize=4)
def _instances(names: tuple[str, ...]) -> dict[str, PackageManager]:
    return {n: ALL[n]() for n in names}


def managers_for(info: SystemInfo, only_available: bool = True) -> dict[str, PackageManager]:
    inst = _instances(tuple(candidate_names(info)))
    if not only_available:
        return dict(inst)
    return {n: m for n, m in inst.items() if m.available()}


def sources_for(pkg: dict, info: SystemInfo) -> list[Source]:
    """Every declared source for this OS, in catalog order (before availability filtering)."""
    out: list[Source] = []
    if info.os == WINDOWS:
        for s in pkg.get("win", []):
            if "winget" in s:
                out.append(Source("winget", s["winget"]))
            elif "url" in s:
                out.append(Source("url", s["url"], "portable" if s.get("portable") else ""))
    elif info.os == MACOS:
        for s in pkg.get("mac", []):
            if "cask" in s:
                out.append(Source("brew", s["cask"], "cask"))
            elif "brew" in s:
                out.append(Source("brew", s["brew"], "formula"))
    else:
        lin = pkg.get("linux", {})
        for pm in ("apt", "dnf", "pacman", "zypper", "flatpak", "snap"):
            if pm in lin:
                val = lin[pm]
                kind = ""
                if pm == "snap" and val.endswith(" --classic"):
                    val, kind = val[: -len(" --classic")], "classic"
                out.append(Source(pm, val, kind))
    return out


def resolve(pkg: dict, info: SystemInfo, available: dict[str, PackageManager],
            prefer: str = "native") -> list[Source]:
    """Ordered, usable sources for ``pkg`` on this host (first = chosen).

    ``prefer``: "native" (distro repo first) or "flatpak" (sandboxed first) on Linux.
    """
    srcs = [s for s in sources_for(pkg, info) if s.pm in available or s.pm == "url"]
    if info.os == LINUX:
        native = native_linux_pm(info)

        def rank(s: Source) -> int:
            if s.pm == native:
                return 0 if prefer != "flatpak" else 1
            if s.pm == "flatpak":
                return 1 if prefer != "flatpak" else 0
            return 2 if s.pm == "snap" else 3

        srcs.sort(key=rank)  # stable: keeps catalog order inside a rank
    # Legacy "open the vendor page" entries are Windows products.
    if not srcs and info.os == WINDOWS and pkg.get("website") and pkg.get("web_only"):
        srcs = [Source("web", pkg["website"])]
    return srcs
