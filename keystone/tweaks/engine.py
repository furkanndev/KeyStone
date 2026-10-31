"""Declarative tweak engine.

A tweak is a list of *operations*. Each operation knows how to apply itself,
revert itself and (optionally) report whether it is currently in effect.
Platform specifics live in small backends (registry, ``defaults``,
``gsettings``, files, commands) that can be swapped for fakes in tests.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from ..core import proc

DELETE = object()   # revert marker: remove the value / key instead of writing one
RESET = object()    # gsettings: back to schema default


# ----------------------------------------------------------------------------- backends

class RegistryBackend(Protocol):
    def get(self, hive: str, key: str, name: str) -> tuple[bool, Any]: ...
    def set(self, hive: str, key: str, name: str, kind: str, value: Any) -> None: ...
    def delete_value(self, hive: str, key: str, name: str) -> None: ...
    def key_exists(self, hive: str, key: str) -> bool: ...
    def delete_key(self, hive: str, key: str) -> None: ...


class WinRegistry:
    """Real Windows registry via ``winreg`` (imported lazily)."""

    def _w(self):
        import winreg  # type: ignore
        return winreg

    def _root(self, hive: str):
        w = self._w()
        return {"HKCU": w.HKEY_CURRENT_USER, "HKLM": w.HKEY_LOCAL_MACHINE}[hive]

    def get(self, hive, key, name):
        w = self._w()
        try:
            with w.OpenKey(self._root(hive), key, 0, w.KEY_READ) as k:
                return True, w.QueryValueEx(k, name)[0]
        except OSError:
            return False, None

    def set(self, hive, key, name, kind, value):
        w = self._w()
        types = {"DWORD": w.REG_DWORD, "SZ": w.REG_SZ, "EXPAND_SZ": w.REG_EXPAND_SZ, "QWORD": w.REG_QWORD}
        with w.CreateKey(self._root(hive), key) as k:
            w.SetValueEx(k, name, 0, types[kind], value)

    def delete_value(self, hive, key, name):
        w = self._w()
        try:
            with w.OpenKey(self._root(hive), key, 0, w.KEY_SET_VALUE) as k:
                w.DeleteValue(k, name)
        except FileNotFoundError:
            pass

    def key_exists(self, hive, key):
        w = self._w()
        try:
            w.CloseKey(w.OpenKey(self._root(hive), key, 0, w.KEY_READ))
            return True
        except OSError:
            return False

    def delete_key(self, hive, key):
        w = self._w()
        root = self._root(hive)
        try:
            with w.OpenKey(root, key, 0, w.KEY_ALL_ACCESS) as k:
                while True:
                    try:
                        child = w.EnumKey(k, 0)
                    except OSError:
                        break
                    self.delete_key(hive, f"{key}\\{child}")
            w.DeleteKey(root, key)
        except FileNotFoundError:
            pass


@dataclass
class Backends:
    registry: RegistryBackend = field(default_factory=WinRegistry)
    run: Callable[..., proc.Result] = proc.run


# ----------------------------------------------------------------------------- operations

class Op:
    checkable = True

    def apply(self, b: Backends) -> None: ...
    def revert(self, b: Backends) -> None: ...
    def check(self, b: Backends) -> bool | None:
        return None


def _same(a: Any, b: Any) -> bool:
    return str(a).strip().lower() == str(b).strip().lower()


@dataclass
class Reg(Op):
    hive: str
    key: str
    name: str
    value: Any
    kind: str = "DWORD"
    undo: Any = DELETE
    checkable: bool = True

    def apply(self, b):
        b.registry.set(self.hive, self.key, self.name, self.kind, self.value)

    def revert(self, b):
        if self.undo is DELETE:
            b.registry.delete_value(self.hive, self.key, self.name)
        else:
            b.registry.set(self.hive, self.key, self.name, self.kind, self.undo)

    def check(self, b):
        if not self.checkable:
            return None
        exists, val = b.registry.get(self.hive, self.key, self.name)
        return exists and _same(val, self.value)


@dataclass
class RegKey(Op):
    """Create a key with an empty default value; revert deletes the key tree."""
    hive: str
    key: str
    delete_root: str = ""     # key to remove on revert (defaults to ``key``)

    def apply(self, b):
        b.registry.set(self.hive, self.key, "", "SZ", "")

    def revert(self, b):
        b.registry.delete_key(self.hive, self.delete_root or self.key)

    def check(self, b):
        return b.registry.key_exists(self.hive, self.key)


def _ok(r: proc.Result, what: str) -> None:
    if not r.ok:
        raise RuntimeError(f"{what}: {r.out.strip()[:300] or f'exit {r.code}'}")


@dataclass
class Defaults(Op):
    """macOS ``defaults`` value."""
    domain: str
    key: str
    kind: str          # bool | int | float | string
    value: Any
    undo: Any = DELETE

    def _fmt(self, v: Any) -> str:
        if self.kind == "bool":
            return "true" if v else "false"
        return str(v)

    def apply(self, b):
        _ok(b.run(["defaults", "write", self.domain, self.key, f"-{self.kind}", self._fmt(self.value)]), "defaults write")

    def revert(self, b):
        if self.undo is DELETE:
            b.run(["defaults", "delete", self.domain, self.key])
        else:
            _ok(b.run(["defaults", "write", self.domain, self.key, f"-{self.kind}", self._fmt(self.undo)]), "defaults write")

    def check(self, b):
        r = b.run(["defaults", "read", self.domain, self.key])
        if not r.ok:
            return False
        got = r.out.strip()
        if self.kind == "bool":
            return got in ("1", "true", "YES") if self.value else got in ("0", "false", "NO")
        if self.kind in ("int", "float"):
            try:
                return float(got) == float(self.value)
            except ValueError:
                return False
        return got == os.path.expanduser(str(self.value))


@dataclass
class GSettings(Op):
    """GNOME / GTK setting. ``value`` is a GVariant literal ("true", "'prefer-dark'")."""
    schema: str
    key: str
    value: str
    undo: Any = RESET

    def apply(self, b):
        _ok(b.run(["gsettings", "set", self.schema, self.key, self.value]), "gsettings set")

    def revert(self, b):
        if self.undo is RESET:
            b.run(["gsettings", "reset", self.schema, self.key])
        else:
            _ok(b.run(["gsettings", "set", self.schema, self.key, self.undo]), "gsettings set")

    def check(self, b):
        r = b.run(["gsettings", "get", self.schema, self.key])
        return r.ok and r.out.strip() == self.value


@dataclass
class RootFile(Op):
    """A drop-in config file owned by root (sysctl.d, etc.)."""
    path: str
    content: str
    after: list[str] = field(default_factory=list)      # command run (as root) after apply/revert

    def apply(self, b):
        script = f"printf %s {_shq(self.content)} > {_shq(self.path)}"
        if self.after:
            script += " && " + " ".join(_shq(a) for a in self.after)
        _ok(b.run(proc.elevate(["sh", "-c", script]), env=proc.elevated_env(), timeout=300), self.path)

    def revert(self, b):
        script = f"rm -f {_shq(self.path)}"
        if self.after:
            script += " && " + " ".join(_shq(a) for a in self.after)
        _ok(b.run(proc.elevate(["sh", "-c", script]), env=proc.elevated_env(), timeout=300), self.path)

    def check(self, b):
        try:
            with open(self.path, encoding="utf-8") as fh:
                return fh.read() == self.content
        except OSError:
            return False


@dataclass
class Cmd(Op):
    """Arbitrary command(s). ``probe`` returns True/False for the current state."""
    do: list[str]
    undo: list[str] | None = None
    probe: Callable[[Backends], bool] | None = None
    root: bool = False
    timeout: float = 600

    def _exec(self, b, cmd):
        env = None
        if self.root:
            env = proc.elevated_env()
            cmd = proc.elevate(cmd)
        _ok(b.run(cmd, timeout=self.timeout, env=env), cmd[0])

    def apply(self, b):
        self._exec(b, self.do)

    def revert(self, b):
        if self.undo:
            self._exec(b, self.undo)

    def check(self, b):
        return self.probe(b) if self.probe else None


def _shq(s: str) -> str:
    import shlex
    return shlex.quote(s)


def ps(script: str) -> list[str]:
    """PowerShell command line."""
    return ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]


# ----------------------------------------------------------------------------- tweak

@dataclass
class Tweak:
    id: str
    os: str
    category: str
    name: dict
    desc: dict
    ops: list[Op]
    restart: str = ""            # explorer | Finder | Dock | SystemUIServer | ""
    admin: bool = False          # needs elevation (HKLM, root files)
    recommended: bool = False
    action: bool = False         # one-shot action, no on/off state
    requires: str = ""           # e.g. "gnome" (desktop) or a binary name
    risk: str = "low"            # low | medium | high

    def state(self, b: Backends) -> bool | None:
        """True = in effect, False = not, None = unknown/one-shot."""
        if self.action:
            return None
        results = [r for r in (op.check(b) for op in self.ops) if r is not None]
        if not results:
            return None
        return all(results)

    def apply(self, b: Backends) -> None:
        for op in self.ops:
            op.apply(b)

    def revert(self, b: Backends) -> None:
        for op in reversed(self.ops):
            op.revert(b)

    def meta(self) -> dict:
        return {
            "id": self.id, "os": self.os, "category": self.category, "name": self.name,
            "desc": self.desc, "restart": self.restart, "admin": self.admin,
            "recommended": self.recommended, "action": self.action, "requires": self.requires,
            "risk": self.risk,
        }
