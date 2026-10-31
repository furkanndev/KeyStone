"""Per-OS locations for KeyStone's own data and for well-known user folders."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .. import APP_NAME


def home() -> Path:
    return Path(os.path.expanduser("~"))


def config_dir() -> Path:
    """Where profiles and settings live.

    A ``keystone-data`` folder next to the executable switches to portable
    mode, which is handy when running KeyStone from a USB stick before a format.
    """
    exe_dir = Path(sys.argv[0]).resolve().parent if sys.argv and sys.argv[0] else Path.cwd()
    portable = exe_dir / "keystone-data"
    if portable.is_dir():
        return portable
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or home() / "AppData" / "Roaming")
        d = base / APP_NAME
    elif sys.platform == "darwin":
        d = home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or home() / ".config")
        d = base / APP_NAME.lower()
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    if sys.platform.startswith("win"):
        d = Path(os.environ.get("LOCALAPPDATA") or home()) / APP_NAME / "cache"
    elif sys.platform == "darwin":
        d = home() / "Library" / "Caches" / APP_NAME
    else:
        d = Path(os.environ.get("XDG_CACHE_HOME") or home() / ".cache") / APP_NAME.lower()
    d.mkdir(parents=True, exist_ok=True)
    return d


def desktop_dir() -> Path:
    if sys.platform.startswith("linux"):
        try:
            import subprocess
            out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=3)
            p = Path(out.stdout.strip())
            if out.returncode == 0 and p.is_dir():
                return p
        except Exception:
            pass
    d = home() / "Desktop"
    return d if d.is_dir() else home()


def default_backup_dir() -> Path:
    return home() / f"{APP_NAME}-Backups"


def resource(*parts: str) -> Path:
    """Path to a bundled resource, both from source and from a PyInstaller build."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)
