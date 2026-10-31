"""Entry point.

    keystone                       open the app (native window, or browser fallback)
    keystone --serve [--port N]    browser mode
    keystone info                  show detected system and package managers
    keystone list [--installed]    list catalogue apps available on this OS
    keystone install ID [ID...]    install apps without the GUI
    keystone profile NAME install  install a saved profile's apps
    keystone backup [-o DIR] [--items a,b] [--password]
    keystone restore FILE [--password] [--items a,b]
    keystone tweaks [apply|revert ID...]
"""
from __future__ import annotations

import argparse
import getpass
import sys
import threading

from . import __version__


def _wait(api, snap: dict) -> int:
    """Block until the job (and any follow-up jobs) finish, printing its log."""
    done = threading.Event()
    watching = {snap["id"]}
    failed = False

    def on(ev: dict) -> None:
        nonlocal failed
        if ev["type"] == "log" and ev["job"] in watching:
            print(ev["line"], flush=True)
        elif ev["type"] == "job":
            j = ev["job"]
            if j["state"] in ("queued", "running"):
                watching.add(j["id"])
            elif j["id"] in watching and j["state"] in ("done", "failed", "cancelled"):
                failed |= j["state"] != "done"
                watching.discard(j["id"])
                if not watching:
                    done.set()

    api.subscribe(on)
    try:
        while not done.wait(0.5):
            pass
    except KeyboardInterrupt:
        for j in list(watching):
            api.job_cancel(j)
        done.wait(10)
        return 130
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="keystone", description="KeyStone — set up, tune and migrate any PC.")
    ap.add_argument("--version", action="version", version=f"KeyStone {__version__}")
    ap.add_argument("--serve", action="store_true", help="run in the browser instead of a native window")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--debug", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("info")
    p_list = sub.add_parser("list")
    p_list.add_argument("--installed", action="store_true")
    p_inst = sub.add_parser("install")
    p_inst.add_argument("ids", nargs="+")
    p_prof = sub.add_parser("profile")
    p_prof.add_argument("name")
    p_prof.add_argument("action", choices=["install", "tweaks", "show"])
    p_bak = sub.add_parser("backup")
    p_bak.add_argument("-o", "--output", default="")
    p_bak.add_argument("--items", default="")
    p_bak.add_argument("--password", action="store_true", help="encrypt (asks for a password)")
    p_res = sub.add_parser("restore")
    p_res.add_argument("file")
    p_res.add_argument("--items", default="")
    p_res.add_argument("--password", action="store_true")
    p_res.add_argument("--plan", action="store_true", help="only show what would happen")
    p_tw = sub.add_parser("tweaks")
    p_tw.add_argument("action", nargs="?", choices=["apply", "revert"])
    p_tw.add_argument("ids", nargs="*")
    args = ap.parse_args(argv)

    if args.cmd is None:
        from .api import Api
        if not args.serve:
            from . import app
            if app.available():
                app.run(debug=args.debug)
                return 0
            print("Native window unavailable (pywebview missing) — opening in your browser.", file=sys.stderr)
        from .server import serve
        serve(Api(), args.port, open_browser=not args.no_browser)
        return 0

    from .api import Api
    api = Api()
    if args.cmd == "info":
        s = api.info
        print(f"{s.os_name} ({s.arch}) · {s.hostname} · admin={s.is_admin} · desktop={s.desktop or '-'}")
        for m in api.bootstrap()["managers"]:
            print(f"  {'✓' if m['available'] else '·'} {m['label']}")
        return 0
    if args.cmd == "list":
        import time
        api.scan()
        while api._scanning:
            time.sleep(0.2)
        for p in api.get_catalog()["packages"]:
            if p["status"] in ("installed", "available") and (not args.installed or p["status"] == "installed"):
                src = p["sources"][0]["label"] if p["sources"] else "-"
                print(f"{'●' if p['status'] == 'installed' else '○'} {p['id']:<26} {p['name']:<40} {src}")
        return 0
    if args.cmd == "install":
        return _wait(api, api.install(args.ids))
    if args.cmd == "profile":
        prof = next((p for p in api.store.profiles() if p["name"].lower() == args.name.lower()), None)
        if not prof:
            print(f"profile not found: {args.name}", file=sys.stderr)
            return 2
        if args.action == "show":
            print(prof)
            return 0
        if args.action == "install":
            return _wait(api, api.install(prof["apps"]))
        return _wait(api, api.tweaks_run([t for t in prof["tweaks"]], "apply"))
    if args.cmd == "backup":
        ids = [i for i in args.items.split(",") if i] or [i["id"] for i in api.backup_items()
                                                          if i.get("supported") and i.get("found")]
        pw = getpass.getpass("Backup password: ") if args.password else ""
        return _wait(api, api.backup_start(ids, args.output, pw))
    if args.cmd == "restore":
        pw = getpass.getpass("Backup password: ") if args.password else ""
        if args.plan:
            import json
            print(json.dumps(api.restore_plan(args.file, pw), indent=1, ensure_ascii=False))
            return 0
        ids = [i for i in args.items.split(",") if i] or None
        return _wait(api, api.restore_start(args.file, pw, ids))
    if args.cmd == "tweaks":
        if not args.action:
            for t in api.get_tweaks():
                mark = {True: "●", False: "○", None: "·"}[t["state"]]
                print(f"{mark} {t['id']:<32} {t['name']['en']}")
            return 0
        return _wait(api, api.tweaks_run(args.ids, args.action))
    return 0


if __name__ == "__main__":
    sys.exit(main())
