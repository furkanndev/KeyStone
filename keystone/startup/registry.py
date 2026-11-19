"""Registry access for the start-up tools, behind an injectable backend so the
write paths can be tested on any OS.
"""
from __future__ import annotations

from typing import Any, Protocol


class NeedsAdmin(Exception):
    pass


class StartupRegistry(Protocol):
    def values(self, hive: str, key: str) -> list[tuple[str, str]]: ...
    def subkeys(self, hive: str, key: str) -> list[str]: ...
    def get_value(self, hive: str, key: str, name: str) -> Any: ...
    def get_binary(self, hive: str, key: str, name: str) -> bytes | None: ...
    def set_binary(self, hive: str, key: str, name: str, data: bytes) -> None: ...
    def set_string(self, hive: str, key: str, name: str, value: str) -> None: ...
    def delete_value(self, hive: str, key: str, name: str) -> None: ...


class WinStartupRegistry:
    """Real registry. Always the 64-bit view; 32-bit entries use the explicit WOW6432Node path."""

    def _w(self):
        import winreg  # type: ignore
        return winreg

    def _root(self, hive: str):
        w = self._w()
        return {"HKCU": w.HKEY_CURRENT_USER, "HKLM": w.HKEY_LOCAL_MACHINE}[hive]

    def _open(self, hive: str, key: str, access: int):
        w = self._w()
        return w.OpenKey(self._root(hive), key, 0, access | w.KEY_WOW64_64KEY)

    def values(self, hive, key):
        """String values only (REG_SZ / REG_EXPAND_SZ) as (name, data)."""
        w = self._w()
        out: list[tuple[str, str]] = []
        try:
            with self._open(hive, key, w.KEY_READ) as k:
                i = 0
                while True:
                    try:
                        name, data, kind = w.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    if kind in (w.REG_SZ, w.REG_EXPAND_SZ):
                        out.append((name, str(data)))
        except OSError:
            pass
        return out

    def subkeys(self, hive, key):
        w = self._w()
        out: list[str] = []
        try:
            with self._open(hive, key, w.KEY_READ) as k:
                i = 0
                while True:
                    try:
                        out.append(w.EnumKey(k, i))
                    except OSError:
                        break
                    i += 1
        except OSError:
            pass
        return out

    def get_value(self, hive, key, name):
        """Typed read: str, int (DWORD), list[str] (MULTI_SZ) or bytes; None when missing."""
        w = self._w()
        try:
            with self._open(hive, key, w.KEY_READ) as k:
                return w.QueryValueEx(k, name)[0]
        except OSError:
            return None

    def get_binary(self, hive, key, name):
        w = self._w()
        try:
            with self._open(hive, key, w.KEY_READ) as k:
                data, kind = w.QueryValueEx(k, name)
                return bytes(data) if kind == w.REG_BINARY else None
        except OSError:
            return None

    def _set(self, hive, key, name, kind, data):
        w = self._w()
        try:
            with w.CreateKeyEx(self._root(hive), key, 0, w.KEY_SET_VALUE | w.KEY_WOW64_64KEY) as k:
                w.SetValueEx(k, name, 0, kind, data)
        except PermissionError as exc:
            raise NeedsAdmin(str(exc)) from exc

    def set_binary(self, hive, key, name, data):
        self._set(hive, key, name, self._w().REG_BINARY, data)

    def set_string(self, hive, key, name, value):
        self._set(hive, key, name, self._w().REG_SZ, value)

    def delete_value(self, hive, key, name):
        w = self._w()
        try:
            with self._open(hive, key, w.KEY_SET_VALUE) as k:
                w.DeleteValue(k, name)
        except FileNotFoundError:
            pass
        except PermissionError as exc:
            raise NeedsAdmin(str(exc)) from exc
