"""Settings and profiles (selection sets), persisted as one JSON file.

Profiles are portable: app ids are catalogue ids (valid on every OS) and the
tweak list may hold ids for several operating systems — only the ones for the
current OS are shown. Profiles can be exported/imported as .ksprofile files.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .core.paths import config_dir, default_backup_dir

FILE = "keystone.json"
LEGACY_BACKUP_IDS = {"vscode": ["editors"], "dev_environment": ["git_ssh", "shell", "env"],
                     "installed_apps": ["apps"], "winget_manifest": ["apps"], "active_tweaks": ["tweaks"],
                     "browsers": ["browsers"], "wifi": ["wifi"]}
DEFAULT_SETTINGS = {"style": "calm", "theme": "system", "lang": "tr", "prefer": "native", "backup_dir": "", "accent": "",
                    "onboarded": False}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _profile(name: str, **kw) -> dict:
    return {"id": kw.get("id") or f"p_{uuid.uuid4().hex[:8]}", "name": name, "created": kw.get("created", _now()),
            "apps": list(kw.get("apps", [])), "tweaks": list(kw.get("tweaks", [])),
            "backup": list(kw.get("backup", [])), "backup_dir": kw.get("backup_dir", "")}


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_dir() / FILE
        self._lock = threading.RLock()
        self.data: dict[str, Any] = {}
        self.load()

    # -- persistence --------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.data = {}
            self.data.setdefault("settings", {})
            for k, v in DEFAULT_SETTINGS.items():
                self.data["settings"].setdefault(k, v)
            profs = [self._clean(p) for p in self.data.get("profiles", []) if isinstance(p, dict)]
            if not profs:
                legacy = self._legacy()
                profs = legacy or [_profile("Varsayılan", id="p_default")]
            self.data["profiles"] = profs
            if self.data.get("active") not in {p["id"] for p in profs}:
                self.data["active"] = profs[0]["id"]
            self.save()

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)

    @staticmethod
    def _clean(p: dict) -> dict:
        backup: list[str] = []
        for b in p.get("backup", p.get("backups", [])):
            for nb in LEGACY_BACKUP_IDS.get(b, [b]):
                if nb not in backup:
                    backup.append(nb)
        return _profile(str(p.get("name") or "Profil").strip()[:60], id=p.get("id"), created=p.get("created", _now()),
                        apps=[str(x) for x in p.get("apps", [])], tweaks=[str(x) for x in p.get("tweaks", [])],
                        backup=backup, backup_dir=str(p.get("backup_dir", "")))

    def _legacy(self) -> list[dict]:
        """Import profiles from KeyStone 2.x (Windows, %APPDATA%\\Keystone\\profiles.json)."""
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return []
        f = Path(appdata) / "Keystone" / "profiles.json"
        try:
            old = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        self.data["settings"]["theme"] = old.get("theme", "system")
        self.data["settings"]["lang"] = old.get("language", "tr")
        self.data["active"] = old.get("active_profile_id")
        return [self._clean(p) for p in old.get("profiles", []) if isinstance(p, dict)]

    # -- settings -----------------------------------------------------------
    @property
    def settings(self) -> dict:
        return self.data["settings"]

    def set_settings(self, **kw) -> dict:
        with self._lock:
            for k, v in kw.items():
                if k in DEFAULT_SETTINGS:
                    self.settings[k] = v
            self.save()
            return self.settings

    def backup_dir(self) -> Path:
        p = self.active().get("backup_dir") or self.settings.get("backup_dir")
        return Path(p) if p else default_backup_dir()

    # -- profiles -----------------------------------------------------------
    def profiles(self) -> list[dict]:
        return self.data["profiles"]

    def active(self) -> dict:
        return next(p for p in self.profiles() if p["id"] == self.data["active"])

    def get(self, pid: str) -> dict | None:
        return next((p for p in self.profiles() if p["id"] == pid), None)

    def activate(self, pid: str) -> dict:
        with self._lock:
            if not self.get(pid):
                raise KeyError(pid)
            self.data["active"] = pid
            self.save()
            return self.active()

    def create(self, name: str, copy_from: str | None = None) -> dict:
        with self._lock:
            src = self.get(copy_from) if copy_from else None
            p = _profile(name.strip()[:60] or "Profil", **({k: src[k] for k in ("apps", "tweaks", "backup", "backup_dir")} if src else {}))
            self.profiles().append(p)
            self.data["active"] = p["id"]
            self.save()
            return p

    def update(self, pid: str, **kw) -> dict:
        with self._lock:
            p = self.get(pid)
            if not p:
                raise KeyError(pid)
            for k in ("name", "apps", "tweaks", "backup", "backup_dir"):
                if k in kw and kw[k] is not None:
                    p[k] = kw[k] if k != "name" else str(kw[k]).strip()[:60] or p["name"]
            self.save()
            return p

    def delete(self, pid: str) -> None:
        with self._lock:
            if len(self.profiles()) <= 1:
                raise ValueError("last profile")
            self.data["profiles"] = [p for p in self.profiles() if p["id"] != pid]
            if self.data["active"] == pid:
                self.data["active"] = self.profiles()[0]["id"]
            self.save()

    def export(self, pid: str, path: Path) -> Path:
        p = dict(self.get(pid) or {})
        p.pop("id", None)
        path.write_text(json.dumps({"keystone_profile": 1, **p}, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    def import_(self, path: Path) -> dict:
        raw = json.loads(path.read_text(encoding="utf-8"))
        with self._lock:
            p = self._clean({**raw, "id": None})
            self.profiles().append(p)
            self.data["active"] = p["id"]
            self.save()
            return p
