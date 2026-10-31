"""Common interface every package manager backend implements."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..core import proc
from ..core.system import which


@dataclass(frozen=True)
class Source:
    """One concrete way to get a package on this host."""
    pm: str              # winget | brew | apt | dnf | pacman | zypper | flatpak | snap | url | web
    id: str              # manager-specific identifier, or URL
    kind: str = ""       # brew: "cask" | "formula"; snap: "classic"; url: "portable"

    def label(self) -> str:
        if self.pm == "brew":
            return f"{'cask' if self.kind == 'cask' else 'brew'}:{self.id}"
        if self.pm in ("url", "web"):
            return self.pm
        return f"{self.pm}:{self.id}"

    def to_dict(self) -> dict:
        return {"pm": self.pm, "id": self.id, "kind": self.kind, "label": self.label()}


LineFn = Callable[[str], None]


class PackageManager:
    name = ""
    label = ""
    binary = ""
    needs_root = False      # install requires elevation (whole batch elevated once)
    batch = False           # can install several ids in one command

    def path(self) -> str | None:
        return which(self.binary) if self.binary else None

    def available(self) -> bool:
        return self.path() is not None

    def version(self) -> str:
        p = self.path()
        if not p:
            return ""
        r = proc.run([p, "--version"], timeout=15)
        first = r.out.strip().splitlines()[0] if r.out.strip() else ""
        return first

    # -- queries ---------------------------------------------------------
    def installed(self) -> set[str]:
        """Identifiers (lower-cased) of installed packages."""
        return set()

    def key(self, src: Source) -> str:
        """Normalised key that ``installed()`` returns for ``src``."""
        return src.id.lower()

    # -- actions ---------------------------------------------------------
    def prepare(self, on_line: LineFn, token: proc.CancelToken | None = None) -> None:
        """One-time setup before installs (refresh index, add remotes...)."""

    def install_cmd(self, sources: list[Source]) -> list[str]:
        raise NotImplementedError

    def upgrade_cmd(self, sources: list[Source]) -> list[str] | None:
        return None

    def uninstall_cmd(self, sources: list[Source]) -> list[str] | None:
        return None

    def ok(self, code: int, output: str) -> bool:
        return code == 0

    def install(self, sources: list[Source], on_line: LineFn,
                token: proc.CancelToken | None = None) -> tuple[bool, str]:
        cmd = self.install_cmd(sources)
        env = None
        if self.needs_root:
            env = proc.elevated_env()
            cmd = proc.elevate(cmd)
        on_line(f"$ {proc.join(cmd)}")
        captured: list[str] = []

        def tee(line: str) -> None:
            captured.append(line)
            on_line(line)

        code = proc.stream(cmd, tee, token, env=env)
        out = "\n".join(captured[-80:])
        if self.ok(code, out):
            return True, ""
        if code in (126, 127) and self.needs_root:
            return False, "auth"
        return False, f"exit {code}"
