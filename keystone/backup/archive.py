"""The .ksbak container: a zip with manifest.json, optionally encrypted."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__
from . import crypto

FORMAT = 2
EXT = ".ksbak"


def write_manifest(stage: Path, host: dict, items: dict) -> dict:
    manifest = {
        "format": FORMAT,
        "app": f"KeyStone {__version__}",
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": host,
        "items": items,
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def pack(stage: Path, dest: Path, password: str | None = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmpzip = tempfile.mkstemp(suffix=".zip", dir=str(dest.parent))
    os.close(fd)
    try:
        with zipfile.ZipFile(tmpzip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(stage).as_posix())
        if password:
            with open(tmpzip, "rb") as src, open(dest, "wb") as dst:
                crypto.encrypt_stream(src, dst, password)
            os.remove(tmpzip)
        else:
            os.replace(tmpzip, dest)
    except BaseException:
        for p in (tmpzip,):
            try:
                os.remove(p)
            except OSError:
                pass
        raise
    return dest


def _safe_extract(zf: zipfile.ZipFile, target: Path) -> None:
    root = target.resolve()
    for info in zf.infolist():
        out = (target / info.filename).resolve()
        if root != out and root not in out.parents:
            raise ValueError(f"unsafe path in archive: {info.filename}")
    zf.extractall(target)


def unpack(src: Path, password: str | None = None) -> tuple[Path, dict]:
    """Extract to a fresh temp dir. Returns (dir, manifest). Caller removes dir."""
    work = Path(tempfile.mkdtemp(prefix="keystone-restore-"))
    try:
        zpath = src
        if crypto.is_encrypted(str(src)):
            if not password:
                raise crypto.BadPassword("password required")
            zpath = work / "_archive.zip"
            with open(src, "rb") as fin, open(zpath, "wb") as fout:
                crypto.decrypt_stream(fin, fout, password)
        with zipfile.ZipFile(zpath) as zf:
            _safe_extract(zf, work / "data")
        if zpath != src:
            os.remove(zpath)
        manifest = json.loads((work / "data" / "manifest.json").read_text(encoding="utf-8"))
        return work / "data", manifest
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def peek(src: Path, password: str | None = None) -> dict:
    """Read just the manifest (decrypting if needed)."""
    if crypto.is_encrypted(str(src)):
        d, m = unpack(src, password)
        shutil.rmtree(d.parent, ignore_errors=True)
        return {**m, "encrypted": True}
    with zipfile.ZipFile(src) as zf:
        m = json.loads(zf.read("manifest.json").decode("utf-8"))
    return {**m, "encrypted": False}


def list_backups(folder: Path) -> list[dict]:
    out = []
    if not folder.is_dir():
        return out
    for p in sorted(folder.glob(f"*{EXT}"), key=lambda x: x.stat().st_mtime, reverse=True):
        entry = {"path": str(p), "name": p.name, "size": p.stat().st_size,
                 "mtime": p.stat().st_mtime, "encrypted": crypto.is_encrypted(str(p))}
        if not entry["encrypted"]:
            try:
                m = peek(p)
                entry["host"] = m.get("host", {})
                entry["items"] = list(m.get("items", {}).keys())
                entry["created"] = m.get("created")
            except Exception:
                entry["broken"] = True
        out.append(entry)
    return out
