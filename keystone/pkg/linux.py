"""Linux backends: apt, dnf, pacman, zypper (native, batched, elevated once)
and flatpak / snap (universal)."""
from __future__ import annotations

from ..core import proc
from .base import LineFn, PackageManager, Source

import shlex

proc_quote = shlex.quote

FLATHUB = "https://dl.flathub.org/repo/flathub.flatpakrepo"


class Apt(PackageManager):
    name, label, binary = "apt", "APT", "apt-get"
    needs_root = True
    batch = True

    def installed(self) -> set[str]:
        out = proc.run(["dpkg-query", "-W", "-f=${Package}\t${db:Status-Abbrev}\n"], timeout=60).out
        return {ln.split("\t")[0].lower() for ln in out.splitlines() if "\tii" in ln}

    def install_cmd(self, sources: list[Source]) -> list[str]:
        # Refresh + install in ONE elevated call so the user sees one password prompt.
        ids = " ".join(proc_quote(s.id) for s in sources)
        return ["sh", "-c", "export DEBIAN_FRONTEND=noninteractive; apt-get update -q && "
                f"apt-get install -y -q {ids}"]

    def uninstall_cmd(self, sources):
        return ["apt-get", "remove", "-y", *[s.id for s in sources]]


class Dnf(PackageManager):
    name, label, binary = "dnf", "DNF", "dnf"
    needs_root = True
    batch = True

    def installed(self) -> set[str]:
        out = proc.run(["rpm", "-qa", "--qf", "%{NAME}\n"], timeout=60).out
        return {x.strip().lower() for x in out.splitlines() if x.strip()}

    def install_cmd(self, sources: list[Source]) -> list[str]:
        return ["dnf", "install", "-y", *[s.id for s in sources]]

    def uninstall_cmd(self, sources):
        return ["dnf", "remove", "-y", *[s.id for s in sources]]


class Zypper(Dnf):
    name, label, binary = "zypper", "Zypper", "zypper"

    def install_cmd(self, sources: list[Source]) -> list[str]:
        return ["zypper", "--non-interactive", "install", *[s.id for s in sources]]

    def uninstall_cmd(self, sources):
        return ["zypper", "--non-interactive", "remove", *[s.id for s in sources]]


class Pacman(PackageManager):
    name, label, binary = "pacman", "pacman", "pacman"
    needs_root = True
    batch = True

    def installed(self) -> set[str]:
        return {x.strip().lower() for x in proc.run(["pacman", "-Qq"], timeout=60).out.split()}

    def install_cmd(self, sources: list[Source]) -> list[str]:
        # Arch does not support partial upgrades: sync + upgrade + install together.
        return ["pacman", "-Syu", "--needed", "--noconfirm", *[s.id for s in sources]]

    def uninstall_cmd(self, sources):
        return ["pacman", "-R", "--noconfirm", *[s.id for s in sources]]


class Flatpak(PackageManager):
    """Installs per-user (--user): no root prompt, works on every distro."""
    name, label, binary = "flatpak", "Flatpak", "flatpak"
    batch = True

    def installed(self) -> set[str]:
        out = proc.run(["flatpak", "list", "--app", "--columns=application"], timeout=60).out
        return {x.strip().lower() for x in out.splitlines() if x.strip() and x.strip() != "Application ID"}

    def prepare(self, on_line: LineFn, token=None) -> None:
        cmd = ["flatpak", "remote-add", "--user", "--if-not-exists", "flathub", FLATHUB]
        on_line(f"$ {proc.join(cmd)}")
        proc.stream(cmd, on_line, token)

    def install_cmd(self, sources: list[Source]) -> list[str]:
        return ["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", *[s.id for s in sources]]

    def uninstall_cmd(self, sources):
        return ["flatpak", "uninstall", "--user", "-y", "--noninteractive", *[s.id for s in sources]]


class Snap(PackageManager):
    name, label, binary = "snap", "Snap", "snap"
    needs_root = True

    def installed(self) -> set[str]:
        out = proc.run(["snap", "list"], timeout=60).out.splitlines()[1:]
        return {ln.split()[0].lower() for ln in out if ln.strip()}

    def install_cmd(self, sources: list[Source]) -> list[str]:
        (src,) = sources
        return ["snap", "install", src.id, *(["--classic"] if src.kind == "classic" else [])]

    def uninstall_cmd(self, sources):
        return ["snap", "remove", sources[0].id]
