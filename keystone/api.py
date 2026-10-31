"""The API the interface talks to. Transport-agnostic: exposed to the native
window through pywebview's js_api and to browsers through ``server.py``.

Every public method takes/returns JSON-compatible values.
"""
from __future__ import annotations

import os
import subprocess
import threading
import webbrowser
from pathlib import Path
from typing import Callable

from . import __version__, backup, catalog, tweaks
from .backup import archive
from .core import proc
from .core.system import MACOS, WINDOWS, detect
from .jobs import JobManager
from .pkg.registry import managers_for
from .store import Store


class Api:
    def __init__(self, store: Store | None = None) -> None:
        self.info = detect()
        self.store = store or Store()
        self._installed: dict[str, set[str]] = {}
        self._scan_lock = threading.Lock()
        self._scanning = False
        self.jobs = JobManager(self.info, self._managers, lambda: self.store.settings)
        self.jobs.on_finished.append(self._after_job)
        self.dialogs = None                 # set by the GUI host (pywebview window)

    # -- plumbing ---------------------------------------------------------------
    def _managers(self):
        return managers_for(self.info)

    def subscribe(self, fn: Callable[[dict], None]) -> None:
        self.jobs.subscribe(fn)

    def _after_job(self, job) -> None:
        if job.kind in ("install",) or (job.kind == "restore"):
            self.scan(force=True)
        if job.kind == "tweaks":
            self.jobs.emit({"type": "tweaks"})

    # -- bootstrap --------------------------------------------------------------
    def bootstrap(self) -> dict:
        mgrs = managers_for(self.info, only_available=False)
        return {
            "version": __version__,
            "system": self.info.to_dict(),
            "managers": [{"name": n, "label": m.label, "available": m.available(),
                          "needs_root": m.needs_root} for n, m in mgrs.items()],
            "settings": self.store.settings,
            "profiles": self.store.profiles(),
            "active": self.store.data["active"],
            "categories": catalog.CATEGORIES,
            "presets": catalog.PRESETS,
            "tweak_categories": tweaks.CATEGORIES,
            "backup_dir": str(self.store.backup_dir()),
            "native_dialogs": self.dialogs is not None,
            "can_elevate": self.info.os == WINDOWS and not self.info.is_admin,
        }

    def manager_versions(self) -> dict:
        return {n: m.version() for n, m in self._managers().items()}

    # -- catalogue --------------------------------------------------------------
    def get_catalog(self) -> dict:
        if not self._installed and not self._scanning:
            self.scan()
        return {"packages": catalog.view(self.info, self._managers(), self._installed,
                                         self.store.settings.get("prefer", "native")),
                "scanning": self._scanning}

    def scan(self, force: bool = False) -> dict:
        """Refresh the installed-package cache in the background; emits 'catalog'."""
        with self._scan_lock:
            if self._scanning:
                return {"scanning": True}
            self._scanning = True

        def work() -> None:
            res = {}
            for name, m in self._managers().items():
                try:
                    res[name] = m.installed()
                except Exception:
                    res[name] = set()
            self._installed = res
            self._scanning = False
            self.jobs.emit({"type": "catalog"})

        threading.Thread(target=work, daemon=True).start()
        return {"scanning": True}

    def install(self, ids: list[str], mode: str = "install", dest: str = "") -> dict:
        return self.jobs.install(ids, mode, dest)

    def export_script(self, ids: list[str]) -> dict:
        """Shell / PowerShell script that installs ``ids`` on this OS."""
        mgrs = self._managers()
        prefer = self.store.settings.get("prefer", "native")
        lines: list[str] = []
        groups: dict[tuple[str, str], list[str]] = {}
        for pid in ids:
            srcs = catalog.first_source(pid, self.info, mgrs, prefer)
            if not srcs:
                lines.append(f"# {pid}: not available on this OS")
                continue
            s = srcs[0]
            if s.pm in ("url", "web"):
                lines.append(f"# {pid}: {s.id}")
            else:
                groups.setdefault((s.pm, s.kind), []).append(s.id)
        cmds = []
        for (pm, kind), pkgs in groups.items():
            if pm == "winget":
                cmds += [f"winget install --id {p} --exact --silent --accept-package-agreements --accept-source-agreements"
                         for p in pkgs]
            elif pm == "brew":
                cmds.append(f"brew install {'--cask ' if kind == 'cask' else ''}{' '.join(pkgs)}")
            elif pm == "apt":
                cmds.append(f"sudo apt-get update && sudo apt-get install -y {' '.join(pkgs)}")
            elif pm == "dnf":
                cmds.append(f"sudo dnf install -y {' '.join(pkgs)}")
            elif pm == "pacman":
                cmds.append(f"sudo pacman -Syu --needed --noconfirm {' '.join(pkgs)}")
            elif pm == "zypper":
                cmds.append(f"sudo zypper --non-interactive install {' '.join(pkgs)}")
            elif pm == "flatpak":
                cmds.append("flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo")
                cmds.append(f"flatpak install --user -y flathub {' '.join(pkgs)}")
            elif pm == "snap":
                cmds += [f"sudo snap install {p}" for p in pkgs]
        if self.info.os == WINDOWS:
            text = "# KeyStone install script (PowerShell)\n" + "\n".join(cmds + lines) + "\n"
            ext = ".ps1"
        else:
            text = "#!/bin/sh\n# KeyStone install script\nset -e\n" + "\n".join(cmds + lines) + "\n"
            ext = ".sh"
        return {"text": text, "ext": ext}

    # -- tweaks -----------------------------------------------------------------
    def get_tweaks(self) -> list[dict]:
        b = tweaks.Backends()
        out = []
        for t in tweaks.for_host(self.info):
            try:
                st = t.state(b)
            except Exception:
                st = None
            out.append({**t.meta(), "state": st})
        return out

    def tweaks_run(self, ids: list[str], action: str = "apply") -> dict:
        return self.jobs.tweaks(ids, action)

    # -- backup -----------------------------------------------------------------
    def backup_items(self) -> list[dict]:
        return backup.detect_all(self.info)

    def list_backups(self, folder: str = "") -> list[dict]:
        return archive.list_backups(Path(folder) if folder else self.store.backup_dir())

    def backup_start(self, ids: list[str], folder: str = "", password: str = "") -> dict:
        folder = folder or str(self.store.backup_dir())
        return self.jobs.backup(ids, folder, password or None)

    def restore_plan(self, path: str, password: str = "") -> dict:
        try:
            return {"ok": True, **backup.plan_restore(self.info, Path(path), password or None)}
        except Exception as exc:
            from .backup.crypto import BadPassword
            return {"ok": False, "error": "password" if isinstance(exc, BadPassword) else str(exc)}

    def restore_start(self, path: str, password: str = "", ids: list[str] | None = None) -> dict:
        return self.jobs.restore(path, password or None, ids)

    # -- jobs -------------------------------------------------------------------
    def job_list(self) -> list[dict]:
        return [j.snapshot() for j in self.jobs.jobs.values()]

    def job_log(self, job_id: str) -> list[str]:
        j = self.jobs.jobs.get(job_id)
        return list(j.log) if j else []

    def job_cancel(self, job_id: str) -> bool:
        self.jobs.cancel(job_id)
        return True

    # -- settings & profiles ----------------------------------------------------
    def settings_set(self, values: dict) -> dict:
        s = self.store.set_settings(**values)
        if "prefer" in values:
            self.jobs.emit({"type": "catalog"})
        return s

    def profile_update(self, pid: str, values: dict) -> dict:
        return self.store.update(pid, **values)

    def profile_create(self, name: str, copy_from: str = "") -> dict:
        return self.store.create(name, copy_from or None)

    def profile_activate(self, pid: str) -> dict:
        return self.store.activate(pid)

    def profile_delete(self, pid: str) -> bool:
        self.store.delete(pid)
        return True

    def profile_export(self, pid: str) -> str | None:
        p = self.store.get(pid)
        if not p:
            return None
        name = f"{p['name']}.ksprofile"
        path = self.save_dialog(name)
        if not path:
            return None
        return str(self.store.export(pid, Path(path)))

    def profile_import(self) -> dict | None:
        path = self.open_dialog(["KeyStone profile (*.ksprofile;*.json)"])
        return self.store.import_(Path(path)) if path else None

    # -- host integration -------------------------------------------------------
    def pick_folder(self, start: str = "") -> str | None:
        return self.dialogs.folder(start) if self.dialogs else None

    def open_dialog(self, types: list[str] | None = None) -> str | None:
        return self.dialogs.open(types or []) if self.dialogs else None

    def save_dialog(self, name: str) -> str | None:
        return self.dialogs.save(name) if self.dialogs else None

    def pick_backup(self) -> str | None:
        return self.open_dialog(["KeyStone backup (*.ksbak)"])

    def save_text(self, name: str, text: str) -> str | None:
        path = self.save_dialog(name)
        if not path:
            return None
        Path(path).write_text(text, encoding="utf-8")
        if path.endswith(".sh") and os.name != "nt":
            os.chmod(path, 0o755)
        return path

    def open_path(self, path: str) -> bool:
        p = Path(path)
        target = str(p if p.is_dir() else p.parent)
        if self.info.os == WINDOWS:
            if p.is_file():
                subprocess.Popen(["explorer", "/select,", str(p)])
            else:
                os.startfile(target)  # type: ignore[attr-defined]
        elif self.info.os == MACOS:
            subprocess.Popen(["open", "-R", str(p)] if p.is_file() else ["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return True

    def open_url(self, url: str) -> bool:
        if url.startswith(("https://", "http://")):
            webbrowser.open(url)
            return True
        return False

    def relaunch_admin(self) -> bool:
        if proc.relaunch_as_admin():
            if self.dialogs:
                self.dialogs.close()
            os._exit(0)
        return False

    def quit(self) -> None:
        if self.dialogs:
            self.dialogs.close()
        else:
            os._exit(0)


PUBLIC = [n for n, v in vars(Api).items() if callable(v) and not n.startswith("_")
          and n not in ("subscribe",)]
