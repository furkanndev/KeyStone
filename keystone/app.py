"""Native window: pywebview hosts the HTML interface in the OS's own web engine
(WebView2 on Windows, WKWebView on macOS, WebKitGTK/Qt on Linux) — no bundled
browser, a few MB on disk and fast start-up."""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable

from . import APP_NAME, __version__
from .api import PUBLIC, Api
from .core.paths import resource


class Dialogs:
    def __init__(self, window) -> None:
        self.w = window

    def _wv(self):
        import webview  # type: ignore
        return webview

    def folder(self, start: str = "") -> str | None:
        wv = self._wv()
        r = self.w.create_file_dialog(getattr(wv, "FOLDER_DIALOG", 20), directory=start or "")
        return r[0] if r else None

    def open(self, types: list[str]) -> str | None:
        wv = self._wv()
        r = self.w.create_file_dialog(getattr(wv, "OPEN_DIALOG", 10), file_types=tuple(types) or ("All files (*.*)",))
        return r[0] if r else None

    def save(self, name: str) -> str | None:
        wv = self._wv()
        r = self.w.create_file_dialog(getattr(wv, "SAVE_DIALOG", 30), save_filename=name)
        if not r:
            return None
        return r if isinstance(r, str) else r[0]

    def close(self) -> None:
        self.w.destroy()


class Bridge:
    """Object exposed to JavaScript as ``window.pywebview.api``.

    pywebview exposes public attributes recursively, so the Api instance is
    kept private and only the whitelisted methods are forwarded.
    """

    def __init__(self, api: Api) -> None:
        self._api = api

    def call(self, name: str, args: list | None = None):
        if name not in PUBLIC:
            raise ValueError(f"unknown method {name}")
        return json.loads(json.dumps(getattr(self._api, name)(*(args or [])), default=str))


class SplashBridge:
    """Exposed to the welcome window: its buttons call ``proceed``."""

    def __init__(self, event: threading.Event) -> None:
        self._event = event

    def proceed(self) -> None:
        self._event.set()


def startup_steps(api: Api, report: Callable[..., None], skip: threading.Event | None = None,
                  scan_timeout: float = 30.0, pace: float = 0.25) -> dict:
    """Run the real start-up checks, telling the welcome window about each one.

    The scan is waited for up to ``scan_timeout``, or until ``skip`` is set:
    slow package managers finish in the background and the app list updates
    itself afterwards. Returns the summary shown beside the arch.
    """
    s = api.info
    mgrs = api.bootstrap()["managers"]
    found = [m["label"] for m in mgrs if m["available"]]

    report("os", "run")
    time.sleep(pace)
    report("os", "done", f"{s.os_name} · {s.arch}")

    report("managers", "run")
    time.sleep(pace)
    report("managers", "done" if found else "lim", ", ".join(found) or "—")

    report("rights", "run")
    time.sleep(pace)
    report("rights", "done" if s.is_admin else "lim", "admin_yes" if s.is_admin else "admin_no")

    report("catalog", "run")
    api.scan()
    deadline = time.monotonic() + scan_timeout
    while api._scanning and time.monotonic() < deadline and not (skip and skip.is_set()):
        time.sleep(0.1)
    pkgs = api.get_catalog()["packages"]
    fit = sum(p["status"] in ("installed", "available") for p in pkgs)
    report("catalog", "done", "sp_fit", {"fit": fit, "total": len(pkgs)})
    return {"managers": " · ".join(f"pm.{m['name']} {'✓' if m['available'] else '✗'}" for m in mgrs),
            "hidden": len(pkgs) - fit}


def _loading_color(settings: dict) -> str:
    """Window colour before the page paints, so a dark theme does not flash white."""
    theme = settings.get("theme")
    dark = theme == "dark"
    if theme == "system":
        try:
            import winreg  # type: ignore
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                dark = winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
        except (ImportError, OSError):
            pass
    return "#111316" if dark else "#F4F5F7"


def run(debug: bool = False) -> None:
    import webview  # type: ignore

    api = Api()
    bridge = Bridge(api)
    proceed = threading.Event()
    splash = webview.create_window(
        APP_NAME, url=str(resource("ui", "splash.html")), js_api=SplashBridge(proceed), width=1180, height=760,
        resizable=False, background_color=_loading_color(api.store.settings), text_select=False)
    window = webview.create_window(
        APP_NAME, url=str(resource("ui", "index.html")), js_api=bridge, hidden=True,
        width=1280, height=820, min_size=(900, 600), background_color="#F4F5F7", text_select=False)
    api.dialogs = Dialogs(window)

    pending: list[str] = []
    ready = threading.Event()
    lock = threading.Lock()

    def push(ev: dict) -> None:
        js = f"window.KS && window.KS.emit({json.dumps(ev, ensure_ascii=False, default=str)})"
        with lock:
            if not ready.is_set():
                pending.append(js)
                return
        try:
            window.evaluate_js(js)
        except Exception:
            pass

    def on_loaded() -> None:
        with lock:
            ready.set()
            queued, pending[:] = list(pending), []
        for js in queued:
            try:
                window.evaluate_js(js)
            except Exception:
                pass

    opened = threading.Event()

    def on_splash_closed() -> None:
        # Closed by hand: nothing has started yet, and the hidden main window (possibly
        # still loading) and the waiting start-up thread must not keep the process alive.
        if not opened.is_set():
            os._exit(0)

    def startup() -> None:
        def call(fn: str, *args) -> None:
            splash.evaluate_js(f"window.Splash.{fn}({', '.join(json.dumps(a, ensure_ascii=False) for a in args)})")

        def report(step: str, state: str, detail: str = "", values: dict | None = None) -> None:
            call("step", step, state, detail, values or {})

        try:
            s = api.store.settings
            first = not s.get("onboarded")
            call("init", {**{k: s.get(k) for k in ("lang", "style", "theme", "accent")}, "first": first})
            summary = startup_steps(api, report, proceed)
            if not proceed.is_set():
                call("finish", summary)
                # The first run waits for "Panele geç"; later runs only show the result briefly.
                proceed.wait(None if first else 2)
            api.store.set_settings(onboarded=True)
            ready.wait(15)
        except Exception:
            pass
        opened.set()
        window.show()
        splash.destroy()

    api.subscribe(push)
    window.events.loaded += on_loaded
    splash.events.closed += on_splash_closed
    webview.start(startup, debug=debug, private_mode=False, storage_path=None)


def available() -> bool:
    try:
        import webview  # type: ignore  # noqa: F401
        return True
    except Exception:
        return False


__all__ = ["run", "available", "__version__"]
