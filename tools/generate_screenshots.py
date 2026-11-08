"""Generate all 8 official KeyStone screenshots in English with no personal info.

Run: python tools/generate_screenshots.py
"""
import base64
import json
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

UI_ROOT = REPO_ROOT / "keystone" / "ui"
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots"

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

# Mock system info: Generic, standard user, Windows 11 Pro 24H2, x64, DESKTOP-PC
MOCK_BOOTSTRAP = {
    "version": "3.1.2",
    "system": {
        "os": "windows",
        "os_name": "Windows 11 Pro 24H2",
        "os_version": "10.0.26100",
        "arch": "x64",
        "distro_id": "",
        "distro_like": [],
        "desktop": "explorer",
        "hostname": "DESKTOP-PC",
        "username": "User",
        "is_admin": False,
    },
    "managers": [{"name": "winget", "label": "winget", "available": True, "needs_root": False}],
    "settings": {
        "style": "calm",
        "theme": "light",
        "lang": "en",
        "prefer": "native",
        "backup_dir": r"D:\Backups",
        "accent": "",
    },
    "profiles": [
        {
            "name": "Admin",
            "apps": ["directx", "vcredist_aio", "dotnet_desktop_10", "klite_codec", "git", "python", "vscode"],
            "tweaks": [
                "classic_context_menu",
                "taskbar_end_task",
                "dark_mode",
                "unpin_downloads_quick_access",
                "remove_gallery",
                "show_this_pc",
                "photos_legacy",
            ],
            "backup": ["apps", "browsers", "wifi", "editors", "git_ssh", "shell", "env", "tweaks"],
            "backup_dir": r"D:\Backups",
            "custom_apps": [],
        }
    ],
    "active": "Admin",
    "categories": [],
    "presets": [],
    "tweak_categories": [],
    "backup_dir": r"D:\Backups",
    "native_dialogs": False,
    "can_elevate": True,
    "initial_view": "apps",
    "target_tweak": None,
}

def get_clean_catalog():
    from keystone import catalog
    from keystone.core.system import SystemInfo, WINDOWS
    from keystone.pkg.registry import managers_for
    info = SystemInfo(WINDOWS, "Windows 11 Pro 24H2", "10.0.26100", "x64", desktop="explorer",
                      hostname="DESKTOP-PC", username="User", is_admin=False)
    installed = {
        "winget": {
            "Microsoft.DirectX",
            "abbodi1406.vcredist",
            "Microsoft.DotNet.DesktopRuntime.10",
            "CodecGuide.K-LiteCodecPack.Full",
            "Git.Git",
            "Python.Python.3.13",
            "Microsoft.VisualStudioCode",
        }
    }
    mgrs = managers_for(info, only_available=False)
    pkgs = catalog.view(info, mgrs, installed, "native", custom_apps=[])
    return {"packages": pkgs, "scanning": False}

def get_clean_tweaks():
    from keystone import tweaks
    from keystone.core.system import SystemInfo, WINDOWS
    info = SystemInfo(WINDOWS, "Windows 11 Pro 24H2", "10.0.26100", "x64", desktop="explorer",
                      hostname="DESKTOP-PC", username="User", is_admin=False)
    tw_list = tweaks.for_host(info)
    enabled_ids = {
        "classic_context_menu",
        "taskbar_end_task",
        "dark_mode",
        "unpin_downloads_quick_access",
        "remove_gallery",
        "show_this_pc",
        "photos_legacy",
    }
    res = []
    for t in tw_list:
        d = t.meta()
        d["state"] = t.id in enabled_ids
        d["current"] = t.id in enabled_ids
        res.append(d)
    return res

def get_clean_backup_items():
    return [
        {
            "id": "apps",
            "name": {"en": "Installed apps", "tr": "Kurulu uygulamalar"},
            "desc": {
                "en": "Catalogue apps found here plus the full package list. Reinstalled with their equivalents on another OS.",
                "tr": "Kataloğdaki kurulu uygulamalar ve tüm paket listesi. Başka bir işletim sisteminde karşılıklarıyla kurulur."
            },
            "restore_on": "any",
            "supported": True,
            "found": {"count": None, "detail": "", "size": 65536},
            "sensitive": False,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "browsers",
            "name": {"en": "Browser bookmarks", "tr": "Tarayıcı yer imleri"},
            "desc": {
                "en": "Chrome, Edge, Brave, Vivaldi, Opera, Arc, Firefox, plus one HTML file any browser can import",
                "tr": "Chrome, Edge, Brave, Vivaldi, Opera, Arc, Firefox..."
            },
            "restore_on": "any",
            "supported": True,
            "found": {"count": 299, "detail": "Brave, Firefox", "size": 5452595},
            "sensitive": False,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "wifi",
            "name": {"en": "Wi-Fi networks", "tr": "Wi-Fi ağları"},
            "desc": {
                "en": "Network name, security type and password (netsh / nmcli / networksetup)",
                "tr": "Ağ adı, güvenlik türü ve parola..."
            },
            "restore_on": "any",
            "supported": True,
            "found": {"count": 4, "detail": "", "size": 4096},
            "sensitive": True,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "editors",
            "name": {"en": "Code editors", "tr": "Kod editörleri"},
            "desc": {
                "en": "VS Code, Cursor, VSCodium, Windsurf settings and extensions",
                "tr": "VS Code, Cursor..."
            },
            "restore_on": "any",
            "supported": True,
            "found": {"count": 1, "detail": "Visual Studio Code", "size": 0},
            "sensitive": False,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "git_ssh",
            "name": {"en": "Git & SSH", "tr": "Git ve SSH"},
            "desc": {
                "en": ".gitconfig, ~/.ssh (file permissions preserved)",
                "tr": ".gitconfig, ~/.ssh..."
            },
            "restore_on": "any",
            "supported": True,
            "found": {"count": 1, "detail": "0 SSH key", "size": 513},
            "sensitive": True,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "shell",
            "name": {"en": "Shell & terminal", "tr": "Kabuk ve terminal"},
            "desc": {
                "en": "zsh/bash/fish, Neovim, tmux and more, or PowerShell and Windows Terminal",
                "tr": "zsh/bash/fish..."
            },
            "restore_on": "family",
            "supported": True,
            "found": {"count": 2, "detail": "powershell7, windows-terminal", "size": 148480},
            "sensitive": False,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "env",
            "name": {"en": "Environment variables", "tr": "Ortam değişkenleri"},
            "desc": {
                "en": "The user PATH is merged, not overwritten",
                "tr": "Kullanıcı PATH..."
            },
            "restore_on": "same",
            "supported": True,
            "found": {"count": 8, "detail": "", "size": 4096},
            "sensitive": False,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "desktop",
            "name": {"en": "Desktop settings", "tr": "Masaüstü ayarları"},
            "desc": {
                "en": "GNOME dconf / macOS Dock and Finder",
                "tr": "GNOME dconf..."
            },
            "restore_on": "same",
            "supported": False,
            "found": None,
            "sensitive": False,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "fonts",
            "name": {"en": "User fonts", "tr": "Kullanıcı yazı tipleri"},
            "desc": {
                "en": "Fonts installed by the user",
                "tr": "Kullanıcı yazı tipleri..."
            },
            "restore_on": "any",
            "supported": True,
            "found": None,
            "sensitive": False,
            "heavy": False,
            "parts": [],
        },
        {
            "id": "tweaks",
            "name": {"en": "Applied tweaks", "tr": "Uygulanan ince ayarlar"},
            "desc": {
                "en": "KeyStone tweaks currently in effect, re-applied in one go on the same OS.",
                "tr": "KeyStone ince ayarları..."
            },
            "restore_on": "same",
            "supported": True,
            "found": {"count": None, "detail": "", "size": 2048},
            "sensitive": False,
            "heavy": False,
            "parts": [],
        },
    ]

class MockServerHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b": ping\n\n")
            return
        rel = url.path.lstrip("/") or "index.html"
        target = (UI_ROOT / rel).resolve()
        if not target.is_file():
            self.send_response(404)
            self.end_headers()
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        # If serving app.js, expose globals inside the closure
        if target.name == "app.js":
            body = body.replace(
                b'window.addEventListener("pywebviewready", () => { if (!S.boot) boot(); });',
                b'window.addEventListener("pywebviewready", () => { if (!S.boot) boot(); });\n  window.__KS = { get S() { return S; }, setSetting, go, applyAppearance, renderShell, renderView, profile };'
            )

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        url = urlparse(self.path)
        name = url.path.removeprefix("/api/")
        n = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(n) or b"{}") if n else {}
        args = payload.get("args", [])

        from keystone import catalog, tweaks
        if name == "bootstrap":
            b = dict(MOCK_BOOTSTRAP)
            b["categories"] = catalog.CATEGORIES
            b["presets"] = catalog.PRESETS
            b["tweak_categories"] = tweaks.CATEGORIES
            res = b
        elif name == "get_catalog":
            res = get_clean_catalog()
        elif name == "get_tweaks":
            res = get_clean_tweaks()
        elif name == "backup_items":
            res = get_clean_backup_items()
        elif name == "list_backups":
            res = []
        elif name in ("save_profile", "profile_save"):
            if args:
                MOCK_BOOTSTRAP["profiles"][0].update(args[0])
            res = {"ok": True}
        elif name in ("set_setting", "settings_set"):
            if args:
                MOCK_BOOTSTRAP["settings"].update(args[0])
            res = MOCK_BOOTSTRAP["settings"]
        elif name == "scan":
            res = {"ok": True}
        else:
            res = {}

        body = json.dumps({"result": res}, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def composite_with_titlebar(content_img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    calm = Image.open(REPO_ROOT / "docs" / "screenshots" / "calm.png")
    bar = Image.new("RGB", (target_w, 31), (32, 32, 33))
    bar.paste(calm.crop((0, 0, 120, 31)), (0, 0))
    bar.paste(calm.crop((1280 - 140, 0, 1280, 31)), (target_w - 140, 0))

    final_img = Image.new("RGB", (target_w, target_h))
    final_img.paste(bar, (0, 0))
    final_img.paste(content_img, (0, 31))
    return final_img

def main():
    print("=== KeyStone Screenshot Generator (v3.1.2) ===", flush=True)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), MockServerHandler)
    server_port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"Mock server running on port {server_port}", flush=True)

    edge_profile = REPO_ROOT / "tmp_edge_profile"
    if edge_profile.exists():
        shutil.rmtree(edge_profile, ignore_errors=True)

    edge_proc = subprocess.Popen([
        EDGE_PATH,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={edge_profile}",
        "--window-size=1280,820",
        "about:blank",
    ])
    print("Edge headless launched...", flush=True)
    time.sleep(2)

    node_runner = REPO_ROOT / "tools" / "cdp_runner.js"
    node_code = f"""
const fs = require('fs');

async function wait(ms) {{
  return new Promise(r => setTimeout(r, ms));
}}

async function connect() {{
  const tabs = await fetch('http://127.0.0.1:9222/json').then(r => r.json());
  const pageTab = tabs.find(t => t.type === 'page') || tabs[0];
  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);

  let id = 1;
  function call(method, params = {{}}) {{
    return new Promise((resolve, reject) => {{
      const curId = id++;
      const handler = (event) => {{
        const msg = JSON.parse(event.data);
        if (msg.id === curId) {{
          ws.removeEventListener('message', handler);
          if (msg.error) reject(msg.error);
          else resolve(msg.result);
        }}
      }};
      ws.addEventListener('message', handler);
      ws.send(JSON.stringify({{ id: curId, method, params }}));
    }});
  }}

  return {{ ws, call }};
}}

async function capture(call, outPath, width, height) {{
  await call('Emulation.setDeviceMetricsOverride', {{
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false
  }});
  await wait(300);
  const snap = await call('Page.captureScreenshot', {{ format: 'png' }});
  fs.writeFileSync(outPath, Buffer.from(snap.data, 'base64'));
}}

async function run() {{
  const {{ ws, call }} = await connect();
  await call('Page.enable', {{}});

  const port = {server_port};
  const appUrl = `http://127.0.0.1:${{port}}/#token=dummy`;
  const splashUrl = `http://127.0.0.1:${{port}}/splash.html`;

  console.log('1. Welcome screen...');
  await call('Page.navigate', {{ url: splashUrl }});
  await wait(700);
  await call('Runtime.evaluate', {{
    expression: `
      Splash.init({{lang: 'en', theme: 'light', style: 'calm', first: true}});
      Splash.step('os', 'done', 'Windows 11 Pro 24H2 · x64');
      Splash.step('managers', 'done', 'winget');
      Splash.step('rights', 'lim', 'admin_no');
      Splash.step('catalog', 'done', 'sp_fit', {{fit: 154, total: 167}});
      Splash.finish({{managers: 'pm.winget ✓', hidden: 13}});
    `,
    awaitPromise: true
  }});
  await wait(400);
  await capture(call, 'tmp_welcome.png', 1180, 729);

  console.log('Navigating to app...');
  await call('Page.navigate', {{ url: appUrl }});
  await wait(1500);

  // Setup profile selection of 7 apps in English
  await call('Runtime.evaluate', {{
    expression: `
      window.__KS.S.boot.profiles[0].apps = ['directx', 'vcredist_aio', 'dotnet_desktop_10', 'klite_codec', 'git', 'python', 'vscode'];
    `,
    awaitPromise: true
  }});

  // 2. Calm (Apps, Light, Rows)
  console.log('2. Calm...');
  await call('Runtime.evaluate', {{
    expression: `
      (async () => {{
        await window.__KS.setSetting({{style: 'calm', theme: 'light', lang: 'en', accent: ''}});
        window.__KS.go('apps');
        const bList = document.querySelector('[data-layout="list"]');
        if (bList) bList.click();
      }})();
    `,
    awaitPromise: true
  }});
  await wait(700);
  await capture(call, 'tmp_calm.png', 1280, 789);

  // 3. Console (Apps, Dark, Rows)
  console.log('3. Console...');
  await call('Runtime.evaluate', {{
    expression: `
      (async () => {{
        await window.__KS.setSetting({{style: 'console', theme: 'dark', lang: 'en', accent: ''}});
        window.__KS.go('apps');
        const bList = document.querySelector('[data-layout="list"]');
        if (bList) bList.click();
      }})();
    `,
    awaitPromise: true
  }});
  await wait(700);
  await capture(call, 'tmp_console.png', 1280, 789);

  // 4. Bold (Apps, Light, Cards)
  console.log('4. Bold...');
  await call('Runtime.evaluate', {{
    expression: `
      (async () => {{
        await window.__KS.setSetting({{style: 'bold', theme: 'light', lang: 'en', accent: ''}});
        window.__KS.go('apps');
        const bCards = document.querySelector('[data-layout="cards"]');
        if (bCards) bCards.click();
      }})();
    `,
    awaitPromise: true
  }});
  await wait(700);
  await capture(call, 'tmp_bold.png', 1280, 789);

  // 5. Apple (Apps, Dark, Rows)
  console.log('5. Apple...');
  await call('Runtime.evaluate', {{
    expression: `
      (async () => {{
        await window.__KS.setSetting({{style: 'apple', theme: 'dark', lang: 'en', accent: ''}});
        window.__KS.go('apps');
        const bList = document.querySelector('[data-layout="list"]');
        if (bList) bList.click();
      }})();
    `,
    awaitPromise: true
  }});
  await wait(700);
  await capture(call, 'tmp_apple.png', 1280, 789);

  // 6. Tweaks (Calm, Light, List)
  console.log('6. Tweaks...');
  await call('Runtime.evaluate', {{
    expression: `
      (async () => {{
        window.__KS.S.tf.layout = 'list';
        await window.__KS.setSetting({{style: 'calm', theme: 'light', lang: 'en', accent: ''}});
        window.__KS.go('tweaks');
      }})();
    `,
    awaitPromise: true
  }});
  await wait(1000);
  await capture(call, 'tmp_tweaks.png', 1280, 789);

  // 7. Backup (Calm, Light)
  console.log('7. Backup...');
  await call('Runtime.evaluate', {{
    expression: `
      (async () => {{
        await window.__KS.setSetting({{style: 'calm', theme: 'light', lang: 'en', accent: ''}});
        window.__KS.go('backup');
      }})();
    `,
    awaitPromise: true
  }});
  await wait(700);
  await capture(call, 'tmp_backup.png', 1280, 789);

  // 8. Settings (Calm, Light)
  console.log('8. Settings...');
  await call('Runtime.evaluate', {{
    expression: `
      (async () => {{
        await window.__KS.setSetting({{style: 'calm', theme: 'light', lang: 'en', accent: ''}});
        window.__KS.go('settings');
      }})();
    `,
    awaitPromise: true
  }});
  await wait(700);
  await capture(call, 'tmp_settings.png', 1280, 759);

  console.log('All views captured successfully!');
  ws.close();
}}

run().catch(err => {{
  console.error('CDP Error:', err);
  process.exit(1);
}});
"""
    node_runner.write_text(node_code, encoding="utf-8")

    try:
        p = subprocess.run(["node", str(node_runner)], capture_output=True, text=True, timeout=60)
        print("Node stdout:\n", p.stdout, flush=True)
        if p.stderr:
            print("Node stderr:\n", p.stderr, flush=True)
        if p.returncode != 0:
            raise RuntimeError(f"Node script failed with code {p.returncode}")

        targets = [
            ("tmp_welcome.png", "welcome.png", 1180, 760),
            ("tmp_calm.png", "calm.png", 1280, 820),
            ("tmp_console.png", "console.png", 1280, 820),
            ("tmp_bold.png", "bold.png", 1280, 820),
            ("tmp_apple.png", "apple.png", 1280, 820),
            ("tmp_tweaks.png", "tweaks.png", 1280, 820),
            ("tmp_backup.png", "backup.png", 1280, 820),
            ("tmp_settings.png", "settings.png", 1280, 790),
        ]

        for tmp_name, final_name, target_w, target_h in targets:
            tmp_path = REPO_ROOT / tmp_name
            if not tmp_path.exists():
                print(f"Warning: {tmp_name} does not exist!", flush=True)
                continue
            content = Image.open(tmp_path)
            final_img = composite_with_titlebar(content, target_w, target_h)
            out_path = OUTPUT_DIR / final_name
            final_img.save(out_path)
            print(f"Wrote {final_name}: size {final_img.size}, bytes {out_path.stat().st_size:,}", flush=True)
            tmp_path.unlink()

        print("All 8 screenshots updated successfully!", flush=True)
    finally:
        edge_proc.terminate()
        edge_proc.wait()
        httpd.shutdown()
        if node_runner.exists():
            node_runner.unlink()
        if edge_profile.exists():
            time.sleep(1)
            shutil.rmtree(edge_profile, ignore_errors=True)

if __name__ == "__main__":
    main()
