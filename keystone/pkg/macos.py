"""Homebrew backend (formulae and casks)."""
from __future__ import annotations

from ..core import proc
from .base import LineFn, PackageManager, Source

BREW_INSTALL = ('/bin/bash -c "$(curl -fsSL '
                'https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')


class Brew(PackageManager):
    name = "brew"
    label = "Homebrew"
    binary = "brew"
    batch = True

    def version(self) -> str:
        p = self.path()
        if not p:
            return ""
        first = proc.run([p, "--version"], timeout=30).out.strip().splitlines()
        return first[0].replace("Homebrew ", "") if first else ""

    def installed(self) -> set[str]:
        p = self.path()
        if not p:
            return set()
        formulae = proc.run([p, "list", "--formula", "-1"], timeout=90).out.split()
        casks = proc.run([p, "list", "--cask", "-1"], timeout=90).out.split()
        return {f"formula:{x.lower()}" for x in formulae} | {f"cask:{x.lower()}" for x in casks}

    def key(self, src: Source) -> str:
        # "python@3.13" installs as "python@3.13"; taps like "homebrew/cask/x" end in x.
        return f"{'cask' if src.kind == 'cask' else 'formula'}:{src.id.split('/')[-1].lower()}"

    def prepare(self, on_line: LineFn, token: proc.CancelToken | None = None) -> None:
        on_line("$ brew update")
        proc.stream([self.path() or "brew", "update"], on_line, token)

    def install_cmd(self, sources: list[Source]) -> list[str]:
        kinds = {s.kind == "cask" for s in sources}
        assert len(kinds) == 1, "casks and formulae are installed in separate batches"
        is_cask = kinds.pop()
        return [self.path() or "brew", "install", *(["--cask"] if is_cask else []), *[s.id for s in sources]]

    def upgrade_cmd(self, sources: list[Source]) -> list[str]:
        is_cask = sources[0].kind == "cask"
        return [self.path() or "brew", "upgrade", *(["--cask"] if is_cask else []), *[s.id for s in sources]]

    def uninstall_cmd(self, sources: list[Source]) -> list[str]:
        is_cask = sources[0].kind == "cask"
        return [self.path() or "brew", "uninstall", *(["--cask"] if is_cask else []), *[s.id for s in sources]]

    def install(self, sources, on_line, token=None):
        # Some casks run a .pkg installer that calls sudo; give it a GUI askpass.
        cmd = self.install_cmd(sources)
        on_line(f"$ {proc.join(cmd)}")
        captured: list[str] = []

        def tee(line: str) -> None:
            captured.append(line)
            on_line(line)

        code = proc.stream(cmd, tee, token, env=proc.askpass_env())
        out = "\n".join(captured)
        if code == 0 or "already installed" in out.lower():
            return True, ""
        return False, f"exit {code}"
