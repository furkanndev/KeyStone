"""Tweaks for the current OS: list, inspect, apply, revert."""
from __future__ import annotations

from ..core.system import LINUX, MACOS, WINDOWS, SystemInfo, which
from .engine import Backends, Tweak

CATEGORIES = ["interface", "performance", "privacy", "debloat", "system", "developer", "maintenance"]


def all_tweaks() -> dict[str, list[Tweak]]:
    from . import linux, macos, windows
    return {WINDOWS: windows.TWEAKS, MACOS: macos.TWEAKS, LINUX: linux.TWEAKS}


def for_host(info: SystemInfo) -> list[Tweak]:
    tweaks = all_tweaks()[info.os]
    if info.os != LINUX:
        return tweaks
    from .linux import requirement_met
    return [t for t in tweaks if requirement_met(t.requires, info.desktop)]


def by_id(info: SystemInfo) -> dict[str, Tweak]:
    return {t.id: t for t in all_tweaks()[info.os]}


def restart_shell(info: SystemInfo, which_: str) -> None:
    from . import linux, macos, windows
    {WINDOWS: windows, MACOS: macos, LINUX: linux}[info.os].restart_shell(which_)


__all__ = ["Backends", "Tweak", "CATEGORIES", "for_host", "by_id", "all_tweaks", "restart_shell", "which"]
