"""Browser bookmarks: Chromium family (raw JSON per profile) + Firefox (places
database rendered to HTML). Every backup also includes one merged
Netscape-format HTML file that any browser on any OS can import."""
from __future__ import annotations

import html
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from ...core import paths
from ...core.system import LINUX, MACOS, WINDOWS, SystemInfo
from ..base import ANY, Ctx, Item, copy_file, restore_file

CHROMIUM = {
    # id: (label, {os: [user-data dirs relative to a base]})
    "chrome": ("Google Chrome", {WINDOWS: ["%L/Google/Chrome/User Data"], MACOS: ["~/Library/Application Support/Google/Chrome"],
                                 LINUX: ["~/.config/google-chrome", "~/.var/app/com.google.Chrome/config/google-chrome"]}),
    "chromium": ("Chromium", {WINDOWS: ["%L/Chromium/User Data"], MACOS: ["~/Library/Application Support/Chromium"],
                              LINUX: ["~/.config/chromium", "~/snap/chromium/common/chromium", "~/.var/app/org.chromium.Chromium/config/chromium"]}),
    "edge": ("Microsoft Edge", {WINDOWS: ["%L/Microsoft/Edge/User Data"], MACOS: ["~/Library/Application Support/Microsoft Edge"],
                                LINUX: ["~/.config/microsoft-edge", "~/.var/app/com.microsoft.Edge/config/microsoft-edge"]}),
    "brave": ("Brave", {WINDOWS: ["%L/BraveSoftware/Brave-Browser/User Data"], MACOS: ["~/Library/Application Support/BraveSoftware/Brave-Browser"],
                        LINUX: ["~/.config/BraveSoftware/Brave-Browser", "~/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser"]}),
    "vivaldi": ("Vivaldi", {WINDOWS: ["%L/Vivaldi/User Data"], MACOS: ["~/Library/Application Support/Vivaldi"],
                            LINUX: ["~/.config/vivaldi", "~/.var/app/com.vivaldi.Vivaldi/config/vivaldi"]}),
    "opera": ("Opera", {WINDOWS: ["%A/Opera Software/Opera Stable"], MACOS: ["~/Library/Application Support/com.operasoftware.Opera"],
                        LINUX: ["~/.config/opera"]}),
    "opera_gx": ("Opera GX", {WINDOWS: ["%A/Opera Software/Opera GX Stable"], MACOS: ["~/Library/Application Support/com.operasoftware.OperaGX"]}),
    "arc": ("Arc", {WINDOWS: [], MACOS: ["~/Library/Application Support/Arc/User Data"]}),
    "thorium": ("Thorium", {WINDOWS: ["%L/Thorium/User Data"], LINUX: ["~/.config/thorium"]}),
    "helium": ("Helium", {WINDOWS: ["%L/imput/Helium/User Data"], MACOS: ["~/Library/Application Support/net.imput.helium"]}),
}
FIREFOX = {WINDOWS: ["%A/Mozilla/Firefox/Profiles"], MACOS: ["~/Library/Application Support/Firefox/Profiles"],
           LINUX: ["~/.mozilla/firefox", "~/.var/app/org.mozilla.firefox/.mozilla/firefox", "~/snap/firefox/common/.mozilla/firefox"]}


def _expand(p: str) -> Path:
    p = p.replace("%L", os.environ.get("LOCALAPPDATA", "~/AppData/Local")).replace("%A", os.environ.get("APPDATA", "~/AppData/Roaming"))
    return Path(os.path.expanduser(p))


def chromium_profiles(info: SystemInfo) -> list[tuple[str, str, Path]]:
    """(browser_id, profile_name, Bookmarks path) for profiles that have bookmarks."""
    found = []
    for bid, (_label, dirs) in CHROMIUM.items():
        for d in dirs.get(info.os, []):
            base = _expand(d)
            if not base.is_dir():
                continue
            cands = [base / "Bookmarks"] + [p / "Bookmarks" for p in sorted(base.iterdir())
                                            if p.is_dir() and (p.name == "Default" or p.name.startswith("Profile "))]
            for bm in cands:
                if bm.is_file() and count_chromium(bm) > 0:
                    found.append((bid, bm.parent.name if bm.parent != base else "Default", bm))
    return found


def firefox_profiles(info: SystemInfo) -> list[tuple[str, Path]]:
    out = []
    for d in FIREFOX.get(info.os, []):
        base = _expand(d)
        if not base.is_dir():
            continue
        for prof in sorted(base.iterdir()):
            places = prof / "places.sqlite"
            if places.is_file():
                out.append((prof.name.split(".", 1)[-1], places))
    return out


def count_chromium(bm: Path) -> int:
    try:
        roots = json.loads(bm.read_text(encoding="utf-8")).get("roots", {})
    except Exception:
        return 0

    def walk(n: dict) -> int:
        if n.get("type") == "url":
            return 1
        return sum(walk(c) for c in n.get("children", []))
    return sum(walk(roots[k]) for k in ("bookmark_bar", "other", "synced") if k in roots)


# ----------------------------------------------------------------------------- HTML rendering

def _chromium_html(roots: dict, label: str) -> list[str]:
    lines: list[str] = []

    def node(n: dict, ind: int) -> None:
        pad = "    " * ind
        name = html.escape(n.get("name") or "")
        if n.get("type") == "url":
            lines.append(f'{pad}<DT><A HREF="{html.escape(n.get("url", ""))}">{name}</A>')
        elif n.get("type") == "folder":
            lines.append(f"{pad}<DT><H3>{name}</H3>")
            lines.append(f"{pad}<DL><p>")
            for c in n.get("children", []):
                node(c, ind + 1)
            lines.append(f"{pad}</DL><p>")

    titles = {"bookmark_bar": "Bookmarks bar", "other": "Other bookmarks", "synced": "Mobile bookmarks"}
    body: list[str] = []
    for key, title in titles.items():
        r = roots.get(key)
        if r and r.get("children"):
            lines.clear()
            for c in r["children"]:
                node(c, 3)
            body += [f"        <DT><H3>{title}</H3>", "        <DL><p>", *lines, "        </DL><p>"]
    if not body:
        return []
    return [f"    <DT><H3>{html.escape(label)}</H3>", "    <DL><p>", *body, "    </DL><p>"]


def _firefox_html(places: Path, label: str) -> tuple[list[str], int]:
    tmpdir = Path(tempfile.mkdtemp())
    try:
        db = tmpdir / "places.sqlite"
        copy_file(places, db)
        for ext in ("-wal", "-shm"):
            side = places.with_name(places.name + ext)
            if side.exists():
                copy_file(side, tmpdir / (db.name + ext))
        con = sqlite3.connect(str(db))
        rows = con.execute(
            "SELECT b.id, b.type, b.parent, b.title, p.url, b.guid, b.position FROM moz_bookmarks b "
            "LEFT JOIN moz_places p ON b.fk = p.id ORDER BY b.parent, b.position").fetchall()
        con.close()
    except Exception:
        return [], 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    children: dict[int, list[tuple]] = {}
    by_guid = {}
    for r in rows:
        children.setdefault(r[2], []).append(r)
        by_guid[r[5]] = r
    count = 0
    lines: list[str] = []

    def node(r: tuple, ind: int) -> None:
        nonlocal count
        pad = "    " * ind
        _id, typ, _p, title, url, _g, _pos = r
        if typ == 1 and url and not url.startswith("place:"):
            count += 1
            lines.append(f'{pad}<DT><A HREF="{html.escape(url)}">{html.escape(title or url)}</A>')
        elif typ == 2:
            lines.append(f"{pad}<DT><H3>{html.escape(title or '')}</H3>")
            lines.append(f"{pad}<DL><p>")
            for c in children.get(_id, []):
                node(c, ind + 1)
            lines.append(f"{pad}</DL><p>")

    body: list[str] = []
    for guid, title in (("toolbar_____", "Bookmarks Toolbar"), ("menu________", "Bookmarks Menu"),
                        ("unfiled_____", "Other Bookmarks"), ("mobile______", "Mobile Bookmarks")):
        root = by_guid.get(guid)
        if not root or not children.get(root[0]):
            continue
        lines.clear()
        for c in children[root[0]]:
            node(c, 3)
        if lines:
            body += [f"        <DT><H3>{title}</H3>", "        <DL><p>", *lines, "        </DL><p>"]
    if not body:
        return [], 0
    return [f"    <DT><H3>{html.escape(label)}</H3>", "    <DL><p>", *body, "    </DL><p>"], count


def wrap_html(sections: list[str]) -> str:
    return "\n".join([
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>", "<H1>Bookmarks</H1>", "<DL><p>", *sections, "</DL><p>", ""])


# ----------------------------------------------------------------------------- item

class Browsers(Item):
    id = "browsers"
    name = {"tr": "Tarayıcı yer imleri", "en": "Browser bookmarks"}
    desc = {"tr": "Chrome, Edge, Brave, Vivaldi, Opera, Arc ve Firefox yer imleri; her tarayıcıya aktarılabilen tek HTML dosyası.",
            "en": "Chrome, Edge, Brave, Vivaldi, Opera, Arc and Firefox bookmarks, plus one HTML file every browser can import."}
    restore_on = ANY

    def detect(self, info):
        chrom = chromium_profiles(info)
        ff = firefox_profiles(info)
        if not chrom and not ff:
            return None
        n = sum(count_chromium(bm) for _, _, bm in chrom)
        browsers = sorted({CHROMIUM[b][0] for b, _, _ in chrom} | ({"Firefox"} if ff else set()))
        return {"count": n, "detail": ", ".join(browsers),
                "size": sum(bm.stat().st_size for _, _, bm in chrom) + sum(p.stat().st_size for _, p in ff)}

    def backup(self, ctx: Ctx) -> dict:
        sections: list[str] = []
        profiles = []
        total = 0
        for bid, prof, bm in chromium_profiles(ctx.info):
            ctx.token.check()
            rel = Path("chromium") / bid / prof / "Bookmarks"
            copy_file(bm, ctx.dir / rel)
            roots = json.loads(bm.read_text(encoding="utf-8")).get("roots", {})
            n = count_chromium(bm)
            total += n
            sections += _chromium_html(roots, f"{CHROMIUM[bid][0]} — {prof}")
            profiles.append({"browser": bid, "profile": prof, "file": rel.as_posix(), "count": n})
            ctx.log(f"{CHROMIUM[bid][0]} ({prof}): {n}")
        for prof, places in firefox_profiles(ctx.info):
            ctx.token.check()
            sec, n = _firefox_html(places, f"Firefox — {prof}")
            if n:
                sections += sec
                total += n
                profiles.append({"browser": "firefox", "profile": prof, "count": n})
                ctx.log(f"Firefox ({prof}): {n}")
        (ctx.dir / "bookmarks.html").write_text(wrap_html(sections), encoding="utf-8")
        return {"count": total, "profiles": profiles}

    def restore(self, ctx: Ctx, meta: dict) -> dict:
        # 1. A universal HTML on the desktop, importable by any browser.
        out = paths.desktop_dir() / "KeyStone-Bookmarks.html"
        shutil.copy2(ctx.dir / "bookmarks.html", out)
        ctx.log(ctx.t(f"Tüm yer imleri: {out} (tarayıcıda 'Yer imlerini içe aktar')",
                      f"All bookmarks: {out} (use 'Import bookmarks' in any browser)"))
        # 2. Put Chromium bookmark files back where the same browser is installed
        #    and has no bookmarks yet (never overwrite an existing collection).
        placed = 0
        for p in meta.get("profiles", []):
            if p["browser"] == "firefox" or "file" not in p:
                continue
            for d in CHROMIUM.get(p["browser"], ("", {}))[1].get(ctx.info.os, []):
                base = _expand(d)
                if not base.is_dir():
                    continue
                target = base / p["profile"] / "Bookmarks" if p["browser"] != "opera" else base / "Bookmarks"
                if target.exists() and count_chromium(target) > 0:
                    continue
                if target.parent.is_dir():
                    restore_file(ctx.dir / p["file"], target)
                    placed += 1
                    ctx.log(f"{CHROMIUM[p['browser']][0]} ({p['profile']}) ✓")
                break
        return {"html": str(out), "placed": placed}
