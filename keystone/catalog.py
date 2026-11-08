"""Package catalog: loading, per-host resolution and cross-OS mapping."""
from __future__ import annotations

import json
import re
from functools import lru_cache

from .core.paths import resource
from .core.system import LINUX, MACOS, WINDOWS, SystemInfo
from .pkg.base import PackageManager, Source
from .pkg.registry import candidate_names, resolve, sources_for

CATEGORIES = ["runtimes", "dev", "ai", "browsers", "utilities", "security", "gaming",
              "database", "virtual", "drivers", "hardware_test", "cad", "github"]
PRESETS = ["essential", "dev", "gamer", "ai", "hardware", "database"]

OS_KEY = {WINDOWS: "win", MACOS: "mac", LINUX: "linux"}


@lru_cache(maxsize=1)
def load() -> list[dict]:
    with open(resource("data", "catalog.json"), encoding="utf-8") as fh:
        return json.load(fh)["packages"]


def by_id(custom_apps: list[dict] | None = None) -> dict[str, dict]:
    cat = {p["id"]: p for p in load()}
    if custom_apps:
        for c in custom_apps:
            cat[c["id"]] = c
    return cat


def platforms(pkg: dict) -> list[str]:
    out = []
    if pkg.get("win") or pkg.get("web_only"):
        out.append(WINDOWS)
    if pkg.get("mac"):
        out.append(MACOS)
    if pkg.get("linux"):
        out.append(LINUX)
    return out


def manual_links(pkg: dict) -> dict:
    """Pages for downloading ``pkg`` by hand when the automatic install fails."""
    repo = next((s["github"] for s in pkg.get("win", []) if "github" in s), "")
    m = re.match(r"https://github\.com/([^/]+/[^/#?]+)", pkg.get("website", ""))
    repo = repo or (m.group(1) if m else "")
    return {"website": pkg.get("website", ""),
            "releases": f"https://github.com/{repo}/releases/latest" if repo else ""}


def view(info: SystemInfo, managers: dict[str, PackageManager], installed: dict[str, set[str]],
         prefer: str = "native", custom_apps: list[dict] | None = None) -> list[dict]:
    """Catalog entries annotated for this host (what the UI renders)."""
    out = []
    possible = set(candidate_names(info))
    all_pkgs = load() + (list(custom_apps) if custom_apps else [])
    for p in all_pkgs:
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
        icon_file = resource("ui", "assets", "apps", f"{p['id']}.png").is_file()
        icon_url = p.get("icon_url", "")
        is_gh = (
            p.get("category") == "github"
            or any(s.pm == "github" for s in declared)
            or any(s.pm == "github" for s in srcs)
            or bool(p.get("custom"))
            or bool(re.match(r"^https?://github\.com/[^/]+/[^/#?]+", p.get("website", "")))
            or (isinstance(p.get("win"), list) and any(isinstance(x, dict) and "github" in x for x in p["win"]))
            or (isinstance(p.get("linux"), list) and any(isinstance(x, dict) and "github" in x for x in p["linux"]))
            or (isinstance(p.get("macos"), list) and any(isinstance(x, dict) and "github" in x for x in p["macos"]))
            or (isinstance(p.get("win"), dict) and "github" in p["win"])
            or (isinstance(p.get("linux"), dict) and "github" in p["linux"])
            or (isinstance(p.get("macos"), dict) and "github" in p["macos"])
        )
        out.append({
            "id": p["id"],
            "name": p["name"],
            "name_tr": p.get("name_tr", p["name"]),
            "category": p["category"],
            "desc": p["desc"],
            "long": p.get("long", p["desc"]),
            "website": p.get("website", ""),
            "icon": icon_file or bool(icon_url),
            "icon_url": icon_url,
            "presets": p.get("presets", []),
            "recommended": p.get("recommended", False),
            "platforms": platforms(p),
            "sources": [s.to_dict() for s in srcs],
            "missing_managers": sorted({s.pm for s in declared if s.pm in possible} - set(managers)) if not srcs else [],
            "status": status,
            "alt": p.get("alt", {}).get(info.os),
            "manual": manual_links(p),
            "custom": bool(p.get("custom")),
            "is_github": is_gh,
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
                 prefer: str = "native", custom_apps: list[dict] | None = None) -> list[Source]:
    p = by_id(custom_apps).get(pkg_id)
    return resolve(p, info, managers, prefer) if p else []
