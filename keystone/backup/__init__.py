"""Backup / restore orchestration over the individual items."""
from __future__ import annotations

import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..core.proc import Cancelled, CancelToken
from ..core.system import SystemInfo
from . import archive
from .base import Ctx
from .items import BY_ID, ITEMS

Progress = Callable[[str, str, float], None]   # (item_id, state, fraction)


def detect_all(info: SystemInfo) -> list[dict]:
    out = []
    for it in ITEMS:
        m = it.meta(info)
        m["found"] = None
        if it.supported(info):
            try:
                m["found"] = it.detect(info)
            except Exception as exc:
                m["found"] = None
                m["error"] = str(exc)
        out.append(m)
    return out


def _safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-") or "pc"


def backup(info: SystemInfo, item_ids: list[str], folder: Path, password: str | None,
           log: Callable[[str], None], progress: Progress, token: CancelToken, lang: str = "tr") -> dict:
    stage = Path(tempfile.mkdtemp(prefix="keystone-backup-"))
    results: dict[str, dict] = {}
    try:
        for i, iid in enumerate(item_ids):
            item = BY_ID[iid]
            token.check()
            progress(iid, "running", i / max(1, len(item_ids)))
            log(f"── {item.name.get(lang, item.id)}")
            d = stage / iid
            d.mkdir()
            try:
                meta = item.backup(Ctx(d, info, log, token, options={"lang": lang}))
                results[iid] = {"ok": True, **meta}
                progress(iid, "done", (i + 1) / len(item_ids))
            except Cancelled:
                raise
            except Exception as exc:
                shutil.rmtree(d, ignore_errors=True)
                results[iid] = {"ok": False, "error": str(exc)}
                log(f"✗ {item.id}: {exc}")
                progress(iid, "failed", (i + 1) / len(item_ids))
        host = {"os": info.os, "os_name": info.os_name, "hostname": info.hostname, "arch": info.arch,
                "distro": info.distro_id, "desktop": info.desktop}
        archive.write_manifest(stage, host, results)
        name = f"{datetime.now():%Y-%m-%d_%H%M}_{_safe_name(info.hostname)}{archive.EXT}"
        dest = archive.pack(stage, folder / name, password or None)
        log(f"→ {dest}")
        return {"path": str(dest), "size": dest.stat().st_size, "items": results}
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def restore(info: SystemInfo, path: Path, password: str | None, item_ids: list[str] | None,
            log: Callable[[str], None], progress: Progress, token: CancelToken, lang: str = "tr") -> dict:
    data, manifest = archive.unpack(path, password)
    try:
        src = manifest.get("host", {})
        options: dict = {"lang": lang}
        results: dict[str, dict] = {}
        todo = [i for i in manifest.get("items", {}) if (item_ids is None or i in item_ids)]
        for n, iid in enumerate(todo):
            token.check()
            meta = manifest["items"][iid]
            item = BY_ID.get(iid)
            if not item or not meta.get("ok"):
                continue
            if not item.can_restore(info, src.get("os", "")):
                results[iid] = {"ok": False, "skipped": "incompatible"}
                progress(iid, "skipped", (n + 1) / len(todo))
                log(f"↷ {item.name.get(lang)}: {src.get('os')} → {info.os}")
                continue
            progress(iid, "running", n / len(todo))
            log(f"── {item.name.get(lang, iid)}")
            try:
                res = item.restore(Ctx(data / iid, info, log, token, source=src, options=options), meta)
                results[iid] = {"ok": True, **res}
                progress(iid, "done", (n + 1) / len(todo))
            except Cancelled:
                raise
            except Exception as exc:
                results[iid] = {"ok": False, "error": str(exc)}
                log(f"✗ {iid}: {exc}")
                progress(iid, "failed", (n + 1) / len(todo))
        return {"items": results, "followups": options.get("followups", {}), "source": src}
    finally:
        shutil.rmtree(data.parent, ignore_errors=True)


def plan_restore(info: SystemInfo, path: Path, password: str | None) -> dict:
    """What a restore of ``path`` would do on this host (no changes made)."""
    from .. import catalog
    from ..pkg.registry import managers_for
    import json

    data, manifest = archive.unpack(path, password)
    try:
        src_os = manifest.get("host", {}).get("os", "")
        items = []
        for iid, meta in manifest.get("items", {}).items():
            item = BY_ID.get(iid)
            if not item:
                continue
            items.append({**item.meta(info), "backup": meta,
                          "compatible": bool(meta.get("ok")) and item.can_restore(info, src_os)})
        apps = []
        pj = data / "apps" / "packages.json"
        if pj.exists():
            ids = json.loads(pj.read_text(encoding="utf-8")).get("catalog", [])
            apps = catalog.map_for_restore(ids, info, managers_for(info))
        return {"manifest": {k: v for k, v in manifest.items() if k != "items"}, "items": items, "apps": apps}
    finally:
        shutil.rmtree(data.parent, ignore_errors=True)
