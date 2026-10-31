"""Apps list, active tweaks, environment variables, desktop settings, user fonts."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from ... import catalog, tweaks
from ...core import proc
from ...core.system import LINUX, MACOS, WINDOWS, which
from ...pkg.registry import managers_for
from ..base import ANY, FAMILY, SAME, Ctx, Item, copy_file, restore_file

def _home() -> Path:
    return Path(os.path.expanduser("~"))


class Apps(Item):
    """Records catalog apps found on this machine plus the raw package list of
    each manager. Restore maps catalog ids to this OS (with alternatives) —
    the actual installation is queued as an install job by the API."""
    id = "apps"
    name = {"tr": "Kurulu uygulamalar", "en": "Installed apps"}
    desc = {"tr": "Kataloğdaki kurulu uygulamalar ve tüm paket listesi. Başka bir işletim sisteminde karşılıklarıyla kurulur.",
            "en": "Catalogue apps found here plus the full package list. Reinstalled with their equivalents on another OS."}
    restore_on = ANY

    def detect(self, info):
        return {"count": None, "detail": "", "size": 64 * 1024}

    def backup(self, ctx: Ctx) -> dict:
        mgrs = managers_for(ctx.info)
        installed = {}
        for name, m in mgrs.items():
            ctx.token.check()
            ctx.log(ctx.t(f"{m.label} taranıyor…", f"Scanning {m.label}…"))
            installed[name] = sorted(m.installed())
        found = [p["id"] for p in catalog.view(ctx.info, mgrs, {k: set(v) for k, v in installed.items()})
                 if p["status"] == "installed"]
        (ctx.dir / "packages.json").write_text(json.dumps({"catalog": found, "managers": installed},
                                                          ensure_ascii=False, indent=1), encoding="utf-8")
        ctx.log(ctx.t(f"Katalogdan {found.__len__()} uygulama bulundu", f"{len(found)} catalogue apps found"))
        return {"catalog": len(found), "raw": {k: len(v) for k, v in installed.items()}}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        data = json.loads((ctx.dir / "packages.json").read_text(encoding="utf-8"))
        plan = catalog.map_for_restore(data.get("catalog", []), ctx.info, managers_for(ctx.info))
        ctx.options.setdefault("followups", {})["install"] = [p["to"] for p in plan if p["action"] != "skip"]
        return {"plan": plan}


class ActiveTweaks(Item):
    id = "tweaks"
    name = {"tr": "Uygulanan ince ayarlar", "en": "Applied tweaks"}
    desc = {"tr": "Şu an açık olan KeyStone ince ayarları; aynı işletim sisteminde tek tıkla yeniden uygulanır.",
            "en": "KeyStone tweaks currently in effect, re-applied in one go on the same OS."}
    restore_on = SAME

    def detect(self, info):
        return {"count": None, "size": 2048}

    def backup(self, ctx: Ctx) -> dict:
        b = tweaks.Backends()
        active = []
        for t in tweaks.for_host(ctx.info):
            if t.action:
                continue
            try:
                if t.state(b):
                    active.append(t.id)
            except Exception:
                pass
        (ctx.dir / "tweaks.json").write_text(json.dumps(active), encoding="utf-8")
        ctx.log(", ".join(active) or "—")
        return {"count": len(active)}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        ids = json.loads((ctx.dir / "tweaks.json").read_text(encoding="utf-8"))
        ctx.options.setdefault("followups", {})["tweaks"] = ids
        return {"queued": len(ids)}


class EnvVars(Item):
    id = "env"
    name = {"tr": "Ortam değişkenleri", "en": "Environment variables"}
    desc = {"tr": "Kullanıcı ortam değişkenleri ve PATH (Windows). PATH birleştirilir, üzerine yazılmaz.",
            "en": "User environment variables and PATH (Windows). PATH is merged, never overwritten."}
    oses = (WINDOWS,)
    restore_on = SAME

    @staticmethod
    def _read() -> dict:
        import winreg  # type: ignore
        out = {}
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            i = 0
            while True:
                try:
                    name, val, typ = winreg.EnumValue(k, i)
                except OSError:
                    break
                out[name] = {"value": val, "expand": typ == winreg.REG_EXPAND_SZ}
                i += 1
        return out

    def detect(self, info):
        try:
            n = len(self._read())
        except Exception:
            return None
        return {"count": n, "size": 4096} if n else None

    def backup(self, ctx: Ctx) -> dict:
        data = self._read()
        (ctx.dir / "environment.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"count": len(data)}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        import winreg  # type: ignore
        data = json.loads((ctx.dir / "environment.json").read_text(encoding="utf-8"))
        current = self._read()
        n = 0
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as k:
            for name, v in data.items():
                if name.lower() in ("temp", "tmp", "onedrive", "onedriveconsumer"):
                    continue
                val = v["value"]
                if name.lower() == "path" and name in current:
                    have = [p for p in current[name]["value"].split(";") if p]
                    val = ";".join(have + [p for p in val.split(";") if p and p not in have])
                elif name in current:
                    continue
                winreg.SetValueEx(k, name, 0, winreg.REG_EXPAND_SZ if v.get("expand") else winreg.REG_SZ, val)
                n += 1
        import ctypes
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x1A, 0, "Environment", 2, 5000, None)  # type: ignore
        return {"restored": n}


MAC_DOMAINS = ["com.apple.dock", "com.apple.finder", "com.apple.screencapture", "com.apple.AppleMultitouchTrackpad",
               "com.apple.driver.AppleBluetoothMultitouch.trackpad", "com.apple.menuextra.clock", "NSGlobalDomain"]


class Desktop(Item):
    id = "desktop"
    name = {"tr": "Masaüstü ayarları", "en": "Desktop settings"}
    desc = {"tr": "GNOME/Cinnamon/MATE ayarları (dconf) ya da macOS Dock, Finder ve trackpad tercihleri.",
            "en": "GNOME/Cinnamon/MATE settings (dconf), or macOS Dock, Finder and trackpad preferences."}
    oses = (LINUX, MACOS)
    restore_on = SAME

    def detect(self, info):
        if info.os == LINUX:
            return {"count": None, "detail": "dconf", "size": 64 * 1024} if which("dconf") else None
        return {"count": len(MAC_DOMAINS), "detail": "Dock, Finder", "size": 64 * 1024}

    def backup(self, ctx: Ctx) -> dict:
        if ctx.info.os == LINUX:
            r = proc.run(["dconf", "dump", "/"], timeout=60)
            (ctx.dir / "dconf.ini").write_text(r.out, encoding="utf-8")
            return {"desktop": ctx.info.desktop, "lines": r.out.count("\n")}
        saved = []
        for d in MAC_DOMAINS:
            if proc.run(["defaults", "export", d, str(ctx.dir / f"{d}.plist")], timeout=30).ok:
                saved.append(d)
        return {"domains": saved}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        if ctx.info.os == LINUX:
            data = (ctx.dir / "dconf.ini").read_text(encoding="utf-8")
            r = proc.run(["dconf", "load", "/"], input=data, timeout=60)
            return {"ok": r.ok}
        n = 0
        for d in meta.get("domains", []):
            if proc.run(["defaults", "import", d, str(ctx.dir / f"{d}.plist")], timeout=30).ok:
                n += 1
        proc.run(["killall", "Dock"], timeout=10)
        proc.run(["killall", "Finder"], timeout=10)
        return {"restored": n}


FONT_EXT = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}


def font_dir(os_: str) -> Path:
    if os_ == WINDOWS:
        return Path(os.environ.get("LOCALAPPDATA", _home() / "AppData" / "Local")) / "Microsoft" / "Windows" / "Fonts"
    if os_ == MACOS:
        return _home() / "Library" / "Fonts"
    return Path(os.environ.get("XDG_DATA_HOME") or _home() / ".local" / "share") / "fonts"


class Fonts(Item):
    id = "fonts"
    name = {"tr": "Kullanıcı yazı tipleri", "en": "User fonts"}
    desc = {"tr": "Kendi kurduğunuz yazı tipleri; her işletim sistemine kurulabilir.",
            "en": "Fonts you installed yourself — installable on any OS."}
    restore_on = ANY

    def _fonts(self, os_: str) -> list[Path]:
        d = font_dir(os_)
        return [p for p in d.rglob("*") if p.suffix.lower() in FONT_EXT and p.is_file()] if d.is_dir() else []

    def detect(self, info):
        f = self._fonts(info.os)
        return {"count": len(f), "size": sum(p.stat().st_size for p in f)} if f else None

    def backup(self, ctx: Ctx) -> dict:
        files = self._fonts(ctx.info.os)
        for p in files:
            copy_file(p, ctx.dir / p.name)
        return {"count": len(files)}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        dst = font_dir(ctx.info.os)
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for p in ctx.dir.iterdir():
            if p.suffix.lower() not in FONT_EXT or (dst / p.name).exists():
                continue
            shutil.copy2(p, dst / p.name)
            n += 1
            if ctx.info.os == WINDOWS:
                import winreg  # type: ignore
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as k:
                    winreg.SetValueEx(k, f"{p.stem} (TrueType)", 0, winreg.REG_SZ, str(dst / p.name))
        if ctx.info.os == LINUX and which("fc-cache"):
            proc.run(["fc-cache", "-f"], timeout=120)
        ctx.log(ctx.t(f"{n} yazı tipi kuruldu", f"{n} fonts installed"))
        return {"restored": n}
