"""Backup item interface and shared helpers."""
from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..core.proc import CancelToken
from ..core.system import WINDOWS, SystemInfo

ANY, FAMILY, SAME = "any", "family", "same"   # restore compatibility


@dataclass
class Ctx:
    dir: Path                         # this item's folder inside the staging area / extracted backup
    info: SystemInfo                  # current host
    log: Callable[[str], None]
    token: CancelToken
    source: dict = field(default_factory=dict)   # host dict of the machine that made the backup
    options: dict = field(default_factory=dict)

    def t(self, tr: str, en: str) -> str:
        return tr if self.options.get("lang", "tr") == "tr" else en


class Item:
    id = ""
    name: dict = {}
    desc: dict = {}
    oses: tuple[str, ...] = ("windows", "macos", "linux")
    restore_on = ANY
    sensitive = False                 # contains secrets -> encourage encryption

    def supported(self, info: SystemInfo) -> bool:
        return info.os in self.oses

    def detect(self, info: SystemInfo) -> dict | None:
        """What would be backed up here: {"count": int, "size": int, "detail": str} or None."""
        return None

    def backup(self, ctx: Ctx) -> dict:
        raise NotImplementedError

    def can_restore(self, info: SystemInfo, source_os: str) -> bool:
        if self.restore_on == ANY:
            return True
        if self.restore_on == SAME:
            return source_os == info.os
        return (source_os == WINDOWS) == (info.os == WINDOWS)

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        raise NotImplementedError

    def meta(self, info: SystemInfo) -> dict:
        return {"id": self.id, "name": self.name, "desc": self.desc, "oses": list(self.oses),
                "restore_on": self.restore_on, "sensitive": self.sensitive,
                "supported": self.supported(info)}


# ----------------------------------------------------------------------------- helpers

def copy_file(src: Path, dst: Path) -> None:
    """Copy even when the source is locked for writing (browsers, editors)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(src, dst)
    except OSError:
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            shutil.copyfileobj(fi, fo)


def copy_tree(src: Path, dst: Path, skip: Callable[[Path], bool] | None = None) -> int:
    n = 0
    for p in src.rglob("*"):
        if p.is_symlink() or not p.is_file():
            continue
        if skip and skip(p):
            continue
        copy_file(p, dst / p.relative_to(src))
        n += 1
    return n


def restore_file(src: Path, dst: Path, private: bool = False) -> bool:
    """Copy a file into place, keeping any existing different file as *.keystone-old."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if dst.read_bytes() == src.read_bytes():
            return False
        old = dst.with_name(dst.name + ".keystone-old")
        if not old.exists():
            shutil.copy2(dst, old)
    shutil.copy2(src, dst)
    if private and os.name != "nt":
        dst.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return True


def dir_size(p: Path) -> int:
    total = 0
    for f in p.rglob("*"):
        try:
            if f.is_file() and not f.is_symlink():
                total += f.stat().st_size
        except OSError:
            pass
    return total


def env_path(var: str, *parts: str) -> Path:
    return Path(os.environ.get(var, "")).joinpath(*parts)
