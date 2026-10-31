"""Subprocess helpers: streaming output, cancellation and privilege elevation.

All external commands go through ``run`` / ``stream`` so that:
  * no console windows flash on Windows,
  * output is decoded the same way everywhere,
  * a running job can be cancelled (whole process tree),
  * elevation is handled per OS (UAC is the installer's job on Windows,
    pkexec / sudo -A on Linux, an osascript askpass on macOS).
"""
from __future__ import annotations

import os
import re
import shlex
import signal
import stat
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from .system import LINUX, MACOS, WINDOWS, detect, which

IS_WIN = sys.platform.startswith("win")
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\r")


def _popen_kwargs() -> dict:
    if IS_WIN:
        si = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        si.wShowWindow = 0
        return {"startupinfo": si, "creationflags": subprocess.CREATE_NO_WINDOW}  # type: ignore[attr-defined]
    return {"start_new_session": True}


def _env(extra: dict | None = None) -> dict:
    env = os.environ.copy()
    if sys.platform.startswith("linux"):
        env["LC_ALL"] = "C.UTF-8"   # stable, parseable tool output
    env["HOMEBREW_NO_ENV_HINTS"] = "1"
    env["HOMEBREW_NO_AUTO_UPDATE"] = env.get("HOMEBREW_NO_AUTO_UPDATE", "1")
    env["DEBIAN_FRONTEND"] = "noninteractive"
    if sys.platform == "darwin":
        # GUI apps launched from Finder get a minimal PATH.
        path = env.get("PATH", "")
        for p in ("/opt/homebrew/bin", "/usr/local/bin"):
            if p not in path.split(os.pathsep):
                path = p + os.pathsep + path
        env["PATH"] = path
    if extra:
        env.update(extra)
    return env


@dataclass
class Result:
    code: int
    out: str

    @property
    def ok(self) -> bool:
        return self.code == 0


class Cancelled(Exception):
    pass


class CancelToken:
    """Shared between a job and every process it spawns."""

    def __init__(self) -> None:
        self._ev = threading.Event()
        self._procs: set[subprocess.Popen] = set()
        self._lock = threading.Lock()

    def cancel(self) -> None:
        self._ev.set()
        with self._lock:
            for p in list(self._procs):
                kill_tree(p)

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def check(self) -> None:
        if self._ev.is_set():
            raise Cancelled()

    def _track(self, p: subprocess.Popen) -> None:
        with self._lock:
            self._procs.add(p)

    def _untrack(self, p: subprocess.Popen) -> None:
        with self._lock:
            self._procs.discard(p)


def kill_tree(p: subprocess.Popen) -> None:
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           capture_output=True, **_popen_kwargs())
        else:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def run(cmd: Sequence[str], timeout: float | None = 120, env: dict | None = None,
        input: str | None = None, cwd: str | None = None) -> Result:
    """Run a command and capture combined output. Never raises for exit codes."""
    try:
        cp = subprocess.run(list(cmd), capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=timeout, env=_env(env), input=input,
                            cwd=cwd, **_popen_kwargs())
        return Result(cp.returncode, (cp.stdout or "") + (cp.stderr or ""))
    except FileNotFoundError:
        return Result(127, f"command not found: {cmd[0]}")
    except subprocess.TimeoutExpired:
        return Result(124, f"timeout after {timeout}s: {' '.join(cmd)}")
    except Exception as exc:  # pragma: no cover - defensive
        return Result(1, str(exc))


def stream(cmd: Sequence[str], on_line: Callable[[str], None], token: CancelToken | None = None,
           env: dict | None = None, cwd: str | None = None) -> int:
    """Run a command, calling ``on_line`` for each output line. Returns exit code."""
    try:
        p = subprocess.Popen(list(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=_env(env), cwd=cwd, **_popen_kwargs())
    except FileNotFoundError:
        on_line(f"command not found: {cmd[0]}")
        return 127
    if token:
        token._track(p)
    try:
        assert p.stdout is not None
        buf = b""
        while True:
            chunk = p.stdout.read1(4096) if hasattr(p.stdout, "read1") else p.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            # winget/brew draw progress with \r — treat it as a line break too.
            parts = re.split(rb"\r\n|\n|\r", buf)
            buf = parts.pop()
            for raw in parts:
                line = ANSI_RE.sub("", raw.decode("utf-8", errors="replace")).rstrip()
                if line.strip():
                    on_line(line)
        if buf.strip():
            on_line(ANSI_RE.sub("", buf.decode("utf-8", errors="replace")).rstrip())
        code = p.wait()
    finally:
        if token:
            token._untrack(p)
    if token and token.cancelled:
        raise Cancelled()
    return code


# --------------------------------------------------------------------------- elevation

_ASKPASS_MAC = """#!/bin/sh
exec /usr/bin/osascript -e 'text returned of (display dialog "KeyStone needs your password to continue." default answer "" with hidden answer with title "KeyStone" with icon caution buttons {"Cancel","OK"} default button "OK")'
"""


def _askpass_path() -> str | None:
    """Return a SUDO_ASKPASS helper that shows a native password dialog."""
    if sys.platform == "darwin":
        from .paths import cache_dir
        p = Path(cache_dir()) / "askpass.sh"
        if not p.exists() or p.read_text() != _ASKPASS_MAC:
            p.write_text(_ASKPASS_MAC)
            p.chmod(p.stat().st_mode | stat.S_IXUSR)
        return str(p)
    for cand in ("ssh-askpass", "ksshaskpass", "lxqt-openssh-askpass", "x11-ssh-askpass"):
        found = which(cand)
        if found:
            return found
    for cand in ("/usr/lib/ssh/ssh-askpass", "/usr/libexec/openssh/gnome-ssh-askpass",
                 "/usr/lib/openssh/gnome-ssh-askpass", "/usr/bin/ksshaskpass"):
        if os.path.exists(cand):
            return cand
    return None


def askpass_env() -> dict:
    ap = _askpass_path()
    return {"SUDO_ASKPASS": ap} if ap else {}


def elevate(cmd: Sequence[str], env_vars: dict | None = None) -> list[str]:
    """Prefix ``cmd`` so it runs as root on unix. Windows returns it unchanged
    (installers raise their own UAC prompt; KeyStone can also relaunch itself
    elevated via ``relaunch_as_admin``)."""
    info = detect()
    cmd = list(cmd)
    envp = [f"{k}={v}" for k, v in (env_vars or {}).items()]
    if info.os == WINDOWS:
        return cmd
    if info.is_admin:
        return ["env", *envp, *cmd] if envp else cmd
    if info.os == LINUX and which("pkexec") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return ["pkexec", "env", *envp, *cmd] if envp else ["pkexec", *cmd]
    if askpass_env():
        return ["sudo", "-A", *(["env", *envp] if envp else []), *cmd]
    return ["sudo", "-n", *(["env", *envp] if envp else []), *cmd]


def elevated_env() -> dict:
    return askpass_env() if detect().os in (LINUX, MACOS) else {}


def relaunch_as_admin() -> bool:
    """Restart KeyStone elevated (Windows UAC). Returns True if a new process started."""
    if not IS_WIN:
        return False
    import ctypes
    params = " ".join(shlex.quote(a) for a in sys.argv[1:])
    exe = sys.executable
    if not getattr(sys, "frozen", False):
        params = f'-m keystone {params}'
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)  # type: ignore[attr-defined]
    return rc > 32


def join(cmd: Iterable[str]) -> str:
    """Human-readable command line for logs."""
    return subprocess.list2cmdline(list(cmd)) if IS_WIN else shlex.join(list(cmd))
