from keystone import catalog
from keystone.pkg.registry import ALL, candidate_names, resolve


def mgrs(*names):
    return {n: ALL[n]() for n in names}

from .conftest import host  # noqa: E402


def test_catalog_integrity():
    pkgs = catalog.load()
    ids = [p["id"] for p in pkgs]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for p in pkgs:
        assert p["category"] in catalog.CATEGORIES, p["id"]
        assert p["desc"]["tr"] and p["desc"]["en"], p["id"]
        assert catalog.platforms(p), f"{p['id']} has no platform"
        for target in p.get("alt", {}).values():
            assert target in ids
        for s in p.get("mac", []):
            assert set(s) <= {"cask", "brew"}
        for k in p.get("linux", {}):
            assert k in ("apt", "dnf", "pacman", "zypper", "flatpak", "snap")


def test_platform_coverage():
    pkgs = catalog.load()
    n = {o: sum(1 for p in pkgs if o in catalog.platforms(p)) for o in ("windows", "macos", "linux")}
    assert n["windows"] >= 150 and n["macos"] >= 80 and n["linux"] >= 60


def test_candidate_managers_per_distro():
    assert candidate_names(host("linux", "ubuntu")) == ["apt", "flatpak", "snap"]
    assert candidate_names(host("linux", "linuxmint", ["ubuntu", "debian"])) == ["apt", "flatpak", "snap"]
    assert candidate_names(host("linux", "fedora")) == ["dnf", "flatpak", "snap"]
    assert candidate_names(host("linux", "endeavouros", ["arch"])) == ["pacman", "flatpak", "snap"]
    assert candidate_names(host("linux", "opensuse-tumbleweed", ["opensuse", "suse"]))[0] == "zypper"
    assert candidate_names(host("macos")) == ["brew"]
    assert candidate_names(host("windows")) == ["winget"]


def test_resolve_prefers_native_then_flatpak():
    vlc = catalog.by_id()["vlc"]
    u = host("linux", "ubuntu")
    assert [s.pm for s in resolve(vlc, u, mgrs("apt", "flatpak"))] == ["apt", "flatpak"]
    assert [s.pm for s in resolve(vlc, u, mgrs("apt", "flatpak"), prefer="flatpak")] == ["flatpak", "apt"]
    # Chrome has only a flatpak id: unavailable until flatpak exists.
    chrome = catalog.by_id()["chrome"]
    assert resolve(chrome, u, mgrs("apt")) == []
    assert resolve(chrome, u, mgrs("apt", "flatpak"))[0].id == "com.google.Chrome"


def test_resolve_macos_and_windows():
    m = resolve(catalog.by_id()["vscode"], host("macos"), mgrs("brew"))[0]
    assert (m.pm, m.id, m.kind) == ("brew", "visual-studio-code", "cask")
    g = resolve(catalog.by_id()["git"], host("macos"), mgrs("brew"))[0]
    assert g.kind == "formula"
    w = resolve(catalog.by_id()["vcredist_aio"], host("windows"), mgrs("winget"))
    assert [s.id for s in w] == ["abbodi1406.vcredist", "Microsoft.VCRedist.2015+.x64", "Microsoft.VCRedist.2015+.x86"]
    assert resolve(catalog.by_id()["vcredist_aio"], host("macos"), mgrs("brew")) == []


def test_windows_backup_restored_on_mac_uses_alternatives():
    plan = catalog.map_for_restore(["vscode", "potplayer", "vcredist_aio", "winrar", "nope"], host("macos"), mgrs("brew"))
    by = {p["from"]: p for p in plan}
    assert by["vscode"]["action"] == "install"
    assert by["potplayer"] == {"from": "potplayer", "to": "iina", "action": "alternative"}
    assert by["winrar"]["to"] == "keka"
    assert by["vcredist_aio"]["action"] == "skip"
    assert by["nope"]["reason"] == "unknown"


def test_view_marks_installed():
    info = host("linux", "ubuntu")
    v = {p["id"]: p for p in catalog.view(info, mgrs("apt"), {"apt": {"git"}})}
    assert v["git"]["status"] == "installed"
    assert v["vlc"]["status"] == "available"
    assert v["chrome"]["status"] == "needs_manager" and v["chrome"]["missing_managers"] == ["flatpak"]
    assert v["directx"]["status"] == "unsupported"


def test_view_identifies_github_apps():
    info = host("windows")
    custom = [{"id": "gh_custom", "name": "Custom", "desc": {"en": "x", "tr": "x"}, "category": "github", "custom": True, "win": [{"github": "u/r"}]}]
    v = {p["id"]: p for p in catalog.view(info, mgrs("winget"), {}, custom_apps=custom)}
    assert v["aurapdf"]["is_github"] is True
    assert v["deskflow"]["is_github"] is True
    assert v["gh_custom"]["is_github"] is True
    assert v["gh_custom"]["custom"] is True
    assert v["cpuz"]["is_github"] is False
    assert v["cpuz"]["custom"] is False


def test_apt_batches_update_and_install_in_one_command():
    from keystone.pkg.base import Source
    cmd = ALL["apt"]().install_cmd([Source("apt", "git"), Source("apt", "vlc")])
    assert cmd[:2] == ["sh", "-c"] and "apt-get update" in cmd[2] and "install -y -q git vlc" in cmd[2]
    pac = ALL["pacman"]().install_cmd([Source("pacman", "git")])
    assert pac[:2] == ["pacman", "-Syu"]


def test_github_asset_choice():
    from keystone.pkg.github import pick_asset
    names = ["app-1.0-linux-x64.tar.gz", "app-1.0-arm64-setup.exe", "app-1.0-x64-setup.exe",
             "app-1.0-x64.zip", "app-1.0-x64-setup.exe.sha256", "app-1.0-win32.exe"]
    assets = [{"name": n} for n in names]
    assert pick_asset(assets)["name"] == "app-1.0-x64-setup.exe"
    assert pick_asset(assets, "ARM64")["name"] == "app-1.0-arm64-setup.exe"
    assert pick_asset(assets, pattern=r"\.zip$")["name"] == "app-1.0-x64.zip"
    assert pick_asset([{"name": "app.deb"}]) is None
    assert pick_asset([{"name": "app-aix-ppc64.zip"}, {"name": "app-windows-386.zip"}, {"name": "app-windows-amd64.zip"}])["name"] == "app-windows-amd64.zip"


def test_github_source_needs_no_manager():
    p = {"id": "x", "win": [{"winget": "A.B"}, {"github": "a/b", "asset": "x"}]}
    assert [(s.pm, s.id, s.kind) for s in resolve(p, host("windows"), {})] == [("github", "a/b", "x")]


def test_manual_links():
    p = {"website": "https://example.com/", "win": [{"github": "a/b"}]}
    assert catalog.manual_links(p)["releases"] == "https://github.com/a/b/releases/latest"
    assert catalog.manual_links({"website": "https://github.com/c/d"})["releases"].startswith("https://github.com/c/d/")
    assert catalog.manual_links({"website": "https://example.com"})["releases"] == ""


def test_failed_download_falls_through_to_next_source(monkeypatch):
    from keystone.jobs import Job, JobManager
    from keystone.pkg import github
    from keystone.pkg.base import Source

    def boom(*a):
        raise OSError("offline")
    monkeypatch.setattr(github, "latest_asset", boom)
    jm = JobManager(host("windows"), dict, dict)
    assert jm._one(Job("install", "install", []), "x", Source("github", "a/b"), "install", "", {}) == (False, "download")


def test_silent_flag_marks_download_only_sources():
    cat = catalog.by_id()
    win = host("windows")
    flags = {pid: [s.silent() for s in resolve(cat[pid], win, mgrs("winget"))]
             for pid in ("ds4windows", "vigem_bus", "poweriso", "powerbi")}
    assert flags["ds4windows"] == [False]          # portable zip: setup file only
    assert flags["vigem_bus"] == [True]            # downloaded, then run with /quiet
    assert flags["poweriso"] == [True, True]       # winget, then direct /S setup
    assert flags["powerbi"][0] is True


def test_new_catalog_entries_are_well_formed():
    cat = catalog.by_id()
    for pid in ("riot_valorant", "riot_league", "battlenet", "windhawk", "jdk"):
        assert pid in cat and cat[pid]["win"]
    assert cat["ds4windows"]["win"][0]["url"].startswith("https://ds4-windows.com/")
    assert cat["jdk"]["website"].startswith("https://www.oracle.com/")


def test_clean_repo_name():
    from keystone.pkg.github import clean_repo_name
    assert clean_repo_name("https://github.com/rustdesk/rustdesk.git") == "rustdesk/rustdesk"
    assert clean_repo_name("https://github.com/rustdesk/rustdesk/releases") == "rustdesk/rustdesk"
    assert clean_repo_name("rustdesk/rustdesk") == "rustdesk/rustdesk"
    assert clean_repo_name("git@github.com:owner/repo.git") == "owner/repo"


def test_custom_apps_in_catalog_view_and_by_id():
    custom = [{
        "id": "gh_custom_app",
        "name": "Custom App",
        "name_tr": "Özel Uygulama",
        "category": "github",
        "desc": {"tr": "Açıklama", "en": "Description"},
        "long": {"tr": "Açıklama", "en": "Description"},
        "website": "https://github.com/custom/app",
        "custom": True,
        "win": [{"github": "custom/app", "asset": r"\.exe$", "silent": "/S"}],
    }]
    cat = catalog.by_id(custom)
    assert "gh_custom_app" in cat
    assert cat["gh_custom_app"]["custom"] is True

    views = catalog.view(host("windows"), mgrs("winget"), {}, custom_apps=custom)
    entry = next((x for x in views if x["id"] == "gh_custom_app"), None)
    assert entry is not None
    assert entry["custom"] is True
    assert entry["status"] == "available"
    assert len(entry["sources"]) == 1
    assert entry["sources"][0]["pm"] == "github"

    srcs = catalog.first_source("gh_custom_app", host("windows"), mgrs("winget"), custom_apps=custom)
    assert len(srcs) == 1
    assert srcs[0].id == "custom/app"
    assert srcs[0].silent() is True


def test_api_add_and_remove_github_app(tmp_path):
    from keystone.api import Api
    from keystone.store import Store

    store = Store(path=tmp_path / "keystone.json")
    api = Api(store=store)

    res = api.add_github_app("user/sample-tool", name="Sample Tool", desc="A sample tool",
                             category="developer", asset_pattern=r"\.exe$", silent_args="/S")
    assert res["ok"] is True
    app_id = res["app"]["id"]
    assert app_id == "gh_user_sample_tool"
    assert res["app"]["category"] == "github"

    cat = api.get_catalog()
    pkg = next(p for p in cat["packages"] if p["id"] == app_id)
    assert pkg["category"] == "github"
    assert pkg["custom"] is True
    assert "icon_url" in pkg
    assert app_id in store.active()["apps"]

    del_res = api.remove_custom_app(app_id)
    assert del_res["ok"] is True
    cat2 = api.get_catalog()
    assert not any(p["id"] == app_id for p in cat2["packages"])
    assert app_id not in store.active()["apps"]


def test_github_scrape_repo_meta(monkeypatch):
    from keystone.pkg import github

    sample_html = """
    <html itemtype="http://schema.org/Organization"><head>
    <meta name="description" content="A blazing fast system information tool. Contribute to owner/repo development by creating an account on GitHub.">
    </head><body></body></html>
    """
    class FakeResponse:
        def read(self): return sample_html.encode("utf-8")
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr(github.urllib.request, "urlopen", lambda req, timeout=10: FakeResponse())
    meta = github._scrape_repo_meta("owner/repo")
    assert meta["desc"] == "A blazing fast system information tool"
    assert meta["icon_url"] == ""  # No app icon file -> no image at all

    # When an actual icon file exists in repo contents:
    items = [{"name": "icon.png", "download_url": "https://raw.githubusercontent.com/owner/repo/HEAD/icon.png"}]
    found_icon = github.find_repo_app_icon("owner/repo", "owner", "repo", "Organization", items=items)
    assert found_icon == "https://raw.githubusercontent.com/owner/repo/HEAD/icon.png"

    # When no icon file exists in contents:
    no_icon = github.find_repo_app_icon("owner/repo", "owner", "repo", "Organization", items=[{"name": "main.py"}])
    assert no_icon == ""


def test_github_extract_readme_desc():
    from keystone.pkg.github import extract_readme_desc

    sample_md = """# My Cool App
[![Build](https://img.shields.io/badge/build-passing-green.svg)](https://example.com)

> **My Cool App** is a fast and lightweight desktop client for managing files seamlessly.

## Features
- Fast
- Secure
"""
    desc = extract_readme_desc(sample_md)
    assert desc == "My Cool App is a fast and lightweight desktop client for managing files seamlessly."


def test_github_language_resolution_rules():
    from keystone.pkg.github import resolve_localized_desc

    # 1. Both TR and EN exist, preferred lang is English
    pri, d = resolve_localized_desc("Türkçe açıklama", "English description", "", preferred_lang="en")
    assert pri == "English description"
    assert d == {"tr": "Türkçe açıklama", "en": "English description"}

    # 2. Both TR and EN exist, preferred lang is Turkish
    pri, d = resolve_localized_desc("Türkçe açıklama", "English description", "", preferred_lang="tr")
    assert pri == "Türkçe açıklama"
    assert d == {"tr": "Türkçe açıklama", "en": "English description"}

    # 3. Only single language (e.g. Spanish) exists, app is English -> still added
    pri, d = resolve_localized_desc("", "", "Descripción en español", preferred_lang="en")
    assert pri == "Descripción en español"
    assert d == {"tr": "Descripción en español", "en": "Descripción en español"}

    # 4. Only single language (e.g. Spanish) exists, app is Turkish -> still added
    pri, d = resolve_localized_desc("", "", "Descripción en español", preferred_lang="tr")
    assert pri == "Descripción en español"
    assert d == {"tr": "Descripción en español", "en": "Descripción en español"}


def test_github_section_description():
    from keystone.pkg.github import extract_section_desc

    md = """# Multilingual Project
## English
This project provides high security encryption for personal files.

## Türkçe
Bu proje kişisel dosyalarınız için yüksek güvenlikli şifreleme sağlar.
"""
    assert "encryption" in extract_section_desc(md, "en")
    assert "şifreleme" in extract_section_desc(md, "tr")



