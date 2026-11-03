"""Extra backup items: personal folders, game saves, app settings, Windows settings, wallpaper, startup apps."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from ...core import proc
from ...core.system import LINUX, MACOS, WINDOWS, SystemInfo
from ..base import ANY, SAME, Ctx, Item, copy_file, restore_file


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _env(var: str, *parts: str) -> Path:
    return Path(os.environ.get(var, "")).joinpath(*parts) if os.environ.get(var) else Path("\0")


def _scan(p: Path, limit_s: float = 4.0) -> tuple[int, int]:
    """(files, bytes) under ``p`` — gives up after ``limit_s`` so huge folders do not stall the page."""
    if p.is_file():
        return 1, p.stat().st_size
    n = size = 0
    end = time.monotonic() + limit_s
    for f in p.rglob("*"):
        try:
            if f.is_file() and not f.is_symlink():
                n += 1
                size += f.stat().st_size
        except OSError:
            continue
        if time.monotonic() > end:
            break
    return n, size


class TreeItem(Item):
    """Copies folders/files that live under per-OS locations. Subclasses define ``locations``."""
    heavy = False
    skip_dirs: tuple[str, ...] = ()

    def locations(self, info: SystemInfo) -> dict[str, Path]:
        raise NotImplementedError

    def _found(self, info: SystemInfo) -> dict[str, Path]:
        return {k: p for k, p in self.locations(info).items() if p.exists()}

    def _skip(self, p: Path) -> bool:
        return any(part in self.skip_dirs for part in p.parts) or p.name.endswith(".keystone-old")

    def detect(self, info):
        found = self._found(info)
        if not found:
            return None
        n = size = 0
        for p in found.values():
            a, b = _scan(p)
            n, size = n + a, size + b
        if not n:
            return None
        return {"count": n, "detail": ", ".join(found), "size": size}

    def backup(self, ctx: Ctx) -> dict:
        keys = {}
        for key, p in self._found(ctx.info).items():
            ctx.token.check()
            if p.is_file():
                copy_file(p, ctx.dir / key / p.name)
                keys[key] = {"file": p.name, "count": 1}
            else:
                n = skipped = 0
                for f in p.rglob("*"):
                    if f.is_symlink() or not f.is_file() or self._skip(f):
                        continue
                    ctx.token.check()
                    try:
                        copy_file(f, ctx.dir / key / f.relative_to(p))
                        n += 1
                    except OSError:
                        skipped += 1
                if skipped:
                    ctx.log(ctx.t(f"{key}: {skipped} dosya kullanımda, atlandı", f"{key}: skipped {skipped} files in use"))
                keys[key] = {"count": n}
            ctx.log(f"{key}: {keys[key]['count']}")
        return {"keys": keys}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        targets = self.locations(ctx.info)
        restored = 0
        for key, m in meta.get("keys", {}).items():
            ctx.token.check()
            dst = targets.get(key)
            src = ctx.dir / key
            if dst is None or not src.exists():
                ctx.log(ctx.t(f"{key}: bu sistemde karşılığı yok", f"{key}: no equivalent on this system"))
                continue
            if m.get("file"):
                restored += bool(restore_file(src / m["file"], dst))
                continue
            for f in src.rglob("*"):
                if not f.is_file():
                    continue
                d = dst / f.relative_to(src)
                if d.exists() and d.stat().st_size == f.stat().st_size:
                    continue
                restored += bool(restore_file(f, d))
        ctx.log(ctx.t(f"{restored} dosya geri yüklendi", f"{restored} files restored"))
        return {"restored": restored}

    def meta(self, info):
        return {**super().meta(info), "heavy": self.heavy}


# ----------------------------------------------------------------------------- personal data

def _user_dir(name: str) -> Path:
    for base in (_home(), _env("OneDrive"), _env("OneDriveConsumer")):
        p = base / name
        if p.is_dir() and any(p.iterdir()):
            return p
    return _home() / name


class UserFolders(TreeItem):
    id = "user_folders"
    name = {"tr": "Kişisel klasörler", "en": "Personal folders"}
    desc = {"tr": "Masaüstü, Belgeler, Resimler, Müzik ve Videolar. Büyük olabilir; varsayılan olarak seçilmez.",
            "en": "Desktop, Documents, Pictures, Music and Videos. Can be large, so not selected by default."}
    restore_on = ANY
    heavy = True
    skip_dirs = ("node_modules", ".git", "__pycache__")

    def locations(self, info):
        return {n: _user_dir(n) for n in ("Desktop", "Documents", "Pictures", "Music", "Videos")}


class Downloads(TreeItem):
    id = "downloads"
    name = {"tr": "İndirilenler klasörü", "en": "Downloads folder"}
    desc = {"tr": "İndirilenler klasörünün içeriği. Büyük olabilir; varsayılan olarak seçilmez.",
            "en": "Contents of the Downloads folder. Can be large, so not selected by default."}
    restore_on = ANY
    heavy = True

    def locations(self, info):
        return {"Downloads": _user_dir("Downloads")}


class GameSaves(TreeItem):
    id = "game_saves"
    name = {"tr": "Oyun kayıtları", "en": "Game saves"}
    desc = {"tr": "My Games, Saved Games, Rockstar/EA/Paradox kayıtları ve Steam kullanıcı verisi.",
            "en": "My Games, Saved Games, Rockstar/EA/Paradox saves and Steam user data."}
    restore_on = ANY
    skip_dirs = ("htmlcache", "logs", "shadercache")

    def locations(self, info):
        docs = _user_dir("Documents")
        out: dict[str, Path] = {}
        if info.os == WINDOWS:
            out = {"My Games": docs / "My Games", "Saved Games": _home() / "Saved Games",
                   "Rockstar Games": docs / "Rockstar Games", "Electronic Arts": docs / "Electronic Arts",
                   "Paradox Interactive": docs / "Paradox Interactive"}
            steam = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam"
            out["Steam userdata"] = steam / "userdata"
        elif info.os == LINUX:
            out = {"Steam userdata": _home() / ".local" / "share" / "Steam" / "userdata",
                   "My Games": docs / "My Games"}
        else:
            out = {"Steam userdata": _home() / "Library" / "Application Support" / "Steam" / "userdata"}
        return out


# ----------------------------------------------------------------------------- app settings

def _config_root(info: SystemInfo) -> Path:
    if info.os == WINDOWS:
        return _env("APPDATA") if os.environ.get("APPDATA") else _home() / "AppData" / "Roaming"
    if info.os == MACOS:
        return _home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME") or _home() / ".config")


class JetBrains(TreeItem):
    id = "jetbrains"
    name = {"tr": "JetBrains IDE ayarları", "en": "JetBrains IDE settings"}
    desc = {"tr": "IntelliJ, PyCharm, WebStorm, Android Studio vb. için ayarlar, tuş eşlemeleri ve kod stilleri.",
            "en": "Settings, keymaps and code styles for IntelliJ, PyCharm, WebStorm, Android Studio and others."}
    restore_on = ANY
    SUB = ("options", "keymaps", "codestyles", "colors", "templates", "fileTemplates")

    def locations(self, info):
        out = {}
        for vendor in ("JetBrains", "Google"):
            root = _config_root(info) / vendor
            if not root.is_dir():
                continue
            for prod in sorted(root.iterdir()):
                if prod.is_dir() and any((prod / s).is_dir() for s in self.SUB):
                    for s in self.SUB:
                        if (prod / s).is_dir():
                            out[f"{vendor}/{prod.name}/{s}"] = prod / s
        return out

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        # product folders carry a version (PyCharm2025.1); map each backed-up product to the newest installed one
        res = 0
        for key, m in meta.get("keys", {}).items():
            vendor, prod, sub = key.split("/", 2)
            root = _config_root(ctx.info) / vendor
            base = prod
            stem = "".join(c for c in prod if not (c.isdigit() or c == "."))
            if root.is_dir():
                same = sorted((d.name for d in root.iterdir() if d.is_dir()
                               and "".join(c for c in d.name if not (c.isdigit() or c == ".")) == stem))
                if same and prod not in same:
                    base = same[-1]
            src = ctx.dir / key
            for f in src.rglob("*"):
                if f.is_file():
                    res += bool(restore_file(f, root / base / sub / f.relative_to(src)))
        return {"restored": res}


class Obs(TreeItem):
    id = "obs"
    name = {"tr": "OBS Studio", "en": "OBS Studio"}
    desc = {"tr": "OBS profilleri, sahne koleksiyonları ve eklenti ayarları.",
            "en": "OBS profiles, scene collections and plugin settings."}
    restore_on = ANY
    skip_dirs = ("logs", "crashes", "plugin_config")

    def locations(self, info):
        return {"basic": _config_root(info) / "obs-studio" / "basic",
                "global.ini": _config_root(info) / "obs-studio" / "global.ini"}


class WindowsApps(TreeItem):
    id = "app_settings"
    name = {"tr": "Uygulama ayarları", "en": "App settings"}
    desc = {"tr": "PowerToys, Notepad++, VLC, qBittorrent, Windows Terminal ve PowerShell profilleri.",
            "en": "PowerToys, Notepad++, VLC, qBittorrent, Windows Terminal and PowerShell profiles."}
    oses = (WINDOWS,)
    restore_on = SAME
    skip_dirs = ("Logs", "Updates", "Cache", "CrashDumps")

    def locations(self, info):
        local = _env("LOCALAPPDATA")
        roam = _config_root(info)
        docs = _user_dir("Documents")
        return {
            "PowerToys": local / "Microsoft" / "PowerToys",
            "Notepad++": roam / "Notepad++",
            "VLC": roam / "vlc" / "vlcrc",
            "qBittorrent": roam / "qBittorrent",
            "Windows Terminal": local / "Packages" / "Microsoft.WindowsTerminal_8wekyb3d8bbwe" / "LocalState" / "settings.json",
            "PowerShell profile": docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
            "Windows PowerShell profile": docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
        }

    def _skip(self, p: Path) -> bool:
        return super()._skip(p) or p.suffix.lower() in (".log", ".tmp", ".dmp", ".lock") or p.name.endswith("-lock")


class RemoteTools(TreeItem):
    id = "remote_tools"
    name = {"tr": "SSH/FTP istemci oturumları", "en": "SSH/FTP client sessions"}
    desc = {"tr": "WinSCP, FileZilla ve PuTTY kayıtlı oturumları. Parola içerebilir; şifreli yedek önerilir.",
            "en": "Saved sessions of WinSCP, FileZilla and PuTTY. May contain passwords; an encrypted backup is advised."}
    oses = (WINDOWS,)
    restore_on = SAME
    sensitive = True

    PUTTY_KEY = r"HKCU\Software\SimonTatham\PuTTY\Sessions"

    def locations(self, info):
        roam = _config_root(info)
        return {"WinSCP.ini": roam / "WinSCP.ini", "FileZilla": roam / "FileZilla"}

    def detect(self, info):
        base = super().detect(info)
        putty = proc.run(["reg", "query", self.PUTTY_KEY], timeout=15).ok
        if not base and not putty:
            return None
        base = base or {"count": 0, "detail": "", "size": 0}
        if putty:
            base["detail"] = ", ".join(x for x in (base["detail"], "PuTTY") if x)
            base["count"] = (base["count"] or 0) + 1
        return base

    def backup(self, ctx: Ctx) -> dict:
        meta = super().backup(ctx)
        out = ctx.dir / "putty.reg"
        meta["putty"] = proc.run(["reg", "export", self.PUTTY_KEY, str(out), "/y"], timeout=30).ok
        return meta

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        res = super().restore(ctx, meta)
        if meta.get("putty") and (ctx.dir / "putty.reg").exists():
            res["putty"] = proc.run(["reg", "import", str(ctx.dir / "putty.reg")], timeout=30).ok
        return res


class HostsFile(TreeItem):
    id = "hosts"
    name = {"tr": "Hosts dosyası", "en": "Hosts file"}
    desc = {"tr": "Özel alan adı yönlendirmeleri (hosts). Geri yüklemek yönetici izni gerektirir.",
            "en": "Custom hostname overrides (hosts). Restoring needs admin rights."}
    restore_on = ANY

    def locations(self, info):
        if info.os == WINDOWS:
            return {"hosts": Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"}
        return {"hosts": Path("/etc/hosts")}


# ----------------------------------------------------------------------------- Windows registry-based

SETTING_KEYS = [
    r"HKCU\Control Panel\Desktop", r"HKCU\Control Panel\Mouse", r"HKCU\Control Panel\Keyboard",
    r"HKCU\Control Panel\Colors", r"HKCU\Control Panel\Cursors", r"HKCU\Control Panel\International",
    r"HKCU\Control Panel\Accessibility",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\PushNotifications",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", r"HKCU\Software\Microsoft\GameBar",
    r"HKCU\Console",
]


class WindowsSettings(Item):
    id = "windows_settings"
    name = {"tr": "Windows ayarları", "en": "Windows settings"}
    desc = {"tr": "Fare, klavye, renkler, görev çubuğu/Gezgin tercihleri, tema, bildirimler ve konsol ayarları (kayıt defteri).",
            "en": "Mouse, keyboard, colours, taskbar/Explorer preferences, theme, notifications and console settings (registry)."}
    oses = (WINDOWS,)
    restore_on = SAME

    def detect(self, info):
        return {"count": len(SETTING_KEYS), "detail": "", "size": 256 * 1024}

    def backup(self, ctx: Ctx) -> dict:
        done = {}
        for i, key in enumerate(SETTING_KEYS):
            ctx.token.check()
            if proc.run(["reg", "export", key, str(ctx.dir / f"{i}.reg"), "/y"], timeout=60).ok:
                done[str(i)] = key
        ctx.log(ctx.t(f"{len(done)} kayıt defteri anahtarı dışa aktarıldı", f"{len(done)} registry keys exported"))
        return {"keys": done}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        n = 0
        for i, key in meta.get("keys", {}).items():
            ctx.token.check()
            f = ctx.dir / f"{i}.reg"
            if f.exists() and proc.run(["reg", "import", str(f)], timeout=60).ok:
                n += 1
        proc.run(["powershell", "-NoProfile", "-Command",
                  "Stop-Process -Name explorer -Force; Start-Process explorer.exe"], timeout=30)
        return {"restored": n}


class Wallpaper(Item):
    id = "wallpaper"
    name = {"tr": "Masaüstü arka planı", "en": "Desktop wallpaper"}
    desc = {"tr": "Geçerli duvar kağıdı resmi ve yerleşim biçimi.", "en": "The current wallpaper image and its fit style."}
    oses = (WINDOWS,)
    restore_on = SAME

    @staticmethod
    def _current() -> tuple[Path | None, dict]:
        import winreg  # type: ignore
        vals = {}
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as k:
            for n in ("Wallpaper", "WallpaperStyle", "TileWallpaper"):
                try:
                    vals[n] = winreg.QueryValueEx(k, n)[0]
                except OSError:
                    pass
        p = Path(vals.get("Wallpaper") or "")
        if not p.is_file():
            p = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Themes" / "TranscodedWallpaper"
        return (p if p.is_file() else None), vals

    def detect(self, info):
        try:
            p, _ = self._current()
        except Exception:
            return None
        return {"count": 1, "detail": p.name, "size": p.stat().st_size} if p else None

    def backup(self, ctx: Ctx) -> dict:
        p, vals = self._current()
        if not p:
            raise RuntimeError("no wallpaper file")
        ext = p.suffix or ".jpg"
        copy_file(p, ctx.dir / f"wallpaper{ext}")
        return {"file": f"wallpaper{ext}", "style": vals.get("WallpaperStyle", "10"), "tile": vals.get("TileWallpaper", "0")}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        import ctypes
        import winreg  # type: ignore
        dst = _config_root(ctx.info) / "KeyStone" / meta["file"]
        copy_file(ctx.dir / meta["file"], dst)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "WallpaperStyle", 0, winreg.REG_SZ, str(meta.get("style", "10")))
            winreg.SetValueEx(k, "TileWallpaper", 0, winreg.REG_SZ, str(meta.get("tile", "0")))
        ctypes.windll.user32.SystemParametersInfoW(0x14, 0, str(dst), 3)  # type: ignore
        return {"restored": 1}


class StartupApps(Item):
    id = "startup_apps"
    name = {"tr": "Başlangıç programları", "en": "Startup programs"}
    desc = {"tr": "Windows ile birlikte açılan (kullanıcı) programların listesi; eksik olanlar geri eklenir.",
            "en": "The per-user programs that start with Windows; missing ones are added back."}
    oses = (WINDOWS,)
    restore_on = SAME
    KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def _read(self) -> dict:
        import winreg  # type: ignore
        out = {}
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.KEY) as k:
            i = 0
            while True:
                try:
                    n, v, _t = winreg.EnumValue(k, i)
                except OSError:
                    break
                out[n] = v
                i += 1
        return out

    def detect(self, info):
        try:
            d = self._read()
        except Exception:
            return None
        return {"count": len(d), "detail": ", ".join(list(d)[:4]), "size": 2048} if d else None

    def backup(self, ctx: Ctx) -> dict:
        d = self._read()
        (ctx.dir / "run.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"count": len(d)}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        import winreg  # type: ignore
        data = json.loads((ctx.dir / "run.json").read_text(encoding="utf-8"))
        have = self._read()
        n = 0
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.KEY) as k:
            for name, cmd in data.items():
                if name not in have:
                    winreg.SetValueEx(k, name, 0, winreg.REG_SZ, cmd)
                    n += 1
        return {"restored": n}
