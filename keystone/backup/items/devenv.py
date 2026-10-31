"""Git identity and SSH keys; shell and terminal configuration."""
from __future__ import annotations

import os
from pathlib import Path

from ...core.system import WINDOWS, SystemInfo
from ..base import ANY, FAMILY, Ctx, Item, copy_file, restore_file

def _home() -> Path:
    return Path(os.path.expanduser("~"))


class GitSsh(Item):
    id = "git_ssh"
    name = {"tr": "Git ve SSH", "en": "Git & SSH"}
    desc = {"tr": ".gitconfig, global ignore dosyası ve ~/.ssh anahtarları (izinler geri yüklenir).",
            "en": ".gitconfig, global ignore file and ~/.ssh keys (permissions restored)."}
    restore_on = ANY
    sensitive = True

    @staticmethod
    def _files() -> list[Path]:
        out = [p for p in (_home() / ".gitconfig", _home() / ".gitignore_global", _home() / ".config" / "git" / "config",
                           _home() / ".config" / "git" / "ignore") if p.is_file()]
        ssh = _home() / ".ssh"
        if ssh.is_dir():
            out += [p for p in ssh.iterdir() if p.is_file() and not p.name.endswith(".keystone-old")
                    and p.name not in ("agent.sock",)]
        return out

    def detect(self, info):
        files = self._files()
        if not files:
            return None
        keys = sum(1 for p in files if p.parent.name == ".ssh" and p.suffix == ".pub")
        return {"count": len(files), "detail": f"{keys} SSH key", "size": sum(p.stat().st_size for p in files)}

    def backup(self, ctx: Ctx) -> dict:
        files = []
        for p in self._files():
            rel = p.relative_to(_home()).as_posix()
            copy_file(p, ctx.dir / "home" / rel)
            files.append(rel)
        ctx.log(", ".join(files))
        return {"files": files}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        n = 0
        for rel in meta.get("files", []):
            src = ctx.dir / "home" / rel
            if not src.exists():
                continue
            private = rel.startswith(".ssh/") and not rel.endswith((".pub", "known_hosts", "config"))
            if restore_file(src, _home() / rel, private=private):
                n += 1
                ctx.log(f"✓ ~/{rel}")
        if os.name != "nt" and (_home() / ".ssh").is_dir():
            (_home() / ".ssh").chmod(0o700)
        return {"restored": n}


UNIX_SHELL = [".bashrc", ".bash_profile", ".bash_aliases", ".profile", ".zshrc", ".zprofile", ".zshenv",
              ".inputrc", ".tmux.conf", ".vimrc", ".config/fish/config.fish", ".config/fish/functions",
              ".config/starship.toml", ".config/nvim", ".config/alacritty", ".config/kitty",
              ".config/wezterm", ".wezterm.lua", ".config/ghostty", ".oh-my-zsh/custom"]


def _windows_shell_paths() -> list[tuple[str, Path]]:
    docs = _home() / "Documents"
    local = Path(os.environ.get("LOCALAPPDATA", _home() / "AppData" / "Local"))
    return [
        ("powershell7", docs / "PowerShell"),
        ("windowspowershell", docs / "WindowsPowerShell"),
        ("windows-terminal", local / "Packages" / "Microsoft.WindowsTerminal_8wekyb3d8bbwe" / "LocalState" / "settings.json"),
        ("windows-terminal-preview", local / "Packages" / "Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe" / "LocalState" / "settings.json"),
        ("starship", _home() / ".config" / "starship.toml"),
    ]


class Shell(Item):
    id = "shell"
    name = {"tr": "Kabuk ve terminal", "en": "Shell & terminal"}
    desc = {"tr": "Bash/Zsh/Fish ve Neovim, tmux, terminal ayarları ya da PowerShell profilleri ve Windows Terminal.",
            "en": "Bash/Zsh/Fish plus Neovim, tmux and terminal configs — or PowerShell profiles and Windows Terminal."}
    restore_on = FAMILY

    def _entries(self, info: SystemInfo) -> list[tuple[str, Path]]:
        if info.os == WINDOWS:
            return [(k, p) for k, p in _windows_shell_paths() if p.exists()]
        return [(rel, _home() / rel) for rel in UNIX_SHELL if (_home() / rel).exists()]

    def detect(self, info):
        e = self._entries(info)
        if not e:
            return None
        size = 0
        for _, p in e:
            size += p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        return {"count": len(e), "detail": ", ".join(k for k, _ in e[:6]), "size": size}

    def backup(self, ctx: Ctx) -> dict:
        saved = []
        for key, p in self._entries(ctx.info):
            dst = ctx.dir / key.replace("/", "__")
            if p.is_file():
                copy_file(p, dst)
            else:
                for f in p.rglob("*"):
                    if f.is_file() and not f.is_symlink() and f.stat().st_size < 5_000_000:
                        copy_file(f, dst / f.relative_to(p))
            saved.append({"key": key, "dir": p.is_dir()})
        ctx.log(", ".join(s["key"] for s in saved))
        return {"entries": saved}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        targets = dict(_windows_shell_paths()) if ctx.info.os == WINDOWS else {}
        n = 0
        for e in meta.get("entries", []):
            key = e["key"]
            src = ctx.dir / key.replace("/", "__")
            dst = targets.get(key, _home() / key)
            if not src.exists():
                continue
            if e["dir"]:
                for f in src.rglob("*"):
                    if f.is_file():
                        n += restore_file(f, dst / f.relative_to(src))
            else:
                n += restore_file(src, dst)
            ctx.log(f"✓ {key}")
        return {"restored": n}
