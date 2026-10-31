"""Package catalog: loading, per-host resolution and cross-OS mapping."""
from __future__ import annotations

import json
from functools import lru_cache

from .core.paths import resource
from .core.system import LINUX, MACOS, WINDOWS, SystemInfo
from .pkg.base import PackageManager, Source
from .pkg.registry import candidate_names, resolve, sources_for

CATEGORIES = ["runtimes", "dev", "ai", "browsers", "utilities", "security", "gaming",
              "database", "virtual", "drivers", "hardware_test"]
PRESETS = ["essential", "dev", "gamer", "ai", "hardware", "database"]

OS_KEY = {WINDOWS: "win", MACOS: "mac", LINUX: "linux"}


@lru_cache(maxsize=1)
def load() -> list[dict]:
    with open(resource("data", "catalog.json"), encoding="utf-8") as fh:
        return json.load(fh)["packages"]


def by_id() -> dict[str, dict]:
    return {p["id"]: p for p in load()}


def platforms(pkg: dict) -> list[str]:
    out = []
    if pkg.get("win") or pkg.get("web_only"):
        out.append(WINDOWS)
    if pkg.get("mac"):
        out.append(MACOS)
    if pkg.get("linux"):
        out.append(LINUX)
    return out


def view(info: SystemInfo, managers: dict[str, PackageManager], installed: dict[str, set[str]],
         prefer: str = "native") -> list[dict]:
    """Catalog entries annotated for this host (what the UI renders)."""
    out = []
    possible = set(candidate_names(info))
    for p in load():
        srcs = resolve(p, info, managers, prefer)
        declared = sources_for(p, info)
        is_installed = False
        for s in srcs:
            pm = managers.get(s.pm)
            if pm and pm.key(s) in installed.get(s.pm, set()):
                is_installed = True
                break
        if srcs:
            status = "installed" if is_installed else "available"
        elif any(s.pm in possible for s in declared):
            status = "needs_manager"       # e.g. only a flatpak id but flatpak missing
        else:
            status = "unsupported"
        out.append({
            "id": p["id"],
            "name": p["name"],
            "name_tr": p.get("name_tr", p["name"]),
            "category": p["category"],
            "desc": p["desc"],
            "long": p.get("long", p["desc"]),
            "website": p.get("website", ""),
            "icon": resource("ui", "assets", "apps", f"{p['id']}.png").is_file(),
            "presets": p.get("presets", []),
            "recommended": p.get("recommended", False),
            "platforms": platforms(p),
            "sources": [s.to_dict() for s in srcs],
            "missing_managers": sorted({s.pm for s in declared if s.pm in possible} - set(managers)) if not srcs else [],
            "status": status,
            "alt": p.get("alt", {}).get(info.os),
        })
    return out


def map_for_restore(pkg_ids: list[str], info: SystemInfo,
                    managers: dict[str, PackageManager]) -> list[dict]:
    """Plan for restoring a list of catalog ids (possibly from another OS)."""
    cat = by_id()
    plan = []
    for pid in pkg_ids:
        p = cat.get(pid)
        if not p:
            plan.append({"from": pid, "action": "skip", "reason": "unknown"})
            continue
        if resolve(p, info, managers):
            plan.append({"from": pid, "to": pid, "action": "install"})
            continue
        alt = p.get("alt", {}).get(info.os)
        if alt and alt in cat and resolve(cat[alt], info, managers):
            plan.append({"from": pid, "to": alt, "action": "alternative"})
            continue
        plan.append({"from": pid, "action": "skip", "reason": "unsupported"})
    return plan


def first_source(pkg_id: str, info: SystemInfo, managers: dict[str, PackageManager],
                 prefer: str = "native") -> list[Source]:
    p = by_id().get(pkg_id)
    return resolve(p, info, managers, prefer) if p else []
