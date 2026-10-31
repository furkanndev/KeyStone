"""Background jobs (install, tweaks, backup, restore) with an event stream.

One job runs at a time — package managers lock their databases and parallel
installs only produce confusing failures. Every state change is published as
an event dict to the subscribers (the GUI bridge or the HTTP/SSE server).
"""
from __future__ import annotations

import os
import threading
import time
import traceback
import urllib.request
import uuid
import webbrowser
from collections import deque
from pathlib import Path
from typing import Callable

from . import backup as backup_mod
from . import catalog, tweaks
from .core import proc
from .core.paths import home
from .core.system import SystemInfo
from .pkg.base import PackageManager, Source

Emit = Callable[[dict], None]


class Job:
    def __init__(self, kind: str, title: str, items: list[dict]) -> None:
        self.id = uuid.uuid4().hex[:10]
        self.kind = kind
        self.title = title
        self.items = {i["id"]: {**i, "state": "queued", "note": ""} for i in items}
        self.order = [i["id"] for i in items]
        self.state = "queued"           # queued | running | done | failed | cancelled
        self.progress = 0.0
        self.result: dict = {}
        self.error = ""
        self.started = 0.0
        self.ended = 0.0
        self.token = proc.CancelToken()
        self.log: deque[str] = deque(maxlen=4000)

    def snapshot(self) -> dict:
        return {"id": self.id, "kind": self.kind, "title": self.title, "state": self.state,
                "progress": round(self.progress, 4), "items": [self.items[i] for i in self.order],
                "result": self.result, "error": self.error, "started": self.started, "ended": self.ended}


class JobManager:
    def __init__(self, info: SystemInfo, managers_fn: Callable[[], dict[str, PackageManager]],
                 settings_fn: Callable[[], dict]) -> None:
        self.info = info
        self.managers_fn = managers_fn
        self.settings_fn = settings_fn
        self.jobs: dict[str, Job] = {}
        self._subs: list[Emit] = []
        self._queue: deque[tuple[Job, Callable[[Job], None]]] = deque()
        self._lock = threading.Lock()
        self._busy = False
        self.on_finished: list[Callable[[Job], None]] = []

    # -- events ---------------------------------------------------------------
    def subscribe(self, fn: Emit) -> None:
        self._subs.append(fn)

    def unsubscribe(self, fn: Emit) -> None:
        if fn in self._subs:
            self._subs.remove(fn)

    def emit(self, ev: dict) -> None:
        for fn in list(self._subs):
            try:
                fn(ev)
            except Exception:
                pass

    def _job_changed(self, job: Job) -> None:
        self.emit({"type": "job", "job": job.snapshot()})

    def _line(self, job: Job, line: str) -> None:
        job.log.append(line)
        self.emit({"type": "log", "job": job.id, "line": line})

    def _item(self, job: Job, iid: str, state: str, note: str = "") -> None:
        it = job.items.get(iid)
        if it is None:
            return
        it["state"], it["note"] = state, note
        done = sum(1 for x in job.items.values() if x["state"] in ("done", "failed", "skipped"))
        job.progress = done / max(1, len(job.items))
        self._job_changed(job)

    # -- queue ----------------------------------------------------------------
    def submit(self, job: Job, fn: Callable[[Job], None]) -> dict:
        self.jobs[job.id] = job
        with self._lock:
            self._queue.append((job, fn))
            start = not self._busy
            self._busy = True
        self._job_changed(job)
        if start:
            threading.Thread(target=self._worker, daemon=True, name="keystone-jobs").start()
        return job.snapshot()

    def _worker(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    self._busy = False
                    return
                job, fn = self._queue.popleft()
            if job.token.cancelled:
                job.state = "cancelled"
                self._job_changed(job)
                continue
            job.state, job.started = "running", time.time()
            self._job_changed(job)
            try:
                fn(job)
                if job.state == "running":
                    failed = any(i["state"] == "failed" for i in job.items.values())
                    job.state = "failed" if failed and not any(i["state"] == "done" for i in job.items.values()) else "done"
            except proc.Cancelled:
                job.state = "cancelled"
                for it in job.items.values():
                    if it["state"] in ("queued", "running"):
                        it["state"] = "skipped"
                self._line(job, "■ cancelled")
            except Exception as exc:
                job.state, job.error = "failed", str(exc)
                self._line(job, "✗ " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
            job.ended = time.time()
            job.progress = 1.0 if job.state == "done" else job.progress
            self._job_changed(job)
            for cb in self.on_finished:
                try:
                    cb(job)
                except Exception:
                    pass

    def cancel(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if job:
            job.token.cancel()

    # =========================================================================
    # Install
    # =========================================================================
    def install(self, pkg_ids: list[str], mode: str = "install", dest: str = "") -> dict:
        cat = catalog.by_id()
        items = [{"id": p, "name": cat[p]["name"]} for p in pkg_ids if p in cat]
        title = {"install": "install", "download": "download", "upgrade": "upgrade", "uninstall": "uninstall"}[mode]
        job = Job("install", title, items)
        return self.submit(job, lambda j: self._run_install(j, mode, dest))

    def _run_install(self, job: Job, mode: str, dest: str) -> None:
        mgrs = self.managers_fn()
        prefer = self.settings_fn().get("prefer", "native")
        plan: dict[str, list[Source]] = {}
        for pid in job.order:
            srcs = catalog.first_source(pid, self.info, mgrs, prefer)
            if not srcs:
                self._item(job, pid, "skipped", "unsupported")
            plan[pid] = srcs
        prepared: set[str] = set()
        before = {}

        def installed_now(pm: str) -> set[str]:
            return mgrs[pm].installed() if pm in mgrs else set()

        # Batchable groups (apt/dnf/pacman/zypper/flatpak/brew): one command per
        # (manager, kind) using each package's preferred source; per-package
        # fallback afterwards for whatever did not land.
        pending = [p for p in job.order if plan[p]]
        if mode in ("install", "upgrade", "uninstall"):
            groups: dict[tuple[str, str], list[str]] = {}
            for pid in pending:
                s = plan[pid][0]
                m = mgrs.get(s.pm)
                if m and m.batch:
                    groups.setdefault((s.pm, s.kind), []).append(pid)
            for (pm, kind), pids in groups.items():
                job.token.check()
                m = mgrs[pm]
                if pm not in prepared and mode == "install":
                    m.prepare(lambda ln: self._line(job, ln), job.token)
                    prepared.add(pm)
                if pm not in before:
                    before[pm] = installed_now(pm)
                for pid in pids:
                    self._item(job, pid, "running")
                srcs = [plan[p][0] for p in pids]
                self._line(job, f"▶ {m.label}: {', '.join(s.id for s in srcs)}")
                if mode == "install":
                    ok, why = m.install(srcs, lambda ln: self._line(job, ln), job.token)
                else:
                    cmd = (m.upgrade_cmd if mode == "upgrade" else m.uninstall_cmd)(srcs)
                    if not cmd:
                        continue
                    if m.needs_root:
                        cmd = proc.elevate(cmd)
                    self._line(job, f"$ {proc.join(cmd)}")
                    ok = proc.stream(cmd, lambda ln: self._line(job, ln), job.token,
                                     env=proc.elevated_env() if m.needs_root else None) == 0
                    why = ""
                now = installed_now(pm)
                for pid, s in zip(pids, srcs):
                    present = m.key(s) in now
                    good = (not present) if mode == "uninstall" else present or (ok and mode == "upgrade")
                    if good:
                        self._item(job, pid, "done", s.label())
                        pending.remove(pid)
                    elif why == "auth":
                        self._item(job, pid, "failed", "auth")
                        pending.remove(pid)
                    else:
                        plan[pid] = plan[pid][1:]      # try the next source below
                        if not plan[pid]:
                            self._item(job, pid, "failed", why or "error")
                            pending.remove(pid)

        # Per-package path: winget, url, web, snap, and fallbacks.
        for pid in list(pending):
            job.token.check()
            self._item(job, pid, "running")
            ok, note = False, ""
            for s in plan[pid]:
                job.token.check()
                ok, note = self._one(job, pid, s, mode, dest, mgrs)
                if ok:
                    break
                self._line(job, f"↻ {pid}: {s.label()} → next")
            self._item(job, pid, "done" if ok else "failed", note)

    def _one(self, job: Job, pid: str, s: Source, mode: str, dest: str,
             mgrs: dict[str, PackageManager]) -> tuple[bool, str]:
        log = lambda ln: self._line(job, ln)  # noqa: E731
        if s.pm == "web":
            webbrowser.open(s.id)
            log(f"↗ {s.id}")
            return True, "web"
        if s.pm == "url":
            return self._download_url(job, s.id, dest or str(home() / "Downloads" / "KeyStone"))
        m = mgrs.get(s.pm)
        if not m:
            return False, "no-manager"
        if mode == "download":
            if hasattr(m, "download_cmd"):
                target = dest or str(home() / "Downloads" / "KeyStone")
                os.makedirs(target, exist_ok=True)
                cmd = m.download_cmd(s, target)  # type: ignore[attr-defined]
                log(f"$ {proc.join(cmd)}")
                code = proc.stream(cmd, log, job.token)
                for y in Path(target).glob("*.yaml"):
                    y.unlink(missing_ok=True)
                return m.ok(code, ""), s.label()
            return False, "download-unsupported"
        if mode == "install":
            ok, why = m.install([s], log, job.token)
            return ok, s.label() if ok else why
        cmd = (m.upgrade_cmd if mode == "upgrade" else m.uninstall_cmd)([s])
        if not cmd:
            return False, "unsupported"
        if m.needs_root:
            cmd = proc.elevate(cmd)
        log(f"$ {proc.join(cmd)}")
        code = proc.stream(cmd, log, job.token, env=proc.elevated_env() if m.needs_root else None)
        return m.ok(code, ""), s.label()

    def _download_url(self, job: Job, url: str, dest: str) -> tuple[bool, str]:
        os.makedirs(dest, exist_ok=True)
        name = url.rstrip("/").split("/")[-1].split("?")[0] or "download.bin"
        target = Path(dest) / name
        self._line(job, f"↓ {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "KeyStone"})
        with urllib.request.urlopen(req, timeout=60) as r, open(target, "wb") as fh:
            total = int(r.headers.get("Content-Length") or 0)
            got, last = 0, -1
            while True:
                job.token.check()
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                fh.write(chunk)
                got += len(chunk)
                if total:
                    pct = int(got * 100 / total)
                    if pct // 10 != last:
                        last = pct // 10
                        self._line(job, f"  {pct}%")
        self._line(job, f"→ {target}")
        return True, str(target)

    # =========================================================================
    # Tweaks
    # =========================================================================
    def tweaks(self, ids: list[str], action: str) -> dict:
        reg = tweaks.by_id(self.info)
        items = [{"id": t, "name": reg[t].name} for t in ids if t in reg]
        job = Job("tweaks", action, items)
        return self.submit(job, lambda j: self._run_tweaks(j, action))

    def _run_tweaks(self, job: Job, action: str) -> None:
        reg = tweaks.by_id(self.info)
        b = tweaks.Backends()
        restarts: set[str] = set()
        lang = self.settings_fn().get("lang", "tr")
        for tid in job.order:
            job.token.check()
            t = reg[tid]
            self._item(job, tid, "running")
            try:
                (t.apply if action == "apply" else t.revert)(b)
                if t.restart:
                    restarts.add(t.restart)
                self._item(job, tid, "done")
                self._line(job, f"✓ {t.name.get(lang)}")
            except PermissionError:
                self._item(job, tid, "failed", "admin")
                self._line(job, f"✗ {t.name.get(lang)}: admin")
            except Exception as exc:
                self._item(job, tid, "failed", str(exc)[:200])
                self._line(job, f"✗ {t.name.get(lang)}: {exc}")
        for r in restarts:
            self._line(job, f"↻ {r}")
            tweaks.restart_shell(self.info, r)

    # =========================================================================
    # Backup / restore
    # =========================================================================
    def backup(self, item_ids: list[str], folder: str, password: str | None) -> dict:
        from .backup.items import BY_ID
        items = [{"id": i, "name": BY_ID[i].name} for i in item_ids if i in BY_ID]
        job = Job("backup", "backup", items)

        def run(j: Job) -> None:
            lang = self.settings_fn().get("lang", "tr")
            j.result = backup_mod.backup(self.info, [i["id"] for i in items], Path(folder), password,
                                         lambda ln: self._line(j, ln),
                                         lambda iid, st, _f: self._item(j, iid, st), j.token, lang)
        return self.submit(job, run)

    def restore(self, path: str, password: str | None, item_ids: list[str] | None) -> dict:
        from .backup.items import BY_ID
        ids = item_ids or list(BY_ID)
        items = [{"id": i, "name": BY_ID[i].name} for i in ids if i in BY_ID]
        job = Job("restore", "restore", items)

        def run(j: Job) -> None:
            lang = self.settings_fn().get("lang", "tr")
            res = backup_mod.restore(self.info, Path(path), password, ids,
                                     lambda ln: self._line(j, ln),
                                     lambda iid, st, _f: self._item(j, iid, st), j.token, lang)
            for it in j.items.values():
                if it["state"] == "queued":
                    it["state"] = "skipped"
            j.result = res
            fu = res.get("followups", {})
            if fu.get("tweaks"):
                self.tweaks([t for t in fu["tweaks"] if t in tweaks.by_id(self.info)], "apply")
            if fu.get("install"):
                self.install(fu["install"], "install")
        return self.submit(job, run)
