"""One-off migration: KeyStone 2.x (Windows-only) package list -> 3.x catalog.json.

Usage:  python tools/migrate_catalog.py <path-to-KeyStone-2.x-checkout>

Kept in the repo so the cross-platform mapping is reviewable; after the
migration, keystone/data/catalog.json is the single source of truth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# id -> sources on macOS / Linux. mac: "cask:<token>" | "brew:<formula>".
MAP: dict[str, dict[str, str]] = {
    "jdk": dict(mac="cask:temurin@21", apt="openjdk-21-jdk", dnf="java-21-openjdk-devel", pacman="jdk21-openjdk", zypper="java-21-openjdk-devel"),
    "ffmpeg": dict(mac="brew:ffmpeg", apt="ffmpeg", dnf="ffmpeg-free", pacman="ffmpeg", zypper="ffmpeg-7"),
    "git": dict(mac="brew:git", apt="git", dnf="git", pacman="git", zypper="git"),
    "python": dict(mac="brew:python@3.13", apt="python3", dnf="python3", pacman="python", zypper="python3"),
    "vscode": dict(mac="cask:visual-studio-code", flatpak="com.visualstudio.code", snap="code --classic", pacman="code"),
    "pycharm": dict(mac="cask:pycharm-ce", flatpak="com.jetbrains.PyCharm-Community"),
    "anaconda": dict(mac="cask:anaconda"),
    "nodejs": dict(mac="brew:node@22", apt="nodejs", dnf="nodejs", pacman="nodejs", zypper="nodejs22"),
    "netbeans": dict(mac="cask:netbeans", flatpak="org.apache.netbeans"),
    "eclipse": dict(mac="cask:eclipse-java", flatpak="org.eclipse.Java"),
    "drawio_portable": dict(mac="cask:drawio", flatpak="com.jgraph.drawio.desktop"),
    "github_desktop": dict(mac="cask:github", flatpak="io.github.shiftey.Desktop"),
    "sublime_text": dict(mac="cask:sublime-text", flatpak="com.sublimetext.three"),
    "postman": dict(mac="cask:postman", flatpak="com.getpostman.Postman"),
    "antigravity_ide": dict(mac="cask:antigravity"),
    "cursor": dict(mac="cask:cursor"),
    "claude_desktop": dict(mac="cask:claude"),
    "chatgpt_desktop": dict(mac="cask:chatgpt"),
    "ollama": dict(mac="brew:ollama", pacman="ollama"),
    "lm_studio": dict(mac="cask:lm-studio"),
    "postgresql": dict(mac="brew:postgresql@17", apt="postgresql", dnf="postgresql-server", pacman="postgresql", zypper="postgresql-server"),
    "dbeaver": dict(mac="cask:dbeaver-community", flatpak="io.dbeaver.DBeaverCommunity"),
    "docker": dict(mac="cask:docker-desktop", apt="docker.io", dnf="moby-engine", pacman="docker", zypper="docker"),
    "vmware": dict(mac="cask:vmware-fusion"),
    "chrome": dict(mac="cask:google-chrome", flatpak="com.google.Chrome"),
    "brave": dict(mac="cask:brave-browser", flatpak="com.brave.Browser"),
    "firefox": dict(mac="cask:firefox", flatpak="org.mozilla.firefox", dnf="firefox", pacman="firefox", zypper="MozillaFirefox"),
    "arc_browser": dict(mac="cask:arc"),
    "operagx": dict(mac="cask:opera-gx"),
    "edge": dict(mac="cask:microsoft-edge", flatpak="com.microsoft.Edge"),
    "vivaldi": dict(mac="cask:vivaldi", flatpak="com.vivaldi.Vivaldi"),
    "torbrowser": dict(mac="cask:tor-browser", flatpak="org.torproject.torbrowser-launcher"),
    "steam": dict(mac="cask:steam", flatpak="com.valvesoftware.Steam", pacman="steam"),
    "epicgames": dict(mac="cask:epic-games"),
    "gog_galaxy": dict(mac="cask:gog-galaxy"),
    "discord": dict(mac="cask:discord", flatpak="com.discordapp.Discord"),
    "7zip": dict(mac="brew:sevenzip", apt="7zip", dnf="p7zip", pacman="7zip", zypper="7zip"),
    "qbittorrent": dict(mac="cask:qbittorrent", flatpak="org.qbittorrent.qBittorrent", apt="qbittorrent", dnf="qbittorrent", pacman="qbittorrent"),
    "mkvtoolnix": dict(mac="cask:mkvtoolnix", flatpak="org.bunkus.mkvtoolnix-gui"),
    "obs": dict(mac="cask:obs", flatpak="com.obsproject.Studio"),
    "spotify": dict(mac="cask:spotify", flatpak="com.spotify.Client"),
    "telegram": dict(mac="cask:telegram-desktop", flatpak="org.telegram.desktop"),
    "slack": dict(mac="cask:slack", flatpak="com.slack.Slack"),
    "ms_teams": dict(mac="cask:microsoft-teams"),
    "zoom": dict(mac="cask:zoom", flatpak="us.zoom.Zoom"),
    "cisco_webex": dict(mac="cask:webex"),
    "teamviewer": dict(mac="cask:teamviewer"),
    "anydesk": dict(mac="cask:anydesk"),
    "calibre": dict(mac="cask:calibre", flatpak="com.calibre_ebook.calibre"),
    "vlc": dict(mac="cask:vlc", flatpak="org.videolan.VLC", apt="vlc", dnf="vlc", pacman="vlc"),
    "stremio": dict(mac="cask:stremio", flatpak="com.stremio.Stremio"),
    "cloudflare_warp": dict(mac="cask:cloudflare-warp"),
    "proton_vpn": dict(mac="cask:protonvpn", flatpak="com.protonvpn.www"),
    "bleachbit": dict(apt="bleachbit", dnf="bleachbit", pacman="bleachbit", flatpak="org.bleachbit.BleachBit"),
    "handbrake": dict(mac="cask:handbrake-app", flatpak="fr.handbrake.ghb"),
    "audacity": dict(mac="cask:audacity", flatpak="org.audacityteam.Audacity"),
    "obsidian": dict(mac="cask:obsidian", flatpak="md.obsidian.Obsidian"),
    "notion": dict(mac="cask:notion"),
    "libreoffice": dict(mac="cask:libreoffice", flatpak="org.libreoffice.LibreOffice", apt="libreoffice", dnf="libreoffice", pacman="libreoffice-fresh"),
    "adobe_acrobat": dict(mac="cask:adobe-acrobat-reader"),
    "gimp": dict(mac="cask:gimp", flatpak="org.gimp.GIMP", apt="gimp", dnf="gimp", pacman="gimp"),
    "canva": dict(mac="cask:canva"),
    "veracrypt_setup": dict(mac="cask:veracrypt"),
    "yubikey_manager": dict(mac="cask:yubico-authenticator", flatpak="com.yubico.yubioath"),
    "keepassxc": dict(mac="cask:keepassxc", flatpak="org.keepassxc.KeePassXC", apt="keepassxc", dnf="keepassxc", pacman="keepassxc"),
    "malwarebytes": dict(mac="cask:malwarebytes"),
    "onepassword": dict(mac="cask:1password"),
    "bitwarden": dict(mac="cask:bitwarden", flatpak="com.bitwarden.desktop"),
    "ultimaker_cura": dict(mac="cask:ultimaker-cura", flatpak="com.ultimaker.cura"),
    "blender": dict(mac="cask:blender", flatpak="org.blender.Blender"),
    "unity_hub": dict(mac="cask:unity-hub", flatpak="com.unity.UnityHub"),
    "godot_engine": dict(mac="cask:godot", flatpak="org.godotengine.Godot"),
    "virtualbox": dict(mac="cask:virtualbox", apt="virtualbox", pacman="virtualbox"),
}

# Cross-platform stand-ins used when a backup from one OS is restored on another.
ALT: dict[str, dict[str, str]] = {
    "potplayer": {"macos": "iina", "linux": "vlc"},
    "gom_player": {"macos": "iina", "linux": "vlc"},
    "klite_codec": {"macos": "iina", "linux": "vlc"},
    "winrar": {"macos": "keka", "linux": "7zip"},
    "winzip": {"macos": "keka", "linux": "7zip"},
    "epicgames": {"linux": "heroic"},
    "gog_galaxy": {"linux": "heroic"},
    "quickshare": {"macos": "localsend", "linux": "localsend"},
    "windows_terminal": {"macos": "iterm2"},
    "powertoys": {"macos": "rectangle"},
    "ccleaner": {"linux": "bleachbit"},
    "cpuz": {"macos": "stats", "linux": "mission_center"},
    "hwinfo": {"macos": "stats", "linux": "mission_center"},
    "hwmonitor": {"macos": "stats", "linux": "mission_center"},
    "everything": {"linux": "fsearch"},
    "msi_afterburner": {"linux": "mission_center"},
    "cursor": {"linux": "vscode"},
    "ms_teams": {"linux": "teams_for_linux"},
    "anydesk": {"linux": "rustdesk"},
    "teamviewer": {"linux": "rustdesk"},
    "notion": {"linux": "obsidian"},
}

# New entries for macOS / Linux / everywhere.
EXTRA = [
    dict(id="heroic", category="gaming", name="Heroic Games Launcher",
         desc={"tr": "Epic, GOG ve Amazon oyunları için açık kaynak başlatıcı.", "en": "Open-source launcher for Epic, GOG and Amazon games."},
         website="https://heroicgameslauncher.com", presets=["gamer"],
         win=[{"winget": "HeroicGamesLauncher.HeroicGamesLauncher"}], mac=[{"cask": "heroic"}],
         linux={"flatpak": "com.heroicgameslauncher.hgl"}),
    dict(id="localsend", category="utilities", name="LocalSend",
         desc={"tr": "Yerel ağda tüm cihazlar arasında AirDrop benzeri dosya paylaşımı.", "en": "AirDrop-style file sharing between any devices on your network."},
         website="https://localsend.org", presets=["essential"],
         win=[{"winget": "LocalSend.LocalSend"}], mac=[{"cask": "localsend"}],
         linux={"flatpak": "org.localsend.localsend_app"}),
    dict(id="rustdesk", category="utilities", name="RustDesk",
         desc={"tr": "Açık kaynak, kendi sunucunla da çalışan uzak masaüstü.", "en": "Open-source remote desktop that can use your own server."},
         website="https://rustdesk.com", presets=[],
         win=[{"winget": "RustDesk.RustDesk"}], mac=[{"cask": "rustdesk"}],
         linux={"flatpak": "com.rustdesk.RustDesk"}),
    dict(id="btop", category="hardware_test", name="btop",
         desc={"tr": "Terminalde CPU, bellek, disk ve ağ kullanımını gösteren izleyici.", "en": "Terminal resource monitor for CPU, memory, disks and network."},
         website="https://github.com/aristocratos/btop", presets=["dev", "hardware"],
         win=[{"winget": "aristocratos.btop4win"}], mac=[{"brew": "btop"}],
         linux={"apt": "btop", "dnf": "btop", "pacman": "btop", "zypper": "btop"}),
    dict(id="iterm2", category="dev", name="iTerm2",
         desc={"tr": "Bölmeli, aranabilir ve profilli macOS terminali.", "en": "Split panes, search and profiles: the macOS terminal upgrade."},
         website="https://iterm2.com", presets=["dev"], mac=[{"cask": "iterm2"}]),
    dict(id="rectangle", category="utilities", name="Rectangle",
         desc={"tr": "Klavye kısayollarıyla pencereleri ekrana yerleştirme.", "en": "Snap windows into place with keyboard shortcuts."},
         website="https://rectangleapp.com", presets=["essential"], mac=[{"cask": "rectangle"}]),
    dict(id="alt_tab", category="utilities", name="AltTab",
         desc={"tr": "macOS'a Windows tarzı pencere geçişi getirir.", "en": "Windows-style window switcher for macOS."},
         website="https://alt-tab-macos.netlify.app", presets=[], mac=[{"cask": "alt-tab"}]),
    dict(id="stats", category="hardware_test", name="Stats",
         desc={"tr": "Menü çubuğunda CPU, GPU, bellek, sıcaklık ve ağ izleyici.", "en": "Menu-bar monitor for CPU, GPU, memory, sensors and network."},
         website="https://github.com/exelban/stats", presets=["hardware"], mac=[{"cask": "stats"}]),
    dict(id="iina", category="utilities", name="IINA",
         desc={"tr": "macOS için modern, her formatı açan video oynatıcı.", "en": "Modern media player for macOS that plays everything."},
         website="https://iina.io", presets=["essential"], mac=[{"cask": "iina"}]),
    dict(id="keka", category="utilities", name="Keka",
         desc={"tr": "macOS için 7z, RAR ve ZIP arşiv yöneticisi.", "en": "7z, RAR and ZIP archiver for macOS."},
         website="https://www.keka.io", presets=["essential"], mac=[{"cask": "keka"}]),
    dict(id="the_unarchiver", category="utilities", name="The Unarchiver",
         desc={"tr": "Neredeyse her arşiv formatını tek tıkla açar.", "en": "Opens almost any archive format in one click."},
         website="https://theunarchiver.com", presets=[], mac=[{"cask": "the-unarchiver"}]),
    dict(id="flatseal", category="security", name="Flatseal",
         desc={"tr": "Flatpak uygulamalarının izinlerini görsel olarak yönetir.", "en": "Review and change Flatpak app permissions."},
         website="https://github.com/tchx84/Flatseal", presets=["essential"], linux={"flatpak": "com.github.tchx84.Flatseal"}),
    dict(id="mission_center", category="hardware_test", name="Mission Center",
         desc={"tr": "Linux için Görev Yöneticisi benzeri CPU/GPU/disk izleyici.", "en": "Task-Manager-style CPU, GPU and disk monitor for Linux."},
         website="https://missioncenter.io", presets=["hardware"], linux={"flatpak": "io.missioncenter.MissionCenter"}),
    dict(id="gnome_tweaks", category="utilities", name="GNOME Tweaks",
         desc={"tr": "GNOME'un gizli görünüm ve davranış ayarları.", "en": "Hidden appearance and behaviour settings for GNOME."},
         website="https://gitlab.gnome.org/GNOME/gnome-tweaks", presets=["essential"],
         linux={"apt": "gnome-tweaks", "dnf": "gnome-tweaks", "pacman": "gnome-tweaks", "zypper": "gnome-tweaks"}),
    dict(id="timeshift", category="utilities", name="Timeshift",
         desc={"tr": "Sistem anlık görüntüleri: bozulan güncellemeden önceki hale dön.", "en": "System snapshots: roll back after a bad update."},
         website="https://github.com/linuxmint/timeshift", presets=["essential"],
         linux={"apt": "timeshift", "dnf": "timeshift", "pacman": "timeshift"}),
    dict(id="fsearch", category="utilities", name="FSearch",
         desc={"tr": "Everything benzeri anlık dosya arama.", "en": "Instant file search in the spirit of Everything."},
         website="https://github.com/cboxdoerfer/fsearch", presets=[], linux={"flatpak": "io.github.cboxdoerfer.FSearch"}),
    dict(id="teams_for_linux", category="utilities", name="Teams for Linux",
         desc={"tr": "Microsoft Teams için topluluk istemcisi.", "en": "Community client for Microsoft Teams."},
         website="https://github.com/IsmaelMartinez/teams-for-linux", presets=[], linux={"flatpak": "com.github.IsmaelMartinez.teams_for_linux"}),
]

NAME_OVERRIDE = {"git": "Git", "python": "Python 3"}

PRESETS = {  # keep IDs of the 2.x presets; labels live in the UI
    "essential", "dev", "gamer", "ai", "hardware", "database", "utilities",
}


def main(src: Path) -> None:
    sys.path.insert(0, str(src))
    from data.packages import PACKAGES  # type: ignore
    from locales import PACKAGES_EN  # type: ignore

    out = []
    for p in PACKAGES:
        en = PACKAGES_EN.get(p["id"], {})
        win: list[dict] = []
        if p.get("winget_id"):
            win.append({"winget": p["winget_id"]})
            win += [{"winget": f} for f in p.get("fallback_winget_ids", [])]
        if p.get("direct_download_url"):
            win.append({"url": p["direct_download_url"], **({"portable": True} if p.get("portable") else {})})
        entry: dict = {
            "id": p["id"],
            "name": NAME_OVERRIDE.get(p["id"]) or en.get("name") or p["name"],
            "category": p["category"],
            "desc": {"tr": p["short_desc"], "en": en.get("short_desc", p["short_desc"])},
            "long": {"tr": p["full_desc"], "en": en.get("full_desc", p["full_desc"])},
            "website": p.get("website", ""),
            "presets": p.get("presets", []),
            "recommended": bool(p.get("recommended")),
        }
        if p["name"] != entry["name"] and p["id"] not in NAME_OVERRIDE:
            entry["name_tr"] = p["name"]
        if win:
            entry["win"] = win
        if p.get("web_link") or (not p.get("winget_id") and not p.get("direct_download_url")):
            entry["web_only"] = True
        m = MAP.get(p["id"], {})
        if "mac" in m:
            kind, token = m["mac"].split(":", 1)
            entry["mac"] = [{kind if kind == "cask" else "brew": token}]
        lin = {k: v for k, v in m.items() if k != "mac"}
        if lin:
            entry["linux"] = lin
        if p["id"] in ALT:
            entry["alt"] = ALT[p["id"]]
        out.append(entry)

    for e in EXTRA:
        e = dict(e)
        e.setdefault("long", e["desc"])
        e.setdefault("recommended", False)
        out.append(e)

    ids = {e["id"] for e in out}
    for e in out:
        for target in e.get("alt", {}).values():
            assert target in ids, f"{e['id']}: alt target {target} missing"

    dest = Path(__file__).resolve().parent.parent / "keystone" / "data" / "catalog.json"
    dest.write_text(json.dumps({"version": 1, "packages": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    plat = {k: sum(1 for e in out if k in e) for k in ("win", "mac", "linux")}
    print(f"wrote {len(out)} packages -> {dest}  {plat}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
