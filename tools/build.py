"""Build a standalone KeyStone for the current OS with PyInstaller.

    python tools/build.py            ->  dist/KeyStone.exe | dist/KeyStone.app | dist/keystone
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEP = os.pathsep


def main() -> None:
    os.chdir(ROOT)
    for d in ("build", "dist"):
        shutil.rmtree(d, ignore_errors=True)
    name = "KeyStone" if sys.platform != "linux" else "keystone"
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--name", name,
        "--add-data", f"keystone/ui{SEP}ui",
        "--add-data", f"keystone/data{SEP}data",
        "--collect-submodules", "keystone",
        "--exclude-module", "tkinter",
        "--exclude-module", "PyQt5", "--exclude-module", "PyQt6", "--exclude-module", "PySide6",
    ]
    if sys.platform == "win32":
        args += ["--onefile", "--windowed", "--icon", "keystone/ui/assets/icon.ico",
                 "--hidden-import", "webview.platforms.edgechromium"]
    elif sys.platform == "darwin":
        args += ["--windowed", "--icon", "keystone/ui/assets/icon.icns" if Path("keystone/ui/assets/icon.icns").exists()
                 else "keystone/ui/assets/icon.png",
                 "--osx-bundle-identifier", "dev.furkann.keystone",
                 "--hidden-import", "webview.platforms.cocoa"]
    else:
        args += ["--onefile", "--hidden-import", "webview.platforms.gtk"]
    args += ["--paths", ".", "tools/launcher.py"]
    print("$", " ".join(args))
    subprocess.check_call(args)
    out = ROOT / "dist"
    print("built:", ", ".join(p.name for p in out.iterdir()), f"({platform.system()} {platform.machine()})")


if __name__ == "__main__":
    main()
