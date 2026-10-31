"""Refresh the app icons bundled in keystone/ui/assets/apps (needs Pillow).

    python tools/fetch_icons.py           only what is missing
    python tools/fetch_icons.py --force   everything

Run by hand when the catalogue changes; the app itself never contacts these
hosts. The icon is looked up by exact winget id, so it belongs to that package
and not to something with a similar name. Without one, the site's favicon is
used, except on code hosts where it would be the host's logo rather than the
app's. Images are decoded and re-encoded, never stored as downloaded.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "keystone" / "ui" / "assets" / "apps"
SIZE = 64
SHARED_HOSTS = {"github.com", "gitlab.gnome.org", "alt-tab-macos.netlify.app"}
ICON_HOSTS = {   # product sites, where the catalogue's website only has the vendor's logo
    "edge": "www.microsoftedgeinsider.com", "ms_teams": "teams.live.com", "powerbi": "app.powerbi.com",
    "vs_community": "visualstudio.microsoft.com", "vlc": "www.videolan.org", "adobe_acrobat": "www.adobe.com",
    "powertoys": "learn.microsoft.com", "veracrypt_portable": "veracrypt.io", "veracrypt_setup": "veracrypt.io",
}


def get(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "KeyStone-icon-fetch"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read(2_000_000)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def is_generic(im: Image.Image) -> bool:
    """True for icons that identify nothing: the four-colour Windows logo, or blank on white."""
    flat = Image.new("RGBA", im.size, "white")
    flat.alpha_composite(im)
    w, h = flat.size
    r, g, b, _ = zip(*(flat.getpixel((w * x // 4, h * y // 4)) for x, y in ((1, 1), (3, 1), (1, 3), (3, 3))))
    quadrants = r[0] > 180 > g[0] and g[1] > 150 > r[1] and b[2] > 180 > r[2] and r[3] > 180 > b[3]
    lo, hi = flat.convert("L").getextrema()
    return quadrants or hi - lo < 40


def to_png(data: bytes | None, min_size: int) -> bytes | None:
    if not data:
        return None
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return None
    if min(im.size) < min_size:
        return None
    im = im.convert("RGBA")
    if is_generic(im):
        return None
    im.thumbnail((SIZE, SIZE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    im.save(out, "PNG", optimize=True)
    return out.getvalue()


def sources(p: dict) -> list[tuple[str, str, int]]:
    urls = []
    for w in p.get("win", []):
        if w.get("winget"):
            urls.append((f"https://api.winstall.app/icons/next/{w['winget']}.webp", "winget id", 32))
            urls.append((f"https://api.winstall.app/icons/{w['winget']}.png", "winget id", 32))
    host = ICON_HOSTS.get(p["id"]) or urlparse(p.get("website", "")).hostname or ""
    if host and host not in SHARED_HOSTS:
        urls.append((f"https://www.google.com/s2/favicons?domain={host}&sz=64", "favicon", 32))
        urls.append((f"https://icons.duckduckgo.com/ip3/{host}.ico", "favicon", 16))
    return urls


def fetch(p: dict) -> tuple[str, str]:
    for url, kind, min_size in sources(p):
        png = to_png(get(url), min_size)
        if png:
            (OUT / f"{p['id']}.png").write_bytes(png)
            return p["id"], kind
    return p["id"], "none"


def main() -> None:
    force = "--force" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    packages = json.loads((ROOT / "keystone" / "data" / "catalog.json").read_text(encoding="utf-8"))["packages"]
    todo = [p for p in packages if force or not (OUT / f"{p['id']}.png").exists()]
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(fetch, todo))
    for kind in ("winget id", "favicon", "none"):
        ids = sorted(i for i, k in results if k == kind)
        print(f"{kind}: {len(ids)}" + (f"  {' '.join(ids)}" if kind != "winget id" else ""))


if __name__ == "__main__":
    main()
