"""VS Code family (VS Code, Insiders, VSCodium, Cursor, Windsurf): user settings,
keybindings, snippets and the extension list. Restores across operating systems."""
from __future__ import annotations

import json
import os
from pathlib import Path

from ...core import proc
from ...core.system import LINUX, MACOS, WINDOWS, SystemInfo, which
from ..base import ANY, Ctx, Item, copy_file, restore_file

# id: (label, folder name under the config root, CLI, flatpak config root)
EDITORS = {
    "vscode": ("Visual Studio Code", "Code", "code", "~/.var/app/com.visualstudio.code/config/Code"),
    "insiders": ("VS Code Insiders", "Code - Insiders", "code-insiders", ""),
    "vscodium": ("VSCodium", "VSCodium", "codium", "~/.var/app/com.vscodium.codium/config/VSCodium"),
    "cursor": ("Cursor", "Cursor", "cursor", ""),
    "windsurf": ("Windsurf", "Windsurf", "windsurf", ""),
}
FILES = ["settings.json", "keybindings.json", "tasks.json", "mcp.json"]
DIRS = ["snippets", "prompts"]


def config_root(info: SystemInfo) -> Path:
    if info.os == WINDOWS:
        return Path(os.environ.get("APPDATA", os.path.expanduser("~/AppData/Roaming")))
    if info.os == MACOS:
        return Path(os.path.expanduser("~/Library/Application Support"))
    return Path(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"))


def user_dirs(info: SystemInfo, eid: str) -> list[Path]:
    _label, folder, _cli, flat = EDITORS[eid]
    cands = [config_root(info) / folder / "User"]
    if info.os == LINUX and flat:
        cands.append(Path(os.path.expanduser(flat)) / "User")
    return [c for c in cands if c.is_dir()]


def cli_for(info: SystemInfo, eid: str) -> list[str] | None:
    cli = EDITORS[eid][2]
    found = which(cli)
    if found:
        return [found]
    if info.os == MACOS:
        app = {"vscode": "Visual Studio Code", "insiders": "Visual Studio Code - Insiders",
               "vscodium": "VSCodium", "cursor": "Cursor", "windsurf": "Windsurf"}[eid]
        p = Path(f"/Applications/{app}.app/Contents/Resources/app/bin/{cli}")
        if p.exists():
            return [str(p)]
    if info.os == WINDOWS:
        local = os.environ.get("LOCALAPPDATA", "")
        folder = {"vscode": "Microsoft VS Code", "insiders": "Microsoft VS Code Insiders",
                  "vscodium": "VSCodium", "cursor": "cursor", "windsurf": "Windsurf"}[eid]
        p = Path(local) / "Programs" / folder / "bin" / f"{cli}.cmd"
        if p.exists():
            return [str(p)]
    if info.os == LINUX and eid == "vscode" and which("flatpak"):
        if proc.run(["flatpak", "info", "com.visualstudio.code"], timeout=15).ok:
            return ["flatpak", "run", "com.visualstudio.code"]
    return None


class Editors(Item):
    id = "editors"
    name = {"tr": "Kod editörleri", "en": "Code editors"}
    desc = {"tr": "VS Code, Cursor, VSCodium ve Windsurf ayarları, kısayolları, snippet'leri ve eklenti listesi.",
            "en": "Settings, keybindings, snippets and extensions for VS Code, Cursor, VSCodium and Windsurf."}
    restore_on = ANY

    def detect(self, info):
        found = [EDITORS[e][0] for e in EDITORS if user_dirs(info, e)]
        if not found:
            return None
        size = sum(f.stat().st_size for e in EDITORS for d in user_dirs(info, e)
                   for f in [d / x for x in FILES] if f.exists())
        return {"count": len(found), "detail": ", ".join(found), "size": size}

    def backup(self, ctx: Ctx) -> dict:
        out = {}
        for eid in EDITORS:
            dirs = user_dirs(ctx.info, eid)
            if not dirs:
                continue
            src = dirs[0]
            dst = ctx.dir / eid
            files = []
            for f in FILES:
                if (src / f).is_file():
                    copy_file(src / f, dst / f)
                    files.append(f)
            for d in DIRS:
                if (src / d).is_dir():
                    for p in (src / d).rglob("*"):
                        if p.is_file():
                            copy_file(p, dst / d / p.relative_to(src / d))
                            files.append(f"{d}/{p.relative_to(src / d).as_posix()}")
            exts: list[str] = []
            cli = cli_for(ctx.info, eid)
            if cli:
                r = proc.run([*cli, "--list-extensions"], timeout=120)
                if r.ok:
                    exts = [x.strip() for x in r.out.splitlines() if x.strip() and "." in x and " " not in x.strip()]
            (dst / "extensions.json").parent.mkdir(parents=True, exist_ok=True)
            (dst / "extensions.json").write_text(json.dumps(exts, indent=1), encoding="utf-8")
            out[eid] = {"files": files, "extensions": len(exts)}
            ctx.log(f"{EDITORS[eid][0]}: {len(files)} dosya / files, {len(exts)} eklenti / extensions")
        return {"editors": out}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        res = {}
        for eid, m in meta.get("editors", {}).items():
            if eid not in EDITORS:
                continue
            src = ctx.dir / eid
            target = (user_dirs(ctx.info, eid) or [config_root(ctx.info) / EDITORS[eid][1] / "User"])[0]
            changed = sum(1 for f in m.get("files", []) if (src / f).exists() and restore_file(src / f, target / f))
            installed = 0
            cli = cli_for(ctx.info, eid)
            exts = json.loads((src / "extensions.json").read_text(encoding="utf-8")) if (src / "extensions.json").exists() else []
            if exts and not cli:
                ctx.log(ctx.t(f"{EDITORS[eid][0]} kurulu değil; eklentiler atlandı ({len(exts)})",
                              f"{EDITORS[eid][0]} not installed; skipped {len(exts)} extensions"))
            for ext in exts if cli else []:
                ctx.token.check()
                r = proc.run([*cli, "--install-extension", ext, "--force"], timeout=300)
                if r.ok:
                    installed += 1
                ctx.log(f"{'✓' if r.ok else '✗'} {ext}")
            res[eid] = {"files": changed, "extensions": installed}
        return res
